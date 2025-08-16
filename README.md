## S-P100 Data Collector

Небольшой сервис для сбора и публикации внутридневных котировок по акциям из S&P 100. 
Состоит из API на FastAPI, PostgreSQL для хранения данных и фоновой cron‑задачи, которая ежедневно подтягивает 1‑минутные свечи через `yfinance`.

### Возможности
- **HTTP API**: статус последнего обновления, все записи (пагинация), данные по тикеру
- **Маркет‑режимы**: расчёт режима рынка по дневным данным с индикаторами `pandas-ta`
- **Автосоздание схемы**: таблицы создаются при старте API/крона
- **Идемпотентная загрузка**: уникальные ключи предотвращают дубликаты
- **Обновление по расписанию**: cron в контейнере выполняет загрузку по будням в 02:00 UTC

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
    models.py         # Модели таблиц stock_data, stock_data_daily
    crud.py           # Запросы к БД
    schemas.py        # Pydantic-схемы ответов
    data_loader.py    # Кэш дневных данных (yfinance -> БД -> DataFrame)
    market_regime.py  # Расчёт режимов рынка по дневным данным
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
Таблица `stock_data` (внутридневные свечи 1m):
- `id` (PK)
- `ticker` (string, index)
- `timestamp` (timestamptz, index)
- `open`, `high`, `low`, `close` (numeric)
- `volume` (int)

Ограничения/индексы:
- `UNIQUE (ticker, timestamp)`
- индекс `(ticker, timestamp)`

Таблица `stock_data_daily` (дневные свечи для индикаторов):
- `id` (PK)
- `ticker` (string, index)
- `date` (timestamptz, index)
- `open`, `high`, `low`, `close` (numeric)
- `volume` (int)

Ограничения/индексы:
- `UNIQUE (ticker, date)`
- индекс `(ticker, date)`

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

Cron по умолчанию запускается в будни в 02:00 UTC и вызывает модуль `cron_job.download_data`.

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

- `GET /regime/{ticker}`
  - Режим рынка для тикера. Возможные значения: `тренд_вверх`, `тренд_вниз`, `сжатие/накопление`, `боковик/пилообразно`, `нет_данных`.

- `GET /regime/all`
  - Словарь `{ticker: regime}` по всему списку S&P 100.

- `GET /regime/by_regime/{regime_name}`
  - Список тикеров, попадающих в указанный режим.

Примеры:
```bash
curl http://localhost/status
curl "http://localhost/data/all?skip=0&limit=200"
curl http://localhost/data/AAPL
curl http://localhost/regime/AAPL
curl http://localhost/regime/all
curl http://localhost/regime/by_regime/тренд_вверх
```

OpenAPI/Swagger: `http://localhost/docs`

## Изменение расписания и списка тикеров
- Расписание: правьте `crontab` (формат `/etc/cron.d`), затем пересоберите/перезапустите контейнеры.
- Тикеры: правьте `cron_job/tickers.py`.

Текущее расписание (будни, 02:00 UTC):
```cron
0 2 * * 1-5 root cd /app && PYTHONPATH=/app . /app/.env; /usr/local/bin/python -m cron_job.download_data >> /var/log/cron.log 2>&1
```

## Зависимости (минимально необходимые)
Убедитесь, что `requirements.txt` содержит библиотеки:
```txt
fastapi
uvicorn[standard]
gunicorn
SQLAlchemy>=2.0
psycopg2-binary
python-dotenv
yfinance
pandas
pandas-ta
pydantic>=2
```

## Частые вопросы
- **Ошибка "DATABASE_URL is not set"**: проверьте `.env` и переменные окружения.
- **Нет данных по тикеру**: `yfinance` может возвращать пустые данные вне торговых часов или при ограничениях API.
- **Часовые пояса**: все временные метки сохраняются как timezone‑aware UTC.
- **Дубликаты**: предотвращаются за счет `UNIQUE (ticker, timestamp)`.
- **Режимы = `нет_данных`**: возвращается, если для расчёта недостаточно дневной истории (меньше ~200 баров) или индикаторы ещё не стабилизировались.

## Лицензия
Добавьте файл лицензии на ваше усмотрение (например, MIT).
