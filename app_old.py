"""
app.py — Ponto de entrada do Monitor de Toner
"""
import os
from datetime import timedelta
from flask import Flask, send_from_directory

from config import SECRET_KEY, SESSION_LIFETIME_MINUTES
from database import init_db, importar_json, limpar_historico_antigo
from routes.api          import api_bp
from routes.crud         import crud_bp
from routes.auth         import auth_bp
from routes.historico    import historico_bp
from routes.notificacao  import notificacao_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = SECRET_KEY
app.json.ensure_ascii = False
app.permanent_session_lifetime = timedelta(minutes=SESSION_LIFETIME_MINUTES)

# Segurança de cookies de sessão
app.config.update(
    SESSION_COOKIE_HTTPONLY  = True,   # JS não acessa o cookie
    SESSION_COOKIE_SAMESITE  = 'Lax',  # Proteção CSRF básica
    SESSION_COOKIE_SECURE    = False,  # Mudar para True se usar HTTPS
)

app.register_blueprint(api_bp)
app.register_blueprint(crud_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(historico_bp)
app.register_blueprint(notificacao_bp)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

@app.route("/")
def index():
    return send_from_directory(TEMPLATE_DIR, "index.html")


def inicializar():
    init_db()
    # Migração de JSON legado
    json_antigo = os.path.join(os.path.dirname(__file__), "impressoras.json")
    if os.path.exists(json_antigo):
        n = importar_json(json_antigo)
        if n > 0:
            print(f"  ✔ Importadas {n} impressoras do JSON para o banco")
            os.rename(json_antigo, json_antigo + ".migrado")
    # Limpa histórico com mais de 90 dias
    limpar_historico_antigo(dias=90)


if __name__ == "__main__":
    from config import HOST, PORT
    inicializar()
    print("=" * 52)
    print("  MONITOR DE TONER v2")
    print(f"  Acesse: http://localhost:{PORT}")
    print(f"  Banco:  data/impressoras.db")
    print("=" * 52)
    app.run(host=HOST, port=PORT, debug=False)
