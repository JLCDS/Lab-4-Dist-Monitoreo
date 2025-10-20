#imagen base de python 
FROM python:3.9-slim

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias e instalar
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar código y templates
COPY app.py /app/
COPY templates /app/templates
COPY static /app/static

# Exponer el puerto de la app
EXPOSE 5000

# Ejecutar la app
ENTRYPOINT ["python", "app.py"]

