"""
app.py — Ponto de entrada do Monitor de Toner
"""
import os
import logging
from datetime import timedelta
from flask import Flask, send_from_directory, make_response, jsonify, request
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import SECRET_KEY, SESSION_LIFETIME_MINUTES
from database import init_db, importar_json, limpar_historico_antigo
from routes.api          import api_bp
from routes.crud         import crud_bp
from routes.auth         import auth_bp
from routes.historico    import historico_bp
from routes.notificacao  import notificacao_bp

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────
# Um único formato, com hora, tanto no console quanto em data/app.log —
# antes disso era uma mistura de print() sem timestamp e logging sem
# basicConfig, o que dificultava investigar "o que aconteceu e quando".
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, "app.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("monitor_toner")

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = SECRET_KEY
app.json.ensure_ascii = False
app.permanent_session_lifetime = timedelta(minutes=SESSION_LIFETIME_MINUTES)

# ─── Confia no proxy reverso (Traefik) para IP real do cliente ──────────────
# Sem isso, request.remote_addr sempre mostra o IP do Traefik, quebrando o
# rate limit de login (routes/auth.py) e a checagem de localhost (/api/debug).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ─── Configurar Sessões (Filesystem) ─────────────────────────────────────────
# Usar filesystem para evitar problemas de serialização com Redis
session_dir = os.path.join(DATA_DIR, "sessions")
os.makedirs(session_dir, exist_ok=True)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = session_dir
logger.info("Sessions: Filesystem (persistido em data/sessions)")

Session(app)

# Segurança de cookies de sessão
# HTTPS_ENABLED=true por padrão porque o docker-compose.yml já serve tudo
# atrás do Traefik com TLS. Só mude para "false" em ambiente local sem HTTPS.
_https_enabled = os.environ.get("HTTPS_ENABLED", "true").lower() == "true"
app.config.update(
    SESSION_COOKIE_HTTPONLY  = True,   # JS não acessa o cookie
    SESSION_COOKIE_SAMESITE  = 'Strict',  # Rejeita POST cross-origin
    SESSION_COOKIE_SECURE    = _https_enabled,
)

# ─── Headers de Segurança HTTP ────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    """Adiciona headers de segurança HTTP"""
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

app.register_blueprint(api_bp)
app.register_blueprint(crud_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(historico_bp)
app.register_blueprint(notificacao_bp)

# ─── Inicialização do banco de dados ───────────────────────────────────────────
def inicializar():
    init_db()
    # Migração de JSON legado
    json_antigo = os.path.join(os.path.dirname(__file__), "impressoras.json")
    if os.path.exists(json_antigo):
        n = importar_json(json_antigo)
        if n > 0:
            logger.info(f"Importadas {n} impressoras do JSON para o banco")
            os.rename(json_antigo, json_antigo + ".migrado")
    # Limpa histórico com mais de 90 dias
    limpar_historico_antigo(dias=90)

# Executa inicialização ao carregar o app (funciona com Gunicorn)
try:
    inicializar()
except Exception as e:
    logger.error(f"Erro na inicialização: {e}")

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

@app.route("/")
def index():
    return send_from_directory(TEMPLATE_DIR, "index.html")


@app.errorhandler(404)
def not_found(e):
    if request_wants_json():
        return jsonify({"erro": "Rota não encontrada"}), 404
    return send_from_directory(TEMPLATE_DIR, "index.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Erro interno: {e}")
    return jsonify({"erro": "Erro interno do servidor"}), 500


def request_wants_json():
    return request.path.startswith("/api") or request.path.startswith("/gerenciar") \
        or request.path.startswith("/historico") or request.path.startswith("/notificacao") \
        or request.path.startswith("/auth")


if __name__ == "__main__":
    from config import HOST, PORT
    logger.info("=" * 52)
    logger.info("  MONITOR DE TONER v2")
    logger.info(f"  Acesse: http://localhost:{PORT}")
    logger.info(f"  Banco:  data/impressoras.db")
    logger.info("=" * 52)
    app.run(host=HOST, port=PORT, debug=False)
