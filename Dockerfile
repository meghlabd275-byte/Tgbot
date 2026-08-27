FROM python:3.13-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The bot uses SQLite by default; put the database somewhere writable.
VOLUME ["/app/data"]

CMD ["python", "bot.py"]