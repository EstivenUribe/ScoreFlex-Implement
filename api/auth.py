from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from pydantic import BaseModel, EmailStr # Importar BaseModel y EmailStr de Pydantic
import os
import logging
import bcrypt
from core import core # Para acceder al gestor de usuarios
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG) # Ensure debug logs are captured

router = APIRouter(
    tags=["Authentication"]
)

# Obtenemos una instancia del gestor de usuarios (full)
gestor_usuarios = core.crear_gestor_full()

# Obtener credenciales de admin desde variables de entorno con valores por defecto
ADMIN_USER_EMAIL = os.getenv("ADMIN_USER_EMAIL", "admin@scoreflex.com")
ADMIN_USER_PASSWORD = os.getenv("ADMIN_USER_PASSWORD", "qwerty24") # Usar variables de entorno

class LoginData(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool # Para informar al frontend si el usuario es admin
    redirect_url: str # URL a donde redirigir después del login

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña utilizando bcrypt"""
    # Si la contraseña almacenada no está en formato bcrypt, asumimos texto plano (compatibilidad)
    if not hashed_password.startswith('$2b$'):
        logger.debug(f"Contraseña en texto plano: Comparando '{plain_password}' con '{hashed_password}'")
        # Comparación directa para contraseñas en texto plano (modo legado)
        result = plain_password == hashed_password
        logger.debug(f"Resultado de verificación texto plano: {result}")
        return result
    
    # Si está en formato bcrypt, verificar correctamente
    try:
        logger.debug(f"Contraseña hasheada: Verificando con bcrypt")
        result = bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        logger.debug(f"Resultado de verificación bcrypt: {result}")
        return result
    except Exception as e:
        logger.error(f"Error verificando contraseña: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generar hash bcrypt para una contraseña"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Validar formato de email
    if '@' not in form_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de correo electrónico inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Establecer tiempo de expiración de la sesión (30 minutos)
    session_expiry = 1800  # 30 minutos en segundos
    
    # Caso especial para el administrador
    if form_data.username == ADMIN_USER_EMAIL and form_data.password == ADMIN_USER_PASSWORD:
        # En un sistema real, aquí se generaría un JWT u otro token seguro.
        # Por ahora, devolvemos un token ficticio y un flag de admin.
        request.session['user_email'] = ADMIN_USER_EMAIL
        request.session['is_admin'] = True
        request.session['expiry'] = session_expiry
        logger.debug(f"Admin session set in /token: {dict(request.session)}")
        return {
            "access_token": "admin_fake_token_for_scoreflex", 
            "token_type": "bearer",
            "is_admin": True,
            "redirect_url": "/dashboard" # Admin ahora va primero al dashboard
        }

    # Para usuarios regulares, buscar en la "base de datos" (users.json)
    usuario_existente = gestor_usuarios.obtener_usuario(email=form_data.username)
    
    if not usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña usando la función segura
    logger.debug(f"Autenticando usuario: {form_data.username}")
    if not verify_password(form_data.password, usuario_existente.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos", # Mismo mensaje para no revelar si el email existe
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Usuario regular autenticado
    request.session['user_email'] = usuario_existente.email
    request.session['is_admin'] = usuario_existente.is_admin
    request.session['expiry'] = session_expiry
    
    logger.debug(f"User session set in /token for {usuario_existente.email}: {dict(request.session)}")
    
    redirect_url = "/dashboard" if not usuario_existente.is_admin else "/home"
    
    return {
        "access_token": f"{usuario_existente.email}_fake_token_for_scoreflex", 
        "token_type": "bearer",
        "is_admin": usuario_existente.is_admin,
        "redirect_url": redirect_url
    }

# Endpoint para registrar nuevos usuarios con contraseña segura
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(login_data: LoginData):
    # Verificar si el usuario ya existe
    usuario_existente = gestor_usuarios.obtener_usuario(email=login_data.email)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Hash de la contraseña antes de almacenarla
    hashed_password = get_password_hash(login_data.password)
    
    # Crear nuevo usuario con contraseña hasheada
    try:
        # Crear objeto Usuario para pasarlo al gestor
        from core.core import Usuario
        nuevo_usuario = Usuario(
            email=login_data.email,
            password=hashed_password,
            nombre="Nuevo Usuario",  # Valor por defecto
            is_admin=False,
            tipo_usuario="Atleta"  # Por defecto todos son atletas
        )
        
        # Registrar el usuario en el gestor
        success = gestor_usuarios.crear_usuario(nuevo_usuario)
        
        if not success:
            logger.error(f"No se pudo crear el usuario: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario"
            )
            
        logger.info(f"Usuario registrado exitosamente: {login_data.email}")
        return {"message": "Usuario registrado correctamente", "email": login_data.email}
    except Exception as e:
        logger.error(f"Error al registrar usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el usuario"
        )
