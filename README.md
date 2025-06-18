# ScoreFlex - Sistema de Gestión Deportiva

![ScoreFlex Badge](https://img.shields.io/badge/ScoreFlex-Sistema%20de%20Gesti%C3%B3n%20Deportiva-1C9FC5)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0%2B-green)
![BCrypt](https://img.shields.io/badge/BCrypt-Seguridad-red)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

**Desarrollado por:** Rafael Uribe Alvarez, Mateo Carvajal, Jorge Eduardo Rivera, Harold Cuesta y Maria Isabel Marin.

## Introducción

ScoreFlex es una plataforma integral para la gestión de eventos deportivos, competencias y calificaciones. El sistema implementa una arquitectura robusta y escalable construida con Python y FastAPI, demostrando la aplicación de principios avanzados de diseño de software, con especial énfasis en el patrón Decorator. 

Nuestra plataforma proporciona:

- **Gestión completa de usuarios** con roles específicos (Administradores, Jueces, Atletas, Entrenadores)
- **Autenticación segura** utilizando bcrypt para el hash de contraseñas
- **Interfaces adaptativas** según el rol del usuario
- **Dashboard personalizado** con opciones relevantes para cada tipo de usuario
- **Panel administrativo** para la gestión centralizada de entidades del sistema

## Arquitectura del Sistema

ScoreFlex implementa una **Arquitectura en Capas (Layered Architecture)** avanzada, que organiza el sistema en componentes funcionales claramente separados:

### Estructura de Capas

1. **Capa de Presentación (Presentation Layer)**
   - **Tecnología principal**: Bootstrap 5.3, Jinja2 Templates, HTML5/CSS3
   - **Componentes**: `templates/dashboard.html`, `templates/login.html`, `templates/register.html`, `templates/home.html`
   - **Responsabilidad**: Interfaz de usuario adaptativa que responde al rol del usuario (Admin, Juez, Atleta, Entrenador)
   - **Característica destacada**: Navegación contextual que muestra opciones relevantes al tipo de usuario

2. **Capa de Aplicación (Application Layer)**
   - **Tecnología principal**: FastAPI, Starlette, Pydantic
   - **Componentes**: `main.py`, `api/auth.py`, `api/users.py`
   - **Responsabilidad**: Gestiona sesiones, autenticación, validación de datos y enrutamiento
   - **Característica destacada**: API RESTful con endpoints optimizados que aprovechan typing hints para validación automática

3. **Capa de Dominio (Domain Layer)**
   - **Tecnología principal**: Python Core, Abstracción OOP, Patrón Decorator
   - **Componentes**: `core/core.py` (definición de entidades y servicios)
   - **Responsabilidad**: Implementa la lógica de negocio y aplica el patrón decorator para extender funcionalidades
   - **Característica destacada**: Modelo de usuarios con roles específicos (tipo_usuario) y servicios decorados

4. **Capa de Infraestructura (Infrastructure Layer)**
   - **Tecnología principal**: JSON, Threading, BCrypt
   - **Componentes**: `core/storage.py`, `users.json`
   - **Responsabilidad**: Persistencia de datos, seguridad y encriptación
   - **Característica destacada**: Hasheo seguro de contraseñas con BCrypt y mecanismos concurrencia-seguros

### Beneficios de la Arquitectura

- **Alta Cohesión, Bajo Acoplamiento**: Cada componente tiene una responsabilidad única y bien definida
- **Escalabilidad**: El sistema puede crecer modularmente incorporando nuevos servicios o componentes
- **Mantenibilidad**: Los cambios en una capa no afectan a otras capas, facilitando las actualizaciones
- **Extensibilidad**: Nuevas funcionalidades se pueden integrar sin modificar el código existente (Open/Closed Principle)

## Patrón de Diseño Principal: Decorator

### Definición e Implementación Técnica

El **Patrón Decorator** es un patrón de diseño estructural que permite extender dinámicamente el comportamiento de objetos mediante una serie de "envolturas" (wrappers) que implementan la misma interfaz. En ScoreFlex, este patrón se implementa mediante:

```python
# Interfaz base (AbstractBaseClass)
class GestorUsuarios(ABC):
    @abstractmethod
    def crear_usuario(self, email, password) -> Usuario: pass
    
    @abstractmethod
    def obtener_usuario(self, email) -> Optional[Usuario]: pass
    
    # Otros métodos abstractos...

# Implementación concreta base
class GestorUsuariosBasico(GestorUsuarios):
    # Implementación base de operaciones CRUD
    ...

# Decorador base (mantiene la interfaz)
class GestorUsuariosDecorator(GestorUsuarios):
    def __init__(self, gestor_decorado: GestorUsuarios):
        self._gestor = gestor_decorado
    
    # Delegación de métodos al objeto decorado
    ...

# Decoradores concretos que añaden comportamiento
class GestorUsuariosConSeguridad(GestorUsuariosDecorator):
    # Añade verificaciones de permisos antes de ejecutar operaciones
    ...

class GestorUsuariosConRegistro(GestorUsuariosDecorator):
    # Añade registro de operaciones (logging)
    ...

class GestorUsuariosConNotificacion(GestorUsuariosDecorator):
    # Añade notificaciones al crear/modificar usuarios
    ...
```

### Justificación Técnica del Patrón Decorator

1. **Composición Dinámica de Comportamientos**:
   - Los decoradores pueden combinarse y anidarse en cualquier orden en tiempo de ejecución
   - La clase base `GestorUsuariosBasico` mantiene su simplicidad y claridad de propósito
   - Ejemplo: `GestorUsuariosConSeguridad(GestorUsuariosConRegistro(GestorUsuariosBasico()))` añade primero registro y luego seguridad

2. **Aplicación de Principios SOLID**:
   - **S (Single Responsibility)**: Cada decorador tiene una única responsabilidad bien definida
   - **O (Open/Closed)**: Extendemos funcionalidad sin modificar código existente
   - **L (Liskov Substitution)**: Todos los decoradores implementan la interfaz `GestorUsuarios` y son intercambiables
   - **I (Interface Segregation)**: La interfaz `GestorUsuarios` define un contrato claro y cohesivo
   - **D (Dependency Inversion)**: Los componentes dependen de abstracciones, no de implementaciones concretas

3. **Ventajas sobre Alternativas**:
   - **vs Herencia**: Evita jerarquías profundas y explosiones combinatorias de clases
   - **vs Estrategia**: Permite combinar múltiples comportamientos en lugar de seleccionar uno
   - **vs Cadena de Responsabilidad**: Garantiza que todas las "capas" procesarán la solicitud

### Factory Pattern para Simplificar Creación

Se implementa un factory method `crear_gestor_full()` que encapsula la lógica de creación del stack de decoradores:

```python
def crear_gestor_full() -> GestorUsuarios:
    """Factory para crear un gestor de usuarios completo con todas las capas."""
    gestor_base = GestorUsuariosBasico()
    gestor_con_registro = GestorUsuariosConRegistro(gestor_base)
    gestor_con_seguridad = GestorUsuariosConSeguridad(gestor_con_registro)
    return GestorUsuariosConNotificacion(gestor_con_seguridad)
```

Esta función permite que los clientes obtengan una instancia completa sin preocuparse por el orden de decoración o la configuración interna, aplicando el principio de abstracción.

## Tecnologías Utilizadas

ScoreFlex integra tecnologías modernas para crear una plataforma robusta y escalable:

### Backend

- **Python 3.9+**: Lenguaje base con typing hints y características modernas
- **FastAPI**: Framework de API de alto rendimiento basado en estándares abiertos (OpenAPI, JSON Schema)
- **Pydantic**: Validación de datos, serialización y documentación automatizada
- **Starlette**: Toolkit ASGI para aplicaciones web asíncronas
- **BCrypt**: Biblioteca de hash seguro para contraseñas
- **Jinja2**: Motor de plantillas para la generación de HTML dinámico
- **Python Standard Library**:
  - **ABC**: Para definir interfaces y clases abstractas (patrón Decorator)
  - **JSON**: Para almacenamiento persistente de datos
  - **Threading**: Para manejo seguro de concurrencia
  - **Typing**: Para anotaciones de tipo y mejor documentación
  - **Logging**: Para registro detallado de eventos del sistema

### Frontend

- **Bootstrap 5.3**: Framework CSS para diseño responsive y componentes UI
- **HTML5/CSS3**: Estándares web para estructura y estilo
- **Bootstrap Icons**: Biblioteca de iconos vectoriales integrada
- **JavaScript**: Interactividad del lado del cliente

### Seguridad

- **Hash de contraseñas**: BCrypt para almacenamiento seguro de credenciales
- **Sesiones seguras**: SessionMiddleware con expiración configurable
- **HTTPS**: Soporte para conexiones cifradas
- **CORS**: Políticas de seguridad para recursos de origen cruzado
- **Validación de entrada**: Verificación rigurosa mediante modelos Pydantic

## Estructura del Proyecto

```
ScoreFlex-Implement/
├── api/
│   ├── __init__.py
│   ├── auth.py             # Autenticación, registro y gestión de sesiones
│   └── users.py            # Endpoints y modelos para gestión de usuarios
├── core/
│   ├── __init__.py
│   ├── core.py             # Lógica de negocio y patrón Decorator
│   └── storage.py          # Persistencia de datos (users.json)
├── static/
│   └── img/                # Imágenes del sistema (logo, etc.)
├── templates/
│   ├── dashboard.html      # Dashboard con navegación adaptativa según rol
│   ├── home.html           # Panel de administración de usuarios
│   ├── login.html          # Formulario de inicio de sesión
│   └── register.html       # Formulario de registro
├── users.json              # Base de datos JSON para usuarios
├── .env                    # Variables de entorno (admin, secret keys)
├── .gitignore              # Archivos y directorios excluidos del control de versiones
├── main.py                 # Punto de entrada de la aplicación FastAPI
├── Procfile                # Configuración para plataformas cloud (Heroku, etc.)
├── README.md               # Documentación del proyecto
└── requirements.txt        # Dependencias del proyecto
```

## Aspectos Clave de Diseño de Software y Características Implementadas

### Principios de Diseño Avanzados

- **Arquitectura Basada en Interfaces**: La clase abstracta `GestorUsuarios` define un contrato claro para todas las operaciones de gestión de usuarios, permitiendo implementaciones intercambiables.

- **Inversión de Dependencias**: Los componentes de mayor nivel (API endpoints) dependen de abstracciones (`GestorUsuarios`), no de implementaciones concretas, siguiendo el principio DIP de SOLID.

- **Composición Modular**: La funcionalidad del sistema se construye mediante la composición de componentes especializados, especialmente visible en la implementación del patrón Decorator.

### Sistema de Roles de Usuario

- **Roles Implementados y Normalizados**:
  - **Atleta**: Acceso a su perfil deportivo, competencias e inscripciones.
  - **Entrenador**: Gestión de atletas, calendarios y estadísticas.
  - **Delegado**: Representación de equipos y gestión administrativa.
  - **Juez**: Puede calificar participantes, ver eventos asignados y generar reportes.
  - **Otro**: Rol genérico para otros tipos de usuarios del sistema.
  - **Administrador**: Acceso completo al sistema (asignado internamente, no seleccionable durante registro).

- **Validación de Roles**: El sistema valida y normaliza los tipos de usuario tanto en el registro como en la actualización, asegurando que solo se utilicen valores permitidos.

- **Interfaz Adaptativa**: El dashboard muestra opciones de navegación personalizadas según el rol del usuario conectado.

### Seguridad e Integridad de Datos

- **Autenticación Segura**: Implementación de hash bcrypt para contraseñas con compatibilidad legacy para sistemas preexistentes.

- **Gestión de Sesiones**: Session middleware con manejo de expiración para proteger contra el secuestro de sesiones.

- **Validación Estructurada**: Uso extensivo de Pydantic para validación de datos, definiendo claramente las estructuras esperadas tanto para entrada como para salida.

### Características Técnicas Destacadas

- **API Asíncrona**: FastAPI con soporte para operaciones asíncronas mediante `async/await` para mejor rendimiento bajo carga.

- **Generación Dinámica de UI**: Templating con Jinja2 que adapta las vistas según los permisos y roles de usuario.

- **Gestión de Concurrencia**: Implementación de `threading.Lock` para operaciones seguras con archivos en entornos multi-hilo.

- **Flujo de Registro Optimizado**: Sistema de registro unificado que valida y normaliza los datos de usuario, asegurando consistencia en los tipos de usuario y evitando duplicidades.

- **Gestión de Usuarios Mejorada**: Interfaz de administración que permite editar roles de usuario de forma segura, manteniendo la integridad del sistema de permisos.

### Consideraciones para Producción

- **Persistencia de Datos**: La solución actual usa archivos JSON, adecuados para desarrollo. Para producción se recomienda migrar a PostgreSQL o MongoDB.

- **Escalabilidad**: La arquitectura actual permite escalar horizontalmente los componentes, especialmente la API FastAPI que puede desplegarse tras un balanceador de carga.

- **Monitoreo**: Se ha implementado logging extensivo para facilitar la depuración y el monitoreo del sistema en producción.

## Conclusiones y Trabajo Futuro

ScoreFlex demuestra la aplicación de principios avanzados de ingeniería de software en un sistema de gestión deportiva, destacando el uso del patrón Decorator para crear una arquitectura modular y extensible.

Este proyecto establece una base sólida para futuras ampliaciones, incluyendo:

1. **Implementación completa de módulos de eventos y competencias** para complementar la gestión de usuarios.

2. **Sistema de calificaciones para jueces** con algoritmos específicos para diferentes disciplinas deportivas.

3. **Integración con servicios externos** como sistemas de streaming para transmisión de eventos.

4. **Optimización de performance** mediante migración a almacenamiento en base de datos y caché.

5. **Expansión de la seguridad** con JWT, OAuth2 y políticas de RBAC (Role-Based Access Control) más granulares.

ScoreFlex representa un ejemplo práctico de cómo los patrones de diseño, especialmente el Decorator, pueden mejorar la mantenibilidad, escalabilidad y extensibilidad de una aplicación web moderna.

## Configuración y Ejecución Local

1.  **Clonar el repositorio** (si aún no lo has hecho).
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd ScoreFlex-Implement
    ```
2.  **Crear y activar un entorno virtual**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Ejecutar la aplicación**:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
5.  **Acceder a la aplicación en tu navegador**:
    *   Registro: `http://localhost:8000/register`
    *   Login: `http://localhost:8000/login`
    *   Documentación API (Swagger): `http://localhost:8000/docs`

## Despliegue

El proyecto está preparado para el despliegue en plataformas como Render o Heroku gracias a:

*   **`gunicorn`**: Incluido en `requirements.txt` como servidor WSGI/ASGI de producción.
*   **`Procfile`**: Especifica el comando `web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app` para iniciar la aplicación.

Recuerda configurar una base de datos persistente en tu plataforma de hosting para el uso en producción.
