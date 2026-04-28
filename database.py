"""
database.py — Gerenciamento do banco de dados SQLite
Tabelas: impressoras, historico, config_notificacao, alertas_enviados
"""
import sqlite3, os
from config import DB_PATH


def get_conn():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError:
        pass  # pasta já existe ou permissão negada — sqlite tentará criar o arquivo diretamente
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # WAL: melhor concorrência, evita locks no Docker
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """Cria todas as tabelas e aplica migrações silenciosas."""
    with get_conn() as conn:
        # ── Impressoras ──────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS impressoras (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT    NOT NULL,
                ip         TEXT    NOT NULL UNIQUE,
                modelo     TEXT    DEFAULT '',
                tipo       TEXT    DEFAULT 'toner',
                setor      TEXT    DEFAULT '',
                empresa    TEXT    DEFAULT '',
                serial     TEXT    DEFAULT '',
                mac        TEXT    DEFAULT '',
                community  TEXT    DEFAULT 'public',
                ativo      INTEGER DEFAULT 1,
                criado_em  TEXT    DEFAULT (datetime('now','localtime')),
                editado_em TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

        # ── Histórico de toner ────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                impressora_id   INTEGER NOT NULL,
                percentual      INTEGER,
                status          TEXT,
                tempo_resposta  REAL,
                registrado_em   TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (impressora_id) REFERENCES impressoras(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_historico_imp_data
            ON historico(impressora_id, registrado_em DESC)
        """)

        # ── Configuração de notificações ──────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_notificacao (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)

        # ── Controle de alertas enviados (evita spam) ─────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alertas_enviados (
                impressora_id INTEGER NOT NULL,
                nivel_alerta  TEXT    NOT NULL,
                enviado_em    TEXT    DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (impressora_id, nivel_alerta)
            )
        """)
        conn.commit()

        # Migrações silenciosas para bancos já existentes
        migrations = [
            "ALTER TABLE impressoras ADD COLUMN tipo       TEXT DEFAULT 'toner'",
            "ALTER TABLE impressoras ADD COLUMN serial     TEXT DEFAULT ''",
            "ALTER TABLE impressoras ADD COLUMN mac        TEXT DEFAULT ''",
            "ALTER TABLE impressoras ADD COLUMN empresa    TEXT DEFAULT ''",
        ]
        for sql in migrations:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass  # coluna já existe — ignora


# ── IMPRESSORAS ───────────────────────────────────────
def listar_impressoras(apenas_ativas=True):
    with get_conn() as conn:
        q = "SELECT * FROM impressoras"
        if apenas_ativas:
            q += " WHERE ativo = 1"
        q += " ORDER BY empresa, setor, nome"
        return [dict(r) for r in conn.execute(q).fetchall()]


def buscar_por_id(id_):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM impressoras WHERE id=?", (id_,)).fetchone()
        return dict(r) if r else None


def buscar_por_ip(ip):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM impressoras WHERE ip=?", (ip,)).fetchone()
        return dict(r) if r else None


def criar_impressora(dados):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO impressoras (nome,ip,modelo,tipo,setor,empresa,serial,mac,community)
            VALUES (:nome,:ip,:modelo,:tipo,:setor,:empresa,:serial,:mac,:community)
        """, {
            "nome":      dados.get("nome","").strip(),
            "ip":        dados.get("ip","").strip(),
            "modelo":    dados.get("modelo","").strip(),
            "tipo":      dados.get("tipo","toner").strip() or "toner",
            "setor":     dados.get("setor","").strip(),
            "empresa":   dados.get("empresa","").strip(),
            "serial":    dados.get("serial","").strip(),
            "mac":       dados.get("mac","").strip(),
            "community": dados.get("community","public").strip(),
        })
        conn.commit()
        return cur.lastrowid


def atualizar_impressora(id_, dados):
    with get_conn() as conn:
        conn.execute("""
            UPDATE impressoras SET
                nome=:nome, ip=:ip, modelo=:modelo, tipo=:tipo,
                setor=:setor, empresa=:empresa, serial=:serial,
                mac=:mac, community=:community, ativo=:ativo,
                editado_em=datetime('now','localtime')
            WHERE id=:id
        """, {
            "id":        id_,
            "nome":      dados.get("nome","").strip(),
            "ip":        dados.get("ip","").strip(),
            "modelo":    dados.get("modelo","").strip(),
            "tipo":      dados.get("tipo","toner").strip() or "toner",
            "setor":     dados.get("setor","").strip(),
            "empresa":   dados.get("empresa","").strip(),
            "serial":    dados.get("serial","").strip(),
            "mac":       dados.get("mac","").strip(),
            "community": dados.get("community","public").strip(),
            "ativo":     int(dados.get("ativo",1)),
        })
        conn.commit()


def excluir_impressora(id_):
    with get_conn() as conn:
        conn.execute("DELETE FROM impressoras WHERE id=?", (id_,))
        conn.commit()


def importar_json(caminho_json):
    import json
    if not os.path.exists(caminho_json):
        return 0
    with open(caminho_json,"r",encoding="utf-8") as f:
        impressoras = json.load(f)
    n = 0
    for imp in impressoras:
        try:
            criar_impressora(imp)
            n += 1
        except Exception:
            pass
    return n


# ── HISTÓRICO ─────────────────────────────────────────
def salvar_historico(impressora_id, percentual, status, tempo_resposta=None):
    """Salva uma leitura no histórico."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO historico (impressora_id, percentual, status, tempo_resposta)
            VALUES (?, ?, ?, ?)
        """, (impressora_id, percentual, status, tempo_resposta))
        conn.commit()


def buscar_historico(impressora_id, dias=30, limite=200):
    """Retorna histórico de uma impressora."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT percentual, status, tempo_resposta, registrado_em
            FROM historico
            WHERE impressora_id = ?
              AND registrado_em >= datetime('now', ?, 'localtime')
            ORDER BY registrado_em DESC
            LIMIT ?
        """, (impressora_id, f"-{dias} days", limite)).fetchall()
        return [dict(r) for r in rows]


def buscar_historico_resumido(impressora_id, limite=48):
    """Retorna últimas N leituras para sparkline no card."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT percentual, registrado_em
            FROM historico
            WHERE impressora_id = ?
              AND percentual IS NOT NULL
            ORDER BY registrado_em DESC
            LIMIT ?
        """, (impressora_id, limite)).fetchall()
        return [dict(r) for r in reversed(rows)]


def limpar_historico_antigo(dias=90):
    """Remove registros mais antigos que N dias e compacta o banco."""
    with get_conn() as conn:
        cur = conn.execute("""
            DELETE FROM historico
            WHERE registrado_em < datetime('now', ?, 'localtime')
        """, (f"-{dias} days",))
        conn.commit()
        removidos = cur.rowcount
        if removidos > 0:
            # VACUUM recupera espaço após deleções em massa
            conn.execute("VACUUM")
            conn.commit()
        return removidos


# ── CONFIG NOTIFICAÇÃO ────────────────────────────────
def get_config_notificacao():
    """Retorna todas as configurações de notificação."""
    defaults = {
        "email_ativo":       "0",
        "email_smtp":        "",
        "email_porta":       "587",
        "email_usuario":     "",
        "email_senha":       "",
        "email_tls":         "1",
        "email_destinos":    "",
        "webhook_ativo":     "0",
        "webhook_url":       "",
        "webhook_tipo":      "generic",
        "nivel_alerta":      "critico",
        "intervalo_horas":   "4",
    }
    with get_conn() as conn:
        rows = conn.execute("SELECT chave, valor FROM config_notificacao").fetchall()
        for row in rows:
            defaults[row["chave"]] = row["valor"]
    return defaults


def salvar_config_notificacao(configs: dict):
    """Salva configurações de notificação."""
    with get_conn() as conn:
        for chave, valor in configs.items():
            conn.execute("""
                INSERT INTO config_notificacao (chave, valor)
                VALUES (?, ?)
                ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor
            """, (chave, str(valor)))
        conn.commit()


# ── ALERTAS ENVIADOS ──────────────────────────────────
def alerta_ja_enviado(impressora_id, nivel, horas=4):
    """Verifica se já enviou alerta recente para evitar spam."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT enviado_em FROM alertas_enviados
            WHERE impressora_id=? AND nivel_alerta=?
              AND enviado_em >= datetime('now', ?, 'localtime')
        """, (impressora_id, nivel, f"-{horas} hours")).fetchone()
        return row is not None


def registrar_alerta_enviado(impressora_id, nivel):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO alertas_enviados (impressora_id, nivel_alerta)
            VALUES (?, ?)
            ON CONFLICT(impressora_id, nivel_alerta)
            DO UPDATE SET enviado_em=datetime('now','localtime')
        """, (impressora_id, nivel))
        conn.commit()


def limpar_alertas_resolvidos(impressora_id):
    """Remove alertas quando impressora volta ao normal."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM alertas_enviados WHERE impressora_id=?",
            (impressora_id,)
        )
        conn.commit()
