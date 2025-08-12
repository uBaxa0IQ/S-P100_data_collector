## S-P100 Data Collector

Небольшой сервис для сбора и публикации внутридневных котировок по акциям из S&P 100. 
Состоит из API на FastAPI, PostgreSQL для хранения данных и фоновой cron‑задачи, которая ежедневно подтягивает 1‑минутные свечи через `yfinance`.

### Возможности
- **HTTP API**: получение статуса последнего обновления, всех записей (с пагинацией) и данных по конкретному тикеру
- **Автосоздание схемы**: таблицы создаются при старте API/крона
- **Идемпотентная загрузка**: уникальный ключ `(ticker, timestamp)` предотвращает дубликаты
- **Обновление по расписанию**: cron в контейнере выполняет загрузку по будням в 23:00 UTC

### Технологии
- **API**: FastAPI + Gunicorn + Uvicorn worker
- **БД**: PostgreSQL + SQLAlchemy (Core/ORM)
- **Загрузка данных**: `yfinance`, `pandas`
- **Инфраструктура**: Docker, docker‑compose, Nginx (reverse proxy)

## Структура репозитория
```
S-P100_data_collector/
  api/                # API и доступ к БД
    main.py           # Точки входа FastAPI, эндпоинты
    database.py       # Подключение к БД, session, Base
    models.py         # Модель таблицы stock_data
    crud.py           # Запросы к БД
    schemas.py        # Pydantic-схемы ответов
  cron_job/
    download_data.py  # Основной скрипт загрузки/апсерта данных
    tickers.py        # Список тикеров S&P 100
  nginx/nginx.conf    # Проксирование на API (порт 80 -> 8000)
  crontab             # Расписание для контейнера с cron
  docker-compose.yml  # Сервисы: db, api, cron, nginx
  Dockerfile          # Базовый образ для api/cron
  requirements.txt    # Python-зависимости
```

## Модель данных
Таблица `stock_data`:
- `id` (PK)
- `ticker` (string, index)
- `timestamp` (timestamptz, index)
- `open`, `high`, `low`, `close` (numeric)
- `volume` (int)

Ограничения/индексы:
- `UNIQUE (ticker, timestamp)`
- индекс `(ticker, timestamp)`

## Переменные окружения
Создайте файл `.env` в корне проекта (используется и API, и cron, и `docker-compose`):
```env
# PostgreSQL
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_DB=stocks

# SQLAlchemy DSN (пример для docker-compose)
DATABASE_URL=postgresql+psycopg2://app:app@db:5432/stocks
```

## Запуск через Docker Compose (рекомендуется)
Требования: установленный Docker и docker‑compose.

1) Создайте `.env` как выше
2) Запустите стек:
```bash
docker-compose up -d --build
```
3) Откройте API:
- Swagger UI: `http://localhost/docs`
- Базовый статус: `http://localhost/status`

Сервисы:
- `db`: PostgreSQL с volume `postgres_data`
- `api`: FastAPI за Nginx
- `cron`: контейнер с системным `cron` и вашим расписанием (`crontab`)
- `nginx`: reverse proxy на `api` (публикует порт 80)

Cron по умолчанию запускается в будни в 23:00 UTC и вызывает `cron_job/download_data.py`.

## Локальный запуск без Docker
Требования: Python 3.9+, локальный PostgreSQL.

1) Установите зависимости:
```bash
pip install -r requirements.txt
```

2) Установите `DATABASE_URL` (например, через `.env`), создайте БД и пользователя при необходимости

3) Запустите API (автосоздаст таблицы):
```bash
uvicorn api.main:app --reload
```
Откройте `http://127.0.0.1:8000/docs`.

4) Разовая загрузка данных (вручную):
```bash
python cron_job/download_data.py
```

## Endpoints
База: `/` (через Nginx) или `:8000` (напрямую до API).

- `GET /status`
  - Возвращает время последнего обновления (ISO8601) или `null`.

- `GET /data/all?skip=0&limit=100`
  - Пагинированный список всех записей.

- `GET /data/{ticker}`
  - Все записи по тикеру (например, `AAPL`).

Примеры:
```bash
curl http://localhost/status
curl "http://localhost/data/all?skip=0&limit=200"
curl http://localhost/data/AAPL
```

OpenAPI/Swagger: `http://localhost/docs`

## Изменение расписания и списка тикеров
- Расписание: правьте `crontab` (формат `/etc/cron.d`), затем пересоберите/перезапустите контейнеры.
- Тикеры: правьте `cron_job/tickers.py`.

Текущее расписание (будни, 23:00 UTC):
```cron
0 23 * * 1-5 root . /app/.env; /usr/local/bin/python /app/cron_job/download_data.py >> /var/log/cron.log 2>&1
```

## Зависимости (минимально необходимые)
Убедитесь, что `requirements.txt` содержит библиотеки:
```txt
fastapi
uvicorn[standard]
gunicorn
SQLAlchemy>=1.4
psycopg2-binary
python-dotenv
yfinance
pandas
pydantic>=2
```

## Частые вопросы
- **Ошибка "DATABASE_URL is not set"**: проверьте `.env` и переменные окружения.
- **Нет данных по тикеру**: `yfinance` может возвращать пустые данные вне торговых часов или при ограничениях API.
- **Часовые пояса**: все временные метки сохраняются как timezone‑aware UTC.
- **Дубликаты**: предотвращаются за счет `UNIQUE (ticker, timestamp)`.

## Лицензия
Добавьте файл лицензии на ваше усмотрение (например, MIT).
