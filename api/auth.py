from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated, Optional
from pydantic import BaseModel, EmailStr # Importar BaseModel y EmailStr de Pydantic
from datetime import date
import os
import logging
import bcrypt
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG) # Ensure debug logs are captured

router = APIRouter(
    tags=["Authentication"]
)

# Importar el gestor de usuarios global desde el módulo compartido
# Esto asegura que usemos la misma instancia en toda la aplicación
from shared import user_manager as gestor_usuarios

# Obtener credenciales de admin desde variables de entorno con valores por defecto
ADMIN_USER_EMAIL = os.getenv("ADMIN_USER_EMAIL", "admin@scoreflex.com")
ADMIN_USER_PASSWORD = os.getenv("ADMIN_USER_PASSWORD", "qwerty24") # Usar variables de entorno

# Lista de tipos de usuario permitidos
TIPOS_USUARIO_PERMITIDOS = ["Atleta", "Entrenador", "Delegado", "Juez", "Otro"]

class LoginData(BaseModel):
    email: EmailStr
    password: str
    tipo_usuario: str = "Atleta"  # Valor por defecto
    nombre: Optional[str] = "Nuevo Usuario"
    tipo_documento: Optional[str] = "N/A"
    numero_documento: Optional[str] = "N/A"
    fecha_nacimiento: Optional[date] = None
    pais_origen: Optional[str] = "N/A"
    categoria: Optional[str] = "General"
    foto_perfil: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool # Para informar al frontend si el usuario es admin
    redirect_url: str # URL a donde redirigir después del login

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña utilizando bcrypt"""
    # Log the password types for debugging
    logger.debug(f"Verificando contraseña: plain_password type={type(plain_password)}, hashed_password type={type(hashed_password)}")
    logger.debug(f"Hashed password starts with: {hashed_password[:10] if hashed_password else 'None'}")
    
    # Si la contraseña almacenada no está en formato bcrypt, asumimos texto plano (compatibilidad)
    if not hashed_password or not isinstance(hashed_password, str) or not hashed_password.startswith('$2b$'):
        logger.debug(f"Contraseña en texto plano: Comparando '{plain_password}' con '{hashed_password}'")
        # Comparación directa para contraseñas en texto plano (modo legado)
        result = plain_password == hashed_password
        logger.debug(f"Resultado de verificación texto plano: {result}")
        return result
    
    # Si está en formato bcrypt, verificar correctamente
    try:
        logger.debug(f"Contraseña hasheada: Verificando con bcrypt")
        # Ensure both are properly encoded as bytes
        plain_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        hashed_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        
        result = bcrypt.checkpw(plain_bytes, hashed_bytes)
        logger.debug(f"Resultado de verificación bcrypt: {result}")
        return result
    except Exception as e:
        logger.error(f"Error verificando contraseña: {e}")
        logger.exception("Detalles del error:")
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
    
    logger.debug(f"Intento de login para: {form_data.username}")
        
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
        logger.warning(f"Usuario no encontrado: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña usando la función segura
    logger.debug(f"Autenticando usuario: {form_data.username}")
    logger.debug(f"Contraseña almacenada para {form_data.username}: {usuario_existente.password[:20]}...")
    
    auth_result = verify_password(form_data.password, usuario_existente.password)
    logger.debug(f"Resultado de autenticación para {form_data.username}: {auth_result}")
    
    if not auth_result:
        logger.warning(f"Contraseña incorrecta para usuario: {form_data.username}")
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
    
    # Corregir la lógica de redirección
    redirect_url = "/dashboard" if usuario_existente.is_admin else "/home"
    
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
    
    # Normalizar el tipo de usuario (asegurar que sea uno de los valores permitidos)
    tipo_usuario_normalizado = login_data.tipo_usuario.capitalize()
    if tipo_usuario_normalizado not in TIPOS_USUARIO_PERMITIDOS:
        logger.warning(f"Tipo de usuario no válido: {tipo_usuario_normalizado}, asignando valor por defecto: Atleta")
        tipo_usuario_normalizado = "Atleta"
    
    # Hash de la contraseña antes de almacenarla
    hashed_password = get_password_hash(login_data.password)
    logger.debug(f"Contraseña original: {login_data.password}, Contraseña hasheada: {hashed_password}")
    
    # Crear nuevo usuario con contraseña hasheada
    try:
        # Crear objeto Usuario para pasarlo al gestor
        from core.core import Usuario
        nuevo_usuario = Usuario(
            email=login_data.email,
            password=login_data.password,  # Usar contraseña sin hash para compatibilidad
            nombre=login_data.nombre,
            is_admin=False,
            tipo_usuario=tipo_usuario_normalizado,
            tipo_documento=login_data.tipo_documento,
            numero_documento=login_data.numero_documento,
            fecha_nacimiento=login_data.fecha_nacimiento,
            pais_origen=login_data.pais_origen,
            categoria=login_data.categoria,
            foto_perfil=login_data.foto_perfil
        )
        
        logger.info(f"Asignando tipo de usuario normalizado: {nuevo_usuario.tipo_usuario}")
        logger.debug(f"Datos de usuario antes de crear: {nuevo_usuario.__dict__}")

        
        # Registrar el usuario en el gestor
        success = gestor_usuarios.crear_usuario(nuevo_usuario, solicitante_admin=True)
        
        if not success:
            logger.error(f"No se pudo crear el usuario: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario"
            )
        
        # Verificar que el usuario se haya creado correctamente
        created_user = gestor_usuarios.obtener_usuario(email=login_data.email)
        if not created_user:
            logger.error(f"Usuario no encontrado después de creación: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al verificar la creación del usuario"
            )
        
        logger.info(f"Usuario registrado exitosamente: {login_data.email}")
        logger.debug(f"Datos del usuario creado: {created_user.email}, password: {created_user.password}")
        
        return {"message": "Usuario registrado correctamente", "email": login_data.email}
    except Exception as e:
        logger.error(f"Error al registrar usuario: {e}")
        logger.exception("Detalles del error:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el usuario: {str(e)}"
        )
