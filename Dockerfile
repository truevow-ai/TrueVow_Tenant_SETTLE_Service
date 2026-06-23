# TrueVow SETTLE-Service — Dockerfile
FROM python:3.13-slim

WORKDIR /app

# System libraries required by WeasyPrint (Pango/HarfBuzz/GDK-PixBuf) for PDF generation,
# plus build-essential to compile C extensions (e.g. pysha3 via opentimestamps)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz-subset0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libjpeg62-turbo \
        shared-mime-info \
        fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
