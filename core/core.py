import abc
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import date
import threading
from dataclasses import asdict # For converting Usuario objects to dicts
try:
    from .storage import load_users, save_users
except ImportError:
    # Fallback for when running the script directly, useful for the __main__ block.
    # When core is imported as a package, the relative import will work.
    from storage import load_users, save_users

# 1. Definir la clase Usuario
@dataclass
class Usuario:
    nombre: str
    email: str
    password: str  # IMPORTANTE: Ya debe venir con hash si es nueva contraseña
    is_admin: bool = False  # Para el decorador de seguridad
    # Campos de perfil adicionales (opcionales)
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    pais_origen: Optional[str] = None
    categoria: Optional[str] = None
    foto_perfil: Optional[str] = None
    tipo_usuario: str = "Atleta"  # Juez, Atleta, Entrenador, etc. - Por defecto es Atleta

# 2. Definir la interfaz GestorUsuarios
class GestorUsuarios(abc.ABC):
    @abc.abstractmethod
    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        pass

    @abc.abstractmethod
    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        pass

    @abc.abstractmethod
    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        pass

    @abc.abstractmethod
    def obtener_usuario(self, email: str) -> Optional[Usuario]:
        pass

    @abc.abstractmethod
    def obtener_todos_los_usuarios(self, solicitante_admin: bool = False) -> List[Usuario]:
        pass

# 3. Implementar GestorUsuariosBasico
class GestorUsuariosBasico(GestorUsuarios):
    def __init__(self):
        self._lock = threading.Lock()
        self._usuarios: Dict[str, Usuario] = {} # Initialized empty, then loaded
        self._load_initial_users()

    def _load_initial_users(self):
        # This method is called during __init__.
        # The lock is acquired here to protect the initial population of self._usuarios.
        with self._lock:
            loaded_data = load_users() # Returns Dict[str, Dict]
            processed_usuarios = {}
            for email, udata in loaded_data.items():
                # Ensure 'password' field exists for successful Usuario instantiation.
                # Provide a placeholder if it's missing (e.g., for users from older data formats).
                if 'password' not in udata:
                    udata['password'] = 'default_password' # Placeholder for missing passwords
                
                # 'is_admin' will use its default from the dataclass if not in udata.
                # Other fields like 'nombre' and 'email' are assumed to be present from older data.
                # Convert fecha_nacimiento from string to date object if present
                if 'fecha_nacimiento' in udata and udata['fecha_nacimiento'] is not None:
                    if isinstance(udata['fecha_nacimiento'], str):
                        if udata['fecha_nacimiento']:  # If it's a non-empty string
                            try:
                                udata['fecha_nacimiento'] = date.fromisoformat(udata['fecha_nacimiento'])
                            except ValueError:
                                print(f"[WARNING] Invalid date format for 'fecha_nacimiento' for user {email}. Setting to None. Value: {udata['fecha_nacimiento']}")
                                udata['fecha_nacimiento'] = None
                        else:  # If it's an empty string
                            udata['fecha_nacimiento'] = None
                    # If it's already a date object, or any other type, we let Usuario(**udata) handle it or fail.
                    # This logic specifically targets the string-to-date conversion from JSON.

                try:
                    processed_usuarios[email] = Usuario(**udata)
                except TypeError as e:
                    # This might catch issues if other essential fields are unexpectedly missing
                    # or if udata contains fields not defined in Usuario dataclass (though **udata handles extra fields gracefully by ignoring them if not defined).
                    print(f"[ERROR] Could not create Usuario object for email '{email}' due to: {e}. User data: {udata}")
                    # Optionally, decide whether to skip this user or raise the error.
                    # For now, we'll let it skip the problematic user entry if a TypeError still occurs.
                    continue 
            self._usuarios = processed_usuarios

    def _persist_users(self):
        """Save users to the storage.
        This is a helper method for internal use by the GestorUsuariosBasico class.
        It prepares the data for JSON serialization."""
        # Asegurarse de que todos los usuarios tengan un tipo_usuario antes de guardar
        for user in self._usuarios.values():
            if not user.tipo_usuario:
                user.tipo_usuario = "Atleta"
        
        users_to_save = {email: asdict(user) for email, user in self._usuarios.items()}
        save_users(users_to_save)

    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        with self._lock:
            if usuario.email in self._usuarios:
                return False  # Usuario ya existe
            self._usuarios[usuario.email] = usuario
            self._persist_users()
            return True

    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        with self._lock:
            if email in self._usuarios:
                del self._usuarios[email]
                self._persist_users()
                return True
            return False # Usuario no encontrado

    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        with self._lock:
            if usuario.email in self._usuarios:
                self._usuarios[usuario.email] = usuario
                self._persist_users()
                return True
            return False # Usuario no encontrado

    def obtener_usuario(self, email: str) -> Optional[Usuario]:
        # Protect read access as well, in case of concurrent modifications
        # or if future modifications to this method require it.
        with self._lock:
            return self._usuarios.get(email)

    def obtener_todos_los_usuarios(self, solicitante_admin: bool = False) -> List[Usuario]:
        with self._lock:
            return list(self._usuarios.values())

# 4. Implementar un decorador base GestorUsuariosDecorador
class GestorUsuariosDecorador(GestorUsuarios):
    def __init__(self, gestor_envuelto: GestorUsuarios):
        self._gestor_envuelto = gestor_envuelto

    #@abc.abstractmethod # No es necesario que sean abstractos si solo delegan
    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        return self._gestor_envuelto.crear_usuario(usuario, solicitante_admin)

    #@abc.abstractmethod
    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        return self._gestor_envuelto.eliminar_usuario(email, solicitante_admin)

    #@abc.abstractmethod
    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        return self._gestor_envuelto.actualizar_usuario(usuario, solicitante_admin)
    
    def obtener_usuario(self, email: str) -> Optional[Usuario]:
        return self._gestor_envuelto.obtener_usuario(email)

    #@abc.abstractmethod
    def obtener_todos_los_usuarios(self, solicitante_admin: bool = False) -> List[Usuario]:
        return self._gestor_envuelto.obtener_todos_los_usuarios(solicitante_admin)

# 5. Implementar tres decoradores concretos

# 5.1 GestorUsuariosConSeguridad
class GestorUsuariosConSeguridad(GestorUsuariosDecorador):
    def _verificar_permiso(self, solicitante_admin: bool):
        if not solicitante_admin:
            raise PermissionError("El usuario no tiene permisos de administrador para realizar esta acción.")

    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        self._verificar_permiso(solicitante_admin)
        return super().crear_usuario(usuario, solicitante_admin)

    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        self._verificar_permiso(solicitante_admin)
        return super().eliminar_usuario(email, solicitante_admin)

    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        self._verificar_permiso(solicitante_admin)
        return super().actualizar_usuario(usuario, solicitante_admin)

    def obtener_todos_los_usuarios(self, solicitante_admin: bool = False) -> List[Usuario]:
        self._verificar_permiso(solicitante_admin)
        return super().obtener_todos_los_usuarios(solicitante_admin)

# 5.2 GestorUsuariosConRegistro
class GestorUsuariosConRegistro(GestorUsuariosDecorador):
    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        print(f"[REGISTRO] Intentando crear usuario: {usuario.email}")
        resultado = super().crear_usuario(usuario, solicitante_admin)
        if resultado:
            print(f"[REGISTRO] Usuario {usuario.email} creado exitosamente.")
        else:
            print(f"[REGISTRO] Fallo al crear usuario {usuario.email}.")
        return resultado

    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        print(f"[REGISTRO] Intentando eliminar usuario: {email}")
        resultado = super().eliminar_usuario(email, solicitante_admin)
        if resultado:
            print(f"[REGISTRO] Usuario {email} eliminado exitosamente.")
        else:
            print(f"[REGISTRO] Fallo al eliminar usuario {email} (no encontrado).")
        return resultado

    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        print(f"[REGISTRO] Intentando actualizar usuario: {usuario.email}")
        resultado = super().actualizar_usuario(usuario, solicitante_admin)
        if resultado:
            print(f"[REGISTRO] Usuario {usuario.email} actualizado exitosamente.")
        else:
            print(f"[REGISTRO] Fallo al actualizar usuario {usuario.email} (no encontrado).")
        return resultado

# 5.3 GestorUsuariosConNotificacion
class GestorUsuariosConNotificacion(GestorUsuariosDecorador):
    def crear_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        resultado = super().crear_usuario(usuario, solicitante_admin)
        if resultado:
            print(f"[NOTIFICACION] Enviando email de bienvenida a {usuario.email}...")
        return resultado

    def eliminar_usuario(self, email: str, solicitante_admin: bool = False) -> bool:
        usuario_existente = self._gestor_envuelto.obtener_usuario(email)
        resultado = super().eliminar_usuario(email, solicitante_admin)
        if resultado and usuario_existente:
            print(f"[NOTIFICACION] Enviando email de despedida a {email}...")
        return resultado

    def actualizar_usuario(self, usuario: Usuario, solicitante_admin: bool = False) -> bool:
        resultado = super().actualizar_usuario(usuario, solicitante_admin)
        if resultado:
            print(f"[NOTIFICACION] Enviando email de actualización de datos a {usuario.email}...")
        return resultado

# 6. Añadir una factoría crear_gestor_full
def crear_gestor_full() -> GestorUsuarios:
    gestor = GestorUsuariosBasico()
    gestor_con_notificacion = GestorUsuariosConNotificacion(gestor)
    gestor_con_registro = GestorUsuariosConRegistro(gestor_con_notificacion)
    gestor_con_seguridad = GestorUsuariosConSeguridad(gestor_con_registro)
    return gestor_con_seguridad

# Ejemplo de uso (opcional, para pruebas)
if __name__ == "__main__":
    print("--- Probando Gestor Básico ---")
    gestor_basico = GestorUsuariosBasico()
    admin_user = Usuario("Admin", "admin@example.com", "password", is_admin=True)
    user1 = Usuario("Test User 1", "user1@example.com", "password")
    
    gestor_basico.crear_usuario(admin_user)
    gestor_basico.crear_usuario(user1)
    print(gestor_basico.obtener_usuario("user1@example.com"))
    gestor_basico.eliminar_usuario("user1@example.com")
    print(gestor_basico.obtener_usuario("user1@example.com"))

    print("\n--- Probando Gestor Full (como admin) ---")
    gestor_completo_admin = crear_gestor_full()
    
    user_nuevo = Usuario("Nuevo Usuario", "nuevo@example.com", "password")
    print("\nCreando usuario (admin):")
    gestor_completo_admin.crear_usuario(user_nuevo, solicitante_admin=True)
    
    print("\nActualizando usuario (admin):")
    user_nuevo_actualizado = Usuario("Nuevo Usuario Actualizado", "nuevo@example.com", "password", is_admin=False)
    gestor_completo_admin.actualizar_usuario(user_nuevo_actualizado, solicitante_admin=True)
    print(gestor_completo_admin.obtener_usuario("nuevo@example.com"))

    print("\nEliminando usuario (admin):")
    gestor_completo_admin.eliminar_usuario("nuevo@example.com", solicitante_admin=True)
    print(gestor_completo_admin.obtener_usuario("nuevo@example.com"))

    print("\n--- Probando Gestor Full (como no admin intentando acción de admin) ---")
    gestor_completo_no_admin = crear_gestor_full()
    
    user_otro = Usuario("Otro Usuario", "otro@example.com", "password")
    try:
        print("\nIntentando crear usuario (no admin):")
        gestor_completo_no_admin.crear_usuario(user_otro, solicitante_admin=False)
    except PermissionError as e:
        print(f"Error esperado: {e}")

    gestor_completo_admin.crear_usuario(Usuario("ParaBorrar", "paraborrar@example.com"), solicitante_admin=True)
    print(f"Usuario para borrar existe: {gestor_completo_admin.obtener_usuario('paraborrar@example.com') is not None}")

    try:
        print("\nIntentando eliminar usuario (no admin):")
        gestor_completo_no_admin.eliminar_usuario("paraborrar@example.com", solicitante_admin=False)
    except PermissionError as e:
        print(f"Error esperado: {e}")
    
    print(f"Usuario para borrar aún existe: {gestor_completo_admin.obtener_usuario('paraborrar@example.com') is not None}")

    user_admin_creado_por_no_admin = Usuario("AdminCreadoPorNoAdmin", "admin_no_admin@example.com", is_admin=True)
    try:
        print("\nIntentando crear usuario ADMIN (solicitante es ADMIN para la acción):")
        gestor_completo_admin.crear_usuario(user_admin_creado_por_no_admin, solicitante_admin=True)
        print(f"Usuario admin creado: {gestor_completo_admin.obtener_usuario('admin_no_admin@example.com')}")
    except PermissionError as e:
        print(f"Error: {e}")

    gestor_completo_admin.eliminar_usuario("admin_no_admin@example.com", solicitante_admin=True)
    gestor_completo_admin.eliminar_usuario("paraborrar@example.com", solicitante_admin=True)
    
    print("\n--- Fin de las pruebas ---")
