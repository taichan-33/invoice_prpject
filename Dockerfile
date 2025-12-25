# Build stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run expects the app to listen on PORT environment variable (default 8080)
ENV PORT=8080

# Command to run the application using uvicorn
# main:app refers to the 'app' instance in main.py
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
