from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware # Para cookies de sesión
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
import logging
import os
import time
from typing import Optional
from dotenv import load_dotenv

from api.users import router as users_router
from api.auth import router as auth_router # Importar el nuevo router de autenticación
from core import core # Para acceder al gestor de usuarios en /home

# Cargar variables de entorno
load_dotenv()

# Configurar directorio base
BASE_DIR = Path(__file__).resolve().parent

# Configurar logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("uvicorn.error") # Use uvicorn's logger for visibility

app = FastAPI(
    title="Scoreflex API",
    description="API para gestionar usuarios con patrón decorador, persistencia y UI básica.",
    version="0.2.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las origenes para el prototipo
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todas las cabeceras
)

# Middleware personalizado para verificar la expiración de sesiones
class SessionExpiryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Verificar si la sesión ha expirado
        if 'user_email' in request.session:
            # Verificar si hay tiempo de expiración establecido
            expiry = request.session.get('expiry', 1800)  # Por defecto 30 minutos
            last_activity = request.session.get('last_activity', time.time())
            
            # Si ha pasado más tiempo que el permitido, limpiar la sesión
            if time.time() - last_activity > expiry:
                request.session.clear()
                logger.warning("Sesión expirada. Usuario desconectado.")
            else:
                # Actualizar último tiempo de actividad
                request.session['last_activity'] = time.time()
        
        # Continuar con la solicitud
        return await call_next(request)

# Obtener clave secreta de variable de entorno o usar una por defecto (solo para desarrollo)
secret_key = os.getenv("SESSION_SECRET_KEY", "super_secret_key_dont_use_in_prod")
if secret_key == "super_secret_key_dont_use_in_prod":
    logger.warning("¡ADVERTENCIA! Usando clave secreta por defecto. NO use esto en producción.")

# IMPORTANTE: El orden de registro de middleware es crucial
# Los middleware se ejecutan en orden INVERSO al que se registran
# Primero añadimos SessionExpiryMiddleware (se ejecutará después)
app.add_middleware(SessionExpiryMiddleware)

# Después añadimos SessionMiddleware (se ejecutará primero)
app.add_middleware(
    SessionMiddleware, 
    secret_key=secret_key,
    max_age=86400  # 24 horas en segundos (tiempo máximo de la cookie)
)

# Montar directorio estático (crea una carpeta 'static' en la raíz del proyecto si la necesitas)
app.mount("/static", StaticFiles(directory=str(Path(BASE_DIR, 'static'))), name="static")

# Montar directorio de plantillas
templates = Jinja2Templates(directory=str(Path(BASE_DIR, 'templates')))

# Incluir routers de API
app.include_router(users_router, prefix="/api", tags=["Usuarios API"])
app.include_router(auth_router, prefix="/api/auth", tags=["Autenticación API"]) # Añadir el router de autenticación con prefijo

# Dependencia para verificar autenticación
async def get_current_user(request: Request) -> Optional[str]:
    return request.session.get("user_email")

# Dependencia para verificar si el usuario es administrador
async def is_admin_user(request: Request) -> bool:
    return request.session.get("is_admin", False)

# --- Endpoints HTML ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False, name="serve_landing_page", tags=["Frontend - Root"])
async def get_landing_page(request: Request):
    """Sirve la página de inicio principal (landing page)."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, include_in_schema=False, name="serve_register_page")
async def get_register_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    # Si el usuario ya está autenticado, redirigir al dashboard
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, include_in_schema=False, name="serve_login_page")
async def get_login_page(request: Request, message: str = None, current_user: Optional[str] = Depends(get_current_user)):
    # Si el usuario ya está autenticado, redirigir al dashboard
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse("login.html", {"request": request, "message": message})

@app.get("/dashboard", response_class=HTMLResponse, name="serve_dashboard_page", include_in_schema=False)
async def serve_dashboard_page(
    request: Request,
    message: str = None,
    current_user: Optional[str] = Depends(get_current_user),
    is_admin: bool = Depends(is_admin_user)
):
    logger.debug(f"Dashboard access attempt. Session content: {dict(request.session)}")
    
    if not current_user:
        logger.warning(f"Dashboard access denied. User not in session. Redirecting to login.")
        return RedirectResponse(
            url=f"/login?message=Por favor, inicia sesión para continuar.", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    # Obtener información adicional del usuario desde el gestor de usuarios
    from api.auth import gestor_usuarios
    usuario = gestor_usuarios.obtener_usuario(current_user)
    tipo_usuario = None
    
    if usuario:
        tipo_usuario = usuario.tipo_usuario
        logger.debug(f"Tipo de usuario para {current_user}: {tipo_usuario}")
    else:
        logger.warning(f"No se pudo obtener información del usuario {current_user}")
    
    logger.info(f"Dashboard access granted for user: {current_user}")
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user_email": current_user,
        "is_admin": is_admin,
        "tipo_usuario": tipo_usuario,
        "message": message
    })

@app.get("/home", response_class=HTMLResponse, name="serve_home_page", include_in_schema=False)
async def serve_home_page(
    request: Request,
    current_user: Optional[str] = Depends(get_current_user),
    admin_status: bool = Depends(is_admin_user)
):
    logger.debug(f"Home access attempt. Session content: {dict(request.session)}")

    if not current_user:
        logger.warning(f"Home access denied. User not in session. Redirecting to login.")
        return RedirectResponse(
            url=app.url_path_for("serve_login_page") + "?message=Por+favor,+inicia+sesión+para+continuar", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    if not admin_status:
        logger.warning(f"Home access denied for user '{current_user}'. Not an admin. Redirecting to dashboard.")
        # Construct dashboard URL carefully, it might not have a query param by default
        dashboard_url = app.url_path_for("serve_dashboard_page")
        return RedirectResponse(
            url=f"{dashboard_url}?message=Acceso+restringido+a+administradores.", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    logger.info(f"Home access granted for admin user: {current_user}")
    users_list = []
    gestor = core.crear_gestor_full()
    try:
        users_list = gestor.obtener_todos_los_usuarios(solicitante_admin=True)
    except Exception as e:
        logger.error(f"Error fetching users for admin {current_user}: {e}")
        # Optionally, display an error on home.html or handle differently
    
    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request, 
            "user_email": current_user, 
            "is_admin": admin_status, 
            "users": users_list
        }
    )

@app.get("/logout", response_class=RedirectResponse, include_in_schema=False, name="serve_logout_page")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=app.url_path_for("serve_login_page") + "?message=Has+cerrado+sesión+exitosamente", status_code=303)

# Para ejecutar (asegúrate que main.py está en la raíz del proyecto):
# pip install -r requirements.txt
# uvicorn main:app --reload --host 0.0.0.0 --port 8000

# IMPORTANTE: Para producción, crea un archivo .env con estas variables:
# SESSION_SECRET_KEY=tu_clave_secreta_muy_segura
# ADMIN_USER_EMAIL=tu_email_admin
# ADMIN_USER_PASSWORD=tu_password_admin_seguro
# LOG_LEVEL=INFO
