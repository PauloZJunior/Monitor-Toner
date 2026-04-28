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

CMD ["gunicorn", \
     "--workers", "1", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
