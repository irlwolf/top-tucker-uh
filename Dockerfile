FROM python:3.10-slim

WORKDIR /app

# Install ffmpeg (required for mutagen/qobuz-dl to handle metadata)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port for the Koyeb Health Check
EXPOSE 8000

CMD ["python", "bot.py"]
