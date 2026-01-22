FROM python:3.12-slim

# Instalace základních systémových knihoven pro kompilaci na ARM
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopírování seznamu závislostí
COPY requirements.txt .

# Instalace knihoven. Pokud instalace s hashy selže (časté na ARM), 
# skript hashe automaticky odstraní a zkusí to znovu.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (sed -i 's/ --hash=.*//g' requirements.txt && \
     sed -i 's/ \\//g' requirements.txt && \
     pip install --no-cache-dir -r requirements.txt)

# Kopírování kódu do kontejneru
COPY src/ /app/src/
COPY main.py /app/main.py

# Nastavení cest pro Python a data
ENV PYTHONPATH=/app/src
ENV DICOM_DATA_DIR=/app/data
ENV FLASK_HOST=0.0.0.0

EXPOSE 5000

CMD ["python", "/app/main.py"]