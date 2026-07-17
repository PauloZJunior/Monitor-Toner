"""
Testes de snmp_raw.py — a parte mais frágil do projeto, porque faz o parsing
manual de ASN.1/BER byte a byte (aritmética de offset à mão). Um erro sutil
aqui não dá erro de sintaxe nenhum — ele só faz a impressora "parecer
offline" ou devolver um valor errado, silenciosamente. Por isso vale ter
testes que não dependam de rede nem de uma impressora real.
"""
import struct

from snmp_raw import _encode_oid, _tlv, _parse_response


# ─── _encode_oid ─────────────────────────────────────────────────────────

def test_encode_oid_sys_name():
    # 1.3.6.1.2.1.1.5.0 é o OID padrão de sysName — valor bem conhecido,
    # serve de referência pra conferir se a codificação continua correta.
    assert _encode_oid("1.3.6.1.2.1.1.5.0") == bytes.fromhex("2b06010201010500")


def test_encode_oid_multi_byte_arc():
    # Testa um arco >= 128 (aqui, 9999), que exige codificação base-128
    # multi-byte com bit de continuação — é o trecho de _encode_oid mais
    # fácil de quebrar numa refatoração.
    assert _encode_oid("1.3.6.1.4.1.9999") == bytes.fromhex("2b06010401ce0f")


def test_encode_oid_supply_current():
    assert _encode_oid("1.3.6.1.2.1.43.11.1.1.9.1") == bytes.fromhex("2b060102012b0b01010901")


# ─── _parse_response ─────────────────────────────────────────────────────

def _build_fake_get_response(oid_str, value_tag, value_bytes, request_id=1, error_status=0):
    """
    Monta um pacote GetResponse SNMP válido usando as mesmas primitivas do
    próprio módulo (_tlv/_encode_oid) — só pra alimentar o parser sem
    precisar de uma impressora de verdade respondendo na rede.
    """
    oid_tlv      = _tlv(0x06, _encode_oid(oid_str))
    value_tlv    = _tlv(value_tag, value_bytes)
    varbind      = _tlv(0x30, oid_tlv + value_tlv)
    varbind_list = _tlv(0x30, varbind)
    req_id       = _tlv(0x02, struct.pack(">I", request_id).lstrip(b'\x00') or b'\x00')
    err_st       = _tlv(0x02, bytes([error_status]))
    err_idx      = _tlv(0x02, b'\x00')
    pdu          = _tlv(0xA2, req_id + err_st + err_idx + varbind_list)  # GetResponse-PDU
    version      = _tlv(0x02, b'\x01')
    comm         = _tlv(0x04, b'public')
    return _tlv(0x30, version + comm + pdu)


def test_parse_response_integer_value():
    pkt = _build_fake_get_response("1.3.6.1.2.1.43.11.1.1.9.1", 0x02, bytes([42]))
    assert _parse_response(pkt) == 42


def test_parse_response_string_value():
    pkt = _build_fake_get_response("1.3.6.1.2.1.43.11.1.1.6.1", 0x04, b"Toner Black")
    assert _parse_response(pkt) == "Toner Black"


def test_parse_response_with_error_status_returns_none():
    # error_status != 0 (ex: noSuchName) — o parser tem que desistir e
    # retornar None, não um valor lixo.
    pkt = _build_fake_get_response("1.3.6.1.2.1.1.5.0", 0x02, bytes([1]), error_status=2)
    assert _parse_response(pkt) is None


def test_parse_response_no_such_object():
    pkt = _build_fake_get_response("1.3.6.1.2.1.1.5.0", 0x80, b"")
    assert _parse_response(pkt) == "noSuchObject"


def test_parse_response_large_integer_value():
    # Testa um valor que ocupa mais de 1 byte (ex: contador de páginas),
    # pra garantir que o int.from_bytes cobre isso corretamente.
    valor = 70000  # não cabe em 2 bytes
    pkt = _build_fake_get_response(
        "1.3.6.1.2.1.43.11.1.1.9.1", 0x02, valor.to_bytes(3, "big")
    )
    assert _parse_response(pkt) == valor


def test_parse_response_garbage_data_does_not_crash():
    # Dado corrompido/incompleto não pode derrubar o processo — só retornar
    # None (é isso que o try/except em volta de _parse_response garante).
    assert _parse_response(b"\x00\x01\x02") is None
    assert _parse_response(b"") is None
