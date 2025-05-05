from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 WebSocket bağlantısı alındı. Toplam bağlantı: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket bağlantısı kesildi. Kalan bağlantı: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        print(f"📤 [broadcast()] Mesaj gönderiliyor: {message}")
        for connection in self.active_connections:
            await connection.send_text(message)

# Global olarak tek bir manager nesnesi kullanılacak
manager = ConnectionManager()
