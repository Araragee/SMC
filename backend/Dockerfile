# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# /app is the Python root — so `import backend.main` works
ENV PYTHONPATH=/app

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend source into /app/backend/ so relative imports work
# (matches how start.sh runs:  python -m uvicorn backend.main:app)
COPY . ./backend/

# Expose the port the app runs on
EXPOSE 8000

# Run as a package — same invocation as start.sh
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
