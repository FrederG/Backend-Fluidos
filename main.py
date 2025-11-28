import bcrypt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from sqlalchemy.orm import Session 
from pydantic import BaseModel, EmailStr
from database import SessionLocal, Resultado, Base, engine
from database import Usuario  # Importa el modelo Usuario
from datetime import datetime
from passlib.context import CryptContext
import json  # Importar json para procesar respuestas múltiples

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="BACKEND - Plataforma de Ejercicios de Fluidos")
# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencia para sesión ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic model ---
class ResultadoIn(BaseModel):
    usuario: str
    ejercicio: int
    respuesta: str
    puntaje: float

# Definir valores correctos para TODOS los ejercicios
valores = {
    # Ejercicios simples (1-5)
    1: {"fijo": "75", "rango": [60, 90]},
    2: {"fijo": "120", "rango": [100, 140]},
    3: {"fijo": "50", "rango": [40, 60]},
    4: {"fijo": "15", "rango": [10, 20]},
    5: {"fijo": "25", "rango": [20, 30]},
    6: {
        "a": {"fijo": "1.0400", "rango": [1, 3], "unidad": "m"},
        "b": {"fijo": "0.8875", "rango": [0.8, 1.2], "unidad": "m"},
        "c": {"fijo": "0.40", "rango": [0.3, 0.5], "unidad": "m"},
        "d": {"fijo": "1.2875", "rango": [1, 1.5], "unidad": "m"}
    },
    7: {"fijo": "15", "rango": [10, 20]},
    8: {"fijo": "25", "rango": [20, 30]},
    9: {"fijo": "15", "rango": [10, 20]},
    10: {
        "a": {"fijo": "53.20", "rango": [52, 55], "unidad": "m"},
        "b": {"fijo": "54.215", "rango": [52, 56], "unidad": "m"},
        "c": {"fijo": "46.00", "rango": [40, 50], "unidad": "m"},
        "d": {"fijo": "1.015", "rango": [1, 1.5], "unidad": "m"}
    },
}
    
class ResultadoRequest(BaseModel):
    usuario: str
    ejercicio: int
    respuesta: str

def verificar_respuesta_simple(ejercicio_id, respuesta_usuario):
    """Verifica respuestas para ejercicios simples (1-5)"""
    if ejercicio_id not in valores or ejercicio_id == 6:
        return "red", 0
    
    valor_real = valores[ejercicio_id]
    
    try:
        if str(respuesta_usuario) == str(valor_real["fijo"]):
            return "green", 1
        elif valor_real["rango"][0] <= float(respuesta_usuario) <= valor_real["rango"][1]:
            return "yellow", 0.5
        else:
            return "red", 0
    except:
        return "red", 0

def verificar_respuesta_multiple(respuestas_usuario):
    """Verifica respuestas para ejercicio 6 (múltiples)"""
    try:
        # Parsear el JSON de respuestas
        respuestas = json.loads(respuestas_usuario)
        
        puntajes_parciales = []
        colores_parciales = []
        
        # Verificar cada respuesta
        for clave, valor_correcto in valores[6].items():
            if clave in respuestas:
                respuesta_usuario = respuestas[clave]
                
                try:
                    # Verificar valor numérico
                    valor_usuario = float(respuesta_usuario["valor"])
                    
                    if str(valor_usuario) == str(valor_correcto["fijo"]):
                        puntajes_parciales.append(1)
                        colores_parciales.append("green")
                    elif valor_correcto["rango"][0] <= valor_usuario <= valor_correcto["rango"][1]:
                        puntajes_parciales.append(0.5)
                        colores_parciales.append("yellow")
                    else:
                        puntajes_parciales.append(0)
                        colores_parciales.append("red")
                except:
                    puntajes_parciales.append(0)
                    colores_parciales.append("red")
            else:
                puntajes_parciales.append(0)
                colores_parciales.append("red")
        
        # Calcular puntaje total (máximo 4 puntos)
        puntaje_total = sum(puntajes_parciales)
        
        # Determinar color general
        if all(color == "green" for color in colores_parciales):
            color_general = "green"
        elif any(color == "green" for color in colores_parciales) or any(color == "yellow" for color in colores_parciales):
            color_general = "yellow"
        else:
            color_general = "red"
            
        return color_general, puntaje_total
        
    except Exception as e:
        print(f"Error procesando respuestas múltiples: {e}")
        return "red", 0

@app.post("/guardar_resultado/")
def guardar_resultado(data: ResultadoRequest, db: Session = Depends(get_db)):
    color = ""
    puntaje = 0

    # 🧩 Verificar si el usuario ya respondió correctamente ese ejercicio
    existente = db.query(Resultado).filter(
        Resultado.usuario == data.usuario,
        Resultado.ejercicio == data.ejercicio
    ).order_by(Resultado.id.desc()).first()

    if existente and existente.color == "green":
        return {
            "mensaje": f"⚠️ Ya respondiste correctamente el ejercicio {data.ejercicio}.",
            "color": "green",
            "puntaje": existente.puntaje,
            "puntajeTotal": sum([r.puntaje for r in db.query(Resultado).filter(Resultado.usuario == data.usuario).all()])
        }

    # --- Lógica de corrección ---
    if data.ejercicio == 6:
        # Ejercicio con respuestas múltiples
        color, puntaje = verificar_respuesta_multiple(data.respuesta)
    elif data.ejercicio in valores:
        # Ejercicios simples (1-5)
        color, puntaje = verificar_respuesta_simple(data.ejercicio, data.respuesta)
    else:
        color = "red"
        puntaje = 0

    # --- Crear el registro ---
    nuevo_resultado = Resultado(
        usuario=data.usuario,
        ejercicio=data.ejercicio,
        respuesta=data.respuesta,
        puntaje=puntaje,
        color=color,
        fecha=datetime.now()
    )

    db.add(nuevo_resultado)
    db.commit()
    db.refresh(nuevo_resultado)

    # --- Calcular total del usuario ---
    total = db.query(Resultado).filter(Resultado.usuario == data.usuario).with_entities(Resultado.puntaje).all()
    puntaje_total = sum([r[0] for r in total])

    return {
        "mensaje": f"Resultado del ejercicio {data.ejercicio} guardado correctamente.",
        "color": color,
        "puntaje": puntaje,
        "puntajeTotal": puntaje_total
    }

@app.get("/resultados/")
def obtener_resultados(db: Session = Depends(get_db)):
    resultados = db.query(Resultado).all()
    return {"resultados": resultados}

@app.get("/resultados_db/")
def obtener_resultados_db(db: Session = Depends(get_db)):
    resultados = db.query(Resultado).all()
    return {
        "resultados": [
            {
                "usuario": r.usuario,
                "ejercicio": r.ejercicio,
                "respuesta": r.respuesta,
                "puntaje": r.puntaje,
                "color": r.color,
                "fecha": r.fecha
            }
            for r in resultados
        ]
    }

@app.delete("/eliminar_resultado/{id}")
def eliminar_resultado(id: int):
    db: Session = SessionLocal()
    resultado = db.query(Resultado).filter(Resultado.id == id).first()

    if not resultado:
        db.close()
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    db.delete(resultado)
    db.commit()
    db.close()

    return {"mensaje": f"Resultado con ID {id} eliminado correctamente."}

@app.delete("/eliminar_todos/")
def eliminar_todos():
    db: Session = SessionLocal()
    db.query(Resultado).delete()
    db.commit()
    db.close()

    return {"mensaje": "Todos los resultados fueron eliminados correctamente."}

class LoginRequest(BaseModel):
    usuario: str
    contrasena: str

# --- Endpoint de login ---
@app.post("/login/")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # ⚠️ Sin encriptar, comparar texto plano
    if usuario.contrasena != data.contrasena:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    return {"mensaje": f"✅ Login exitoso, bienvenido {data.usuario}"}

class UsuarioCreate(BaseModel):
    usuario: str
    email: str
    contrasena: str

# --- Crear usuario ---
@app.post("/register/")
def register(data: UsuarioCreate):
    db = SessionLocal()
    existe = db.query(Usuario).filter(Usuario.usuario == data.usuario).first()
    if existe:
        raise HTTPException(status_code=400, detail="El usuario ya existe")

    # ⚠️ Sin encriptar por ahora
    nuevo_usuario = Usuario(
        usuario=data.usuario,
        email=data.email,
        contrasena=data.contrasena
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    db.close()

    return {"mensaje": f"Usuario {data.usuario} registrado correctamente."}

@app.get("/puntaje_total/{usuario}")
def obtener_puntaje_total(usuario: str, db: Session = Depends(get_db)):
    resultados = db.query(Resultado).filter(Resultado.usuario == usuario).all()
    if not resultados:
        return {"usuario": usuario, "puntaje_total": 0}

    total = sum(r.puntaje for r in resultados)
    return {"usuario": usuario, "puntaje_total": total}