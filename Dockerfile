# Production Dockerfile for Signal Flow Trading System - OPTIMIZED
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install essential system dependencies only
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    curl \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements-production.txt .

# Install Python dependencies with optimization
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-production.txt --timeout 1000

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p logs backend/logs cache data

# Set environment variables
ENV PYTHONPATH=/app/backend:/app:$PYTHONPATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "backend/railway_start.py"]
