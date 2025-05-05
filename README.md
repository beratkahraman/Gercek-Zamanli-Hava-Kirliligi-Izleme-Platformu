# Gerçek Zamanlı Hava Kirliliği İzleme Platformu

![Proje Mimarisi](https://via.placeholder.com/800x400?text=System+Architecture+Diagram)  
*Monolitik/Microservice mimarisi ile hava kirliliği veri izleme platformu.*

## 📌 İçindekiler
- [Proje Tanımı](#-proje-tanımı)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Kurulum](#-kurulum)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Anomali Tespiti](#-anomali-tespiti)
- [Katkıda Bulunanlar](#-katkıda-bulunanlar)
- [Lisans](#-lisans)

---

## 🌍 Proje Tanımı
Dünya genelindeki hava kirliliği verilerini gerçek zamanlı işleyen, analiz eden ve web üzerinden görselleştiren platform. Anomali tespiti ve eşik aşım uyarıları içerir.

---

## 🏗 Sistem Mimarisi
```text
┌───────────┐     ┌────────────┐     ┌───────────┐
│  Frontend │◄──►│ API Gateway │◄──►│  Backend  │
└───────────┘     └────────────┘     └───────────┘
                      │  │  │
         ┌────────────┘  │  └───────────┐
         │               │              │
    ┌─────────┐      ┌───────────┐   ┌────────┐
    │ RabbitMQ│      │InfluxDB   │   │ Mail/  │
    │  Kafka  │      │TimescaleDB│   │Sms Serv│
    └─────────┘      └───────────┘   └────────┘
```
## 🛠 Teknoloji Yığını

| Bileşen          | Teknolojiler                          |
|-------------------|---------------------------------------|
| **Backend**       | Python (FastAPI)                      |
| **Frontend**      | React, Leaflet/Mapbox, Recharts       |
| **Veritabanı**    | InfluxDB, TimescaleDB, MongoDB        |
| **Mesaj Kuyruğu** | RabbitMQ, Apache Kafka                |
| **Container**     | Docker, Docker Compose                |

## ⚙️ Kurulum

### Önkoşullar
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

### Kurulum Adımları
```bash
# 1. Repository'yi klonlayın
git clone https://github.com/beratkahraman/Gercek-Zamanli-Hava-Kirliligi-Izleme-Platformu.git

# 2. Proje dizinine gidin
cd Gercek-Zamanli-Hava-Kirliligi-Izleme-Platformu

# 3. Docker konteynerlerini başlatın
docker-compose up --build
```
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000
- Swagger UI: http://localhost:8000/docs (API dokümantasyonu ve testleri için)

## 📡 API Dokümantasyonu

### Endpoint'ler

| Method | Endpoint                              | Parametreler                          | Açıklama                                   |
|--------|---------------------------------------|---------------------------------------|-------------------------------------------|
| GET    | `/api/data`                           | `lat`, `lon`, `radius_km`             | Belirtilen koordinat ve yarıçap içindeki hava kalitesi verilerini getirir |
| GET    | `/api/anomalies`                      | `limit`                               | Tespit edilen anomalileri listeler (varsayılan: son 10 kayıt) |
| GET    | `/api/heatmap`                        | `grid_size_deg`                      | Hava kirliliği ısı haritası verilerini döner |

### Örnek İstekler

```bash
# Temel veri sorgulama
curl "http://localhost:8000/api/data?lat=41.01&lon=28.97&radius_km=10"

# Anomali listesi
curl "http://localhost:8000/api/anomalies?limit=5"

# Isı haritası verisi
curl "http://localhost:8000/api/heatmap?grid_size_deg=0.05"
```
## ⚠️ Anomali Tespiti
Platform, veri analizinde aşağıdaki yöntemleri kullanarak anomalileri tespit eder:

- İstatistiksel yöntemler (Z-score)

- WHO standartlarına göre basit eşik değerleri

- Son 24 saatlik ortalamaya göre %50 artış gösteren durumlar

- Yakın bölgeler arasında beklenmeyen değer farklılıkları
