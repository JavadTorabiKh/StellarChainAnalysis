## stellar chain analysis
# Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Tehran

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    python3-full \
    postgresql-14 \
    postgresql-contrib-14 \
    libpq-dev \
    pgloader \
    nginx \
    curl \
    wget \
    git \
    gcc \
    g++ \
    make \
    build-essential \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libatlas-base-dev \
    libopenblas-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --set python /usr/bin/python3.10

RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

RUN mkdir -p /app/staticfiles /app/media /var/log/nginx /var/log/gunicorn

RUN service postgresql start && \
    su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD '';\"" && \
    su - postgres -c "psql -c \"CREATE DATABASE stellar OWNER postgres;\"" && \
    su - postgres -c "psql -c \"ALTER USER postgres WITH SUPERUSER;\""

RUN if [ -f "db.sqlite3" ]; then \
    service postgresql start && \
    pgloader sqlite:///app/db.sqlite3 postgresql://postgres:@localhost:5432/stellar 2>/dev/null || true; \
    fi

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/hemayat.conf /etc/nginx/conf.d/stellar.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R www-data:www-data /app/staticfiles /app/media /var/log/nginx /var/log/gunicorn && \
    chmod -R 755 /app/staticfiles /app/media /var/log/nginx /var/log/gunicorn

EXPOSE 80 8000 5432


ENTRYPOINT ["/entrypoint.sh"]
