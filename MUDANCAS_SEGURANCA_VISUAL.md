# 🎯 RESUMO VISUAL DAS MUDANÇAS DE SEGURANÇA

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                 4 VULNERABILIDADES CRÍTICAS CORRIGIDAS ✅                       ║
╚════════════════════════════════════════════════════════════════════════════════╝

┌─ 1️⃣  SQL INJECTION via Community String ─────────────────────────────────────┐
│                                                                                │
│ ❌ ANTES:                                                                      │
│    POST /gerenciar/impressoras                                               │
│    {                                                                          │
│      "community": "'; DROP TABLE historico; --"  ← ACEITO!                  │
│    }                                                                          │
│                                                                                │
│ ✅ DEPOIS:                                                                     │
│    routes/crud.py:_validar_community()                                      │
│    regex: r'^[a-zA-Z0-9_\-\.]{1,32}$'  ← APENAS alphanumeric               │
│                                                                                │
│    Resultado: ❌ 400 Bad Request (community inválida)                        │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─ 2️⃣  Senha SMTP em Plaintext (Criptografia Fraca) ──────────────────────────┐
│                                                                                │
│ ❌ ANTES:                                                                      │
│    def _obfuscar_senha(senha):                                              │
│        key = "monitor-toner"  ← FIXA no código                             │
│        xored = senha XOR key  ← REVERSÍVEL                                │
│        return base64(xored)                                                 │
│                                                                                │
│ ✅ DEPOIS:                                                                     │
│    from cryptography.fernet import Fernet                                   │
│                                                                                │
│    class PasswordVault:                                                      │
│        - Gera chave única via Fernet.generate_key()                        │
│        - Persiste em data/.vault_key (chmod 600)                          │
│        - Encrypta com encrypt() — reversível apenas com chave             │
│        - Decrypta com decrypt() — seguro                                  │
│                                                                                │
│    Segurança: AES-128 (NIST approved) em CBC mode                         │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─ 3️⃣  Hardcoded Senha Admin "admin123" ──────────────────────────────────────┐
│                                                                                │
│ ❌ ANTES:                                                                      │
│    ADMIN_PASSWORD_HASH = os.environ.get(                                    │
│        "ADMIN_PASSWORD_HASH",                                               │
│        hashlib.sha256(b"admin123").hexdigest()  ← PADRÃO PERIGOSO          │
│    )                                                                          │
│                                                                                │
│    Hash SHA256("admin123") = 0192023a7bbd73250516f069df18b500             │
│    ↑ Encontrado em TODAS as rainbow tables!                                │
│                                                                                │
│ ✅ DEPOIS:                                                                     │
│    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")            │
│                                                                                │
│    if not ADMIN_PASSWORD_HASH:                                             │
│        print("❌ ERRO: Variável ADMIN_PASSWORD_HASH não definida!")       │
│        sys.exit(1)  ← OBRIGATÓRIO                                         │
│                                                                                │
│    Gerar com: python3 generate_password_hash.py                            │
│                                                                                │
│    Resultado: $2b$12$YourHashHereFullHash...                              │
│    - Bcrypt com 12 rounds (computacionalmente caro)                        │
│    - Cada hash é único (mesmo para mesma senha)                            │
│    - Impossível reverter para senha original                               │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─ 4️⃣  Sessões em Memória (Perdidas em Restart) ─────────────────────────────┐
│                                                                                │
│ ❌ ANTES:                                                                      │
│    session["autenticado"] = True  ← Armazenado em RAM                     │
│                                                                                │
│    docker restart monitor-toner                                            │
│    ↓                                                                          │
│    Todas as sessões perdidas! (usuários desconectados)                    │
│                                                                                │
│ ✅ DEPOIS:                                                                     │
│    app.py:                                                                   │
│    from flask_session import Session                                       │
│    import redis                                                             │
│                                                                                │
│    # Tenta Redis (produção)                                                │
│    app.config['SESSION_TYPE'] = 'redis'                                   │
│    app.config['SESSION_REDIS'] = redis.from_url(REDIS_URL)               │
│    Session(app)                                                             │
│                                                                                │
│    # Fallback: Filesystem (se Redis indisponível)                         │
│    app.config['SESSION_TYPE'] = 'filesystem'                              │
│    app.config['SESSION_FILE_DIR'] = 'data/sessions'                      │
│    Session(app)                                                             │
│                                                                                │
│    Docker-compose.yml:                                                      │
│    services:                                                                 │
│      redis:                                                                  │
│        image: redis:7-alpine  ← Novo serviço                              │
│        volumes:                                                              │
│          - redis_data:/data    ← Persistido                               │
│                                                                                │
│    docker restart monitor-toner                                            │
│    ↓                                                                          │
│    Sessões continuam válidas! ✓                                            │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════╗
║                          ARQUIVOS MODIFICADOS                                  ║
╚════════════════════════════════════════════════════════════════════════════════╝

  📝 requirements.txt
     + cryptography>=41.0.0
     + Flask-Session>=0.5.0
     + redis>=5.0.0
     + bcrypt>=4.0.0

  ⚙️  config.py
     - Removido: hashlib import
     - Adicionado: sys import
     ✓ ADMIN_PASSWORD_HASH agora obrigatório via ENV

  🛡️  routes/auth.py
     - Removido: hashlib (SHA256)
     ✓ Adicionado: bcrypt.checkpw()
     ✓ Agora verifica contra hash bcrypt

  🚀 routes/crud.py
     ✓ Adicionado: re, ipaddress imports
     ✓ _validar_ip() — ipaddress.IPv4Address()
     ✓ _validar_community() — regex proteção SQL injection
     ✓ Validação rigorosa no _validar_dados()

  🔐 modules/notificacao.py
     ✓ Adicionado: cryptography, socket imports
     ✓ PasswordVault class (Fernet encryption)
     ✓ _obfuscar_senha() → vault.encrypt()
     ✓ _deobfuscar_senha() → vault.decrypt()
     ✓ socket.timeout handling em _enviar_webhook()

  🌐 app.py
     ✓ Adicionado: flask_session, redis imports
     ✓ Flask-Session com Redis (ou filesystem fallback)
     ✓ set_security_headers() — CSP, HSTS, X-Frame-Options, etc.
     ✓ SameSite=Strict (era Lax)

  🐳 docker-compose.yml
     ✓ Novo serviço: redis (7-alpine)
     ✓ health check para Redis
     ✓ Dependência: monitor-toner depends_on redis
     ✓ ADMIN_PASSWORD_HASH obrigatório no environment
     ✓ REDIS_URL configurado

  📦 Novos Arquivos:
     ✓ .env.example — Documentação de variáveis
     ✓ generate_password_hash.py — Utilitário de senha
     ✓ SECURITY_UPDATES.md — Documentação de mudanças
     ✓ MUDANCAS_SEGURANCA_VISUAL.md (este arquivo)

╔════════════════════════════════════════════════════════════════════════════════╗
║                     COMO USAR O NOVO SISTEMA                                   ║
╚════════════════════════════════════════════════════════════════════════════════╝

┌─ PASSO 1: Gerar Hash Bcrypt ─────────────────────────────────────────────────┐
│                                                                                │
│  $ python3 generate_password_hash.py                                        │
│  Digite a senha do administrador: ••••••••••••••                            │
│  Confirme a senha: ••••••••••••••                                           │
│                                                                                │
│  ✓ Hash bcrypt gerado com sucesso!                                         │
│  ────────────────────────────────────────────────────────────────────────   │
│                                                                                │
│  Hash:                                                                        │
│  $2b$12$n4Tx7R5RGRzYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYn │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─ PASSO 2: Criar arquivo .env ────────────────────────────────────────────────┐
│                                                                                │
│  $ cp .env.example .env                                                      │
│  $ nano .env  (ou seu editor favorito)                                      │
│                                                                                │
│  ADMIN_PASSWORD_HASH=$2b$12$n4Tx7R5RGRzYnYnYnYnYn...                       │
│  REDIS_URL=redis://redis:6379/0                                            │
│  TZ=America/Sao_Paulo                                                        │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌─ PASSO 3: Deploy com Docker ─────────────────────────────────────────────────┐
│                                                                                │
│  $ docker-compose up -d                                                     │
│                                                                                │
│  Criando redis container...                                                  │
│  Aguardando health check...                                                  │
│  Criando monitor-toner container...                                         │
│  ✓ Redis: RUNNING                                                           │
│  ✓ Monitor-Toner: RUNNING                                                  │
│  ✓ Sessions: Redis (persistido)                                            │
│                                                                                │
│  Acesse: http://localhost                                                    │
│  Login: Use a senha configurada                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════╗
║                        VERIFICAÇÃO DE SEGURANÇA                                ║
╚════════════════════════════════════════════════════════════════════════════════╝

✅ SQL Injection:
   curl -X POST http://localhost/gerenciar/impressoras \
     -H "Content-Type: application/json" \
     -d '{"nome":"T","ip":"192.168.1.1","community":"'; DROP --"}'
   
   ✓ Esperado: 400 Bad Request (community inválida)

✅ Criptografia SMTP:
   sqlite3 data/impressoras.db
   SELECT valor FROM config_notificacao WHERE chave='email_senha';
   
   ✓ Esperado: $FERNET$<encrypted_token> (não plaintext!)

✅ Senha Admin:
   docker-compose up -d
   # Sem ADMIN_PASSWORD_HASH definido
   
   ✓ Esperado: ❌ ERRO na inicialização

✅ Sessão Persiste:
   1. Fazer login
   2. docker-compose restart
   3. Refrescar página — ainda autenticado!
   
   ✓ Esperado: Sessão válida após restart

✅ Headers de Segurança:
   curl -I http://localhost
   
   ✓ Esperado:
     Content-Security-Policy: default-src 'self'...
     X-Frame-Options: DENY
     X-Content-Type-Options: nosniff
     Strict-Transport-Security: max-age=...

╔════════════════════════════════════════════════════════════════════════════════╗
║                            ANTES vs DEPOIS                                     ║
╚════════════════════════════════════════════════════════════════════════════════╝

MÉTRICA                    ANTES              DEPOIS              IMPACTO
─────────────────────────────────────────────────────────────────────────────
Community SNMP             Sem validação      Regex whitelist     🔒 CRÍTICO
Senha SMTP                 XOR (reversível)   Fernet (seguro)     🔒 CRÍTICO
Senha Admin                Hardcoded          Bcrypt+ENV          🔒 CRÍTICO
Sessão                     RAM (efêmera)      Redis (persistida)  🔒 CRÍTICO
IP Validation              Básica             ipaddress lib.      ✓ Melhoria
SNMP Community             Sem limite         32 chars max        ✓ Melhoria
Headers HTTP               Não                CSP+HSTS+X-Frame    ✓ Melhoria
CSRF Protection            SameSite=Lax       SameSite=Strict     ✓ Melhoria
Timeout Webhook            Nenhum             10s máximo          ✓ Melhoria

╔════════════════════════════════════════════════════════════════════════════════╗
║                      ROADMAP DE SEGURANÇA FUTURO                               ║
╚════════════════════════════════════════════════════════════════════════════════╝

FASE 2 (Próxima semana):
  ☐ Rate limiting com Redis (memória compartilhada)
  ☐ Logging/Auditoria estruturado
  ☐ Validação de Webhook URL (SSRF protection)
  ☐ XSS protection em JavaScript (escape HTML)

FASE 3 (Próximo mês):
  ☐ Content Security Policy aprimorado
  ☐ Cache com TTL para SNMP
  ☐ Validação de OID SNMP
  ☐ Path traversal protection

FASE 4 (Futuro):
  ☐ HTTPS/TLS (Let's Encrypt)
  ☐ Certificado auto-assinado para desenvolvimento
  ☐ HSTS preload
  ☐ 2FA (Two-factor authentication)
  ☐ Token JWT (em vez de sessões)
  ☐ SNMP v3 com criptografia

═══════════════════════════════════════════════════════════════════════════════

Status:     ✅ CONCLUÍDO
Versão:     2.1.0-security
Data:       28/04/2026
Próxima:    Faseamento das correções ALTAS (item 6-13)
```
