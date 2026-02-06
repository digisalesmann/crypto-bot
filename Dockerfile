# Use an official lightweight Python image.
# 3.10-slim is standard for modern bots (small & secure).
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disc
# PYTHONUNBUFFERED: Ensures logs are flushed immediately (vital for Docker logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (if needed for crypto libraries or DBs)
# standard build-essential and libpq-dev are common safe bets
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port if you are running a web dashboard (app.py usually implies Flask/FastAPI)
# If this is just a bot script, this is optional but good practice.
EXPOSE 5000 
EXPOSE 8000

# Default command. 
# Since you have both main.py and app.py, I am assuming main.py runs the bot.
# If app.py is the entry point, change "main.py" to "app.py" below.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]