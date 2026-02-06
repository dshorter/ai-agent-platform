FROM python:3.11-slim

# System dependencies for lxml, SQLite, and cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    sqlite3 \
    cron \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/db data/db/backups data/raw data/text \
    data/docpacks data/extractions data/graphs

# Initialize the database
RUN python scripts/init_db.py

# Set up cron jobs
# Daily SQLite backup at 5:30 AM ET (before pipeline run)
# Daily pipeline run at 6:00 AM ET
RUN echo '30 5 * * * cd /app && sqlite3 data/db/predictor.db ".backup data/db/backups/predictor_$(date +\%Y\%m\%d).db" && find data/db/backups -name "predictor_*.db" -mtime +30 -delete >> /var/log/cron.log 2>&1' > /etc/cron.d/predictor \
    && echo '0 6 * * * cd /app && make ingest >> /var/log/cron.log 2>&1' >> /etc/cron.d/predictor \
    && echo '' >> /etc/cron.d/predictor \
    && chmod 0644 /etc/cron.d/predictor \
    && crontab /etc/cron.d/predictor \
    && touch /var/log/cron.log

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /app/data/db/predictor.db && pgrep cron > /dev/null || exit 1

CMD ["cron", "-f"]
