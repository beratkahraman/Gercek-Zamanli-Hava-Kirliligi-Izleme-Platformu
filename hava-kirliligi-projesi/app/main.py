import asyncio
import threading
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# WebSocket router’ınız
from app.routes.websocket import router as websocket_router
# REST API router’ınız
from app.routes.api_routes import router as api_router
# RabbitMQ tüketiciniz
from app.rabbitmq_consumer import start_consuming

# Uvicorn’un error logger’ını alıyoruz; INFO seviyesindeki log’lar burada görüntülenecek
logger = logging.getLogger("uvicorn.error")

app = FastAPI()

# === MAIN.PY İÇERİĞİ YÜKLENDİ ===
logger.info("=== MAIN.PY İÇERİĞİ YÜKLENDİ ===")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bu satır artık doğrudan app ayağa kalktığında değil, startup etkinliği tetiklendiğinde log’lanacak
# print("🔃 startup_event tetiklendi — consumer thread başlıyor…")

# --- startup_event: consumer thread’i burada başlatıyoruz ---
@app.on_event("startup")
def startup_event():
    logger.info("🔃 startup_event tetiklendi — consumer thread başlıyor…")
    loop = asyncio.get_event_loop()

    def consumer_thread():
        logger.info("📥 Consumer çalışıyor. Kuyruk dinleniyor…")
        start_consuming(loop)

    t = threading.Thread(target=consumer_thread, daemon=True)
    t.start()

# --- Router’ları ekle ---
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)
