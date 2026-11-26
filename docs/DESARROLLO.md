# Guía de desarrollo

## Requisitos
Python 3.14, PostgreSQL, Node.js y pnpm.

## Variables de entorno

`backend/.env`

| Variable | Descripción |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | Conexión PostgreSQL |
| `SECRET_KEY` | Clave de firma del JWT |
| `ALGORITHM` | Algoritmo JWT (p. ej. `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vida del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Vida del refresh token |
| `DB_ENGINE` | Opcional, por defecto `postgres` |

`frontend/.env`: `VITE_API_URL` — URL base del backend (p. ej. `http://localhost:8000`).

## Arranque

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt      # requirements.txt está en UTF-16; si pip falla, convertirlo a UTF-8
uvicorn src.main:app --reload

cd frontend
pnpm install
pnpm dev
```

Las tablas se crean solas al arrancar el backend. Para poder iniciar sesión hay que crear primero un rol (`POST /auth/roles/`) y luego un usuario (`POST /auth/users/`) con ese `role_id`.

## Deuda técnica detectada

**Seguridad**
1. ~~Endpoints sin proteger~~ Corregido: `GET /auth/users/{username}` exige Bearer token; `POST /auth/roles/` y `POST /auth/users/` también, salvo mientras no exista ningún usuario (arranque inicial para crear el primer rol y usuario).
2. `backend/.env` y `frontend/.env` pueden estar sin excluir del control de versiones; confirmar `.gitignore` y rotar credenciales si se publicaron.
3. Tokens en `sessionStorage` (accesibles a XSS). ~~Sin logout~~ Corregido: `POST /auth/logout` revoca la sesión; el refresh token ahora rota, se guarda hasheado y su reutilización cierra todas las sesiones.
4. ~~Cualquier usuario autenticado podía crear roles/usuarios~~ Corregido: solo admin (`ADMIN_ROLE_NAMES`). Pendiente: el primer usuario creado en el arranque inicial no se fuerza a ser admin.

**Bugs de integración (corregidos)**
5. ~~El interceptor llamaba a `/auth/refresh` con body `{}`~~ Ahora envía `{refresh_token}`, guarda los tokens nuevos y no intenta refrescar en 401 de `/auth/login` ni `/auth/refresh`.
6. ~~`refresh_token` no devolvía `username`/`role`~~ Ahora los devuelve y rechaza usuarios inactivos.
7. ~~Sesión perdida al recargar~~ `authStore` inicializa `user` desde sessionStorage.
8. ~~`get_current_user` sin implementar~~ Sustituido por `get_by_id` + `exists_any` en el puerto/adaptador y `decode_access_token` / `get_user_from_token` en la capa de aplicación.

**Mantenimiento**
8. ~~`datetime.utcnow()`~~ Corregido: `datetime.now(timezone.utc)`.
9. Sin migraciones (Alembic); `create_all` en el arranque.
10. `DB_ENGINE=mongo` referenciado pero sin implementación.
11. Código muerto: `Home.tsx`/`App.css` (plantilla Vite), bloque comentado en `databases/__init__.py`, duplicados `use-toast`/`use-mobile`, `backend/vscode.config.json` vacío, módulos `sales`/`expenses` vacíos.
12. CORS fijo a `localhost:5173` (debería venir de configuración).
13. Pruebas: backend con pytest (`pip install -r requirements-dev.txt`, luego `pytest` en `backend/`; 91 pruebas (repositorios en memoria, más una integración con SQLAlchemy sobre SQLite), sin Postgres). Frontend con Vitest + Testing Library (`npx pnpm@10 test` en `frontend/`; 19 pruebas: formularios de cosecha y costo, mapa de plantas, descarga de archivos y refresh de tokens en axios).
14. `requirements.txt` en UTF-16 e incluye dependencias no usadas (watchfiles, websockets, PyYAML…) y falta `PyJWT[crypto]` solo si se usan otros algoritmos.

## Notas de la reescritura del frontend

- Los refresh tokens anteriores (en claro) dejan de funcionar: hay que volver a iniciar sesión una vez.
- Código no usado movido a `frontend/.removed/` (componentes shadcn sin uso, hooks duplicados, plantilla de Vite, landing antigua). Se puede borrar o recuperar con shadcn.
- Se eliminaron del login "Recordarme" y "¿Olvidaste tu contraseña?" porque no tenían funcionalidad.
- Instalar dependencias con pnpm 10 (`npx pnpm@10 install`): el `node_modules` actual usa el store v10.
