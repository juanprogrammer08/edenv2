# EDÉN - Asistente Empresarial Inteligente

## Descripción General

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un asistente empresarial inteligente. La aplicación consta de tres servicios coordinados:

- **Frontend:** SPA React 18 + Vite, con login/registro y guardia de rutas basada en token JWT.
- **Backend:** API FastAPI con autenticación JWT, persistencia en PostgreSQL o SQLite.
- **Servidor Web:** Nginx que sirve la SPA y proxya la API.

El despliegue se realiza mediante Docker Compose con los tres servicios: base de datos, API y frontend.

---

## Contenido del Proyecto

- `README.md` — Documentación y guía de uso.
- `api/` — Código backend FastAPI.
- `web.Dockerfile` — Dockerfile para construir y servir la SPA React con Nginx.
- `docker-compose.yml` — Orquestación de servicios.
- `nginx.conf` — Configuración Nginx para SPA y proxy API.
- `index.html` — Entrada HTML para la SPA React.
- `package.json` — Dependencias y scripts frontend.
- `src/` — Código fuente React (App.jsx, main.jsx, style.css).
- `vite.config.js` — Configuración Vite.

---

## Desarrollo Local

### Requisitos Previos

- Docker y Docker Compose instalados.
- Node.js 18+ y npm para desarrollo frontend local.

### Levantar la Aplicación Completa con Docker Compose

1. Clonar el repositorio:

```bash
git clone <url-del-repositorio>
cd <directorio-del-proyecto>
```

2. Construir y levantar los servicios:

```bash
docker-compose up --build
```

3. Acceder a la aplicación frontend en:

```
http://localhost:8080
```

4. La API estará disponible en:

```
http://localhost:8080/api
```

### Desarrollo Frontend Local (sin Docker)

1. Entrar en el directorio frontend:

```bash
cd src
```

2. Instalar dependencias:

```bash
npm install
```

3. Ejecutar servidor de desarrollo:

```bash
npm run dev
```

4. Abrir en el navegador:

```
http://localhost:5173
```

> Nota: El frontend en desarrollo intentará consumir la API en `/api`. Para evitar problemas de CORS, se recomienda levantar también el backend con Docker o configurar proxy en Vite.

### Desarrollo Backend Local (sin Docker)

1. Entrar en el directorio `api`:

```bash
cd api
```

2. Crear y activar entorno virtual Python 3.12+:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecutar la API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Acceder a la documentación Swagger UI en:

```
http://localhost:8000/api/docs
```

---

## Usuarios de Prueba

Se incluyen usuarios de prueba para facilitar el acceso inicial:

| Usuario  | Contraseña |
|---------|------------|
| admin   | admin123   |
| usuario | usuario123 |

> Estos usuarios se pueden registrar también mediante el formulario de registro en la aplicación.

---

## Uso de la Aplicación

- **Login / Registro:** La pantalla inicial permite autenticarse o crear una cuenta nueva.
- **Autenticación:** Se usa token JWT almacenado en `localStorage`. Cada petición a la API incluye el token en el header `Authorization: Bearer <token>`.
- **Rutas protegidas:** Solo accesibles tras autenticación.
- **Datos de ejemplo:** El frontend usa datos de ejemplo si la API no responde.

---

## Despliegue en Dokploy

Para desplegar EDÉN en Dokploy, siga estos pasos:

1. Suba el proyecto a un repositorio Git accesible.

2. Cree un nuevo proyecto en Dokploy y configure el despliegue con Docker Compose.

3. Configure las variables de entorno para el servicio `api`:

- `AUTH_SECRET`: Cadena secreta para firmar los tokens JWT (ejemplo: `supersecreto123`).
- `DATABASE_URL`: Cadena de conexión a la base de datos PostgreSQL. Por defecto:

```
postgresql+psycopg://studio:studio@db:5432/producto
```

4. Configure el dominio personalizado en Dokploy para que apunte al puerto **8080** del servicio `web`.

5. Inicie el despliegue. Dokploy levantará los tres servicios:

- `db`: PostgreSQL con base de datos `producto`.
- `api`: Backend FastAPI.
- `web`: Servidor Nginx con la SPA React.

6. Acceda a la aplicación mediante el dominio configurado.

---

## Notas Técnicas

- La API está montada bajo el prefijo `/api`, por lo que todas las rutas (incluyendo `/auth`, `/health`) se acceden como `/api/auth`, `/api/health`, etc.
- El backend intenta conectarse a PostgreSQL, pero si falla, usa SQLite local `./app.db` para garantizar que la aplicación arranque siempre.
- El frontend no usa librerías externas para routing o peticiones HTTP, solo React y fetch nativo.
- El servidor Nginx sirve la SPA y proxya las peticiones `/api` al backend.
- El token JWT se obtiene en `/api/auth/login` y se usa para proteger las rutas CRUD.

---

## Contacto

Para soporte o consultas, contactar con el equipo de desarrollo de YERUZZA STUDIO.

---

¡Gracias por usar EDÉN - Asistente Empresarial Inteligente!