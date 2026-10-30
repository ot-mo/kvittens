FROM python:3.12-slim

# DejaVu-typsnitt för åäö på bongarna, libusb för USB-skrivare
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core libusb-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

ENV DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
