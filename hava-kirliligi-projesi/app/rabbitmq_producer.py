# app/rabbitmq_producer.py

import os
import json
import random
import time

import pika
from dotenv import load_dotenv

# Ortam değişkenlerini yükle (.env içindeki RABBITMQ_URL’i alacak)
load_dotenv()
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

# Rastgele parametreler
parameters = ["PM2.5", "PM10", "NO2", "SO2", "O3"]

def publish_fake_data():
    # RabbitMQ bağlantısı için URL parametrelerini oluştur
    params = pika.URLParameters(RABBITMQ_URL)

    # RabbitMQ hazır olana kadar retry döngüsü
    while True:
        try:
            connection = pika.BlockingConnection(params)
            print("✅ RabbitMQ bağlantısı kuruldu.")
            break
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ'a bağlanılamadı, 5 saniye sonra yeniden denenecek...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue="pollution_queue", durable=True)

    try:
        while True:
            # Rastgele sahte veri oluştur
            data = {
                "latitude": round(random.uniform(40.9, 41.1), 6),
                "longitude": round(random.uniform(28.8, 29.0), 6),
                "parameter": random.choice(parameters),
                "value": round(random.uniform(60, 180), 2),  # WHO eşiklerini aşacak şekilde
                "timestamp": None
            }
            message = json.dumps(data)
            channel.basic_publish(
                exchange="",
                routing_key="pollution_queue",
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # mesajı persistent yapar
                )
            )
            print(f"📤 Gönderilen veri: {message}")
            time.sleep(5)  # 5 saniyede bir veri gönder

    except KeyboardInterrupt:
        connection.close()
        print("❌ Veri gönderimi durduruldu.")

if __name__ == "__main__":
    publish_fake_data()
