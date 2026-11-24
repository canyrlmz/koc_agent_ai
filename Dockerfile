# Farkora: sunucu (Render vb.) için kapsayıcı. Yerelde çalıştırmak için gerekmez.
FROM python:3.10-slim

# ffmpeg: video karesi ve fotoğraf işleme
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY run.py hesap.py ./

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PORT=10000
EXPOSE 10000

# Üretim: yeniden yükleme yok; HTTPS'i sağlayıcının vekil sunucusu karşılar
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
