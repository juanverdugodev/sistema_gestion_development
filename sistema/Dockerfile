FROM python:3.11-slim-bookworm

WORKDIR /app

# Agregamos libgl1 y libglib2.0-0 para que OpenCV funcione correctamente
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiamos los requerimientos desde la carpeta sistema
COPY sistema/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el contenido del proyecto al contenedor
COPY . .

# Exponemos el puerto 80
EXPOSE 5000

# Ejecutamos el run.py que está dentro de sistema/app/
CMD ["flask", "--app", "sistema/app/run.py", "run", "--host=0.0.0.0", "--port=5000", "--debug"]