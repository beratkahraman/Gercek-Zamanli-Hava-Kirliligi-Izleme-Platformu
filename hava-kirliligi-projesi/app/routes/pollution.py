from fastapi import APIRouter, HTTPException
from ..models import PollutionData
from ..rabbitmq_producer import send_to_queue

router = APIRouter()

@router.post("/veri-ekle")
def add_pollution_data(data: PollutionData):
    try:
        # Gelen veriyi dict formatına çevirip RabbitMQ kuyruğuna gönder
        send_to_queue(data.dict())
        return {"message": "Veri kuyruğa gönderildi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
