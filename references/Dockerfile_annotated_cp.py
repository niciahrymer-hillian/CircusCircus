
# [BASE] Use official Python image for ARM (Apple Silicon)
FROM python:3.11-slim
# [WHY] Ensures compatibility and small image size for M1/M2 Macs and production

# [BUILD-ESSENTIAL] Install build tools and PostgreSQL client libraries for psycopg2
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
	&& rm -rf /var/lib/apt/lists/*
# [WHY] Required for building psycopg2 from source in Docker

# [WORKDIR] Set working directory
WORKDIR /app
# [EFFECT] All subsequent commands run from /app

# [COPY] Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# [WHY] Installs all Python dependencies for the app

# [COPY] Copy project files
COPY . .
# [EFFECT] All app code and resources are available in the container

# [EXPOSE] Expose port for gunicorn
EXPOSE 8000
# [EFFECT] Makes port 8000 available for Docker networking

# [CMD] Run gunicorn
CMD ["gunicorn", "forum.app:app", "--bind", "0.0.0.0:8000"]
# [WHY] Launches the Flask app using gunicorn for production, binds to all interfaces for Docker
