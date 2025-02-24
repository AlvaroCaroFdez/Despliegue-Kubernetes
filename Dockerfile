# Usa una imagen base de Python
FROM python:3.10

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala GPG para manejar el cifrado
RUN apt-get update && apt-get install -y gnupg gpg-agent

# Crear directorio seguro para GPG dentro del contenedor
RUN mkdir -p /root/.gnupg && chmod 700 /root/.gnupg

# Copia los archivos necesarios
COPY .env.gpg ./
COPY private.key ./

# Importa la clave privada sin interacción
RUN gpg --batch --import private.key && rm private.key

# Desencripta el archivo .env.gpg al archivo .env
RUN gpg --batch --yes --decrypt --output .env .env.gpg || echo "Error al desencriptar .env"

# Copia los archivos de la app
COPY requirements.txt ./
COPY . .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto en el que correrá FastAPI
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
