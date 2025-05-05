# app/rabbitmq_consumer.py
import json
import sys
import os
import asyncio
import time
import logging

import pika
from pika.exceptions import AMQPConnectionError
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# Proje dizinlerini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# FastAPI WebSocket yöneticisi
from app.routes.websocket import manager

load_dotenv()

# Uvicorn’un stderr/stdout’unu kullanan logger
logger = logging.getLogger("uvicorn.error")

# Çevresel değişkenlerden alınan ayarlar
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
DB_HOST      = os.getenv("DB_HOST")
DB_PORT      = os.getenv("DB_PORT")
DB_NAME      = os.getenv("DB_NAME")
DB_USER      = os.getenv("DB_USER")
DB_PASSWORD  = os.getenv("DB_PASSWORD")

WHO_THRESHOLDS = {
    "PM2.5": 25,
    "PM10":  50,
    "NO2":   200,
    "SO2":    20,
    "O3":    100,
}

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def get_average_last_24h(param: str, lat: float, lon: float) -> float:
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT AVG(value) FROM pollution_data
             WHERE parameter = %s
               AND latitude  BETWEEN %s AND %s
               AND longitude BETWEEN %s AND %s
               AND timestamp > NOW() - INTERVAL '24 hours'
        """, (
            param,
            lat - 0.1, lat + 0.1,
            lon - 0.1, lon + 0.1
        ))
        avg = cur.fetchone()[0]
        cur.close()
        conn.close()
        return avg or 0.0
    except Exception as e:
        logger.error("📛 Ortalama hesaplama hatası: %s", e)
        return 0.0

def check_anomaly(data: dict) -> bool:
    thr = WHO_THRESHOLDS.get(data["parameter"].upper())
    return thr is not None and data["value"] > thr

async def broadcast_anomaly_message(message: str):
    logger.info("📤 [broadcast()] Mesaj gönderiliyor: %s", message)
    await manager.broadcast(message)

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        logger.info("📦 Yeni veri alındı: %s", data)

        # timestamp yoksa şimdiki zamanı ekle
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()

        # 24h ortalama kontrolü
        avg24 = get_average_last_24h(
            data["parameter"],
            data["latitude"],
            data["longitude"]
        )

        json_data = json.dumps(data)

        # Ortalama üstü anomali
        if avg24 > 0 and data["value"] > avg24 * 1.5:
            logger.warning("⚠️ ORTALAMA ÜSTÜ ANOMALİ: %s", data)
            asyncio.run(broadcast_anomaly_message(json_data))

        # WHO eşiği aşıldı
        if check_anomaly(data):
            logger.warning("⚠️ WHO EŞİĞİ AŞILDI: %s", data)
            asyncio.run(broadcast_anomaly_message(json_data))

        # Veritabanına kaydet
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO pollution_data
              (latitude, longitude, parameter, value, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data["latitude"],
            data["longitude"],
            data["parameter"],
            data["value"],
            data["timestamp"]
        ))
        conn.commit()
        cur.close()
        conn.close()

        logger.info("✅ Veri kaydedildi: %s", data)

    except Exception as e:
        logger.error("❌ Hata oluştu: %s", e)

def start_consuming(loop=None):
    """
    Eğer startup_event içinden geliyorsa loop parametresi
    FastAPI ana loop'u olur; broadcasting için
    asyncio.run yerine loop.create_task de kullanılabilir.
    Biz burada basit kalıyoruz.
    """
    params = pika.URLParameters(RABBITMQ_URL)

    # RabbitMQ hazır olana kadar retry döngüsü
    while True:
        try:
            connection = pika.BlockingConnection(params)
            break
        except AMQPConnectionError:
            logger.error("RabbitMQ'a bağlanılamadı, 5 saniye sonra yeniden denenecek...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue="pollution_queue", durable=True)

    channel.basic_consume(
        queue="pollution_queue",
        on_message_callback=callback,
        auto_ack=True
    )

    logger.info("📥 Consumer çalışıyor. Kuyruk dinleniyor...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()
