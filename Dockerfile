FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY locale/ ./locale/
COPY .env .

EXPOSE 8000
CMD ["python", "src/main.py"]