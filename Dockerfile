# Production Dockerfile for Signal Flow Trading System
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install comprehensive system dependencies needed for compilation and runtime
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    build-essential \
    curl \
    wget \
    git \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements-production.txt .

# Install Python dependencies with comprehensive toolchain
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-production.txt

# Copy the entire project
COPY . .

# Create all necessary directories
RUN mkdir -p logs backend/logs cache data/polygon_flatfiles

# Set Python path to include backend directory
ENV PYTHONPATH=/app/backend:/app:$PYTHONPATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Enhanced health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=5 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Start the application with uvicorn for production
CMD ["python", "backend/railway_start.py"]
