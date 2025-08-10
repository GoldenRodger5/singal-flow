# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-railway.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copy the entire project
COPY . .

# Set the working directory to backend for the start command
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "railway_test.py"]
