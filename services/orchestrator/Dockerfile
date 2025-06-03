# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements-lock.txt first to leverage Docker cache
COPY requirements-lock.txt .

# Install dependencies from locked requirements
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy application code
COPY . .

# Create empty .env file if not exists
RUN touch .env

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]