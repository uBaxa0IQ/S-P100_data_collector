FROM python:3.9-slim

# Install system dependencies (cron, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Setup cron job
COPY crontab /etc/cron.d/stock-cron
RUN chmod 0644 /etc/cron.d/stock-cron && \
    touch /var/log/cron.log

# Default command can be overridden in docker-compose for specific services
CMD ["bash", "-lc", "python -m api.main"]


