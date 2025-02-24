# Despliegue de FastApi con Kubernetes

En esta guía, se detallan los pasos necesarios para desplegar una aplicación FastAPI en un clúster de Kubernetes, utilizando cinco réplicas.


# Índice
[1. Creación de la aplicación FastAPI](#1-creación-de-la-aplicación-fastapi)    
[2. Creación del Dockerfile](#2-creación-del-dockerfile)    
[3. Configuración de Kubernetes](#3-configuración-de-kubernetes)    
   - [3.1. Definición del Deployment](#31-definición-del-deployment)    
   - [3.2. Creación del Servicio](#32-creación-del-servicio)    

[4. Despliegue en Kubernetes](#4-despliegue-en-kubernetes)  
[5. Verificación del Despliegue](#5-verificación-del-despliegue)  


<br>


## 1. Creación de la aplicación FastAPI

Primero, se debe crear un archivo `main.py` que contendrá nuestra API:

```python
from typing import Optional
from fastapi import HTTPException # type: ignore
from fastapi import FastAPI # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient # type: ignore
from bson import ObjectId # type: ignore
from fastapi.encoders import jsonable_encoder # type: ignore
from pydantic import BaseModel # type: ignore
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient # type: ignore

load_dotenv()
app = FastAPI()

# Configuración de la URI
#MONGO_URI = "mongodb+srv://Grupo1:grupo1@cluster0.h4a3o.mongodb.net/Usuarios?retryWrites=true&w=majority"

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("Falta la variable de entorno MONGO_URI")

# Crear cliente y base de datos
client = AsyncIOMotorClient(MONGO_URI)
db = client["Usuarios"]

class UserSchema(BaseModel):
    id: str
    nombre: str
    password: str

class UserCreateSchema(BaseModel):
    nombre: str
    password: str

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = None  # Edad opcional

class UserResponse(User):
    id: str  # Convertimos ObjectId a str

# Función para convertir ObjectId a str
def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [objectid_to_str(i) for i in obj]
    return obj

@app.get("/")
async def root():
    return "Bienvenido a la API de usuari"

@app.get("/users")
async def get_users():
    try:
        # Obtener los usuarios de la colección
        usuarios_collection = db["Usuarios"]
        users = await usuarios_collection.find().to_list(100)
        
        # Convertir ObjectIds a str antes de devolver
        users = [objectid_to_str(user) for user in users]
        
        if not users:
            return {"message": "No hay usuarios en la base de datos"}
        
        return {"usuarios": users}
    
    except Exception as e:
        # Capturar cualquier excepción
        return {"error": f"Hubo un error: {str(e)}"}
    
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db["Usuarios"].find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user["id"] = str(user["_id"])
    del user["_id"]

    return user

@app.post("/users")
async def create_user(user: UserCreateSchema):
    user_dict = user.dict()  # Convertir Pydantic model a diccionario
    result = await db["Usuarios"].insert_one(user_dict)  # Insertar en MongoDB
    user_dict["_id"] = str(result.inserted_id)  # Convertir ObjectId a string
    return user_dict  # Devolver usuario con _id convertido

@app.put("/users/{user_id}")
async def update_user(user_id: str, user: UserCreateSchema):
    user_dict = user.dict()  # Convertir el modelo a diccionario
    result = await db["Usuarios"].update_one({"_id": ObjectId(user_id)}, {"$set": user_dict})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"message": "Usuario actualizado correctamente"}

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await db["Usuarios"].delete_one({"_id": ObjectId(user_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"message": "Usuario eliminado correctamente"}
```

<br>

## 2. Creación del Dockerfile

En el mismo directorio, se debe agregar un archivo `Dockerfile` con las instrucciones para construir la imagen del contenedor:

```dockerfile
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
```

Para construir la imagen, se ejecuta el siguiente comando:

```bash
docker build -t alvarokro/mi-api-segura .
```

<br>

## 3. Configuración de Kubernetes

### 3.1. Definición del Deployment

Se debe crear un archivo YAML `deployment.yaml` con la configuración del despliegue:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-kubernetes
spec:
  replicas: 5
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      containers:
      - name: fastapi
        image: alvarokro/mi-api-segura:latest  # Imagen creada anteriormente
        ports:
        - containerPort: 8000
```

---

### 3.2. Creación del Servicio

Para exponer la aplicación, se debe definir un servicio en el archivo `service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
spec:
  selector:
    app: fastapi
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

<br>

## 4. Despliegue en Kubernetes

Si se está utilizando Docker Desktop en Windows, es necesario habilitar Kubernetes en **Configuración > Kubernetes**.

![Habilitar Kubernetes en Docker Desktop](/img/kubernetes-docker-desktop.png)

Para desplegar la aplicación, se deben ejecutar los siguientes comandos:

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```
![Despliegue aplicación](/img/kubectl-apply.png)

<br>

## 5. Verificación del Despliegue

Para comprobar que la aplicación se ha desplegado correctamente, se ejecutan los siguientes comandos:

```bash
kubectl get pods         # Muestra los pods en ejecución
```
![Despliegue aplicación](/img/kubectl-pods.png)

```bash
kubectl get deployments  # Lista los despliegues activos
```
![Despliegues activos](/img/kubectl-deployments.png)

```bash
kubectl get services     # Muestra el servicio y su IP externa
```
![Mostrar servicio](/img/kubectl-services.png)


Se puede verificar también desde la interfaz de Docker Desktop:

![Mostrar servicio en Docker Desktop](/img/docker-desktop.png)