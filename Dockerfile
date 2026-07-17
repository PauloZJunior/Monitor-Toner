FROM python:3.11-slim

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código (data/ excluída via .dockerignore)
COPY . .

# Cria pasta de dados com permissões corretas
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 5000

# Verifica a cada 30s se o app está respondendo (via /healthz, sem SNMP).
# Usa o próprio Python em vez de curl/wget pra não precisar instalar nada
# a mais na imagem slim.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/healthz', timeout=3).status == 200 else 1)" || exit 1

CMD ["gunicorn", \
     "--workers", "1", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
