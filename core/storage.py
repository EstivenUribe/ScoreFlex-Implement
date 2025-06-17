import json
import os
import logging
from typing import Dict, Any
from datetime import date
from pathlib import Path

# Configurar logger
logger = logging.getLogger(__name__)

# Determinar la ruta base del proyecto y la ruta del archivo users.json
BASE_DIR = Path(__file__).resolve().parent.parent
USERS_FILE = os.path.join(BASE_DIR, "users.json")

def load_users() -> Dict[str, Dict]:
    """Carga los usuarios desde users.json. Devuelve un diccionario vacío si el archivo no existe."""
    if not os.path.exists(USERS_FILE):
        logger.warning(f"El archivo de usuarios no existe en la ruta: {USERS_FILE}. Se creará uno nuevo.")
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        # Crear archivo vacío
        save_users({})
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Usuarios cargados correctamente. Total: {len(data)}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON de usuarios: {e}")
        # Hacer backup del archivo corrupto
        backup_file = f"{USERS_FILE}.bak"
        try:
            os.rename(USERS_FILE, backup_file)
            logger.info(f"Archivo corrupto respaldado como: {backup_file}")
        except OSError as e:
            logger.error(f"No se pudo hacer backup del archivo corrupto: {e}")
        
        # Devolver diccionario vacío y crear nuevo archivo
        save_users({})
        return {}
    except IOError as e:
        logger.error(f"Error de IO al leer usuarios: {e}")
        return {}

def json_date_serializer(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, date):
        return obj.isoformat()
    # Añadir otros tipos si es necesario
    raise TypeError(f"Tipo no serializable: {type(obj).__name__}")

def save_users(data: Dict[str, Dict]) -> bool:
    """Guarda los datos de los usuarios en users.json, sobrescribiendo el archivo.
    Utiliza una indentación de 2 espacios para mejor legibilidad.
    
    Retorna:
        bool: True si la operación fue exitosa, False en caso contrario.
    """
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        
        # Primero escribimos a un archivo temporal para no corromper el original en caso de error
        temp_file = f"{USERS_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=json_date_serializer)
        
        # Si todo va bien, reemplazamos el archivo original
        if os.path.exists(USERS_FILE):
            os.replace(temp_file, USERS_FILE)
        else:
            os.rename(temp_file, USERS_FILE)
            
        logger.info(f"Usuarios guardados correctamente. Total: {len(data)}")
        return True
    except IOError as e:
        logger.error(f"Error al guardar usuarios: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al guardar usuarios: {e}")
        return False
