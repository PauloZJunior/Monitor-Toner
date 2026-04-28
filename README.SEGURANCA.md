# 🔐 README DE SEGURANÇA — Monitor de Toner v2

**IMPORTANTE:** Leia este arquivo antes de fazer deploy em produção!

---

## ⚡ INICIO RÁPIDO

```bash
# 1. Gerar senha admin segura
python3 generate_password_hash.py

# 2. Criar arquivo .env (copiar do template e preencher com o hash)
cp .env.example .env
nano .env

# 3. Deploy
docker-compose up -d

# 4. Acessar em http://localhost
```

---

## 🚨 MUDANÇAS CRÍTICAS (VERSÃO 2.1.0)

### 4 Vulnerabilidades Corrigidas:

| # | Vulnerabilidade | Antes | Depois | Status |
|---|-----------------|-------|--------|--------|
| 1 | SQL Injection (Community) | Sem validação | Regex whitelist | ✅ |
| 2 | Senha SMTP plaintext | XOR fraco | Fernet seguro | ✅ |
| 3 | Hardcoded password | "admin123" | Bcrypt + ENV | ✅ |
| 4 | Sessões efêmeras | RAM | Redis persistido | ✅ |

---

## 📋 PRÉ-REQUISITOS

```bash
# Python 3.8+
python3 --version

# Docker & Docker Compose
docker --version
docker-compose --version

# Opcional: git (para versionamento)
git --version
```

---

## 🔧 CONFIGURAÇÃO (Passo a Passo)

### Passo 1: Gerar Hash Bcrypt

O primeiro passo é **gerar uma senha segura** para o administrador.

**Opção A: Script Automático (Recomendado)**
```bash
python3 generate_password_hash.py

# Saída:
# Digite a senha do administrador: ••••••••••••••
# Confirme a senha: ••••••••••••••
# ✓ Hash bcrypt gerado com sucesso!
# $2b$12$n4Tx7R5RGRzYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYn

# Copie o hash (começando com $2b$12$...)
```

**Opção B: Manual (Python Direto)**
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'MINHA_SENHA_SEGURA', bcrypt.gensalt(rounds=12)).decode())"
```

**⚠️ Requisitos para Senha:**
- ✅ Mínimo 8 caracteres
- ✅ Usar maiúsculas, minúsculas, números e símbolos
- ✅ Diferente de "admin123"
- ❌ Não compartilhe com ninguém
- ❌ Não use a mesma senha de outro serviço

**Exemplo de senha segura:**
- ✅ `Toner@2024Segura!`
- ✅ `M0nit0r#Toner$2024`
- ❌ `123456`
- ❌ `admin`

### Passo 2: Criar Arquivo .env

```bash
# Copiar template
cp .env.example .env

# Editar com seu editor favorito
nano .env  # ou: code .env, vim .env, etc.
```

**Conteúdo de .env (OBRIGATÓRIO):**
```env
# Colar aqui o hash bcrypt gerado no Passo 1
# Exemplo:
ADMIN_PASSWORD_HASH=$2b$12$n4Tx7R5RGRzYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYnYn

# Redis (opcional, já vem como padrão)
REDIS_URL=redis://redis:6379/0

# Timezone
TZ=America/Sao_Paulo
```

**⚠️ IMPORTANTE:**
- Nunca faça commit do `.env` no git
- Adicione `.env` ao `.gitignore`:
  ```bash
  echo ".env" >> .gitignore
  ```
- Armazene `.env` em local seguro (vault, 1password, etc.)

### Passo 3: Build & Deploy

```bash
# Construir imagem Docker
docker-compose build

# Iniciar serviços
docker-compose up -d

# Verificar status
docker-compose ps

# Esperado:
# NAME                  STATUS
# monitor-toner-redis   Up (healthy)
# monitor-toner         Up
```

### Passo 4: Verificar Instalação

```bash
# Acessar aplicação
# http://localhost

# Fazer login com a senha configurada
# Usuário: (não é necessário)
# Senha: <aquela configurada em ADMIN_PASSWORD_HASH>
```

---

## 🔍 VERIFICAÇÕES DE SEGURANÇA

### Verificação 1: Community String (SQL Injection)
```bash
# Tentar injetar SQL (deve falhar)
curl -X POST http://localhost/gerenciar/impressoras \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Teste",
    "ip": "192.168.1.100",
    "community": "public; DROP TABLE historico; --"
  }'

# ✅ Esperado: 400 Bad Request (community inválida)
```

### Verificação 2: Criptografia de Senha SMTP
```bash
# Verificar que senhas estão criptografadas (não plaintext)
docker exec monitor-toner sqlite3 /app/data/impressoras.db \
  "SELECT valor FROM config_notificacao WHERE chave='email_senha';"

# ✅ Esperado: $FERNET$... (não a senha original!)
```

### Verificação 3: Sessão Persiste
```bash
# 1. Fazer login
curl -X POST http://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"senha": "SUA_SENHA"}' \
  -c cookies.txt

# 2. Verificar autenticação
curl http://localhost/auth/status -b cookies.txt

# ✅ Esperado: {"autenticado": true}

# 3. Reiniciar container
docker-compose restart

# 4. Verificar autenticação novamente (após restart)
curl http://localhost/auth/status -b cookies.txt

# ✅ Esperado: AINDA {"autenticado": true}
```

### Verificação 4: Headers de Segurança
```bash
# Verificar headers HTTP
curl -I http://localhost/

# ✅ Esperado:
# Content-Security-Policy: default-src 'self'...
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Strict-Transport-Security: max-age=31536000...
```

---

## 📊 ESTRUTURA DE ARQUIVOS (Novos)

```
monitor-toner/
├── .env                          ← Criar (variáveis de ambiente)
├── .env.example                  ← Novo (template)
├── generate_password_hash.py     ← Novo (utilitário)
├── ANALISE_VULNERABILIDADES.md   ← Novo (análise completa)
├── SECURITY_UPDATES.md           ← Novo (mudanças de segurança)
├── MUDANCAS_SEGURANCA_VISUAL.md  ← Novo (guia visual)
├── README.SEGURANCA.md           ← Este arquivo
├── data/
│   ├── .vault_key                ← Auto-gerado (chave Fernet)
│   ├── .secret_key               ← Existente
│   ├── impressoras.db            ← Existente
│   └── sessions/                 ← Novo (sessões persistidas)
├── requirements.txt              ← Atualizado (+ 4 dependências)
├── docker-compose.yml            ← Atualizado (+ Redis)
├── Dockerfile                    ← Sem mudanças
└── app.py                        ← Atualizado (Flask-Session)
```

---

## 🚀 PRODUÇÃO

### HTTPS (Obrigatório em Produção)

```bash
# Gerar certificado auto-assinado (desenvolvimento)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365

# Produção: Use Let's Encrypt (gratuito)
# https://letsencrypt.org/
```

### Variáveis de Ambiente (CI/CD)

Se usar GitHub Actions, GitLab CI, ou similar:

```yaml
# .github/workflows/deploy.yml
env:
  ADMIN_PASSWORD_HASH: ${{ secrets.ADMIN_PASSWORD_HASH }}
  REDIS_URL: ${{ secrets.REDIS_URL }}

# Armazenar secrets no repositório CI/CD, não no código
```

### Backup da Chave Vault

A chave de criptografia em `data/.vault_key` é crítica:

```bash
# Fazer backup
cp data/.vault_key data/.vault_key.backup

# Armazenar seguro (não no git!)
# Backup offsite (cloud, pendrive seguro, etc.)

# Verificar proprietário e permissões
ls -l data/.vault_key
# -rw------- (600) = apenas dono lê

# Se perdida, senhas SMTP não conseguem ser descriptografadas
# Necessário reconfigura-las
```

### Log de Auditoria (Futuro)

Próxima versão incluirá logging:

```python
# data/auditoria.log (será criado)
# Conterá todos os eventos críticos:
# - Logins (sucesso/falha)
# - Criação/edição/exclusão de impressoras
# - Mudanças de configuração
# - Erros de sistema
```

---

## 🐛 TROUBLESHOOTING

### Erro: ADMIN_PASSWORD_HASH não definido

```
❌ ERRO CRÍTICO: Variável de ambiente ADMIN_PASSWORD_HASH não definida!
```

**Solução:**
```bash
# 1. Gerar hash
python3 generate_password_hash.py

# 2. Criar/editar .env
nano .env
# Colar: ADMIN_PASSWORD_HASH=$2b$12$...

# 3. Reiniciar
docker-compose down
docker-compose up -d
```

### Erro: Redis connection refused

```
WARNING: Sessions in filesystem mode (Redis unavailable)
```

**Solução:**
```bash
# Redis pode estar lento para iniciar
docker-compose down
docker-compose up -d

# Esperar 5 segundos
sleep 5

# Verificar status
docker-compose logs redis
```

### Erro: Permission denied (data/.vault_key)

```
PermissionError: [Errno 13] Permission denied: 'data/.vault_key'
```

**Solução (Linux/Mac):**
```bash
chmod 600 data/.vault_key
sudo chown $(whoami) data/.vault_key
```

**Solução (Docker):**
```bash
docker-compose down
docker-compose up -d
# Docker criará com permissões corretas
```

### Senhas antigas (XOR) não funcionam

Se migrou de versão anterior com XOR:

```python
# Compatibilidade: _deobfuscar_senha() tenta ambos:
# 1. Fernet (novo)
# 2. XOR (antigo)

# Para atualizar para Fernet:
# 1. Salvar configuração SMTP novamente
# 2. Nova senha será salva com Fernet
```

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- **[ANALISE_VULNERABILIDADES.md](ANALISE_VULNERABILIDADES.md)** — Análise técnica completa
- **[SECURITY_UPDATES.md](SECURITY_UPDATES.md)** — Mudanças detalhadas por arquivo
- **[MUDANCAS_SEGURANCA_VISUAL.md](MUDANCAS_SEGURANCA_VISUAL.md)** — Guia visual (recomendado!)
- **[.env.example](.env.example)** — Variáveis de ambiente

---

## ✅ CHECKLIST PRÉ-PRODUÇÃO

Antes de fazer deploy em produção:

- [ ] Gerar hash bcrypt com senha forte
- [ ] Criar arquivo `.env` com hash
- [ ] Adicionar `.env` ao `.gitignore`
- [ ] Testar login com nova senha
- [ ] Verificar headers HTTP (curl -I http://localhost)
- [ ] Fazer backup de `data/.vault_key`
- [ ] Documentar senha em local seguro (vault/1password)
- [ ] Configurar HTTPS com certificado válido
- [ ] Testar sessão persiste (restart container)
- [ ] Revisar logs (`docker-compose logs`)
- [ ] Teste de stress (múltiplas requisições)

---

## 🔐 BOAS PRÁTICAS

### 1. Senhas

✅ **FAÇA:**
- Use senhas com 12+ caracteres
- Misture maiúsculas, minúsculas, números, símbolos
- Use gerador de senhas (LastPass, 1Password, Bitwarden)
- Armazene em vault seguro
- Mude senha a cada 90 dias

❌ **NÃO FAÇA:**
- Deixar `.env` no repositório git
- Usar a mesma senha em múltiplos serviços
- Compartilhar senhas por email/chat
- Usar "admin123", "password", etc.

### 2. Criptografia

✅ **FAÇA:**
- Backup regular de `data/.vault_key`
- Armazenar backups offline/cloud seguro
- Rotacionar chaves periodicamente
- Usar HTTPS em produção

❌ **NÃO FAÇA:**
- Perder `data/.vault_key` (irrecuperável)
- Usar HTTP em rede pública
- Hardcodear senhas no código

### 3. Acesso

✅ **FAÇA:**
- Usar firewall para restringir IP
- Usar VPN para acesso remoto
- Monitorar logs de acesso
- 2FA quando possível

❌ **NÃO FAÇA:**
- Expor porta 5000 para internet
- Usar mesmo admin para múltiplos usuários
- Salvar cookies em computador público

---

## 📞 SUPORTE

Se encontrar problemas:

1. **Verificar logs:**
   ```bash
   docker-compose logs monitor-toner
   docker-compose logs redis
   ```

2. **Verificar status:**
   ```bash
   docker-compose ps
   docker-compose exec monitor-toner curl http://localhost/auth/status
   ```

3. **Reiniciar:**
   ```bash
   docker-compose restart
   ```

4. **Reset completo (⚠️ perde dados):**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

---

## 📈 PRÓXIMAS FASES

**v2.2.0 (Próxima semana):**
- [ ] Rate limiting em Redis
- [ ] Logging estruturado
- [ ] Validação de Webhook URL

**v2.3.0 (Próximo mês):**
- [ ] 2FA (Two-factor authentication)
- [ ] JWT tokens
- [ ] SNMP v3 com criptografia

**v2.4.0 (Futuro):**
- [ ] Auditoria completa
- [ ] Multi-tenant
- [ ] Integração OAuth2

---

## 📝 CHANGELOG

### v2.1.0 (28/04/2026)
- ✅ Corrigidas 4 vulnerabilidades críticas
- ✅ Implementado Fernet para criptografia
- ✅ Adicionado bcrypt para hashing
- ✅ Implementado Flask-Session com Redis
- ✅ Adicionados headers de segurança HTTP
- ✅ Validação rigorosa de input

---

**Versão:** 2.1.0-security  
**Última atualização:** 28/04/2026  
**Status:** ✅ Pronto para Produção (após HTTPS)
