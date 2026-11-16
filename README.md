# Gerçek Zamanlı Hava Kirliliği İzleme Platformu

Akan hava kalitesi ölçümlerini (PM2.5, PM10, NO2, SO2, O3) mesaj kuyruğu üzerinden alan, zaman serisi veritabanında saklayan, anomalileri anlık olarak tespit edip WebSocket ile yayınlayan ve kısa vadeli kirlilik tahmini yapan bir veri platformu.

## 📌 İçindekiler
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Kurulum](#️-kurulum)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Anomali Tespiti](#️-anomali-tespiti)
- [Tahminleme](#-tahminleme)

---

## 🏗 Sistem Mimarisi
```text
┌──────────────┐   pollution_queue   ┌──────────────────────┐      ┌──────────────────────┐
│   Producer   │ ──────────────────► │  Consumer (FastAPI)  │ ───► │ TimescaleDB          │
│ (sensör sim.)│      RabbitMQ       │  anomali kontrolü    │      │ (PostgreSQL)         │
└──────────────┘                     └──────────┬───────────┘      └──────────┬───────────┘
                                                │ WebSocket                   │ REST API
                                                ▼                             ▼
                                      ┌──────────────────────────────────────────────┐
                                      │            Frontend (hava-kirliligi-ui)      │
                                      └──────────────────────────────────────────────┘
```

1. **Producer** her ölçümü JSON olarak RabbitMQ'daki `pollution_queue` kuyruğuna yazar (şu an İstanbul koordinatlarında simüle edilmiş sensör verisi üretir).
2. **Consumer** mesajı okur, anomali kontrollerini yapar ve kaydı TimescaleDB'ye yazar.
3. Anomali bulunduğunda `/ws/anomali` WebSocket kanalına bağlı tüm istemcilere anlık uyarı gönderilir.
4. REST API, konum bazlı sorgu, ısı haritası, anomali listesi ve tahmin sunar.

## 🛠 Teknoloji Yığını

| Bileşen           | Teknolojiler                                   |
|-------------------|------------------------------------------------|
| **Backend**       | Python, FastAPI, Uvicorn, WebSocket            |
| **Mesaj Kuyruğu** | RabbitMQ (pika, aio-pika)                       |
| **Veritabanı**    | TimescaleDB (PostgreSQL), psycopg2, SQLAlchemy |
| **Analiz**        | pandas, NumPy, statsmodels (Holt-Winters)      |
| **Container**     | Docker, Docker Compose                         |

## ⚙️ Kurulum

### Önkoşullar
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

### Kurulum Adımları
```bash
# 1. Repository'yi klonlayın
git clone https://github.com/beratkahraman/Gercek-Zamanli-Hava-Kirliligi-Izleme-Platformu.git
cd Gercek-Zamanli-Hava-Kirliligi-Izleme-Platformu

# 2. Ortam değişkenlerini oluşturun (yerel geliştirme için varsayılan değerler hazırdır)
cp hava-kirliligi-projesi/.env.example hava-kirliligi-projesi/.env

# 3. Konteynerleri başlatın
docker-compose up --build
```
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- RabbitMQ yönetim paneli: http://localhost:15673
- Frontend UI: http://localhost:3000

## 📡 API Dokümantasyonu

| Method | Endpoint                 | Parametreler                       | Açıklama |
|--------|--------------------------|------------------------------------|----------|
| GET    | `/api/data`              | `lat`, `lon`, `radius_km`          | Verilen koordinat ve yarıçap içindeki ölçümler |
| GET    | `/api/anomalies`         | `start`, `end`, `limit`            | Tespit edilen anomaliler (zaman aralığı filtresiyle) |
| GET    | `/api/heatmap`           | `grid_size_deg`                    | Izgara bazlı ortalama kirlilik (ısı haritası) |
| GET    | `/api/forecast`          | `parameter`, `hours` (1–48)        | Seçilen kirletici için saatlik tahmin |
| POST   | `/api/broadcast-anomaly` | Anomali kaydı (JSON)               | Manuel anomali yayını |
| WS     | `/ws/anomali`            | –                                  | Anlık anomali bildirimleri |

### Örnek İstekler
```bash
curl "http://localhost:8000/api/data?lat=41.01&lon=28.97&radius_km=10"
curl "http://localhost:8000/api/anomalies?limit=5"
curl "http://localhost:8000/api/heatmap?grid_size_deg=0.05"
curl "http://localhost:8000/api/forecast?parameter=PM2.5&hours=24"
```

## ⚠️ Anomali Tespiti
Her yeni ölçüm iki kurala göre kontrol edilir:

- **WHO eşik değeri:** Ölçüm, ilgili kirletici için WHO sınırını aşıyorsa.
- **Yerel ani artış:** Ölçüm, aynı bölgenin (±0.1°) son 24 saatlik ortalamasının %50 üzerindeyse.

## 📈 Tahminleme
`/api/forecast` endpoint'i, seçilen kirleticinin geçmiş ölçümlerini saatlik seriye çevirir ve **Holt-Winters üstel düzeltme** (statsmodels `ExponentialSmoothing`) modeliyle (toplamsal trend + yeterli veri varsa 24 saatlik mevsimsellik) 48 saate kadar ileriye tahmin üretir.
