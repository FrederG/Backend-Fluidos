from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ---  Conexión a la base de datos SQLite ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./fluidos.db"

# ---  Crear el motor ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# --- Crear la sesión local ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Clase base para los modelos ---
Base = declarative_base()

# ---  Definir el modelo de tabla ---
class Resultado(Base):
    __tablename__ = "resultados"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, index=True)
    ejercicio = Column(Integer)
    respuesta = Column(String)
    puntaje = Column(Float)
    color = Column(String)
    fecha = Column(DateTime, default=datetime.now)

# ---  Crear las tablas ---

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    contrasena = Column(String)
Base.metadata.create_all(bind=engine)

