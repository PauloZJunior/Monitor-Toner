"""
routes/api.py — Endpoints de monitoramento
Inclui: leitura de toner, tempo de resposta, histórico, notificações, despertar, exportar
"""
import io, csv, time
from flask import Blueprint, jsonify, Response, request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from database import listar_impressoras, buscar_por_ip
from snmp_raw import snmp_get, snmp_get_str, snmp_get_int
from modules.toner import (
    detectar_fabricante, cor_por_pct,
    ler_toner_padrao, ler_toner_brother,
    ler_toner_ricoh, ler_toner_epson,
)
from modules.wake import despertar_impressora
from modules.historico import registrar_leitura, obter_historico_card
from modules.notificacao import processar_notificacoes
from config import OID_SYS_NAME, OID_SERIAL, OID_MAC, SNMP_MAX_WORKERS

import socket as _sock

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _formatar_mac(raw):
    try:
        if isinstance(raw, bytes) and len(raw) == 6:
            return ":".join(f"{b:02X}" for b in raw)
        if isinstance(raw, str) and raw:
            clean = raw.replace(":","").replace("-","").replace(" ","")
            if len(clean) == 12:
                return ":".join(clean[i:i+2].upper() for i in range(0,12,2))
    except Exception:
        pass
    return None


def _testar_tcp(ip, portas=(9100, 515, 631, 80, 443, 8080), timeout=2):
    """
    Testa conectividade da impressora de etiqueta.
    1. Tenta TCP nas portas comuns de impressão
    2. Fallback: ICMP ping via socket raw (se nenhuma porta TCP responder)
    """
    # Tentativa TCP
    for porta in portas:
        try:
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, porta)) == 0:
                s.close()
                return True
            s.close()
        except Exception:
            pass

    # Fallback: ICMP ping via socket UDP (se não tiver portas TCP abertas)
    # Zebra e algumas Argox não expõem portas TCP mas respondem a ping
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.settimeout(timeout)
        # Envia pacote UDP para porta fechada — se o host existir, recebe ICMP port unreachable
        # Se host não existir, não recebe nada (timeout)
        s.sendto(b"\x00", (ip, 9))  # porta 9 = discard
        try:
            s.recvfrom(1024)
        except _sock.timeout:
            # Timeout = nenhuma resposta = offline
            s.close()
            return False
        except Exception:
            # Qualquer outra exceção (ICMP unreachable, etc.) = host existe = online
            s.close()
            return True
        s.close()
        return True
    except Exception:
        pass

    # Último recurso: SNMP UDP (porta 161) — muitas impressoras de etiqueta têm SNMP
    try:
        from snmp_raw import snmp_get_str
        from config import OID_SYS_NAME
        community = "public"
        val = snmp_get_str(ip, community, OID_SYS_NAME, timeout=timeout)
        if val and val not in ("noSuchObject", "noSuchInstance", ""):
            return True
    except Exception:
        pass

    return False


def _consultar_impressora(impressora):
    ip        = impressora.get("ip","")
    community = impressora.get("community","public")
    modelo    = impressora.get("modelo","")
    tipo      = impressora.get("tipo","toner") or "toner"
    imp_id    = impressora.get("id")

    resultado = {
        "id":        imp_id,
        "nome":      impressora.get("nome", ip),
        "ip":        ip,
        "modelo":    modelo,
        "tipo":      tipo,
        "setor":     impressora.get("setor",""),
        "empresa":   impressora.get("empresa",""),
        "serial":    impressora.get("serial") or None,
        "mac":       impressora.get("mac") or None,
        "status":    "offline",
        "percentual": None,
        "nivel": None, "nivel_max": None,
        "tintas": None,
        "cor_status": "offline",
        "tempo_resposta": None,
        "sparkline": [],
        "ultima_atualizacao": datetime.now().strftime("%H:%M:%S"),
    }

    t_inicio = time.monotonic()

    # ── Etiqueta: verifica apenas TCP ────────────────
    if tipo == "etiqueta":
        online = _testar_tcp(ip)
        t_ms = round((time.monotonic() - t_inicio) * 1000)
        if online:
            resultado["status"]         = "online"
            resultado["cor_status"]     = "ok"
            resultado["tempo_resposta"] = t_ms
        try:
            registrar_leitura(imp_id, None, resultado["status"], t_ms)
            resultado["sparkline"] = obter_historico_card(imp_id)
        except Exception:
            resultado["sparkline"] = []
        return resultado

    # ── Toner/Tinta: via SNMP ─────────────────────────
    try:
        sys_name = snmp_get_str(ip, community, OID_SYS_NAME, timeout=2)
        t_ms = round((time.monotonic() - t_inicio) * 1000)
        resultado["tempo_resposta"] = t_ms

        if not sys_name or sys_name in ("noSuchObject","noSuchInstance",""):
            registrar_leitura(imp_id, None, "offline", t_ms)
            resultado["sparkline"] = obter_historico_card(imp_id)
            return resultado

        resultado["status"] = "online"

        if not resultado["serial"]:
            s = snmp_get_str(ip, community, OID_SERIAL, timeout=2)
            if s and s not in ("noSuchObject","noSuchInstance",""):
                resultado["serial"] = s.strip()

        if not resultado["mac"]:
            resultado["mac"] = _formatar_mac(snmp_get(ip, community, OID_MAC, timeout=2))

        fabricante = detectar_fabricante(modelo)

        if fabricante == "epson":
            tintas = ler_toner_epson(ip, community)
            if tintas:
                resultado["tintas"]     = tintas
                resultado["percentual"] = min(t["pct"] for t in tintas)
                resultado["cor_status"] = cor_por_pct(resultado["percentual"])
                resultado["tipo_display"] = "tinta"
            else:
                resultado["cor_status"] = "sem_dados"

        elif fabricante == "brother":
            pct, nota = ler_toner_brother(ip, community)
            if pct is not None and nota != "nd":
                resultado["percentual"] = pct
                resultado["cor_status"] = cor_por_pct(pct)
            else:
                resultado["cor_status"] = "sem_dados"

        elif fabricante == "ricoh":
            pct, _ = ler_toner_ricoh(ip, community)
            if pct is None:
                pct, cur, mx = ler_toner_padrao(ip, community)
                resultado["nivel"] = cur; resultado["nivel_max"] = mx
            if pct is not None:
                resultado["percentual"] = pct
                resultado["cor_status"] = cor_por_pct(pct)
            else:
                resultado["cor_status"] = "sem_dados"

        else:
            pct, cur, mx = ler_toner_padrao(ip, community)
            if pct is None: pct, _ = ler_toner_ricoh(ip, community)
            if pct is None: pct, _ = ler_toner_brother(ip, community)
            if pct is not None:
                resultado["percentual"] = pct
                resultado["nivel"] = cur; resultado["nivel_max"] = mx
                resultado["cor_status"] = cor_por_pct(pct)
            else:
                resultado["cor_status"] = "sem_dados"

        # Salva histórico (nunca deve derrubar a requisição principal)
        try:
            registrar_leitura(imp_id, resultado["percentual"], resultado["status"], t_ms)
            resultado["sparkline"] = obter_historico_card(imp_id)
        except Exception:
            resultado["sparkline"] = []

        # Notificações (nunca deve derrubar a requisição principal)
        try:
            if resultado["percentual"] is not None:
                processar_notificacoes(resultado, resultado["percentual"])
        except Exception:
            pass

    except Exception as e:
        resultado["erro"] = str(e)
        try:
            registrar_leitura(imp_id, None, "offline", None)
        except Exception:
            pass

    return resultado


def _consultar_todas(impressoras):
    resultados = []
    with ThreadPoolExecutor(max_workers=SNMP_MAX_WORKERS) as ex:
        futures = {ex.submit(_consultar_impressora, imp): imp for imp in impressoras}
        for f in as_completed(futures):
            try:
                resultados.append(f.result())
            except Exception:
                imp = futures[f]
                resultados.append({
                    "id": imp.get("id"), "nome": imp.get("nome", imp.get("ip")),
                    "ip": imp.get("ip"), "modelo": imp.get("modelo",""),
                    "tipo": imp.get("tipo","toner"),
                    "setor": imp.get("setor",""), "empresa": imp.get("empresa",""),
                    "status":"offline","percentual":None,"cor_status":"offline",
                    "tempo_resposta":None, "sparkline":[],
                })
    ordem = {"critico":0,"baixo":1,"medio":2,"ok":3,"sem_dados":4,"offline":5}
    resultados.sort(key=lambda x: (
        ordem.get(x["cor_status"],9), x.get("empresa",""), x.get("setor",""), x.get("nome","")
    ))
    return resultados


# ── ROTAS ─────────────────────────────────────────────

@api_bp.route("/debug")
def debug():
    """
    Endpoint de diagnóstico — acessível apenas a partir do próprio servidor.
    Retorna 403 para acessos externos.
    """
    import sys
    allowed = {"127.0.0.1", "::1", "localhost"}
    client_ip = request.remote_addr or ""
    if client_ip not in allowed:
        return jsonify({"erro": "Acesso negado"}), 403

    resultado = {"status": "ok", "python": sys.version,
                 "db_ok": False, "impressoras_count": 0, "erros": []}
    try:
        from database import listar_impressoras
        imps = listar_impressoras(apenas_ativas=False)
        resultado["db_ok"] = True
        resultado["impressoras_count"] = len(imps)
    except Exception as e:
        resultado["erros"].append(f"DB: {e}")
    return jsonify(resultado)

@api_bp.route("/impressoras")
def get_impressoras():
    try:
        impressoras = listar_impressoras(apenas_ativas=True)
    except Exception as e:
        return jsonify({"erro": f"Erro ao ler banco de dados: {e}", "impressoras": [], "resumo": {}}), 500

    try:
        dados = _consultar_todas(impressoras)
    except Exception as e:
        return jsonify({"erro": f"Erro ao consultar impressoras: {e}", "impressoras": [], "resumo": {}}), 500

    online  = [d for d in dados if d["status"]=="online"]
    t_vals  = [d["tempo_resposta"] for d in online if d.get("tempo_resposta")]
    t_medio = round(sum(t_vals) / len(t_vals)) if t_vals else 0

    return jsonify({
        "impressoras": dados,
        "resumo": {
            "total":          len(dados),
            "online":         len(online),
            "criticas":       sum(1 for d in dados if d["cor_status"]=="critico"),
            "baixas":         sum(1 for d in dados if d["cor_status"]=="baixo"),
            "offline":        sum(1 for d in dados if d["status"]=="offline"),
            "tempo_medio_ms": t_medio,
        },
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    })


@api_bp.route("/impressoras/<ip>/status")
def get_status_impressora(ip):
    imp = buscar_por_ip(ip)
    if not imp:
        return jsonify({"erro":"Não encontrada"}), 404
    return jsonify(_consultar_impressora(imp))


@api_bp.route("/despertar", methods=["POST"])
def despertar_todas():
    impressoras = listar_impressoras(apenas_ativas=True)
    resultados  = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(despertar_impressora, imp): imp for imp in impressoras}
        for f in as_completed(futures):
            try: resultados.append(f.result())
            except:
                imp = futures[f]
                resultados.append({"ip":imp.get("ip"),"nome":imp.get("nome",""),"acordou":False})
    acordaram = sum(1 for r in resultados if r["acordou"])
    return jsonify({"total":len(resultados),"acordaram":acordaram,
                    "falhas":len(resultados)-acordaram,"detalhes":resultados})


@api_bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta status das impressoras em CSV.
    Usa os dados da última consulta (cache) para evitar SNMP scan completo.
    Se não houver dados em cache, faz a consulta.
    """
    from database import buscar_historico_resumido
    impressoras = listar_impressoras(apenas_ativas=True)
    # Monta dados rápidos do banco (último registro histórico) sem SNMP
    dados = []
    for imp in impressoras:
        hist = buscar_historico_resumido(imp["id"], limite=1)
        pct  = hist[0]["percentual"] if hist else None
        print("HIST DEBUG:", hist)
        st   = hist[0].get("status", "desconhecido") if hist else "desconhecido"
        dados.append({**imp, "percentual": pct, "status": st,
                      "cor_status": cor_por_pct(pct) if pct is not None else "desconhecido"})
    dados.sort(key=lambda x: (x.get("empresa",""), x.get("setor",""), x.get("nome","")))

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Nome","IP","Modelo","Tipo","Setor","Empresa",
                     "Status","Toner (%)","Tempo Resp. (ms)","Últ. Atualização"])
    for d in dados:
        writer.writerow([
            d.get("nome",""), d.get("ip",""), d.get("modelo",""),
            d.get("tipo","toner"), d.get("setor",""), d.get("empresa",""),
            d.get("status",""), d.get("percentual",""),
            d.get("tempo_resposta",""),
            d.get("ultima_atualizacao",""),
        ])

    nome_arquivo = f"monitor_toner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        "\ufeff" + output.getvalue(),  # BOM para Excel abrir com acentos
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )
