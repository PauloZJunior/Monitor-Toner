"""
modules/toner.py — Leitura de nível de toner/tinta por fabricante
Cada função retorna (percentual, nota) ou (None, None)
"""
from snmp_raw import snmp_get, snmp_get_int, snmp_get_str
from config import (
    SNMP_TIMEOUT, IGNORE_WORDS, COR_TINTA,
    OID_SUPPLY_DESC, OID_SUPPLY_MAX, OID_SUPPLY_CURR,
    OID_BROTHER_TONER_PCT, OID_BROTHER_TONER_STS, OID_BROTHER_TONER_ALT,
    OID_RICOH_TONER_CURR, OID_RICOH_TONER_MAX,
    OID_RICOH_TONER_CURR2, OID_RICOH_TONER_MAX2,
    OID_EPSON_INK_CURR, OID_EPSON_INK_MAX,
)

T = SNMP_TIMEOUT


def cor_por_pct(pct):
    """Retorna a chave de cor baseada no percentual."""
    if pct <= 10:  return "critico"
    if pct <= 25:  return "baixo"
    if pct <= 50:  return "medio"
    return "ok"


def detectar_fabricante(modelo):
    """Detecta fabricante pelo campo modelo cadastrado."""
    m = (modelo or "").lower()
    if "brother" in m: return "brother"
    if "ricoh"   in m: return "ricoh"
    if "epson"   in m: return "epson"
    return "padrao"


# ─── SAMSUNG / PADRÃO ────────────────────────────────
def ler_toner_padrao(ip, community):
    """
    Lê toner via Printer MIB padrão (RFC 3805).
    Funciona para Samsung e maioria dos modelos genéricos.
    Retorna (pct, curr, max) ou (None, None, None).
    """
    for idx in range(1, 11):
        desc = snmp_get_str(ip, community, f"{OID_SUPPLY_DESC}.{idx}", timeout=T) or ""
        if any(x in desc.lower() for x in IGNORE_WORDS):
            continue

        mx  = snmp_get_int(ip, community, f"{OID_SUPPLY_MAX}.{idx}",  timeout=T)
        cur = snmp_get_int(ip, community, f"{OID_SUPPLY_CURR}.{idx}", timeout=T)

        # Sentinelas RFC 3805
        if cur == -1: return 100, None, None        # ilimitado
        if cur in (-2, -3): continue                # desconhecido/algum restante

        if mx and mx > 0 and cur is not None and cur >= 0:
            return min(100, round(cur / mx * 100)), cur, mx

    return None, None, None


# ─── BROTHER ─────────────────────────────────────────
def ler_toner_brother(ip, community):
    """
    Lê toner via OIDs proprietários Brother.
    Suporta modelos novos (retornam % direto) e antigos (NC-8200h).
    Retorna (pct, nota) ou (None, None).
    """
    # Modelos novos: OID retorna inteiro 0-100 diretamente
    for oid in [OID_BROTHER_TONER_PCT, OID_BROTHER_TONER_ALT]:
        val = snmp_get_int(ip, community, oid, timeout=T)
        if val is not None and 0 <= val <= 100:
            return val, None

    # Modelos antigos (NC-8200h): OID retorna bytes binários
    raw = snmp_get(ip, community, OID_BROTHER_TONER_PCT, timeout=T)
    if isinstance(raw, (bytes, bytearray)) and len(raw) >= 2:
        try:
            val_2b = int.from_bytes(raw[:2], 'big')
            if 5 <= val_2b <= 100:
                return val_2b, "estimado"
        except Exception:
            pass

    # Fallback: Printer MIB com sentinelas
    hit_sentinel = False
    for idx in range(1, 5):
        desc = snmp_get_str(ip, community, f"{OID_SUPPLY_DESC}.{idx}", timeout=T) or ""
        if any(x in desc.lower() for x in IGNORE_WORDS):
            continue
        cur = snmp_get_int(ip, community, f"{OID_SUPPLY_CURR}.{idx}", timeout=T)
        mx  = snmp_get_int(ip, community, f"{OID_SUPPLY_MAX}.{idx}",  timeout=T)
        if cur == -1: return 100, None
        if cur in (-2, -3):
            hit_sentinel = True  # sabe que há toner mas não sabe quanto
            continue
        if cur is not None and mx and mx > 0 and cur >= 0:
            return min(100, round(cur / mx * 100)), None

    # Modelo reporta sentinela (-3 = "algum restante") — usa status numérico como estimativa
    # Isso cobre o Brother DCP-7065DN / NC-8200h firmware
    sts = snmp_get_int(ip, community, OID_BROTHER_TONER_STS, timeout=T)
    if sts is not None and isinstance(sts, int):
        # Status Brother: 0=OK, 1=OK, 2=baixo, 3=muito baixo, 4=vazio, 5=erro
        mapa = {0: 80, 1: 80, 2: 30, 3: 15, 4: 5, 5: 5}
        val = mapa.get(sts)
        if val is not None:
            return val, "estimado"

    # Se chegou aqui via sentinela e não achou status: retorna estimativa conservadora
    # (melhor que mostrar "Nível não disponível" para um modelo que claramente tem SNMP)
    if hit_sentinel:
        return 50, "estimado"  # estimativa: metade — não sabemos o real

    return None, None


# ─── RICOH ───────────────────────────────────────────
def ler_toner_ricoh(ip, community):
    """
    Lê toner via OIDs proprietários Ricoh SP.
    OID principal retorna percentual direto (confirmado no SP 3710SF).
    Retorna (pct, nota) ou (None, None).
    """
    # SP 3710SF e similares: retorna % direto
    oids_diretos = [
        "1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.1",
        "1.3.6.1.4.1.367.3.2.1.2.19.1.1.5.1",
    ]
    for oid in oids_diretos:
        val = snmp_get_int(ip, community, oid, timeout=T)
        if val is not None and 0 <= val <= 100:
            return val, None

    # Fallback: pares curr/max para modelos mais antigos
    pares = [
        (OID_RICOH_TONER_CURR,  OID_RICOH_TONER_MAX),
        (OID_RICOH_TONER_CURR2, OID_RICOH_TONER_MAX2),
    ]
    for curr_oid, max_oid in pares:
        cur = snmp_get_int(ip, community, curr_oid, timeout=T)
        mx  = snmp_get_int(ip, community, max_oid,  timeout=T)
        if cur == -1: return 100, None
        if cur in (-2, -3, None): continue
        if mx and mx > 0 and cur >= 0:
            return min(100, round(cur / mx * 100)), None

    return None, None


# ─── EPSON ───────────────────────────────────────────
def _identificar_cor(descricao):
    """Mapeia descrição SNMP para chave de cor."""
    d = (descricao or "").lower().strip()
    for key in ["black", "cyan", "magenta", "yellow"]:
        if key in d: return key
    abrev = {"k":"black","bk":"black","blk":"black","c":"cyan","cy":"cyan",
             "m":"magenta","mg":"magenta","y":"yellow","yl":"yellow"}
    return abrev.get(d, d or "unknown")


def ler_toner_epson(ip, community):
    """
    Lê níveis de tinta Epson com suporte a múltiplas cores.
    Retorna lista de dicts [{cor, label, hex, pct}] ou None.
    """
    tintas = []

    # OIDs proprietários Epson
    #for idx in range(1, 8):
    #    cur = snmp_get_int(ip, community, f"{OID_EPSON_INK_CURR}.{idx}", timeout=T)
    #    mx  = snmp_get_int(ip, community, f"{OID_EPSON_INK_MAX}.{idx}",  timeout=T)
    #    if cur is not None and mx and mx > 0:
    #        tintas.append({"idx": idx, "pct": min(100, round(cur/mx*100)), "source": "epson"})

    # WF-L6490 funciona pela Printer-MIB padrão
    tintas = []

    for idx in range(1, 10):
        desc = snmp_get_str(
            ip,
            community,
            f"{OID_SUPPLY_DESC}.{idx}",
            timeout=T
        ) or ""

        if any(
            x in desc.lower()
            for x in [
                "drum",
                "cilindro",
                "fus",
                "maintenance",
                "waste",
                "caixa",
                "manut"
            ]
        ):
            continue

        mx = snmp_get_int(
            ip,
            community,
            f"{OID_SUPPLY_MAX}.{idx}",
            timeout=T
        )

        cur = snmp_get_int(
            ip,
            community,
            f"{OID_SUPPLY_CURR}.{idx}",
            timeout=T
        )

        if mx and cur is not None and mx > 0 and cur >= 0:
            tintas.append({
                "idx": idx,
                "pct": min(100, round(cur / mx * 100)),
                "desc": desc,
                "source": "padrao"
            })

    # Fallback: Printer MIB padrão
    if not tintas:
        for idx in range(1, 10):
            desc = snmp_get_str(ip, community, f"{OID_SUPPLY_DESC}.{idx}", timeout=T) or ""
            if any(x in desc.lower() for x in ["drum","cilindro","fus","maintenance","waste","caixa","manut"]):
                continue
            mx  = snmp_get_int(ip, community, f"{OID_SUPPLY_MAX}.{idx}",  timeout=T)
            if max is None:
                mx  = snmp_get_int(ip, community, f"{OID_SUPPLY_MAX}.{idx}",  timeout=T)
            cur = snmp_get_int(ip, community, f"{OID_SUPPLY_CURR}.{idx}", timeout=T)
            if cur is None:
                cur = snmp_get_int(ip, community, f"{OID_SUPPLY_CURR}.{idx}", timeout=T)
            if mx and cur is not None and mx > 0 and cur >= 0:
                tintas.append({"idx": idx, "pct": min(100, round(cur/mx*100)), "desc": desc, "source": "padrao"})

    if not tintas:
        return None

    # Enriquece com nome/cor
    resultado = []
    for t in tintas:
        if "desc" not in t:
            t["desc"] = snmp_get_str(ip, community, f"{OID_SUPPLY_DESC}.{t['idx']}", timeout=T) or ""
        cor  = _identificar_cor(t["desc"])
        info = COR_TINTA.get(cor, {"label": t["desc"] or f"Tinta {t['idx']}", "hex": "#888888"})
        resultado.append({"cor": cor, "label": info["label"], "hex": info["hex"], "pct": t["pct"]})

    # Ordena: Preto → Ciano → Magenta → Amarelo
    ordem = {"black":0,"k":0,"cyan":1,"c":1,"magenta":2,"m":2,"yellow":3,"y":3}
    resultado.sort(key=lambda x: ordem.get(x["cor"], 9))
    return resultado
