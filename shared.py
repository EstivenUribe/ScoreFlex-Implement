"""
Módulo compartido para mantener instancias globales accesibles por toda la aplicación.
Esto evita la creación de múltiples instancias y problemas de importación circular.
"""
import logging
from core import core

# Configurar logger
logger = logging.getLogger(__name__)

# Crear una instancia global del gestor de usuarios
# Esta instancia será compartida por toda la aplicación
logger.info("Inicializando gestor de usuarios global")
user_manager = core.crear_gestor_full()
logger.info("Gestor de usuarios global inicializado")
