import os, pika, json
# 1) Parametreleri al
params = pika.URLParameters(os.getenv("RABBITMQ_URL"))
# 2) Bağlan
conn = pika.BlockingConnection(params)
ch = conn.channel()
# 3) Kuyruğu hazırla
ch.queue_declare(queue="pollution_queue", durable=True)
# 4) Veri
data = {"latitude":41.01,"longitude":28.97,"parameter":"PM2.5","value":55.0}
msg = json.dumps(data)
# 5) Yayınla
ch.basic_publish(exchange="", routing_key="pollution_queue", body=msg)
print("✅ Mesaj yayınlandı:", msg)
conn.close()
