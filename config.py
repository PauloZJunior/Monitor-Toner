"""
config.py — Configurações globais, OIDs SNMP e constantes
"""
import os
import sys

# ── Caminhos ──────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "data", "impressoras.db")

# ── Servidor ──────────────────────────────────────────
HOST      = "0.0.0.0"
PORT      = 5000
WORKERS   = 2
TIMEOUT   = 120

# ── SNMP ──────────────────────────────────────────────
SNMP_TIMEOUT      = 3
SNMP_MAX_WORKERS  = 15

# OIDs padrão Printer MIB (RFC 3805)
OID_SYS_NAME    = "1.3.6.1.2.1.1.5.0"
OID_SYS_DESCR   = "1.3.6.1.2.1.1.1.0"
OID_SERIAL      = "1.3.6.1.2.1.43.5.1.1.17.1"
OID_MAC         = "1.3.6.1.2.1.2.2.1.6.1"
OID_SUPPLY_DESC = "1.3.6.1.2.1.43.11.1.1.6.1"
OID_SUPPLY_MAX  = "1.3.6.1.2.1.43.11.1.1.8.1"
OID_SUPPLY_CURR = "1.3.6.1.2.1.43.11.1.1.9.1"

# OIDs Brother
OID_BROTHER_TONER_PCT = "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.10.0"
OID_BROTHER_TONER_STS = "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.8.0"
OID_BROTHER_TONER_ALT = "1.3.6.1.4.1.2435.2.4.3.1.3.0"

# OIDs Ricoh SP
OID_RICOH_TONER_CURR  = "1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.1"
OID_RICOH_TONER_MAX   = "1.3.6.1.4.1.367.3.2.1.2.24.1.1.6.1"
OID_RICOH_TONER_CURR2 = "1.3.6.1.4.1.367.3.2.1.2.19.1.1.5.1"
OID_RICOH_TONER_MAX2  = "1.3.6.1.4.1.367.3.2.1.2.19.1.1.6.1"

# OIDs Epson
OID_EPSON_INK_CURR = "1.3.6.1.4.1.1248.1.2.2.1.1.1.4.1"
OID_EPSON_INK_MAX  = "1.3.6.1.4.1.1248.1.2.2.1.1.1.5.1"

IGNORE_WORDS = ["drum", "cilindro", "fus", "imaging unit", "transfer", "maintenance", "roller", "waste"]

COR_TINTA = {
    "black":   {"label": "Preto",   "hex": "#222222"},
    "k":       {"label": "Preto",   "hex": "#222222"},
    "cyan":    {"label": "Ciano",   "hex": "#00aadd"},
    "c":       {"label": "Ciano",   "hex": "#00aadd"},
    "magenta": {"label": "Magenta", "hex": "#dd0077"},
    "m":       {"label": "Magenta", "hex": "#dd0077"},
    "yellow":  {"label": "Amarelo", "hex": "#ddaa00"},
    "y":       {"label": "Amarelo", "hex": "#ddaa00"},
}

# ── Autenticação ──────────────────────────────────────
# OBRIGATÓRIO: Definir senha via variável de ambiente ADMIN_PASSWORD_HASH
# Gere com: python3 -c "import bcrypt; print(bcrypt.hashpw(b'SENHA_SEGURA', bcrypt.gensalt(rounds=12)).decode())"
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    import sys
    print("❌ ERRO CRÍTICO: Variável de ambiente ADMIN_PASSWORD_HASH não definida!")
    print("   Gere um hash bcrypt seguro com:")
    print("   python3 -c \"import bcrypt; print(bcrypt.hashpw(b'SENHA_SEGURA', bcrypt.gensalt(rounds=12)).decode())\"")
    print("   Depois exporte: export ADMIN_PASSWORD_HASH=<hash_gerado>")
    sys.exit(1)

# ── SECRET_KEY persistida em arquivo ─────────────────
# FIX BUG 1: SECRET_KEY deve ser a mesma entre todos os workers Gunicorn.
# Gera uma vez e salva em disco. Na próxima inicialização, reutiliza a mesma.
def _get_or_create_secret_key():
    key_file = os.path.join(BASE_DIR, "data", ".secret_key")
    # Prioridade 1: variável de ambiente
    env_key = os.environ.get("SECRET_KEY", "")
    if env_key:
        return env_key
    # Prioridade 2: arquivo persistido
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            key = f.read().strip()
            if key:
                return key
    # Gera nova chave e persiste
    import secrets
    key = secrets.token_hex(32)
    with open(key_file, "w") as f:
        f.write(key)
    return key

SECRET_KEY = _get_or_create_secret_key()

# Tempo de expiração da sessão (minutos)
SESSION_LIFETIME_MINUTES = 120
