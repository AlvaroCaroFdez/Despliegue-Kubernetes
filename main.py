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

