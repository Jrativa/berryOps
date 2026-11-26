# Arquitectura

> Legacy document (Spanish). Being replaced by English docs as areas are rewritten; see docs/README.md.

## 1. Visión general

```
┌──────────────────────────┐   HTTP/JSON (axios)    ┌───────────────────────────┐
│ Frontend (SPA)           │ ─────────────────────► │ Backend (FastAPI)         │
│ React 19 · Vite · Zustand│   Bearer access_token  │ routes → services → repos │
│ localhost:5173           │ ◄───────────────────── │ localhost:8000            │
└──────────────────────────┘                        └─────────────┬─────────────┘
                                                                  │ SQLAlchemy
                                                         ┌────────▼────────┐
                                                         │ PostgreSQL      │
                                                         │ roles · users · │
                                                         │ user_sessions   │
                                                         └─────────────────┘
```

- Monorepo con dos aplicaciones independientes (`apps/backend/`, `apps/frontend/`).
- Comunicación únicamente vía API REST. CORS permite los orígenes de `CORS_ORIGINS` (por defecto `http://localhost:5173`; `*` se rechaza).
- Autenticación con **access token JWT** (corto) + **refresh token opaco** persistido en base de datos.

## 2. Backend: Arquitectura hexagonal por feature

Cada feature (`auth`, `inventory`, y los esqueletos `sales`, `expenses`) sigue la misma estructura de cuatro capas:

```
apps/backend/src/features/<feature>/
├── domain/           Contratos puros: schemas Pydantic y puertos (typing.Protocol)
├── application/      Casos de uso / servicios; solo dependen de los puertos
├── infrastructure/   Adaptadores concretos (hoy solo postgres/)
└── presentation/     Routers FastAPI (HTTP)
```

Regla de dependencias: `presentation → application → domain ← infrastructure`.
El servicio de aplicación nunca importa SQLAlchemy; recibe repositorios por constructor.

```
 routes.py ──Depends──► dependencies.get_auth_service ──► AuthService(user_repo, role_repo, session_repo)
                                  │                                   │ usa
                                  │ construye con la sesión           ▼
                                  │ del UnitOfWork            domain.repository_ports (Protocol)
                                  ▼                                   ▲
        infrastructure.postgres.repositories  ─ implementa ──────────┘
```

Solo existe el adaptador PostgreSQL. No hay selector de motor: `dependencies.py` importa `infrastructure.postgres.repositories` directamente (la variable `DB_ENGINE`, el `importlib` y el soporte de MongoDB ya no existen).

### Núcleo (`apps/backend/src/core`)
- `config.py` — `Settings` (pydantic-settings) leída de `apps/backend/.env`; construye `DATABASE_URL` con `DB_USER/PASSWORD/HOST/PORT/NAME`.
- `databases/postgres_db.py` — `engine`, `SessionLocal` y la única `Base` declarativa. No crea tablas: el esquema lo gestiona Alembic.
- `uow.py` — unidad de trabajo: una sesión y **una transacción por petición** (commit si termina bien, rollback ante cualquier excepción). Se obtiene con el alias `UnitOfWork` (`scope="function"`); los repositorios solo hacen `flush()`. Ver [ADR-003](adr/003-unit-of-work.md).
- `errors.py` — envelope de errores `{detail, code}` y mapeo de `IntegrityError` (409/422).

### Arranque (`src/main.py`)
Se crea la app `FastAPI`, se registran los manejadores de error (`register_error_handlers`), se añade CORS y se montan los routers de auth bajo `/auth` y de inventario bajo `/inventory`. No se crean tablas al arrancar.

## 3. Modelo de datos (PostgreSQL)

```
roles (id UUID PK, name UNIQUE, description)
   │ 1
   │
   │ N
users (id UUID PK, role_id FK, username UNIQUE, email UNIQUE, password_hash,
       full_name, is_active, created_at, created_by)
   │ 1
   │
   │ N
user_sessions (id UUID PK, user_id FK, refresh_token UNIQUE, expires_at, is_revoked)
```

Las tablas las crea Alembic (`apps/backend/migrations/`, revisión `0001_baseline`); la aplicación no ejecuta `create_all`. Ver [operations/migrations.md](operations/migrations.md).

## 4. Flujo de autenticación

```
Login
 UI Login/LoginForm → authStore.login → authAPI.login → POST /auth/login
   AuthService.login: busca por username → verify bcrypt → comprueba is_active
                      → JWT (sub=user.id) + refresh_token (secrets.token_urlsafe) guardado en user_sessions
   ← {access_token, refresh_token, token_type, username, role}
 authStore guarda access_token, refresh_token y user_data en sessionStorage

Petición protegida
 axios request interceptor añade  Authorization: Bearer <access_token>

Expiración (401)
 axios response interceptor → POST /auth/refresh (una sola renovación en vuelo, compartida) → reintenta la petición original una vez
 si falla → limpia sessionStorage una vez y redirige a /login
```

Los endpoints protegidos validan el JWT (`get_current_user`) y el cliente envía el refresh token en el cuerpo de `/auth/refresh`. Deuda pendiente: ver "Deuda técnica" en [DESARROLLO.md](DESARROLLO.md) y [tech-debt.md](tech-debt.md).

## 5. Frontend: módulos por dominio

```
src/
├── main.tsx / App.tsx        Punto de entrada y enrutado
├── core/api/                 Instancia axios + interceptores
├── i18n/                     i18next (en / es)
├── modules/<modulo>/
│   ├── application/          Estado (Zustand)
│   ├── infrastructure/       Llamadas HTTP
│   └── ui/                   Componentes React
└── shared/                   ui (shadcn/Radix), hooks, lib/utils
```

Replica la separación del backend (application / infrastructure / ui). Los componentes de `shared/ui` son la biblioteca shadcn generada; no contienen lógica de negocio.

## 6. Decisiones clave

| Decisión | Motivo |
|---|---|
| Puertos `Protocol` + adaptadores de infraestructura | La lógica de negocio no depende de SQLAlchemy y se prueba con repositorios en memoria |
| Feature-first (vertical slices) | Añadir sales/expenses sin afectar auth |
| JWT corto + refresh en BD | Permite revocar sesiones (`is_revoked`) |
| Zustand + sessionStorage | Estado ligero; sesión ligada a la pestaña |
| i18next con idioma persistido en localStorage | UI bilingüe en/es |

## 7. Inventario de producción

```
users 1 ──< plots 1 ──< harvests   (plot_id, harvested_on, quantity_kg, grade)
                       └──< plot_costs (plot_id, incurred_on, category, amount)
```

- Propiedad por usuario: el repositorio filtra por `owner_id`; un recurso ajeno es indistinguible de uno inexistente (404).
- `InventoryService` recibe un `Actor(id, is_admin)` en vez de depender de auth; `inventory/dependencies.py` hace de puente con `auth.get_current_user`.
- Un lote con cosechas se archiva al borrarlo para conservar el histórico.
- El resumen (totales, rendimiento, mes, calidad) se calcula en la capa de aplicación a partir de los repositorios, no en SQL, para poder probarlo con repositorios en memoria.

### Plantas individuales

```
plots 1 ──< plants 1 ──< plant_observations
            (row, col, status actual)   (status, notes, observed_on, recorded_by)
```

- El **estado actual** vive en `plants.status` (lectura rápida para el mapa) y el **historial** en `plant_observations`; cada observación actualiza ambos.
- La cuadrícula se genera una vez (filas × columnas) y después solo se registran excepciones; las dimensiones se derivan de las posiciones existentes.
- `PlantService` reutiliza la regla de acceso de `InventoryService` en lugar de duplicarla.
