# Monitor de Toner

Painel web para monitoramento de nível de toner/tinta de impressoras de rede via SNMP, com histórico, previsão de esgotamento, notificações por e-mail/webhook e exportação de dados.

Feito para ambientes com múltiplas impressoras de fabricantes diferentes (Samsung, Brother, Ricoh, Epson e modelos genéricos compatíveis com Printer-MIB), incluindo suporte a impressoras de etiqueta (monitoradas apenas por conectividade TCP).

---

## Funcionalidades

- **Leitura de toner/tinta via SNMP puro** (sem dependências externas tipo `pysnmp`) — v1 e v2c, com detecção automática e cache da versão que funciona por IP.
- **Suporte multi-fabricante**: Samsung/genéricos (Printer-MIB padrão), Brother (OIDs proprietários + fallback por status), Ricoh SP, Epson (múltiplas cores de tinta).
- **Impressoras de etiqueta**: monitoradas só por conectividade (TCP nas portas comuns de impressão, com fallback ICMP/SNMP), já que normalmente não expõem nível de suprimento.
- **Histórico e previsão**: guarda leituras no SQLite e estima em quantos dias o toner deve acabar, por regressão linear simples sobre as últimas leituras.
- **Notificações**: e-mail (SMTP/TLS) e webhook (Microsoft Teams, Slack ou genérico), com controle de nível de alerta e intervalo mínimo entre avisos (evita spam).
- **Exportação CSV** do status atual de todas as impressoras.
- **"Despertar" impressoras** — tenta reativar equipamentos em modo de economia de energia.
- **Autenticação simples por senha** (bcrypt) para operações de gerenciamento (cadastrar/editar/excluir impressoras e mexer nas notificações). A visualização do painel é sempre pública.
- **Tema claro/escuro**, com preferência salva no navegador.
- Interface totalmente responsiva, sem frameworks de frontend (HTML + CSS + JS puro).

---

## Stack

| Camada         | Tecnologia                                   |
|----------------|-----------------------------------------------|
| Backend        | Python 3.11 + Flask                          |
| SNMP           | Implementação própria via UDP puro (`snmp_raw.py`) — sem `pysnmp`/`net-snmp` |
| Banco de dados | SQLite (modo WAL)                            |
| Sessão         | Flask-Session (filesystem)                    |
| Senhas/segredos| bcrypt (senha admin) + Fernet/`cryptography` (senha SMTP) |
| Servidor WSGI  | Gunicorn                                      |
| Deploy         | Docker + Docker Compose, atrás de Traefik    |
| Frontend       | HTML/CSS/JS puro, modular (sem build step)   |

---

## Estrutura do projeto

```
Monitor-Toner/
├── app.py                    # Ponto de entrada Flask
├── config.py                 # Configurações, OIDs SNMP, constantes
├── database.py                # Acesso ao SQLite (impressoras, histórico, notificações)
├── snmp_raw.py                 # Cliente SNMP v1/v2c via UDP puro
├── modules/
│   ├── toner.py               # Leitura de toner/tinta por fabricante
│   ├── historico.py            # Histórico e previsão de esgotamento
│   ├── notificacao.py          # E-mail e webhook
│   └── wake.py                  # "Despertar" impressoras
├── routes/
│   ├── api.py                   # Consulta SNMP, resumo, exportação, despertar
│   ├── crud.py                   # Cadastro/edição/exclusão de impressoras
│   ├── auth.py                    # Login/logout/status de sessão
│   ├── historico.py                # Histórico detalhado por impressora
│   └── notificacao.py               # Configuração de notificações
├── static/
│   ├── css/main.css               # Todo o estilo da aplicação
│   └── js/                         # Módulos JS (state, api, render, events, crud, etc.)
├── templates/index.html            # Único template HTML
└── docker-compose.yml
```

---

## Como rodar

### Com Docker (recomendado)

1. Gere o hash bcrypt da senha de administrador:
   ```bash
   python3 -c "import bcrypt; print(bcrypt.hashpw(b'SUA_SENHA_AQUI', bcrypt.gensalt(rounds=12)).decode())"
   ```
2. Crie um arquivo `.env` na raiz do projeto:
   ```env
   ADMIN_PASSWORD_HASH=<hash gerado no passo anterior>
   ```
3. Suba o container:
   ```bash
   docker compose up -d --build
   ```

O `docker-compose.yml` já vem configurado para rodar atrás de um Traefik externo (rede `traefik`, roteamento por `Host`). Se for expor a porta diretamente, descomente o bloco `ports` no compose.

> **Rede**: o SNMP precisa alcançar as impressoras na rede local. Em Linux, isso geralmente exige `network_mode: host` (comentado no compose) — no Windows/Mac com Docker Desktop isso não funciona; nesse caso, use uma rede bridge com rota para a VLAN das impressoras.

### Localmente, sem Docker

```bash
pip install -r requirements.txt
export ADMIN_PASSWORD_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'SUA_SENHA', bcrypt.gensalt(rounds=12)).decode())")
python3 app.py
```

Acesse em `http://localhost:5000`.

---

## Configuração

### Cadastrando impressoras

Pelo botão **Gerenciar** no painel (requer login com a senha de administrador). Campos: nome, IP, modelo, tipo (`toner` ou `etiqueta`), setor, empresa, número de série, MAC e community SNMP (padrão `public`).

O fabricante é detectado automaticamente a partir do texto digitado em "Modelo" (procura por `brother`, `ricoh` ou `epson`; qualquer outro texto cai no modo padrão/Samsung via Printer-MIB).

### Notificações

Pelo botão **Alertas**, configure:
- **E-mail**: servidor SMTP, porta, usuário, senha (criptografada em disco com Fernet — nunca fica em texto puro), lista de destinatários, uso de TLS.
- **Webhook**: URL e tipo (Microsoft Teams, Slack ou payload JSON genérico).
- **Nível de alerta**: a partir de qual status (médio, baixo ou crítico) começar a notificar.
- **Intervalo mínimo**: horas entre alertas repetidos da mesma impressora, para não gerar spam.

### Variáveis de ambiente

| Variável              | Obrigatória | Descrição                                            |
|------------------------|:-----------:|-------------------------------------------------------|
| `ADMIN_PASSWORD_HASH`  | ✅          | Hash bcrypt da senha de administrador                 |
| `SECRET_KEY`           | –           | Chave de sessão Flask. Se omitida, é gerada e persistida em `data/.secret_key` |

---

## API

Todas as rotas de leitura são públicas; as de escrita (cadastro/edição/exclusão de impressoras e configuração de notificações) exigem sessão autenticada via `/auth/login`.

| Método | Rota                          | Descrição                                      |
|--------|-------------------------------|--------------------------------------------------|
| GET    | `/api/impressoras`            | Consulta todas as impressoras via SNMP e retorna status + resumo |
| GET    | `/api/impressoras/<ip>/status`| Consulta uma impressora específica              |
| POST   | `/api/despertar`               | Tenta "acordar" todas as impressoras            |
| GET    | `/api/exportar/csv`             | Exporta status atual em CSV                     |
| GET    | `/api/debug`                     | Diagnóstico (somente acesso local)              |
| GET    | `/gerenciar/impressoras`         | Lista impressoras (inclui inativas)             |
| GET    | `/gerenciar/impressoras/<id>`    | Busca uma impressora                            |
| POST   | `/gerenciar/impressoras` 🔒      | Cadastra impressora                             |
| PUT    | `/gerenciar/impressoras/<id>` 🔒 | Atualiza impressora                             |
| DELETE | `/gerenciar/impressoras/<id>` 🔒 | Remove impressora                               |
| GET    | `/historico/impressoras/<id>`   | Histórico detalhado + previsão de esgotamento   |
| GET    | `/notificacao/config`           | Retorna configuração de notificações            |
| POST   | `/notificacao/config` 🔒        | Salva configuração de notificações              |
| POST   | `/notificacao/testar/email` 🔒  | Envia e-mail de teste                           |
| POST   | `/notificacao/testar/webhook` 🔒| Envia webhook de teste                          |
| POST   | `/auth/login`                   | Autentica (rate limit: 5 tentativas / 5 min por IP) |
| POST   | `/auth/logout`                  | Encerra sessão                                  |
| GET    | `/auth/status`                  | Verifica se a sessão está autenticada           |

🔒 = requer autenticação

---

## Segurança

- Senha de administrador armazenada apenas como hash bcrypt (nunca em texto puro).
- Senha de SMTP criptografada em disco com Fernet (chave própria em `data/.vault_key`, permissão `600`).
- Rate limiting de login (5 tentativas / 5 minutos por IP) com delay progressivo em falhas.
- Headers de segurança HTTP (CSP, `X-Frame-Options`, `X-Content-Type-Options`, HSTS) aplicados em todas as respostas.
- Validação de IP e de *community string* SNMP no cadastro de impressoras (evita valores que poderiam ser usados para injeção).
- Aplicação espera rodar atrás de um proxy reverso (Traefik) — o app já usa `ProxyFix` para reconhecer o IP real do cliente a partir do cabeçalho `X-Forwarded-For`.

---

## Licença

Defina a licença que preferir (MIT, uso interno, etc.) — não incluída por padrão.
