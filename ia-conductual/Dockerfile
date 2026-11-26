FROM python:3.11-slim

WORKDIR /app

# Invariante FOSS y dependencias locales
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar artefactos del modelo y código del microservicio
COPY models/ /app/models/
COPY app/ /app/app/

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
