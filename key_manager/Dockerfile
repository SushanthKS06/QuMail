FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Install system dependencies
# We need build-essential, git, cmake, and libssl-dev for building liboqs
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements as base
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy key manager code
COPY key_manager/ .

# Copy backend for imports
COPY backend/crypto_engine /app/backend/crypto_engine
ENV PYTHONPATH=/app/backend:$PYTHONPATH

# Expose port
EXPOSE 8001

# Run the application
CMD ["python", "main.py"]
