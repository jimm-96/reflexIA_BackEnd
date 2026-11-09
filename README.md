# ReflexIA: Backend

API REST en Django y Django REST Framework para **ReflexIA**, la plataforma de práctica profesional pedagógica de la Universidad Central.

El proyecto completo tiene tres partes:

1. **Frontend** en React + TypeScript: listo, en el repo [`reflexIA`](https://github.com/gvbr-iel/reflexIA).
2. **Backend** en Django: este repositorio.
3. **Integración** entre ambos mediante la API: en iteraciones futuras.

> **Estado:** etapa 1 de 8, usuarios autorizados (whitelist). Los demás modelos se agregan por etapas. Ver [docs/plan-incremental.md](./docs/plan-incremental.md).

---

## Tecnologías

* **Python:** 3.13
* **Django:** 6.1
* **Django REST Framework:** 3.18
* **Base de datos:** SQLite en desarrollo; MySQL en una etapa posterior.

---

## Estructura

```
reflexIA_BackEnd/
├── reflexIA_Proyect/     # Proyecto Django
│   ├── settings.py       # Configuración (apps instaladas, idioma, base de datos)
│   └── urls.py           # Rutas raíz: /admin/ y /api/
├── reflexIA_App/         # Aplicación principal
│   ├── models.py         # Modelos (tablas)
│   ├── serializers.py    # Conversión de modelos a JSON
│   ├── views.py          # ViewSets de la API
│   ├── urls.py           # Router de DRF con los recursos
│   └── admin.py          # Registro de modelos en el panel de administración
├── docs/                 # Documentación
├── manage.py
└── requirements.txt
```

---

## Instalación y ejecución local

### 1. Clonar el repositorio
```bash
git clone https://github.com/jimm-96/reflexIA_BackEnd.git
cd reflexIA_BackEnd
```

### 2. Crear y activar el entorno virtual

* **En Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
  Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
* **En Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Aplicar las migraciones
```bash
python manage.py migrate
```

### 5. Crear un superusuario para el panel de administración
```bash
python manage.py createsuperuser
```

### 6. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

| Dirección | Qué hay |
|---|---|
| `http://127.0.0.1:8000/admin/` | Panel de administración de Django |
| `http://127.0.0.1:8000/api/` | Raíz de la API (interfaz navegable de DRF) |

---

## Endpoints

Esta sección se completa en cada etapa.

### 1. Recurso: Usuarios autorizados (`/api/usuarios/`)

Whitelist de correos que pueden ingresar a ReflexIA (HU-01).

| Método | Ruta | Acción |
| :--- | :--- | :--- |
| GET | `/api/usuarios/` | Lista todos los usuarios autorizados |
| POST | `/api/usuarios/` | Autoriza un correo nuevo |
| GET | `/api/usuarios/<id>/` | Muestra un usuario |
| PUT / PATCH | `/api/usuarios/<id>/` | Modifica un usuario (por ejemplo, revoca su acceso) |
| DELETE | `/api/usuarios/<id>/` | Elimina un usuario definitivamente |

* **Payload esperado (JSON):**
  ```json
  {
    "correo": "ana.perez@ucen.cl",
    "nombre": "Ana Pérez",
    "rol": "student"
  }
  ```
* **Valores permitidos:** `rol` = `student`, `teacher` o `admin`; `estado` = `active` o `revoked`.
* **Validaciones:** el correo debe terminar en `@ucen.cl` y no puede repetirse (sin importar mayúsculas). Si no se cumple, la API responde `400 Bad Request` con el motivo.

---

## Flujo de trabajo incremental

La configuración inicial (etapa 0) está en `main`. Cada etapa siguiente se desarrolla en su propia rama y se integra a `main` mediante un Pull Request:

```bash
git switch main
git pull
git switch -c feature/recurso-<nombre>     # por ejemplo, feature/recurso-usuarios
# ... commits de la etapa ...
git push -u origin feature/recurso-<nombre>
```

Dentro de cada rama, el recurso se agrega en commits pequeños, con este orden:

1. Modelo en `models.py` y su migración.
2. Registro en `admin.py` y prueba desde el panel.
3. Serializer en `serializers.py`.
4. ViewSet en `views.py`.
5. Ruta en `urls.py` y prueba en `/api/`.

El detalle de cada etapa y los mensajes de commit sugeridos están en [docs/plan-incremental.md](./docs/plan-incremental.md).
