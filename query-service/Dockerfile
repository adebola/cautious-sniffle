FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install shared library
COPY chatcraft-common/ /tmp/chatcraft-common/
RUN pip install --no-cache-dir /tmp/chatcraft-common/ && rm -rf /tmp/chatcraft-common/

# Copy and install service dependencies
COPY query-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY query-service/ .

EXPOSE 8086

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8086"]
