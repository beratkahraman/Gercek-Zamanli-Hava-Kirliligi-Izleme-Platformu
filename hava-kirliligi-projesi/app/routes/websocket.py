# app/routes/websocket.py

import asyncio
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket bağlantısı alındı. Toplam bağlantı: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket ayrıldı. Toplam bağlantı: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """
        Kuyruktan veya test-endpoint’ten gelen tüm mesajları
        kayıtlı WebSocket bağlantılarına gönderir.
        """
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                print("🚨 Gönderim hatası:", e)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

# global manager örneği
manager = ConnectionManager()

@router.websocket("/ws/anomali")
async def websocket_endpoint(websocket: WebSocket):
    """
    /ws/anomali endpoint’ine bağlanan her client için:
    - manager.connect ile kabul edilir
    - sonsuz döngü ile açık tutulur
    - disconnect ile oturum kapandığında listeden çıkarılır
    """
    await manager.connect(websocket)
    try:
        while True:
            # Client’tan mesaj beklemiyoruz ama bağlantıyı canlı tutmak için uyutuyoruz
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
