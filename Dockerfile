FROM python:3.12-slim

# Evitar prompts interactivos de apt
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema:
# - ca-certificates: HTTPS seguro
# - postgresql-client: pg_dump/psql (backups)
# - ffmpeg: necesario para pydub + SpeechRecognition (audio webm/mp3/ogg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        postgresql-client \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (mejor cache de Docker)
COPY requirements.txt /app/requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar el resto del código del proyecto
COPY . /app

# Exponer puerto (Railway usará la variable PORT igualmente)
EXPOSE 8080

# Comando de arranque con Gunicorn.
# Usa la variable PORT si existe (Railway la inyecta), o 8080 por defecto.
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080}"]
