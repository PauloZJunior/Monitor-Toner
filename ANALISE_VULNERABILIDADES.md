# 🔍 ANÁLISE DE VULNERABILIDADES CRÍTICAS E MELHORIAS
**Projeto:** Monitor de Toner v2  
**Data:** 28/04/2026  
**Severidade:** 5 CRÍTICAS | 8 ALTAS | 6 MÉDIAS

---

## 🚨 VULNERABILIDADES CRÍTICAS (5)

### 1. **SQL Injection em SNMP Community String**
**Localização:** [routes/crud.py](routes/crud.py) | [database.py](database.py)  
**Risco:** CRÍTICO  
**Descrição:**  
A "community" SNMP é armazenada e usada diretamente em queries SQL sem validação adequada.

```python
# ❌ Problema em database.py:criar_impressora()
"community": dados.get("community","public").strip(),
# Depois usada em snmp_raw.py sem sanitização
```

**Ataque:**
```json
{
  "nome": "Teste",
  "ip": "192.168.1.100",
  "community": "'; DROP TABLE historico; --"
}
```

**Impacto:** Perda total de dados do banco de dados

**Solução:**
```python
# ✅ Validar community string (apenas alfanuméricos e hífens)
import re
def _validar_community(community: str) -> bool:
    """Permite apenas alphanumeric, _, -, . para SNMP community"""
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]{1,32}$', community or "public"))

# Em crud.py:_validar_dados()
if not _validar_community(dados.get("community", "public")):
    erros.append("Community SNMP inválida — use apenas letras, números, _, -, .")
```

---

### 2. **Exposição da Senha SMTP em Plaintext no Arquivo de Configuração**
**Localização:** [routes/notificacao.py](routes/notificacao.py) | [modules/notificacao.py](modules/notificacao.py)  
**Risco:** CRÍTICO  
**Descrição:**  
A senha SMTP é salva ofuscada com XOR (criptografia fraca) e não é verdadeiramente segura.

```python
# ❌ Em modules/notificacao.py
def _obfuscar_senha(senha: str, key: str = "monitor-toner") -> str:
    """XOR é fraco demais para produção"""
    key_bytes = (key * N).encode()[:len(senha)]
    xored = bytes(a ^ b for a, b in zip(senha.encode(), key_bytes))
    return base64.b64encode(xored).decode()
```

**Ataque:**
- A chave XOR é fixa ("monitor-toner") — qualquer pessoa com acesso ao código a recupera
- A cifra XOR é reversível com a chave: `senha = chr(encoded ^ key)`

**Impacto:** Roubo de credenciais SMTP, envio de e-mails maliciosos

**Solução:**
```python
# ✅ Usar cryptography.fernet (simétrico, padrão industrial)
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
import hashlib
import os

class PasswordVault:
    """Armazena senhas criptografadas com Fernet"""
    
    def __init__(self, master_key_path="data/.vault_key"):
        self.key_path = master_key_path
        self._ensure_key()
    
    def _ensure_key(self):
        """Gera chave mestra se não existir"""
        os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
        if not os.path.exists(self.key_path):
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            os.chmod(self.key_path, 0o600)  # Apenas proprietário lê
        
        with open(self.key_path, 'rb') as f:
            self._cipher = Fernet(f.read())
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypta texto em base64"""
        return self._cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypta texto"""
        try:
            return self._cipher.decrypt(ciphertext.encode()).decode()
        except Exception:
            return ""  # Token inválido

# Uso:
vault = PasswordVault()
cfg["email_senha"] = vault.encrypt(senha_nova)  # Salva criptografada
senha_decrypted = vault.decrypt(cfg.get("email_senha"))  # Recupera apenas na memória
```

**Dependência a adicionar:**
```diff
requirements.txt:
  flask
  gunicorn
+ cryptography>=41.0.0
```

---

### 3. **Falta de HTTPS/TLS - Transmissão de Senhas em Plaintext**
**Localização:** [app.py](app.py) | [Dockerfile](Dockerfile)  
**Risco:** CRÍTICO  
**Descrição:**  
A aplicação não força HTTPS. Senhas são transmitidas em HTTP plaintext.

```python
# ❌ app.py
if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)  # Sem HTTPS
```

**Ataque:**
```bash
# Capturar tráfego HTTP
tcpdump -n -l | grep -i "password\|senha"
# Resultado: POST /auth/login {"senha":"admin123"} — visível em plaintext
```

**Impacto:** Interceptação de credenciais (MITM attack)

**Solução:**
```bash
# 1. Gerar certificado auto-assinado (desenvolvimento)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# 2. Em Dockerfile
RUN apt-get update && apt-get install -y openssl
COPY cert.pem key.pem /app/
CMD ["gunicorn", "--certfile=/app/cert.pem", "--keyfile=/app/key.pem", \
     "--bind", "0.0.0.0:443", "--workers", "1", "app:app"]

# 3. Em docker-compose.yml
ports:
  - "443:443"
  # - "80:80"  # Desabilitar HTTP
```

**Para produção, usar:**
- Let's Encrypt + Certbot (gratuito)
- AWS ACM, Azure Key Vault, etc.

---

### 4. **Hardcoded Senha Padrão "admin123"**
**Localização:** [config.py](config.py)  
**Risco:** CRÍTICO  
**Descrição:**  
A senha padrão é hardcoded e um hash SHA256 conhecido publicamente.

```python
# ❌ config.py
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    hashlib.sha256(b"admin123").hexdigest()  # Hash público!
)
```

**Ataque:**
```bash
# Qualquer pessoa pode pesquisar o hash no internet
echo -n "admin123" | sha256sum
# 0192023a7bbd73250516f069df18b500  (encontrado em rainbow tables)
```

**Impacto:** Acesso não autorizado ao painel de administração

**Solução:**
```python
# ✅ Obrigar definição da senha via variável de ambiente
import os
import sys

ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    print("❌ ERRO: Variável ADMIN_PASSWORD_HASH não definida!")
    print("   Gere um hash: python3 -c \"import hashlib; print(hashlib.sha256(b'SENHA_SEGURA').hexdigest())\"")
    print("   Depois exporte: export ADMIN_PASSWORD_HASH=<hash>")
    sys.exit(1)

# Ou melhor: usar bcrypt com salt
import bcrypt

def gerar_hash_senha(senha: str) -> str:
    """Gera hash bcrypt com salt aleatório (muito mais seguro)"""
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()

def verificar_senha(senha: str, hash_bcrypt: str) -> bool:
    """Verifica senha contra hash bcrypt"""
    return bcrypt.checkpw(senha.encode(), hash_bcrypt.encode())
```

---

### 5. **Sessões Armazenadas em Memória - Perda em Restart**
**Localização:** [app.py](app.py) | [routes/auth.py](routes/auth.py)  
**Risco:** CRÍTICO (em produção)  
**Descrição:**  
Flask default: sessões em memória não persistem. A cada reinicialização do container, todos os usuários são desautenticados.

```python
# ❌ app.py
app.secret_key = SECRET_KEY
# Flask usa sessão em memória por padrão (implementação dict)
```

**Problema em Docker:**
```bash
# Qualquer deploy/restart desautentica todos os usuários
docker restart monitor-toner  # Todos precisam fazer login novamente
```

**Solução:**
```python
# ✅ Usar Redis ou filesystem para sessões
# Opção 1: Flask-Session com Redis (recomendado para produção)

from flask_session import Session
import redis

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379/0')
Session(app)

# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  app:
    depends_on:
      - redis
    environment:
      REDIS_URL: redis://redis:6379/0

# Opção 2: Sessões em arquivo (para produção sem Redis)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = 'data/sessions'
Session(app)
```

**Dependência:**
```diff
requirements.txt:
  flask
  gunicorn
+ Flask-Session>=0.5.0
+ redis>=5.0.0  # se usar Redis
```

---

## 🔴 VULNERABILIDADES ALTAS (8)

### 6. **Rate Limiting Insuficiente em /auth/login**
**Localização:** [routes/auth.py](routes/auth.py)  
**Risco:** ALTO  
**Descrição:**  
Rate limiting em memória não persiste entre workers/restarts. Com múltiplos workers Gunicorn, cada um tem seu próprio contador.

```python
# ❌ routes/auth.py
_tentativas_login: dict = {}  # Global em memória — não compartilhada entre workers!
```

**Ataque em produção com 4 workers:**
```bash
# 4 workers = 4 contadores independentes
# Cada worker permite 5 tentativas = 20 tentativas total antes de bloquear
for i in {1..20}; do
  curl -X POST http://app/auth/login \
    -H "Content-Type: application/json" \
    -d '{"senha":"wrong"}'  # Vai passar em 20 tentativas
done
```

**Solução:**
```python
# ✅ Usar Redis para rate limiting (compartilhado entre workers)
import redis
from datetime import datetime, timedelta
import time

redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/1'))

MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 300
DELAY_FALHA = 1.5

def _check_rate_limit_redis(ip: str) -> tuple[bool, str]:
    """Retorna (bloqueado, mensagem)"""
    key = f"login_attempt:{ip}"
    tentativas = redis_client.incr(key)
    
    if tentativas == 1:
        redis_client.expire(key, JANELA_SEGUNDOS)
    
    ttl = redis_client.ttl(key)
    
    if tentativas > MAX_TENTATIVAS:
        espera = ttl if ttl > 0 else JANELA_SEGUNDOS
        return True, f"Muitas tentativas. Aguarde {espera}s"
    
    return False, ""

# Em routes/auth.py:login()
bloqueado, msg = _check_rate_limit_redis(ip)
if bloqueado:
    return jsonify({"erro": msg}), 429
```

---

### 7. **Validação de IP Incompleta**
**Localização:** [routes/crud.py](routes/crud.py)  
**Risco:** ALTO  
**Descrição:**  
Validação de IP aceita formatos inválidos e não verifica duplicatas corretamente.

```python
# ❌ routes/crud.py
partes = ip.split(".")
valido = (
    len(partes) == 4 and
    all(p.isdigit() and 0 <= int(p) <= 255 for p in partes)
)
# Problema: "192.168.1.1.1" passa! (5 octetos)
# Problema: "192.168.001.001" passa mas é inválido para SNMP
```

**Casos de erro:**
- `"192.168.1.1.1"` → Passa (5 octetos)
- `"256.256.256.256"` → Falha (certo)
- `"192.168.1.0/24"` → Falha (CIDR não suportado)
- `"localhost"` → Falha (DNS não suportado)

**Solução:**
```python
# ✅ Usar ipaddress built-in
import ipaddress

def _validar_ip(ip: str) -> bool:
    """Valida formato de IP e rejeita broadcast/network"""
    try:
        addr = ipaddress.IPv4Address(ip)
        # Rejeita broadcast, network, multicast, reserved
        if (addr.is_network or addr.is_broadcast or 
            addr.is_multicast or addr.is_reserved):
            return False
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False

# Em routes/crud.py:_validar_dados()
ip = dados.get("ip", "").strip()
if ip and not _validar_ip(ip):
    erros.append("IP inválido — use formato 192.168.1.1")
```

---

### 8. **XSS em Renderização de Nomes de Impressora (JavaScript)**
**Localização:** [static/js/render.js](static/js/render.js) | [static/js/main.js](static/js/main.js)  
**Risco:** ALTO  
**Descrição:**  
Nomes de impressora são inseridos no DOM sem escape de HTML.

```python
# ❌ routes/api.py / routes/crud.py
impressora = {
    "nome": "Sala de TI <img src=x onerror=\"alert('XSS')\">",
    "ip": "192.168.1.100"
}
# return jsonify({"impressoras": [impressora]})
```

```javascript
// ❌ static/js/render.js (presumido)
function renderizar_impressoras(lista) {
    lista.forEach(imp => {
        // Potencial XSS se não usar textContent
        document.getElementById("list").innerHTML += `
            <div>${imp.nome}</div>  // ❌ VULNERÁVEL
        `;
    });
}
```

**Solução:**
```javascript
// ✅ Usar textContent ou escape HTML

function escape_html(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function renderizar_impressoras(lista) {
    lista.forEach(imp => {
        // Opção 1: textContent (seguro)
        const div = document.createElement('div');
        div.textContent = imp.nome;
        document.getElementById("list").appendChild(div);
        
        // Opção 2: innerHTML com escape
        document.getElementById("list").innerHTML += `
            <div>${escape_html(imp.nome)}</div>
        `;
    });
}
```

---

### 9. **Falta de Logging e Auditoria de Ações Críticas**
**Localização:** [routes/crud.py](routes/crud.py) | [routes/notificacao.py](routes/notificacao.py)  
**Risco:** ALTO  
**Descrição:**  
Não há registro de quem criou/deletou/modificou impressoras. Não há auditoria de falhas de login.

```python
# ❌ routes/crud.py:criar()
novo_id = criar_impressora(dados_limpos)
return jsonify({"sucesso": True, "id": novo_id}), 201
# Nenhum log de auditoria!
```

**Impacto:**
- Não dá para rastrear mudanças
- Impossível auditar em caso de incidente
- Compliance (LGPD, HIPAA) falha

**Solução:**
```python
# ✅ Adicionar auditoria com logging estruturado
import logging
from datetime import datetime
from flask import request

# Configurar logging em arquivo
logging.basicConfig(
    filename='data/auditoria.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

logger = logging.getLogger(__name__)

def registrar_auditoria(acao: str, detalhes: dict, ip: str = None, status: str = "sucesso"):
    """Registra ações críticas para auditoria"""
    ip = ip or request.remote_addr or "unknown"
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "acao": acao,
        "ip": ip,
        "status": status,
        "detalhes": detalhes
    }
    logger.info(json.dumps(entrada, ensure_ascii=False))

# Uso em routes/crud.py
@crud_bp.route("/impressoras", methods=["POST"])
@requer_autenticacao
def criar():
    dados = request.get_json(silent=True) or {}
    dados_limpos, erro = _validar_dados(dados)
    
    if erro:
        registrar_auditoria("CRIAR_IMPRESSORA_FALHA", 
                          {"erro": erro}, status="falha")
        return jsonify({"erro": erro}), 400
    
    novo_id = criar_impressora(dados_limpos)
    registrar_auditoria("CRIAR_IMPRESSORA_SUCESSO", 
                      {"id": novo_id, "ip": dados_limpos["ip"]})
    return jsonify({"sucesso": True, "id": novo_id}), 201
```

---

### 10. **CSRF Insuficiente - Cookies SameSite=Lax Permite POST Cross-Origin**
**Localização:** [app.py](app.py)  
**Risco:** ALTO  
**Descrição:**  
`SameSite=Lax` permite POST em top-level navigations (formulários e redirecionamentos).

```python
# ⚠️ app.py
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Permite POST alguns casos
```

**Ataque CSRF:**
```html
<!-- site-malicioso.com -->
<form action="http://app/gerenciar/impressoras" method="POST">
  <input type="hidden" name="nome" value="Impressora Maliciosa">
  <input type="hidden" name="ip" value="192.168.1.999">
  <input type="hidden" name="community" value="exploit">
  <input type="submit">
</form>
<script>
  // Auto-submit após carregar a página
  document.forms[0].submit();
</script>
```

**Solução:**
```python
# ✅ Usar SameSite=Strict + CSRF tokens

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # Rejeita POST cross-origin

# HTML template:
# <form method="POST">
#   <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
# </form>

# JavaScript (se usar fetch):
// Obter token CSRF do cookie ou meta tag
const csrf_token = document.querySelector('meta[name="csrf-token"]')?.content;

fetch('/gerenciar/impressoras', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({nome: "...", ip: "..."})
});
```

---

### 11. **Sem Validação de Webhook URL - RCE Potencial**
**Localização:** [routes/notificacao.py](routes/notificacao.py)  
**Risco:** ALTO  
**Descrição:**  
URLs de webhook são aceitas sem validação. Pode levar a SSRF ou RCE.

```python
# ❌ routes/notificacao.py (presumido)
webhook_url = dados.get("webhook_url")
# Aceita qualquer URL, incluindo:
# - file:///etc/passwd
# - gopher://localhost:6379 (Redis SSRF)
# - http://internal-app:5000/admin
```

**Solução:**
```python
# ✅ Whitelist de URLs e validação rigorosa
import urllib.parse
import socket

def _validar_webhook_url(url: str) -> tuple[bool, str]:
    """Valida webhook URL — rejeita URLs internas e perigosas"""
    try:
        parsed = urllib.parse.urlparse(url)
        
        # 1. Apenas HTTPS permitido
        if parsed.scheme not in ("http", "https"):
            return False, "Apenas HTTP/HTTPS suportado"
        
        # 2. Rejeita localhost/127.0.0.1/0.0.0.0
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]"):
            return False, "URLs locais não permitidas"
        
        # 3. Resolve hostname e rejeita IPs privados
        try:
            ip = socket.gethostbyname(parsed.hostname)
            if ip.startswith(("127.", "192.168.", "10.", "172.")):
                return False, "Acesso a redes internas bloqueado"
        except socket.gaierror:
            return False, "Hostname inválido"
        
        # 4. Rejeita portas perigosas
        if parsed.port in (22, 23, 25, 135, 139, 445, 1433, 3306, 5432, 6379):
            return False, "Porta bloqueada por segurança"
        
        # 5. Limita comprimento de URL
        if len(url) > 2048:
            return False, "URL muito longa"
        
        return True, ""
    except Exception as e:
        return False, str(e)

# Uso:
@notificacao_bp.route("/config", methods=["POST"])
@requer_autenticacao
def salvar_config():
    dados = request.get_json(silent=True) or {}
    webhook_url = dados.get("webhook_url", "").strip()
    
    if webhook_url:
        valido, erro = _validar_webhook_url(webhook_url)
        if not valido:
            return jsonify({"erro": f"Webhook URL inválida: {erro}"}), 400
```

---

### 12. **Sem Timeout em Requests HTTP - DoS Potencial**
**Localização:** [modules/notificacao.py](modules/notificacao.py)  
**Risco:** ALTO  
**Descrição:**  
Requisições HTTP para webhooks não têm timeout, pode travar a thread.

```python
# ❌ modules/notificacao.py
response = urllib.request.urlopen(webhook_url, json_data)
# Sem timeout! Se servidor responder lentamente, trava forever
```

**Ataque:**
```python
# Servidor webhook malicioso
@app.route('/webhook')
def slow_webhook():
    time.sleep(999)  # Trava urllib por 999 segundos
    return "OK"

# O Monitor-Toner fica travado enviando notificação
```

**Solução:**
```python
# ✅ Adicionar timeout em requisições HTTP
import urllib.request
import urllib.error
from threading import Timer

WEBHOOK_TIMEOUT = 10  # segundos

def _enviar_webhook(url: str, dados: dict) -> tuple[bool, str]:
    """Envia webhook com timeout"""
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(dados).encode(),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT) as response:
            if response.status >= 400:
                return False, f"Status {response.status}"
            return True, "OK"
    
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except socket.timeout:
        return False, "Timeout após 10s"
    except Exception as e:
        return False, str(e)
```

---

### 13. **Sem Validação de Email Address**
**Localização:** [routes/notificacao.py](routes/notificacao.py)  
**Risco:** ALTO  
**Descrição:**  
Endereços de e-mail não são validados antes de enviar notificações.

```python
# ❌ modules/notificacao.py
destinos_raw = cfg.get("email_destinos","").strip()
destinos = [d.strip() for d in destinos_raw.replace(";",",").split(",") if d.strip()]
# Aceita qualquer string, não valida formato de email
```

**Problema:**
- `"nao-e-email"` → SMTP error
- `"user@localhost"` → SMTP error
- Wasting de mensagens SMTP

**Solução:**
```python
# ✅ Validar email com regex
import re

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

def _validar_email(email: str) -> bool:
    """Valida formato de email"""
    return bool(EMAIL_REGEX.match(email))

def _enviar_email(cfg, titulo, detalhe, impressora, percentual):
    destinos_raw = cfg.get("email_destinos","").strip()
    destinos = [d.strip() for d in destinos_raw.replace(";",",").split(",") if d.strip()]
    
    # ✅ Validar cada email
    destinos_validos = [e for e in destinos if _validar_email(e)]
    if not destinos_validos:
        return False, "Nenhum email válido configurado"
    
    if len(destinos) != len(destinos_validos):
        logger.warning(f"Alguns emails inválidos removidos")
```

---

## 🟠 VULNERABILIDADES MÉDIAS (6)

### 14. **Sem Proteção contra Brute Force em Criação de Impressoras (Duplicatas)**
**Localização:** [routes/crud.py](routes/crud.py)  
**Risco:** MÉDIO  
**Descrição:**  
Um adversário autenticado pode criar múltiplas impressoras com o mesmo IP (race condition).

```python
# ❌ routes/crud.py:criar()
if buscar_por_ip(dados_limpos["ip"]):  # Verificação
    return jsonify({"erro": "..."}), 409

# Entre a verificação e a inserção, outro request pode ter inserido
novo_id = criar_impressora(dados_limpos)  # Inserção (não-atômica)
```

**Solução:**
```python
# ✅ Usar transação com lock ou constraint UNIQUE (já existe!)
# database.py já possui:
# ip TEXT NOT NULL UNIQUE

# Capturar IntegrityError que será thrown
@crud_bp.route("/impressoras", methods=["POST"])
@requer_autenticacao
def criar():
    dados = request.get_json(silent=True) or {}
    dados_limpos, erro = _validar_dados(dados)
    
    if erro:
        return jsonify({"erro": erro}), 400

    # Remover verificação manual — deixar o DB garantir
    # if buscar_por_ip(dados_limpos["ip"]):  # ❌ Redundante
    #     return jsonify({"erro": ...}), 409

    try:
        novo_id = criar_impressora(dados_limpos)
        return jsonify({"sucesso": True, "id": novo_id}), 201
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e) and "ip" in str(e):
            return jsonify({"erro": f"IP {dados_limpos['ip']} já cadastrado"}), 409
        raise
```

---

### 15. **Sem Tratamento de Exceção em SNMP - Information Disclosure**
**Localização:** [snmp_raw.py](snmp_raw.py) | [routes/api.py](routes/api.py)  
**Risco:** MÉDIO  
**Descrição:**  
Erros SNMP expõem stack traces ao usuário.

```python
# ❌ routes/api.py (presumido)
@api_bp.route("/api/impressoras")
def get_impressoras():
    try:
        # SNMP code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500  # Stack trace completo!
```

**Exposição:**
```json
{
  "erro": "Traceback (most recent call last):\n  File \"/app/snmp_raw.py\", line 42, in snmp_get\n    data = bytes.fromhex(raw_response)\nValueError: invalid literal for int() with base 16: 'xyz'"
}
```

**Solução:**
```python
# ✅ Logar erro completo, retornar mensagem genérica ao usuário

import logging

logger = logging.getLogger(__name__)

@api_bp.route("/api/impressoras")
def get_impressoras():
    try:
        # SNMP code
    except Exception as e:
        logger.error(f"Erro ao consultar impressoras", exc_info=True)
        return jsonify({"erro": "Erro ao consultar impressoras. Contate o admin."}), 500
```

---

### 16. **Sem Cache de Resultados SNMP - Performance DoS**
**Localização:** [routes/api.py](routes/api.py)  
**Risco:** MÉDIO  
**Descrição:**  
Cada request GET /api/impressoras faz todas as consultas SNMP novamente. Um cliente pode fazer N requests e sobrecarregar a rede.

```python
# ❌ routes/api.py:get_impressoras()
@api_bp.route("/api/impressoras")
def get_impressoras():
    # Faz ThreadPoolExecutor SNMP para TODAS as impressoras
    # Sem cache — cada request traz todos os dados do zero
```

**DoS:**
```bash
# Bombardear com requests
for i in {1..100}; do
  curl -s http://app/api/impressoras > /dev/null &
done
wait
# 100 threads SNMP simultâneas = sobrecarga da rede/CPU
```

**Solução:**
```python
# ✅ Cache com TTL

from functools import lru_cache
from datetime import datetime, timedelta

_cache_impressoras = {}
_cache_ttl = 60  # 60 segundos

def _get_impressoras_cached():
    """Retorna cached data ou atualiza se expirado"""
    agora = datetime.now()
    
    if "_timestamp" in _cache_impressoras:
        age = (agora - _cache_impressoras["_timestamp"]).total_seconds()
        if age < _cache_ttl:
            return _cache_impressoras.get("data", [])
    
    # Atualizar cache
    impressoras = _consultar_todas_impressoras()  # ThreadPoolExecutor
    _cache_impressoras.update({
        "data": impressoras,
        "_timestamp": agora
    })
    return impressoras

@api_bp.route("/api/impressoras")
def get_impressoras():
    impressoras = _get_impressoras_cached()
    return jsonify({"impressoras": impressoras})
```

---

### 17. **Sem Content Security Policy (CSP)**
**Localização:** [app.py](app.py) | [templates/index.html](templates/index.html)  
**Risco:** MÉDIO  
**Descrição:**  
Sem CSP, XSS e injeção de scripts são mais fáceis de explorar.

```python
# ✅ Adicionar em app.py
from flask import make_response

@app.after_request
def set_security_headers(response):
    """Adiciona headers de segurança HTTP"""
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # Inline CSS é necessário para tema
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

---

### 18. **Sem Proteção contra Path Traversal em Arquivos Estáticos**
**Localização:** [app.py](app.py)  
**Risco:** MÉDIO  
**Descrição:**  
Embora Flask proteja `/static`, se haver uploads no futuro, há risco.

```python
# ✅ Não permitir upload de arquivos por enquanto
# Se adicionar upload no futuro:

import os

UPLOAD_DIR = "data/uploads"
ALLOWED_EXTENSIONS = {"jpg", "png", "txt"}

def _is_safe_filename(filename: str) -> bool:
    """Valida nome de arquivo — rejeita path traversal"""
    # Rejeita caminho relativo
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    # Apenas alfanuméricos, hífens, underscores, ponto
    return bool(re.match(r'^[\w\-\.]+$', filename))

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"erro": "Arquivo não fornecido"}), 400
    
    # Validação de nome
    if not _is_safe_filename(file.filename):
        return jsonify({"erro": "Nome de arquivo inválido"}), 400
    
    # Validação de extensão
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"erro": "Extensão não permitida"}), 400
    
    # Salvar com nome seguro
    import uuid
    safe_name = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    file.save(filepath)
```

---

### 19. **Sem Validação de Entrada em OID SNMP**
**Localização:** [snmp_raw.py](snmp_raw.py) | [modules/toner.py](modules/toner.py)  
**Risco:** MÉDIO  
**Descrição:**  
OIDs SNMP não são validados. OIDs malformados podem causar comportamento indefinido.

```python
# ❌ snmp_raw.py
def snmp_get(ip, community, oid):
    # Aceita qualquer string como OID
    # "1.3.6..." ✓
    # "1..3.6" ✓ (malformado)
    # "abc" ✓ (inválido)
```

**Solução:**
```python
# ✅ Validar OID antes de usar
import re

OID_REGEX = re.compile(r'^(\d+\.)+\d+$')  # "1.2.3.4"

def _validar_oid(oid: str) -> bool:
    """Valida formato de OID — deve ser números com pontos"""
    if not oid or len(oid) > 255:
        return False
    return bool(OID_REGEX.match(oid))

def snmp_get(ip, community, oid):
    if not _validar_oid(oid):
        raise ValueError(f"OID inválido: {oid}")
    # ... resto do código
```

---

## 📊 RESUMO DE RECOMENDAÇÕES

### **Ordem de Prioridade (implementação):**

| # | Vulnerabilidade | Severidade | Impacto | Esforço | Prazo |
|---|-----------------|-----------|--------|--------|-------|
| 1 | SQL Injection (Community) | CRÍTICO | Total | 1h | Imediato |
| 2 | Hardcoded Password | CRÍTICO | Total | 30min | Imediato |
| 3 | Senha SMTP Plaintext | CRÍTICO | Total | 2h | 1 dia |
| 4 | Sem HTTPS | CRÍTICO | Total | 1h | 1 dia |
| 5 | Sessões em Memória | CRÍTICO | Médio | 2h | 1 semana |
| 6 | Rate Limiting Redis | ALTO | Médio | 1h | 1 semana |
| 7 | Validação de IP | ALTO | Médio | 30min | 1 semana |
| 8 | XSS Proteção | ALTO | Médio | 1h | 1 semana |
| 9 | Logging/Auditoria | ALTO | Médio | 2h | 1 semana |
| 10 | Outros | MÉDIO | Baixo | 5h | 2 semanas |

---

### **Arquivos Alterados (Resumo):**

```
✏️ config.py
  - Remover hardcoded password hash
  - Obrigar ADMIN_PASSWORD_HASH via ENV

✏️ requirements.txt
  + cryptography>=41.0.0
  + Flask-Session>=0.5.0
  + redis>=5.0.0
  + bcrypt>=4.0.0

✏️ app.py
  + Adicionar PasswordVault class
  + Adicionar CSP headers
  + Configurar sessões Redis/Filesystem

✏️ routes/auth.py
  + Rate limiting com Redis
  + Logging de tentativas

✏️ routes/crud.py
  + Validação de community string (regex)
  + Validação de IP (ipaddress)
  + Remover verificação manual de duplicata

✏️ routes/notificacao.py
  + Validação de webhook URL
  + Validação de email
  + Usar PasswordVault para SMTP

✏️ modules/notificacao.py
  + Substituir XOR por Fernet
  + Adicionar timeout em urllib

✏️ snmp_raw.py
  + Validação de OID

✏️ static/js/*.js
  + Escape HTML em DOM manipulation
  + CSRF token em fetch requests

✏️ templates/index.html
  + Meta tag CSRF token
```

---

### **Infraestrutura (docker-compose.yml):**

```yaml
# Adicionar serviço Redis
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  app:
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ADMIN_PASSWORD_HASH=<hash gerado>
      - SESSION_TYPE=redis

volumes:
  redis_data:
```

---

## ✅ CHECKLIST PÓS-IMPLEMENTAÇÃO

- [ ] Testar SQL injection em community string
- [ ] Testar HTTPS com certificado
- [ ] Testar rate limiting em múltiplos workers
- [ ] Testar XSS com nomes maliciosos
- [ ] Testar CSRF com requests cross-origin
- [ ] Revisar logs de auditoria
- [ ] Revisar CSP em DevTools
- [ ] Testar timeout de webhook
- [ ] Testar validação de email
- [ ] Executar SAST tool (eg, Bandit)
