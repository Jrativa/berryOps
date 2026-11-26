# Backend

Stack: FastAPI 0.135 · Starlette 0.52 · SQLAlchemy 2.0.48 · psycopg2-binary · Pydantic 2 / pydantic-settings · PyJWT · passlib[bcrypt] · Uvicorn.

## Árbol de código

```
backend/
├── .env                      Variables de entorno (no versionar)
├── requirements.txt          Dependencias fijadas (¡archivo en UTF-16!)
└── src/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   └── databases/{__init__.py, postgres_db.py}
    └── features/
        ├── auth/             Implementado
        ├── inventory/        Implementado (lotes y cosechas)
        ├── sales/            Esqueleto vacío
        └── expenses/         Esqueleto vacío
```

## Módulos del núcleo

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Crea `FastAPI(title="API Arándanos Fam", v1.0.0)`, llama a `init_db()`, CORS (`localhost:5173`, credenciales on), monta `/auth`, ruta `GET /` de bienvenida |
| `core/config.py` | `Settings`: `DB_ENGINE`, `DB_USER/PASSWORD/HOST/PORT/NAME`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`; propiedad `DATABASE_URL` |
| `core/databases/__init__.py` | Selector dinámico de motor (`importlib`); reexporta `get_db`, `init_db` (con no-op si el motor no define `init_db`). Contiene una versión anterior comentada |
| `core/databases/postgres_db.py` | Engine, `SessionLocal`, `Base`, dependencia `get_db`, `init_db` (importa modelos y `create_all`) |

## Feature `auth`

### domain
- `schemas.py` — `RoleBase/Create/Response`, `UserBase/Create/Response` (`password` mín. 8), `LoginRequest` (username ≥3, password ≥8), `LoginResponse`, `RefreshTokenRequest`.
- `repository_ports.py` — `Protocol`: `RoleRepository` (`get_by_name`, `create`), `UserRepository` (`get_by_email`, `get_by_username`, `get_by_login_id`, `get_current_user`, `create`), `SessionRepository` (`create_session`, `get_valid_session`).

### application
- `services.py` — `AuthService`: `create_role`, `register_user`, `login`, `refresh_token`. Lanza `ValueError` para reglas de negocio; la capa de presentación las traduce a HTTP.
- `access_tokens.py` — `create_access_token(data, expires_delta)` (JWT HS con `SECRET_KEY`/`ALGORITHM`, claim `exp`).
- `passwords_handler.py` — `hash_password`, `verify_password` (bcrypt vía passlib).

### infrastructure/postgres
- `models.py` — ORM `Role`, `User`, `UserSession` (UUID como PK).
- `repositories.py` — implementaciones SQLAlchemy de los tres puertos. `get_valid_session` filtra por no revocada y no expirada.

### presentation
- `routes.py` — router con los endpoints (ver [API.md](API.md)); mapea `ValueError` → 400/401.
- `../dependencies.py` — `get_auth_service`: resuelve el módulo de repositorios según `DB_ENGINE` y construye `AuthService`.

## Cómo añadir una feature nueva (p. ej. `sales`)

1. `domain/schemas.py` y `domain/repository_ports.py` (Protocols).
2. `application/services.py` con la lógica; solo depender de puertos.
3. `infrastructure/postgres/{models,repositories}.py`; importar los modelos en `postgres_db.init_db()`.
4. `dependencies.py` análogo al de auth para inyectar el servicio.
5. `presentation/routes.py` y registrar el router en `main.py`.

## Estado de los módulos

| Módulo | Estado |
|---|---|
| auth | Completo (registro, login, refresh con rotación, logout, roles/usuarios solo admin) |
| inventory | Completo (lotes, cosechas, resumen) |
| sales | Archivos vacíos |
| expenses | Archivos vacíos |
| mongo | Referenciado en config/selector, sin implementar |

## Feature `inventory`

Misma estructura hexagonal que `auth`:

- `domain/` — `schemas.py` (lotes, cosechas, resumen) y `repository_ports.py` (`PlotRepository`, `HarvestRepository`).
- `application/services.py` — `InventoryService` y `Actor(id, is_admin)`. El servicio **no depende de auth**: recibe un `Actor`. Aplica la propiedad (ajeno → `LookupError` → 404), las validaciones y calcula el resumen.
- `infrastructure/postgres/` — tablas `plots` (única por `owner_id`+`name`) `harvests` (índice `plot_id, harvested_on`) y `plot_costs` (índice `plot_id, incurred_on`), y sus repositorios. `init_db()` las crea con `create_all`; no toca tablas existentes.
- `dependencies.py` — `get_inventory_service` (módulo de repositorios según `DB_ENGINE`) y `get_actor`, que convierte el usuario autenticado de `auth` en un `Actor`.
- `presentation/routes.py` — montado en `/inventory`.

Pruebas: `tests/test_inventory_services.py` y `tests/test_inventory_api.py` (repositorios en memoria en `tests/fakes_inventory.py`; el usuario se simula con la cabecera `X-User`).

### Plantas individuales (dentro de `inventory`)

- `domain/plant_schemas.py`, `domain/plant_ports.py` (`PlantRepository`, `ObservationRepository`).
- `application/plant_service.py` — `PlantService` compone `InventoryService`: el acceso al lote (propiedad, admin solo lectura) lo decide `InventoryService.access_plot`, así hay una sola regla de acceso.
- Tablas `plants` (única por `plot_id, row_num, col_num`; `status` actual desnormalizado) y `plant_observations` (historial; `created_at` con microsegundos desde Python para ordenar de forma estable observaciones del mismo día). Se borran en cascada con el lote.
- Las dimensiones de la cuadrícula **no se guardan**: se derivan de `max(row)`/`max(col)`. Así `plots` no cambia y no hace falta migración.
- Altas masivas por bloques (`insert` ORM con lotes de 2.000). El contador `plots.plant_count` se mantiene sincronizado.
- Pruebas: `tests/test_plants_service.py`, `tests/test_plants_api.py` y `tests/test_inventory_integration.py`, que ejecuta los **repositorios SQL reales sobre SQLite en memoria** (consultas, unicidad, cascadas). No sustituye una prueba con PostgreSQL.
