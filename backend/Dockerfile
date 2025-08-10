# Production Dockerfile for Signal Flow Trading System
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for compilation and runtime
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements-production.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-production.txt

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p logs backend/logs

# Set Python path to include backend directory
ENV PYTHONPATH=/app/backend:/app:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Start the application
CMD ["python", "backend/railway_start.py"]
