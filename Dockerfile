# [BASE] Use official Python image for ARM (Apple Silicon)

# Use python:3.11-slim as base
FROM python:3.11-slim

# Install build dependencies for psycopg2
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
	&& rm -rf /var/lib/apt/lists/*

# [WORKDIR] Set working directory
WORKDIR /app

# [COPY] Copy requirements and install

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copy project files
COPY . .

# [EXPOSE] Expose port for gunicorn
EXPOSE 8000

# [CMD] Run gunicorn
CMD ["gunicorn", "forum.app:app", "--bind", "0.0.0.0:8000"]
