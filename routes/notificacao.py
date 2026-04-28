"""
routes/notificacao.py — Endpoints de configuração de notificações
Blueprint: /notificacao
"""
from flask import Blueprint, jsonify, request
from database import get_config_notificacao, salvar_config_notificacao
from modules.notificacao import testar_email, testar_webhook, _obfuscar_senha
from routes.auth import requer_autenticacao

notificacao_bp = Blueprint("notificacao", __name__, url_prefix="/notificacao")

CAMPOS_PERMITIDOS = [
    "email_ativo","email_smtp","email_porta","email_usuario",
    "email_senha","email_tls","email_destinos",
    "webhook_ativo","webhook_url","webhook_tipo",
    "nivel_alerta","intervalo_horas",
]


@notificacao_bp.route("/config")
def get_config():
    cfg = get_config_notificacao()
    # Não expõe senha no GET
    cfg_safe = {k: ("***" if k == "email_senha" and v else v)
                for k, v in cfg.items()}
    return jsonify(cfg_safe)


@notificacao_bp.route("/config", methods=["POST"])
@requer_autenticacao
def salvar_config():
    dados = request.get_json(silent=True) or {}
    # Filtra apenas campos permitidos
    configs = {k: v for k, v in dados.items() if k in CAMPOS_PERMITIDOS}
    # Não sobrescreve senha se vier mascarada ou vazia
    if configs.get("email_senha") in ("***", "", None):
        configs.pop("email_senha", None)
    elif configs.get("email_senha"):
        # Ofusca a senha antes de salvar
        configs["email_senha"] = _obfuscar_senha(configs["email_senha"])
    salvar_config_notificacao(configs)
    return jsonify({"sucesso": True, "mensagem": "Configurações salvas"})


@notificacao_bp.route("/testar/email", methods=["POST"])
@requer_autenticacao
def testar_email_route():
    cfg = get_config_notificacao()
    # Permite sobrescrever com dados do body (para testar sem salvar)
    dados = request.get_json(silent=True) or {}
    cfg.update({k: v for k, v in dados.items() if k in CAMPOS_PERMITIDOS})
    ok, msg = testar_email(cfg)
    return jsonify({"sucesso": ok, "mensagem": msg})


@notificacao_bp.route("/testar/webhook", methods=["POST"])
@requer_autenticacao
def testar_webhook_route():
    cfg = get_config_notificacao()
    dados = request.get_json(silent=True) or {}
    cfg.update({k: v for k, v in dados.items() if k in CAMPOS_PERMITIDOS})
    ok, msg = testar_webhook(cfg)
    return jsonify({"sucesso": ok, "mensagem": msg})
