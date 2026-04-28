"""
SNMP v1/v2c GET e WALK via UDP puro — sem dependencias externas
"""
import socket
import struct


def _encode_oid(oid_str):
    parts = [int(x) for x in oid_str.strip(".").split(".")]
    # Primeiro byte: 40 * parts[0] + parts[1]
    encoded = [40 * parts[0] + parts[1]]
    for val in parts[2:]:
        if val == 0:
            encoded.append(0)
        else:
            buf = []
            while val > 0:
                buf.append(val & 0x7F)
                val >>= 7
            buf.reverse()
            for i, b in enumerate(buf):
                encoded.append(b | (0x80 if i < len(buf) - 1 else 0))
    return bytes(encoded)


def _tlv(tag, value):
    length = len(value)
    if length < 128:
        return bytes([tag, length]) + value
    elif length < 256:
        return bytes([tag, 0x81, length]) + value
    else:
        return bytes([tag, 0x82, (length >> 8) & 0xFF, length & 0xFF]) + value


def _build_get_request(community, oid_str, request_id=1):
    community_bytes = community.encode()
    oid_encoded     = _encode_oid(oid_str)
    oid_tlv         = _tlv(0x06, oid_encoded)
    # VarBind: SEQUENCE { OID, NULL }
    varbind         = _tlv(0x30, oid_tlv + b'\x05\x00')
    # VarBindList
    varbind_list    = _tlv(0x30, varbind)
    # PDU fields: request-id, error-status, error-index
    req_id  = _tlv(0x02, struct.pack(">I", request_id).lstrip(b'\x00') or b'\x00')
    err_st  = _tlv(0x02, b'\x00')
    err_idx = _tlv(0x02, b'\x00')
    # GetRequest-PDU (tag A0)
    pdu = _tlv(0xA0, req_id + err_st + err_idx + varbind_list)
    # SNMP message: version (v2c=1), community, PDU
    version = _tlv(0x02, b'\x01')  # v2c
    comm    = _tlv(0x04, community_bytes)
    message = _tlv(0x30, version + comm + pdu)
    return message


def _decode_value(data, offset):
    tag    = data[offset]; offset += 1
    length = data[offset]; offset += 1
    if length & 0x80:
        n      = length & 0x7F
        length = int.from_bytes(data[offset:offset+n], 'big')
        offset += n
    value = data[offset:offset+length]
    offset += length

    if tag == 0x02:   # INTEGER
        return int.from_bytes(value, 'big', signed=True), offset
    elif tag == 0x04: # OCTET STRING
        try:
            decoded = value.decode('utf-8', errors='replace').strip('\x00').strip()
            non_print = sum(1 for c in decoded if ord(c) < 32 or ord(c) == 0xFFFD)
            if len(decoded) > 0 and non_print / len(decoded) > 0.3:
                return value, offset  # bytes brutos para parsing pelo chamador
            return decoded, offset
        except Exception:
            return value, offset
    elif tag == 0x06: # OID — skip, retorna None
        return None, offset
    elif tag == 0x05: # NULL
        return None, offset
    elif tag in (0x41, 0x42, 0x43, 0x47): # Counter/Gauge/TimeTicks
        return int.from_bytes(value, 'big'), offset
    elif tag == 0x80: # noSuchObject
        return "noSuchObject", offset
    elif tag == 0x81: # noSuchInstance
        return "noSuchInstance", offset
    else:
        try:
            return value.decode('utf-8', errors='replace').strip(), offset
        except Exception:
            return value.hex(), offset


def _parse_response(data):
    """Extrai o valor do primeiro VarBind da resposta SNMP"""
    try:
        offset = 2  # skip outer SEQUENCE tag+length (simplificado)
        # Pula comprimento (pode ser multi-byte)
        if data[1] & 0x80:
            offset += data[1] & 0x7F

        # Version
        offset += 2 + data[offset+1]
        # Community
        offset += 2 + data[offset+1]

        # PDU (GetResponse = 0xA2)
        pdu_tag = data[offset]; offset += 1
        pdu_len = data[offset]; offset += 1
        if pdu_len & 0x80:
            n = pdu_len & 0x7F
            offset += n

        # Request-ID, Error-status, Error-index
        offset += 2 + data[offset+1]  # request-id
        err_status = data[offset+2]
        offset += 2 + data[offset+1]  # error-status
        offset += 2 + data[offset+1]  # error-index

        if err_status != 0:
            return None

        # VarBindList SEQUENCE
        offset += 2  # tag + length
        if data[offset-1] & 0x80:
            offset += data[offset-2] & 0x7F

        # VarBind SEQUENCE
        offset += 2
        if data[offset-1] & 0x80:
            offset += data[offset-2] & 0x7F

        # OID (skip)
        oid_len = data[offset+1]; offset += 2 + oid_len

        # Valor
        val, _ = _decode_value(data, offset)
        return val
    except Exception:
        return None


# Cache de versão SNMP por IP — evita tentar ambas as versões toda consulta
# { "192.168.1.1": 0 }  →  0=v1, 1=v2c
# Limitado a 500 entradas para evitar crescimento ilimitado de memória
_snmp_version_cache: dict = {}
_CACHE_MAX = 500


def _build_get_v1(community, oid_str, request_id=1):
    """Constrói pacote SNMPv1 (version=0)"""
    community_bytes = community.encode()
    oid_encoded     = _encode_oid(oid_str)
    oid_tlv         = _tlv(0x06, oid_encoded)
    varbind         = _tlv(0x30, oid_tlv + b'\x05\x00')
    varbind_list    = _tlv(0x30, varbind)
    req_id  = _tlv(0x02, struct.pack(">I", request_id).lstrip(b'\x00') or b'\x00')
    err_st  = _tlv(0x02, b'\x00')
    err_idx = _tlv(0x02, b'\x00')
    pdu     = _tlv(0xA0, req_id + err_st + err_idx + varbind_list)
    version = _tlv(0x02, b'\x00')  # SNMPv1
    comm    = _tlv(0x04, community_bytes)
    return  _tlv(0x30, version + comm + pdu)


def _send_snmp(ip, packet, timeout, port):
    """Envia pacote UDP e retorna resposta parseada ou None."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, (ip, port))
        response, _ = sock.recvfrom(4096)
        sock.close()
        return _parse_response(response)
    except Exception:
        return None


def snmp_get(ip, community, oid, timeout=2, port=161):
    """
    Faz SNMP GET via UDP puro.
    Na primeira consulta a um IP, testa v2c e v1 e memoriza qual funciona.
    Nas consultas seguintes usa direto a versão que já funcionou — sem overhead.
    """
    cached = _snmp_version_cache.get(ip)

    if cached == 1:
        # Já sabemos que este IP usa v2c
        return _send_snmp(ip, _build_get_request(community, oid), timeout, port)

    if cached == 0:
        # Já sabemos que este IP usa v1
        return _send_snmp(ip, _build_get_v1(community, oid), timeout, port)

    # Primeira vez — descobre qual versão funciona (timeout reduzido para ser rápido)
    pkt_v2c = _build_get_request(community, oid)
    val = _send_snmp(ip, pkt_v2c, timeout, port)
    if val is not None:
        if len(_snmp_version_cache) >= _CACHE_MAX:
            # Remove entrada mais antiga para liberar espaço
            _snmp_version_cache.pop(next(iter(_snmp_version_cache)))
        _snmp_version_cache[ip] = 1  # memoriza: este IP usa v2c
        return val

    pkt_v1 = _build_get_v1(community, oid)
    val = _send_snmp(ip, pkt_v1, timeout, port)
    if val is not None:
        if len(_snmp_version_cache) >= _CACHE_MAX:
            _snmp_version_cache.pop(next(iter(_snmp_version_cache)))
        _snmp_version_cache[ip] = 0  # memoriza: este IP usa v1
    return val


def snmp_get_int(ip, community, oid, timeout=3):
    val = snmp_get(ip, community, oid, timeout)
    if val is None: return None
    try: return int(val)
    except: return None


def snmp_get_str(ip, community, oid, timeout=3):
    val = snmp_get(ip, community, oid, timeout)
    if val is None: return None
    return str(val).strip()
