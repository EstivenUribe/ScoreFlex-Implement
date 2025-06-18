from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import date

# Ajusta la ruta de importación según la estructura de tu proyecto
# Si 'core' está en el mismo nivel que 'api' y ambos son paquetes (tienen __init__.py)
# o si ScoreFlex-Implement es la raíz del proyecto y está en PYTHONPATH:
from core.core import Usuario as CoreUsuario, GestorUsuarios
import sys
from pathlib import Path

# Importar el gestor de usuarios global desde el módulo compartido
from shared import user_manager


# --- Pydantic Models ---
class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, example="Juan Pérez")
    email: EmailStr = Field(..., example="juan.perez@example.com")

class UsuarioIn(UsuarioBase):
    # Campos heredados: nombre, email
    password: str = Field(..., min_length=6, description="Contraseña del usuario")
    tipo_documento: str = Field(..., example="Cédula de Ciudadanía")
    numero_documento: str = Field(..., example="123456789")
    fecha_nacimiento: date = Field(..., example="2000-01-01")
    pais_origen: str = Field(..., example="Colombia")
    categoria: str = Field(..., example="Juez") # O deporte principal para otros roles
    foto_perfil: Optional[str] = Field(None, example="nombre_archivo.jpg")
    # is_admin se omite aquí porque siempre será False en la creación desde este endpoint.
    # Si se quisiera permitir su envío, se añadiría: 
    # is_admin: bool = Field(default=False, description="Define si el usuario es administrador")

class UsuarioOut(UsuarioBase):
    is_admin: bool
    tipo_documento: str
    numero_documento: str
    fecha_nacimiento: date
    pais_origen: str
    categoria: str
    foto_perfil: Optional[str]
    
    class Config:
        from_attributes = True # Compatible con objetos ORM/dataclass como nuestro CoreUsuario

# Lista de tipos de usuario permitidos
TIPOS_USUARIO_PERMITIDOS = ["Atleta", "Entrenador", "Delegado", "Juez", "Otro"]

class UsuarioUpdate(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario a actualizar (identificador)")
    nombre: Optional[str] = Field(None, min_length=1, example="Juan Carlos Pérez")
    # Password no se incluye aquí; usualmente se maneja en un endpoint dedicado.
    # is_admin se ha eliminado para evitar cambios no autorizados en el estado de administrador
    tipo_usuario: Optional[str] = Field(None, description="Tipo de usuario", example="Atleta")
    tipo_documento: Optional[str] = Field(None, example="Cédula de Ciudadanía")
    numero_documento: Optional[str] = Field(None, example="123456789")
    fecha_nacimiento: Optional[date] = Field(None, example="2000-01-01")
    pais_origen: Optional[str] = Field(None, example="Colombia")
    categoria: Optional[str] = Field(None, example="Futbol")
    foto_perfil: Optional[str] = Field(None, example="nombre_archivo_actualizado.jpg")


# --- API Router ---
router = APIRouter()

# Usar la instancia global del gestor de usuarios
# Asumimos que las operaciones de API son realizadas por un administrador
# por lo que pasamos solicitante_admin=True a los métodos del gestor.
# El flag se pasa a cada método.
gestor_usuarios = user_manager
SOLICITANTE_ES_ADMIN = True # Flag para las llamadas al gestor

# --- Helper para convertir CoreUsuario a UsuarioOut ---
def convertir_a_usuario_out(core_usuario: CoreUsuario) -> UsuarioOut:
    return UsuarioOut(
        nombre=core_usuario.nombre, # Corregido de nombre_completo
        email=core_usuario.email,
        is_admin=core_usuario.is_admin,
        tipo_documento=core_usuario.tipo_documento,
        numero_documento=core_usuario.numero_documento,
        fecha_nacimiento=core_usuario.fecha_nacimiento,
        pais_origen=core_usuario.pais_origen,
        categoria=core_usuario.categoria,
        foto_perfil=core_usuario.foto_perfil,
        tipo_usuario=core_usuario.tipo_usuario
    )

# --- Endpoints ---
@router.post("/users", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
async def crear_nuevo_usuario(usuario_in: UsuarioIn):
    print("DEBUG: Entrando a crear_nuevo_usuario") # <--- PRINT DE DEBUG
    print(f"DEBUG: Datos recibidos: {usuario_in.model_dump_json(indent=2)}") # <--- PRINT DE DEBUG
    """
    Crea un nuevo usuario.
    - Devuelve **201 Created** si tiene éxito.
    - Devuelve **409 Conflict** si el usuario (email) ya existe.
    - Devuelve **403 Forbidden** si el solicitante no tiene permisos (manejado por el gestor).
    """
    print("DEBUG: Intentando crear instancia de CoreUsuario...")
    try:
        # 1. Crear la instancia de CoreUsuario (solo con los campos que espera)
        core_usuario = CoreUsuario(
            nombre=usuario_in.nombre,
            email=usuario_in.email,
            password=usuario_in.password,
            is_admin=False,  # Los usuarios creados aquí no son administradores
            tipo_documento=usuario_in.tipo_documento,
            numero_documento=usuario_in.numero_documento,
            fecha_nacimiento=usuario_in.fecha_nacimiento,
            pais_origen=usuario_in.pais_origen,
            categoria=usuario_in.categoria,
            foto_perfil=usuario_in.foto_perfil
        )
        print(f"DEBUG: CoreUsuario instanciado: {core_usuario}")

        # 2. Intentar guardar el usuario usando el gestor
        print("DEBUG: Intentando llamar a gestor_usuarios.crear_usuario...")
        creado = gestor_usuarios.crear_usuario(core_usuario, solicitante_admin=SOLICITANTE_ES_ADMIN)
        print(f"DEBUG: Resultado de gestor_usuarios.crear_usuario: {creado}")

        if not creado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario con este email ya existe."
            )

        # 3. Construir y devolver el objeto de respuesta UsuarioOut usando el helper
        return convertir_a_usuario_out(core_usuario)

    except PermissionError as e:
        # Este error es específico y se maneja como Forbidden
        print(f"DEBUG: PermissionError en crear_nuevo_usuario: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    except Exception as e:
        # Captura CUALQUIER otra excepción no esperada (como TypeError, ValueError, etc.)
        print(f"ERROR CRITICO: Excepción no controlada en crear_nuevo_usuario: {type(e).__name__} - {e}")
        import traceback
        print("----------- TRACEBACK COMPLETO -----------")
        traceback.print_exc()  # Imprime el traceback completo en la consola de Uvicorn
        print("----------------------------------------")
        # Devuelve un error HTTP 500 con un cuerpo JSON para que el frontend no falle al parsear
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal Server Error", "message": f"Ocurrió un error inesperado en el servidor: {type(e).__name__}"}
        )

@router.get("/users", response_model=List[UsuarioOut], tags=["Usuarios"])
async def obtener_usuarios():
    """
    Obtiene una lista de todos los usuarios.
    - Devuelve **403 Forbidden** si el solicitante no tiene permisos (manejado por el gestor).
    """
    try:
        lista_core_usuarios = gestor_usuarios.obtener_todos_los_usuarios(solicitante_admin=SOLICITANTE_ES_ADMIN)
        return [convertir_a_usuario_out(u) for u in lista_core_usuarios]
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/users/{email}", response_model=UsuarioOut, tags=["Usuarios"])
async def obtener_usuario_por_email(email: EmailStr):
    """
    Obtiene un usuario específico por su email.
    - Devuelve **404 Not Found** si el usuario no existe.
    - Devuelve **403 Forbidden** si el solicitante no tiene permisos (manejado por el gestor).
    """
    try:
        # El método obtener_usuario del gestor no requiere solicitante_admin en su firma actual
        # para la capa de seguridad, pero si lo requiriera, se pasaría.
        # La seguridad en obtener_usuario no está implementada en GestorUsuariosConSeguridad.
        # Si se quisiera proteger, se debería añadir.
        usuario = gestor_usuarios.obtener_usuario(email) # No hay chequeo de solicitante_admin aquí
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        return convertir_a_usuario_out(usuario)
    except PermissionError as e: # Si se añade seguridad a obtener_usuario
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/users/{email}", status_code=status.HTTP_204_NO_CONTENT, tags=["Usuarios"])
async def eliminar_usuario_por_email(email: EmailStr):
    """
    Elimina un usuario por su email.
    - Devuelve **204 No Content** si tiene éxito.
    - Devuelve **404 Not Found** si el usuario no existe.
    - Devuelve **403 Forbidden** si el solicitante no tiene permisos (manejado por el gestor).
    """
    try:
        eliminado = gestor_usuarios.eliminar_usuario(email, solicitante_admin=SOLICITANTE_ES_ADMIN)
        if not eliminado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        return # FastAPI devuelve 204 No Content automáticamente si no hay cuerpo de respuesta
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.put("/users", response_model=UsuarioOut, tags=["Usuarios"])
async def actualizar_usuario_existente(usuario_update: UsuarioUpdate):
    """
    Actualiza un usuario existente. El email en el cuerpo identifica al usuario.
    - Devuelve **200 OK** si tiene éxito.
    - Devuelve **404 Not Found** si el usuario no existe.
    - Devuelve **403 Forbidden** si el solicitante no tiene permisos (manejado por el gestor).
    """
    try:
        # Primero, obtener el usuario actual para actualizar solo los campos proporcionados
        usuario_actual = gestor_usuarios.obtener_usuario(usuario_update.email)
        if not usuario_actual:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado para actualizar.")

        # Normalizar el tipo de usuario si se proporciona
        tipo_usuario_normalizado = None
        if usuario_update.tipo_usuario is not None:
            tipo_usuario_normalizado = usuario_update.tipo_usuario.capitalize()
            if tipo_usuario_normalizado not in TIPOS_USUARIO_PERMITIDOS:
                print(f"WARNING: Tipo de usuario no válido: {tipo_usuario_normalizado}, manteniendo valor actual")
                tipo_usuario_normalizado = usuario_actual.tipo_usuario
        
        # Crear un objeto CoreUsuario con los datos actualizados
        # Si un campo no está en usuario_update, se usa el valor actual de usuario_actual
        # El password se toma del usuario_actual ya que no se modifica aquí.
        core_usuario_actualizado = CoreUsuario(
            email=usuario_actual.email, # Email no cambia, es el identificador
            password=usuario_actual.password, # Mantener la contraseña existente
            nombre=usuario_update.nombre if usuario_update.nombre is not None else usuario_actual.nombre,
            is_admin=usuario_actual.is_admin, # Mantener el estado de administrador actual, no se permite cambiar
            tipo_usuario=tipo_usuario_normalizado if tipo_usuario_normalizado is not None else usuario_actual.tipo_usuario,
            tipo_documento=usuario_update.tipo_documento if usuario_update.tipo_documento is not None else usuario_actual.tipo_documento,
            numero_documento=usuario_update.numero_documento if usuario_update.numero_documento is not None else usuario_actual.numero_documento,
            fecha_nacimiento=usuario_update.fecha_nacimiento if usuario_update.fecha_nacimiento is not None else usuario_actual.fecha_nacimiento,
            pais_origen=usuario_update.pais_origen if usuario_update.pais_origen is not None else usuario_actual.pais_origen,
            categoria=usuario_update.categoria if usuario_update.categoria is not None else usuario_actual.categoria,
            foto_perfil=usuario_update.foto_perfil if usuario_update.foto_perfil is not None else usuario_actual.foto_perfil
        )

        actualizado_flag = gestor_usuarios.actualizar_usuario(core_usuario_actualizado, solicitante_admin=SOLICITANTE_ES_ADMIN)
        
        if not actualizado_flag: # Esto podría ocurrir si el usuario fue eliminado entre el GET y el PUT
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado durante el proceso de actualización.")
            
        return convertir_a_usuario_out(core_usuario_actualizado)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
