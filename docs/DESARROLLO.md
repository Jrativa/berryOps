# Guía de desarrollo

> Legacy document (Spanish). Being replaced by English docs as areas are rewritten; see docs/README.md.

## Requisitos
Python 3.14, PostgreSQL, Node.js y pnpm.

## Variables de entorno

`apps/backend/.env` (se localiza respecto al código, no al directorio de trabajo)

| Variable | Descripción |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Conexión PostgreSQL |
| `SECRET_KEY` | Clave de firma del JWT. **Mínimo 32 caracteres**: con menos, el arranque (y Alembic, que lee los mismos `Settings`) falla con un mensaje claro que nunca muestra el valor. Rotarla invalida los access tokens vigentes; los refresh tokens (opacos, en BD) no se ven afectados |
| `ALGORITHM` | Algoritmo JWT (p. ej. `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vida del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Vida del refresh token |
| `ADMIN_ROLE_NAMES` | Opcional. Nombres de rol con permisos de administrador, separados por coma y sin distinguir mayúsculas (por defecto `admin,administrador`) |
| `CORS_ORIGINS` | Opcional. Orígenes permitidos separados por coma (por defecto `http://localhost:5173`). `*` se rechaza porque la API permite credenciales |
| `BOOTSTRAP_PASSWORD` | Solo para el CLI `bootstrap`: contraseña del primer administrador. No pertenece a `Settings`; se lee del entorno del proceso (si falta, el CLI la pide por prompt). No guardarla en `.env` |

`apps/frontend/.env`: `VITE_API_URL` — URL base del backend (p. ej. `http://localhost:8000`).

## Arranque

```bash
# Backend: siempre desde la raíz del repositorio
cd apps/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt      # requirements.txt está en UTF-16; si pip falla, convertirlo a UTF-8
cd ../..
uvicorn apps.backend.src.main:app --reload

# Pruebas del backend (también desde la raíz)
python -m pytest apps/backend        # todo: las pruebas `pg` se incluyen si hay TEST_DATABASE_URL
python -m pytest apps/backend -m pg  # solo las de PostgreSQL
python -m pytest apps/backend -m "not pg"  # sin PostgreSQL

cd apps/frontend
pnpm install --frozen-lockfile
pnpm dev
```

### Pruebas contra PostgreSQL (`pg`)

Usan una BD **separada**, `arandanos_test`, nunca la de desarrollo.

1. Copiar `apps/backend/.env.test.example` a `apps/backend/.env.test` (no versionado) y poner en `TEST_DATABASE_URL` el mismo servidor y credenciales que `.env`, con BD `arandanos_test`.
2. Crearla una sola vez (idempotente): `python -m apps.backend.scripts.create_test_db` (desde la raíz).
3. `python -m pytest apps/backend -m pg`.

- Guard (`apps/backend/tests/pg_guard.py`): se rechaza toda BD cuyo nombre no termine en `_test` o sea la BD de `.env`; se comprueba antes de abrir conexiones y hace **fallar** (no saltar) la sesión.
- Decisión: los tests `pg` forman parte de la ejecución normal si `TEST_DATABASE_URL` está definido (en el entorno o en `.env.test`). Si falta o la BD es inaccesible se saltan y el resumen de pytest imprime un aviso en rojo: un salto no es un éxito.
- Esquema: al iniciar la sesión se vacía la BD de pruebas (guardada, `tests/pg_migrations.py`) y se aplica `alembic upgrade head`. Aislamiento: `TRUNCATE ... RESTART IDENTITY CASCADE` antes de cada test `pg`. Para concurrencia, `run_concurrently` (`tests/pg_support.py`) lanza callables en hilos con `threading.Barrier`; cada uno abre su propia conexión.
- Herramientas PostgreSQL (no están en el PATH; no se modificó): `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe` y `psql.exe` (versión 18.3). Se usarán para las migraciones/respaldos.
- Alembic 1.20.1 está fijado en `requirements.txt`; ver «Migraciones» abajo.

### Migraciones (Alembic)

El backend **ya no crea tablas al arrancar**: una BD nueva necesita `alembic upgrade head` antes de usarse. Comandos desde la raíz del repo:

```bash
alembic -c apps/backend/alembic.ini upgrade head
alembic -c apps/backend/alembic.ini current
alembic -c apps/backend/alembic.ini revision --autogenerate -m "descripcion"   # revisar a mano
```

La BD de desarrollo ya fue adoptada con `alembic stamp 0001_baseline` (respaldo verificado previo). Una BD nueva (sin tablas) se crea con `alembic upgrade head`; sobre una BD con tablas pero sin `alembic_version`, `upgrade head` fallará (protege los datos) y se adopta con respaldo verificado y `stamp`, solo con aprobación explícita. Procedimiento completo y recuperación: `docs/operations/migrations.md`.

### Primer administrador (instalación nueva)

No hay registro anónimo: `POST /auth/roles/` y `POST /auth/users/` exigen siempre un administrador autenticado. El primer administrador se crea solo con el CLI, desde la raíz del repo y con la BD ya migrada:

```bash
# la contraseña nunca es un argumento: variable de entorno o prompt interactivo
set BOOTSTRAP_PASSWORD=...        # PowerShell: $env:BOOTSTRAP_PASSWORD = "..."
python -m apps.backend.src.cli bootstrap --username <usuario> --full-name "<nombre>" --email <correo>
```

- Crea el rol `Administrador` (`--role-name` lo cambia, pero debe estar en `ADMIN_ROLE_NAMES`) y el usuario con ese rol.
- Escribe en la BD de `apps/backend/.env` (o `--database-url`). Muestra host, puerto y BD de destino (nunca la contraseña) y pide escribir `yes`; la bandera `--yes-i-know-this-targets-the-configured-database` omite la pregunta.
- Si ya existen usuarios no hace nada más: `--force-additional` permite crear otro administrador. Si el usuario ya existe, no hace nada.
- `python -m apps.backend.src.cli report-varieties` (solo lectura, transacción `READ ONLY`) lista las variedades distintas de `plots.variety`, las grafías unificadas y los casi-duplicados (distancia de edición ≤ 2; los pares pueden ser ruido: cadenas cortas distintas pueden quedar a esa distancia sin ser la misma variedad). Prepara la migración al catálogo de variedades.
- **No implementado todavía:** `grant-superuser` y la creación de organización/finca/membresía (llegan con T1.x).

## Deuda técnica detectada

**Seguridad**
1. ~~Endpoints sin proteger~~ Corregido: `GET /auth/users/{username}` exige Bearer token y solo devuelve el propio perfil (otro nombre, exista o no, da el mismo 404); `POST /auth/roles/` y `POST /auth/users/` exigen siempre un administrador autenticado (se eliminó el arranque anónimo; el primer admin se crea con el CLI).
2. `apps/backend/.env` y `apps/frontend/.env` pueden estar sin excluir del control de versiones; confirmar `.gitignore` y rotar credenciales si se publicaron.
3. Tokens en `sessionStorage` (accesibles a XSS). ~~Sin logout~~ Corregido: `POST /auth/logout` revoca la sesión; el refresh token ahora rota, se guarda hasheado y su reutilización cierra todas las sesiones.
4. ~~Cualquier usuario autenticado podía crear roles/usuarios~~ Corregido: solo admin (`ADMIN_ROLE_NAMES`). El primer administrador ya no sale de un endpoint abierto: lo crea el CLI `bootstrap`.

**Bugs de integración (corregidos)**
5. ~~El interceptor llamaba a `/auth/refresh` con body `{}`~~ Ahora envía `{refresh_token}`, guarda los tokens nuevos y no intenta refrescar en 401 de `/auth/login` ni `/auth/refresh`.
6. ~~`refresh_token` no devolvía `username`/`role`~~ Ahora los devuelve y rechaza usuarios inactivos.
7. ~~Sesión perdida al recargar~~ `authStore` inicializa `user` desde sessionStorage.
8. ~~`get_current_user` sin implementar~~ Sustituido por `get_by_id` + `exists_any` en el puerto/adaptador y `decode_access_token` / `get_user_from_token` en la capa de aplicación.

**Mantenimiento**
9. ~~`datetime.utcnow()`~~ Corregido: `datetime.now(timezone.utc)`.
10. ~~Sin migraciones~~ Alembic (`0001_baseline`); sin `create_all` en el arranque. La BD de desarrollo ya está adoptada (`stamp 0001_baseline`, 2026-11-26, con respaldo verificado; ver `docs/operations/migrations.md`).
11. ~~`DB_ENGINE=mongo` referenciado pero sin implementación~~ Eliminado: ya no existen `DB_ENGINE`, el selector `importlib` ni la referencia a MongoDB; solo hay adaptador PostgreSQL.
12. Código muerto: la plantilla Vite (`Home.tsx`/`App.css`) y los duplicados `use-toast`/`use-mobile` ya no están en `src/` (están en `apps/frontend/.removed/`); sigue habiendo `apps/backend/vscode.config.json` vacío y módulos `sales`/`expenses` vacíos. (El bloque comentado de `databases/__init__.py` ya no existe.)
13. ~~CORS fijo a `localhost:5173`~~ Corregido: `CORS_ORIGINS` (ver tabla de variables).
14. Pruebas: backend con pytest (`pip install -r requirements-dev.txt`, luego `python -m pytest apps/backend` desde la raíz del repo: repositorios en memoria, una integración SQLite y pruebas contra PostgreSQL (migraciones, transacciones, concurrencia) marcadas `pg`, que se saltan con aviso si no hay `TEST_DATABASE_URL`; el total cambia, ver `python -m pytest apps/backend --collect-only -q`). Frontend con Vitest + Testing Library (`npx pnpm@10 test` en `apps/frontend/`; 24 pruebas en 5 archivos: formularios de cosecha y costo, mapa de plantas, descarga de archivos y refresh de tokens en axios, incluido el refresh de una sola vez con peticiones paralelas).
15. `requirements.txt` en UTF-16 e incluye dependencias no usadas (watchfiles, websockets, PyYAML…) y falta `PyJWT[crypto]` solo si se usan otros algoritmos.

## Notas de la reescritura del frontend

- Los refresh tokens anteriores (en claro) dejan de funcionar: hay que volver a iniciar sesión una vez.
- Código no usado movido a `apps/frontend/.removed/` (componentes shadcn sin uso, hooks duplicados, plantilla de Vite, landing antigua). Se puede borrar o recuperar con shadcn.
- Se eliminaron del login "Recordarme" y "¿Olvidaste tu contraseña?" porque no tenían funcionalidad.
- Instalar dependencias con pnpm 10 (`npx pnpm@10 install`): el `node_modules` actual usa el store v10.
- `node_modules` debe instalarse desde `apps/frontend` con `pnpm install --frozen-lockfile` (respeta el lockfile).
- `pnpm lint` informa hoy errores solo bajo `apps/frontend/.removed/` (código no usado que ESLint no debería recorrer); ver `docs/tech-debt.md`.
