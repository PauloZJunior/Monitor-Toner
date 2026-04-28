"""
modules/notificacao.py — Envio de notificações (e-mail e webhook)
Suporta: SMTP, Microsoft Teams, Slack, webhook genérico
"""
import smtplib
import json
import base64
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import (
    get_config_notificacao, alerta_ja_enviado,
    registrar_alerta_enviado, limpar_alertas_resolvidos,
)


def _obfuscar_senha(senha: str, key: str = "monitor-toner") -> str:
    """Ofusca senha com XOR + base64 antes de salvar no banco."""
    if not senha:
        return ""
    key_bytes  = (key * (len(senha) // len(key) + 1)).encode()[:len(senha)]
    xored      = bytes(a ^ b for a, b in zip(senha.encode(), key_bytes))
    return base64.b64encode(xored).decode()


def _deobfuscar_senha(token: str, key: str = "monitor-toner") -> str:
    """Reverte a ofuscação da senha."""
    if not token:
        return ""
    try:
        xored      = base64.b64decode(token.encode())
        key_bytes  = (key * (len(xored) // len(key) + 1)).encode()[:len(xored)]
        return bytes(a ^ b for a, b in zip(xored, key_bytes)).decode()
    except Exception:
        return token  # se falhar, retorna como está (senha antiga sem ofuscação)

NIVEL_EMOJI = {
    "critico": "🔴",
    "baixo":   "🟠",
    "medio":   "🟡",
}
NIVEL_LABEL = {
    "critico": "CRÍTICO",
    "baixo":   "BAIXO",
    "medio":   "MÉDIO",
}


def _montar_mensagem(impressora, percentual):
    """Monta texto da notificação."""
    emoji = NIVEL_EMOJI.get(impressora.get("cor_status",""), "⚠️")
    nivel = NIVEL_LABEL.get(impressora.get("cor_status",""), "ALERTA")
    nome  = impressora.get("nome","")
    ip    = impressora.get("ip","")
    setor = impressora.get("setor","") or ""
    modelo= impressora.get("modelo","") or ""
    pct   = f"{percentual}%" if percentual is not None else "desconhecido"

    titulo  = f"{emoji} Toner {nivel} — {nome}"
    detalhe = (
        f"Impressora: {nome}\n"
        f"IP: {ip}\n"
        f"Modelo: {modelo}\n"
        f"Setor: {setor}\n"
        f"Nível de toner: {pct}\n"
        f"Status: {nivel}"
    )
    return titulo, detalhe


def _enviar_email(cfg, titulo, detalhe, impressora, percentual):
    """Envia notificação por e-mail via SMTP."""
    destinos_raw = cfg.get("email_destinos","").strip()
    if not destinos_raw:
        return False, "Nenhum destinatário configurado"

    destinos = [d.strip() for d in destinos_raw.replace(";",",").split(",") if d.strip()]
    usuario  = cfg.get("email_usuario","").strip()
    senha    = cfg.get("email_senha","").strip()
    smtp     = cfg.get("email_smtp","").strip()
    porta    = int(cfg.get("email_porta", 587))
    usar_tls = cfg.get("email_tls","1") == "1"

    if not smtp or not usuario or not senha:
        return False, "Configurações SMTP incompletas"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = titulo
        msg["From"]    = usuario
        msg["To"]      = ", ".join(destinos)

        # Parte texto
        texto = detalhe
        # Parte HTML
        pct_val  = impressora.get("percentual", 0) or 0
        cor_barra = "#ff2d55" if pct_val <= 10 else "#ff8c00" if pct_val <= 25 else "#f0c040"
        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
          <div style="background:#0f1217;padding:1.2rem 1.5rem;border-radius:8px 8px 0 0">
            <h2 style="color:#fff;margin:0;font-size:1.1rem">{titulo}</h2>
          </div>
          <div style="background:#f5f7fa;padding:1.2rem 1.5rem;border-radius:0 0 8px 8px;border:1px solid #dde">
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:.4rem 0;color:#555;width:40%">Impressora</td><td style="font-weight:600">{impressora.get('nome','')}</td></tr>
              <tr><td style="padding:.4rem 0;color:#555">IP</td><td style="font-family:monospace">{impressora.get('ip','')}</td></tr>
              <tr><td style="padding:.4rem 0;color:#555">Modelo</td><td>{impressora.get('modelo','') or '—'}</td></tr>
              <tr><td style="padding:.4rem 0;color:#555">Setor</td><td>{impressora.get('setor','') or '—'}</td></tr>
              <tr><td style="padding:.4rem 0;color:#555">Nível</td>
                  <td><div style="background:#ddd;border-radius:4px;height:12px;width:100%;margin-top:4px">
                    <div style="background:{cor_barra};width:{pct_val}%;height:100%;border-radius:4px"></div>
                  </div><span style="font-size:.85rem;color:{cor_barra};font-weight:700">{pct_val}%</span></td></tr>
            </table>
          </div>
          <p style="font-size:.75rem;color:#aaa;margin-top:.5rem;text-align:center">Monitor de Toner</p>
        </div>"""

        msg.attach(MIMEText(texto, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if usar_tls:
            server = smtplib.SMTP(smtp, porta, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp, porta, timeout=10)

        senha_real = _deobfuscar_senha(senha)
        server.login(usuario, senha_real)
        server.sendmail(usuario, destinos, msg.as_string())
        server.quit()
        return True, f"E-mail enviado para {len(destinos)} destinatário(s)"

    except Exception as e:
        return False, str(e)


def _enviar_webhook(cfg, titulo, detalhe, impressora, percentual):
    """Envia notificação via webhook (Teams, Slack ou genérico)."""
    url  = cfg.get("webhook_url","").strip()
    tipo = cfg.get("webhook_tipo","generic")

    if not url:
        return False, "URL do webhook não configurada"

    pct_val   = impressora.get("percentual", 0) or 0
    cor_status = impressora.get("cor_status","")
    cor_hex   = "#ff2d55" if cor_status=="critico" else "#ff8c00" if cor_status=="baixo" else "#f0c040"

    try:
        if tipo == "teams":
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": cor_hex.replace("#",""),
                "summary": titulo,
                "sections": [{
                    "activityTitle": titulo,
                    "facts": [
                        {"name": "Impressora", "value": impressora.get("nome","")},
                        {"name": "IP",         "value": impressora.get("ip","")},
                        {"name": "Modelo",     "value": impressora.get("modelo","") or "—"},
                        {"name": "Setor",      "value": impressora.get("setor","") or "—"},
                        {"name": "Nível",      "value": f"{pct_val}%"},
                    ]
                }]
            }
        elif tipo == "slack":
            payload = {
                "text": titulo,
                "attachments": [{
                    "color": cor_hex,
                    "fields": [
                        {"title": "Impressora", "value": impressora.get("nome",""),  "short": True},
                        {"title": "IP",         "value": impressora.get("ip",""),    "short": True},
                        {"title": "Modelo",     "value": impressora.get("modelo","") or "—", "short": True},
                        {"title": "Nível",      "value": f"{pct_val}%",              "short": True},
                    ]
                }]
            }
        else:  # generic
            payload = {
                "titulo":     titulo,
                "mensagem":   detalhe,
                "impressora": impressora.get("nome",""),
                "ip":         impressora.get("ip",""),
                "nivel":      pct_val,
                "status":     cor_status,
            }

        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return True, f"Webhook enviado (HTTP {resp.status})"

    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def processar_notificacoes(impressora, percentual):
    """
    Verifica se deve enviar notificação para uma impressora.
    Chamado após cada leitura de toner.
    """
    if not impressora.get("id"):
        return

    cfg          = get_config_notificacao()
    cor_status   = impressora.get("cor_status","")
    imp_id       = impressora["id"]
    nivel_config = cfg.get("nivel_alerta","critico")
    intervalo    = int(cfg.get("intervalo_horas", 4))

    # Define se deve alertar baseado no nível configurado
    deve_alertar = False
    if nivel_config == "medio"   and cor_status in ("critico","baixo","medio"):
        deve_alertar = True
    elif nivel_config == "baixo" and cor_status in ("critico","baixo"):
        deve_alertar = True
    elif nivel_config == "critico" and cor_status == "critico":
        deve_alertar = True

    # Impressora voltou ao normal — limpa alertas enviados
    if cor_status in ("ok", "offline", "sem_dados"):
        limpar_alertas_resolvidos(imp_id)
        return

    if not deve_alertar:
        return

    # Evita spam — respeita intervalo configurado
    if alerta_ja_enviado(imp_id, cor_status, intervalo):
        return

    titulo, detalhe = _montar_mensagem(impressora, percentual)
    resultados      = []

    if cfg.get("email_ativo","0") == "1":
        ok, msg = _enviar_email(cfg, titulo, detalhe, impressora, percentual)
        resultados.append(("email", ok, msg))

    if cfg.get("webhook_ativo","0") == "1":
        ok, msg = _enviar_webhook(cfg, titulo, detalhe, impressora, percentual)
        resultados.append(("webhook", ok, msg))

    if resultados:
        registrar_alerta_enviado(imp_id, cor_status)

    return resultados


def testar_email(cfg):
    """Testa as configurações de e-mail enviando uma mensagem de teste."""
    imp_fake = {"nome":"Impressora Teste","ip":"192.168.0.1","modelo":"Teste","setor":"TI","percentual":15,"cor_status":"baixo"}
    titulo   = "✅ Teste de Notificação — Monitor de Toner"
    detalhe  = "Este é um e-mail de teste do Monitor de Toner.\nSe recebeu, as configurações estão corretas!"
    return _enviar_email(cfg, titulo, detalhe, imp_fake, 15)


def testar_webhook(cfg):
    """Testa o webhook."""
    imp_fake = {"nome":"Impressora Teste","ip":"192.168.0.1","modelo":"Teste","setor":"TI","percentual":15,"cor_status":"baixo"}
    titulo   = "✅ Teste de Webhook — Monitor de Toner"
    detalhe  = "Este é um teste do Monitor de Toner."
    return _enviar_webhook(cfg, titulo, detalhe, imp_fake, 15)
