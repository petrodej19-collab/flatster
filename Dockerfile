FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Xvfb for running browser in headed mode without a real display
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Start Xvfb and then the app
CMD ["bash", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &>/dev/null & export DISPLAY=:99 && sleep 1 && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
