FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requerimientos y luego instalarlos para aprovechar cache de Docker
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY ./app ./app

# Exponer el puerto en el que correrá la API
EXPOSE 8000

# Variable de entorno para que uvicorn no escriba logs en color (mejor para logs en contenedores)
ENV UVICORN_LOG_LEVEL=info

# Comando para ejecutar la aplicación con uvicorn, usando root_path /api para que /docs y /openapi.json funcionen bajo /api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]