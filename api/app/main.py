from fastapi import FastAPI, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, Boolean
from typing import Optional, List
from datetime import datetime, timedelta
import os

# Configuración y constantes
AUTH_SECRET = os.getenv("AUTH_SECRET", "cambiameporunasecretomuyseguro")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Motor y sesión SQLAlchemy
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    # Test connection
    with engine.connect() as conn:
        conn.execute(select(1))
except Exception:
    # Fallback a SQLite local
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app con root_path para que /docs y /openapi.json funcionen bajo /api
app = FastAPI(root_path="/api")

# CORS (permitir frontend local y producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos SQLAlchemy

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(50), default="pendiente")  # pendiente, aceptada, rechazada
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="cotizaciones")
    items = relationship("ItemCotizacion", back_populates="cotizacion", cascade="all, delete-orphan")

class ItemCotizacion(Base):
    __tablename__ = "items_cotizacion"
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(200), nullable=False)
    cantidad = Column(Float, default=1.0)
    precio_unitario = Column(Float, default=0.0)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"))

    cotizacion = relationship("Cotizacion", back_populates="items")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(50), default="activo")  # activo, finalizado, cancelado
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="proyectos")
    tareas = relationship("Tarea", back_populates="proyecto", cascade="all, delete-orphan")

class Tarea(Base):
    __tablename__ = "tareas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_vencimiento = Column(DateTime, nullable=True)
    completada = Column(Boolean, default=False)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"))

    proyecto = relationship("Proyecto", back_populates="tareas")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Schemas Pydantic

from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserOut(UserBase):
    id: int
    full_name: Optional[str] = None
    is_active: bool

    class Config:
        orm_mode = True

class ItemCotizacionBase(BaseModel):
    descripcion: str = Field(..., max_length=200)
    cantidad: float = 1.0
    precio_unitario: float = 0.0

class ItemCotizacionCreate(ItemCotizacionBase):
    pass

class ItemCotizacionOut(ItemCotizacionBase):
    id: int

    class Config:
        orm_mode = True

class CotizacionBase(BaseModel):
    titulo: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    estado: Optional[str] = "pendiente"

class CotizacionCreate(CotizacionBase):
    items: List[ItemCotizacionCreate] = []

class CotizacionOut(CotizacionBase):
    id: int
    fecha_creacion: datetime
    items: List[ItemCotizacionOut] = []

    class Config:
        orm_mode = True

class ProyectoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    estado: Optional[str] = "activo"

class ProyectoCreate(ProyectoBase):
    pass

class ProyectoOut(ProyectoBase):
    id: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None

    class Config:
        orm_mode = True

class TareaBase(BaseModel):
    titulo: str = Field(..., max_length=150)
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    completada: bool = False

class TareaCreate(TareaBase):
    pass

class TareaOut(TareaBase):
    id: int

    class Config:
        orm_mode = True

# Dependencias

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seguridad y autenticación

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, username: str):
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

# Routers

api_router = APIRouter(prefix="/api")

# Healthcheck

@api_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

# Auth endpoints

@api_router.post("/auth/register", response_model=UserOut, tags=["auth"])
async def register(username: str = Form(...), password: str = Form(...), full_name: Optional[str] = Form(None), db: Session = Depends(get_db)):
    user = get_user(db, username)
    if user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password, full_name=full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@api_router.post("/auth/login", response_model=Token, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me", response_model=UserOut, tags=["auth"])
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# CRUD Cotizaciones

@api_router.post("/cotizaciones", response_model=CotizacionOut, tags=["cotizaciones"])
async def create_cotizacion(cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_cotizacion = Cotizacion(
        titulo=cotizacion.titulo,
        descripcion=cotizacion.descripcion,
        estado=cotizacion.estado,
        owner_id=current_user.id,
    )
    db.add(db_cotizacion)
    db.commit()
    db.refresh(db_cotizacion)
    # Añadir items
    for item in cotizacion.items:
        db_item = ItemCotizacion(
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            cotizacion_id=db_cotizacion.id,
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_cotizacion)
    return db_cotizacion

@api_router.get("/cotizaciones", response_model=List[CotizacionOut], tags=["cotizaciones"])
async def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizaciones = db.execute(select(Cotizacion).where(Cotizacion.owner_id == current_user.id)).scalars().all()
    return cotizaciones

@api_router.get("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut, tags=["cotizaciones"])
async def get_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cotizacion

@api_router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionOut, tags=["cotizaciones"])
async def update_cotizacion(cotizacion_id: int, cotizacion_in: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    cotizacion.titulo = cotizacion_in.titulo
    cotizacion.descripcion = cotizacion_in.descripcion
    cotizacion.estado = cotizacion_in.estado
    # Borrar items antiguos
    db.execute(delete(ItemCotizacion).where(ItemCotizacion.cotizacion_id == cotizacion.id))
    db.commit()
    # Añadir nuevos items
    for item in cotizacion_in.items:
        db_item = ItemCotizacion(
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            cotizacion_id=cotizacion.id,
        )
        db.add(db_item)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion

@api_router.delete("/cotizaciones/{cotizacion_id}", status_code=204, tags=["cotizaciones"])
async def delete_cotizacion(cotizacion_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cotizacion = db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id, Cotizacion.owner_id == current_user.id)).scalar_one_or_none()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cotizacion)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# CRUD Proyectos

@api_router.post("/proyectos", response_model=ProyectoOut, tags=["proyectos"])
async def create_proyecto(proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proyecto = Proyecto(
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        estado=proyecto.estado,
        owner_id=current_user.id,
    )
    db.add(db_proyecto)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@api_router.get("/proyectos", response_model=List[ProyectoOut], tags=["proyectos"])
async def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyectos = db.execute(select(Proyecto).where(Proyecto.owner_id == current_user.id)).scalars().all()
    return proyectos

@api_router.get("/proyectos/{proyecto_id}", response_model=ProyectoOut, tags=["proyectos"])
async def get_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto

@api_router.put("/proyectos/{proyecto_id}", response_model=ProyectoOut, tags=["proyectos"])
async def update_proyecto(proyecto_id: int, proyecto_in: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    proyecto.nombre = proyecto_in.nombre
    proyecto.descripcion = proyecto_in.descripcion
    proyecto.estado = proyecto_in.estado
    db.commit()
    db.refresh(proyecto)
    return proyecto

@api_router.delete("/proyectos/{proyecto_id}", status_code=204, tags=["proyectos"])
async def delete_proyecto(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# CRUD Tareas

@api_router.post("/proyectos/{proyecto_id}/tareas", response_model=TareaOut, tags=["tareas"])
async def create_tarea(proyecto_id: int, tarea: TareaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db_tarea = Tarea(
        titulo=tarea.titulo,
        descripcion=tarea.descripcion,
        fecha_vencimiento=tarea.fecha_vencimiento,
        completada=tarea.completada,
        proyecto_id=proyecto.id,
    )
    db.add(db_tarea)
    db.commit()
    db.refresh(db_tarea)
    return db_tarea

@api_router.get("/proyectos/{proyecto_id}/tareas", response_model=List[TareaOut], tags=["tareas"])
async def list_tareas(proyecto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == proyecto_id, Proyecto.owner_id == current_user.id)).scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    tareas = db.execute(select(Tarea).where(Tarea.proyecto_id == proyecto.id)).scalars().all()
    return tareas

@api_router.get("/tareas/{tarea_id}", response_model=TareaOut, tags=["tareas"])
async def get_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id)).scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == tarea.proyecto_id)).scalar_one_or_none()
    if proyecto.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    return tarea

@api_router.put("/tareas/{tarea_id}", response_model=TareaOut, tags=["tareas"])
async def update_tarea(tarea_id: int, tarea_in: TareaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id)).scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == tarea.proyecto_id)).scalar_one_or_none()
    if proyecto.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    tarea.titulo = tarea_in.titulo
    tarea.descripcion = tarea_in.descripcion
    tarea.fecha_vencimiento = tarea_in.fecha_vencimiento
    tarea.completada = tarea_in.completada
    db.commit()
    db.refresh(tarea)
    return tarea

@api_router.delete("/tareas/{tarea_id}", status_code=204, tags=["tareas"])
async def delete_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tarea = db.execute(select(Tarea).where(Tarea.id == tarea_id)).scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    proyecto = db.execute(select(Proyecto).where(Proyecto.id == tarea.proyecto_id)).scalar_one_or_none()
    if proyecto.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    db.delete(tarea)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Montar router en app
app.include_router(api_router)