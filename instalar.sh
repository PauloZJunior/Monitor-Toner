#!/bin/bash
# ============================================================
#  Monitor de Toner v2 — Script de Instalação
#  Ubuntu 22.04 / 24.04 com Docker
# ============================================================
set -e

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✔ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
erro() { echo -e "${RED}  ✘ $1${NC}"; exit 1; }

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     MONITOR DE TONER v2              ║"
echo "  ║     Instalação com Docker            ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# Verifica se está na pasta correta
[ ! -f "app.py" ] && erro "Execute este script dentro da pasta do projeto!"

# Instala Docker se necessário
if ! command -v docker &>/dev/null; then
    info "Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$USER"
    ok "Docker instalado"
else
    ok "Docker já instalado: $(docker --version)"
fi

# Instala docker compose plugin se necessário
if ! docker compose version &>/dev/null; then
    info "Instalando Docker Compose plugin..."
    apt-get install -y docker-compose-plugin 2>/dev/null || \
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
         -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
    ok "Docker Compose instalado"
else
    ok "Docker Compose: $(docker compose version)"
fi

# Cria pasta de dados
mkdir -p data
ok "Pasta data/ criada"

# Para container anterior se existir
docker compose down 2>/dev/null || true

# Build e sobe
info "Construindo imagem Docker..."
docker compose build --no-cache

info "Iniciando container..."
docker compose up -d

sleep 3

# Verifica se subiu
if docker compose ps | grep -q "Up\|running"; then
    IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}  ╔══════════════════════════════════════════╗"
    echo -e "  ║        INSTALAÇÃO CONCLUÍDA! ✔           ║"
    echo -e "  ╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Acesse: ${CYAN}http://$IP${NC}"
    echo ""
    echo -e "  Senha padrão admin: ${YELLOW}admin123${NC}"
    echo -e "  Para alterar: edite config.py e reconstrua"
    echo ""
    echo -e "  Comandos úteis:"
    echo -e "  ${YELLOW}docker compose logs -f${NC}          → ver logs"
    echo -e "  ${YELLOW}docker compose restart${NC}          → reiniciar"
    echo -e "  ${YELLOW}docker compose down${NC}             → parar"
    echo -e "  ${YELLOW}docker compose up -d --build${NC}    → atualizar após mudanças"
else
    erro "Container não iniciou. Veja os logs: docker compose logs"
fi
