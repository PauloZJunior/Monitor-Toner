"""
routes/auth.py — Autenticação por senha para operações de gerenciamento
Blueprint: /auth

Apenas as operações de escrita (POST, PUT, DELETE) exigem autenticação.
A visualização do dashboard é sempre pública.
"""
import hashlib
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, jsonify, request, session
from config import ADMIN_PASSWORD_HASH, SESSION_LIFETIME_MINUTES

# Controle simples de tentativas de login (em memória)
_tentativas_login: dict = {}  # {ip: [timestamp, ...]}
MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 300   # 5 minutos
DELAY_FALHA     = 1.5   # segundos de espera em cada falha

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─── DECORATOR ───────────────────────────────────────
def requer_autenticacao(f):
    """
    Decorator que protege rotas de escrita.
    Retorna 401 se o usuário não estiver autenticado.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _esta_autenticado():
            return jsonify({
                "erro": "Autenticação necessária",
                "codigo": "NAO_AUTENTICADO"
            }), 401
        return f(*args, **kwargs)
    return wrapper


def _esta_autenticado():
    """Verifica se há sessão válida e não expirada."""
    if not session.get("autenticado"):
        return False
    expira_em = session.get("expira_em")
    if not expira_em:
        return False
    try:
        expira_dt = datetime.fromisoformat(expira_em)
        if datetime.now() > expira_dt:
            session.clear()
            return False
        return True
    except Exception:
        return False


# ─── ROTAS ───────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Autentica o usuário. Rate limiting: máx 5 tentativas por 5 minutos por IP.
    Body: { "senha": "..." }
    """
    ip    = request.remote_addr or "unknown"
    agora = time.time()

    # Rate limiting — limpa tentativas antigas
    tentativas = _tentativas_login.get(ip, [])
    tentativas = [t for t in tentativas if agora - t < JANELA_SEGUNDOS]

    if len(tentativas) >= MAX_TENTATIVAS:
        espera = int(JANELA_SEGUNDOS - (agora - tentativas[0]))
        return jsonify({
            "erro": f"Muitas tentativas. Aguarde {espera}s antes de tentar novamente."
        }), 429

    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha", "")

    if not senha:
        return jsonify({"erro": "Senha não informada"}), 400

    hash_recebido = hashlib.sha256(senha.encode()).hexdigest()

    if hash_recebido != ADMIN_PASSWORD_HASH:
        # Registra tentativa falha e aplica delay
        tentativas.append(agora)
        _tentativas_login[ip] = tentativas
        time.sleep(DELAY_FALHA)
        restantes = MAX_TENTATIVAS - len(tentativas)
        return jsonify({
            "erro": f"Senha incorreta. {restantes} tentativa(s) restante(s)."
        }), 403

    # Login OK — limpa tentativas do IP
    _tentativas_login.pop(ip, None)

    session["autenticado"] = True
    session["expira_em"]   = (
        datetime.now() + timedelta(minutes=SESSION_LIFETIME_MINUTES)
    ).isoformat()
    session.permanent = True

    return jsonify({
        "sucesso":      True,
        "mensagem":     "Autenticado com sucesso",
        "expira_em":    session["expira_em"],
        "validade_min": SESSION_LIFETIME_MINUTES,
    })


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Encerra a sessão autenticada."""
    session.clear()
    return jsonify({"sucesso": True, "mensagem": "Sessão encerrada"})


@auth_bp.route("/status")
def status():
    """Retorna se o usuário está autenticado (usado pelo frontend)."""
    autenticado = _esta_autenticado()
    resp = {"autenticado": autenticado}
    if autenticado:
        resp["expira_em"] = session.get("expira_em")
    return jsonify(resp)
