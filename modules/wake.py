"""
modules/wake.py — Lógica de despertar impressoras em standby
Estratégias diferentes por fabricante
"""
import socket
from modules.toner import detectar_fabricante


def _despertar_udp_snmp(ip, community="public"):
    """
    Envia pacote SNMP UDP para acordar o stack de rede da impressora.
    Funciona para Brother, Ricoh e Epson que não expõem porta 9100.
    """
    try:
        from snmp_raw import _build_get_request, _build_get_v1
        OID_PING = "1.3.6.1.2.1.1.5.0"
        for build_fn in [_build_get_request, _build_get_v1]:
            try:
                pkt = build_fn(community, OID_PING)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2)
                    sock.sendto(pkt, (ip, 161))
            except Exception:
                pass
        return True
    except Exception:
        return False


def _despertar_tcp(ip, portas, payload=b"\x00"):
    """
    Tenta acordar a impressora abrindo conexão TCP nas portas informadas.
    Retorna (True, porta) se conseguiu ou (False, None).
    """
    for porta in portas:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            if s.connect_ex((ip, porta)) == 0:
                try: s.send(payload)
                except Exception: pass
                s.close()
                return True, porta
            s.close()
        except Exception:
            pass
    return False, None


def despertar_impressora(impressora):
    """
    Acorda uma impressora em standby usando a estratégia correta por fabricante.

    Samsung/genérico → TCP porta 9100 (raw print socket)
    Brother/Ricoh/Epson → UDP SNMP 161 + HTTP TCP 80/443

    Retorna dict com resultado.
    """
    ip        = impressora.get("ip", "")
    nome      = impressora.get("nome", ip)
    modelo    = impressora.get("modelo", "")
    community = impressora.get("community", "public")
    fabricante = detectar_fabricante(modelo)

    result = {"ip": ip, "nome": nome, "acordou": False, "metodo": None}

    if fabricante in ("brother", "ricoh", "epson"):
        # Acorda via SNMP UDP — não precisa de porta TCP aberta
        ok = _despertar_udp_snmp(ip, community)
        if ok:
            result["acordou"] = True
            result["metodo"]  = "UDP:SNMP"

        # Reforça com HTTP
        tcp_ok, porta = _despertar_tcp(ip, [80, 443],
                                        payload=b"GET / HTTP/1.0\r\n\r\n")
        if tcp_ok:
            result["acordou"] = True
            result["metodo"]  = f"TCP:{porta}"

    else:
        # Samsung e genéricos: porta 9100 (raw printing)
        tcp_ok, porta = _despertar_tcp(ip, [9100, 80, 631])
        if tcp_ok:
            result["acordou"] = True
            result["metodo"]  = f"TCP:{porta}"

    return result
