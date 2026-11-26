# Backend

> Legacy document (Spanish). Being replaced by English docs as areas are rewritten; see docs/README.md.

Stack: FastAPI 0.135 · Starlette 0.52 · SQLAlchemy 2.0.48 · Alembic 1.20 · psycopg2-binary · Pydantic 2 / pydantic-settings · PyJWT · passlib[bcrypt] · Uvicorn.

## Árbol de código

```
apps/backend/
├── .env                      Variables de entorno (no versionar)
├── requirements.txt          Dependencias fijadas (¡archivo en UTF-16!); requirements-dev.txt: pytest, httpx
├── alembic.ini · migrations/ Migraciones (revisión 0001_baseline); ver operations/migrations.md
├── scripts/                  create_test_db.py (BD de pruebas)
├── tests/
└── src/
    ├── main.py · cli.py
    ├── core/
    │   ├── config.py · errors.py · uow.py · variety_analysis.py
    │   ├── decimal_input.py · units.py · money.py · domain/grade.py   (núcleo numérico, ADR-011)
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
| `main.py` | Crea `FastAPI(title="API Arándanos Fam", v1.0.0)`, registra los manejadores de error, CORS (`settings.cors_origins`, credenciales on), monta `/auth` e `/inventory`, ruta `GET /` de bienvenida |
| `core/config.py` | `Settings`: `DB_USER/PASSWORD/HOST/PORT/NAME`, `SECRET_KEY` (mín. 32 caracteres, validado al arrancar sin mostrar el valor), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `ADMIN_ROLE_NAMES`, `CORS_ORIGINS` (lista separada por coma; por defecto `http://localhost:5173`; `*` se rechaza); propiedad `DATABASE_URL` construida con `URL.create` (la contraseña se escapa); `hide_input_in_errors` evita imprimir valores en errores de validación |
| `core/databases/__init__.py` | Reexporta `SessionLocal` |
| `core/databases/postgres_db.py` | Engine, `SessionLocal` y la única `Base`. No crea tablas |
| `core/uow.py` | `get_uow` / alias `UnitOfWork`: una transacción por petición (commit al terminar bien, rollback ante excepción). Los repositorios solo hacen `flush()` |
| `core/errors.py` | Envelope `{detail, code}`, `register_error_handlers`, mapeo de `IntegrityError` a 409/422 |
| `core/variety_analysis.py` | Análisis puro (sin BD) de `plots.variety`: normalización, grafías unificadas y casi-duplicados (distancia de edición ≤ 2). Lo usa `report-varieties` |
| `cli.py` | CLI de administración (`python -m apps.backend.src.cli`, desde la raíz): `bootstrap` (primer administrador; contraseña por `BOOTSTRAP_PASSWORD` o prompt, nunca argumento; pide confirmación del destino) y `report-varieties` (solo lectura). `grant-superuser` y la creación de organización **no existen todavía**. Uso: [DESARROLLO.md](DESARROLLO.md) |

### Núcleo numérico (`core/`, puro y sin BD)

Decisión y alternativas: [adr/011-decimal-money-and-units.md](adr/011-decimal-money-and-units.md). **Todavía no está conectado a rutas ni esquemas de entrada** (solo lo cubren pruebas: `tests/test_core_units_money_grade.py`).

| Archivo | API pública |
|---|---|
| `decimal_input.py` | `require_decimal(value, name)`: solo acepta `Decimal` finitos (`float`, `int` y `str` → `TypeError`; NaN/inf → `ValueError`); normaliza el cero negativo |
| `units.py` | `WeightUnit` (`kg`, `lb`), `parse_unit`, `kg_per_unit`, `KG_PER_LB = 0.45359237`, `to_kg(quantity, unit)` (kg canónico, 3 decimales), `from_kg(quantity_kg, unit, places=None)` (solo visualización: 3 decimales en kg, 1 en lb). Cantidades negativas → `ValueError` |
| `money.py` | `quantize_money(amount, currency_scale)`, `line_total(quantity, unit_price, currency_scale)`, `price_per_unit(price_per_kg, unit, currency_scale)`; escala de moneda entera 0..3 (COP = 0) |
| `domain/grade.py` | `Grade` (`premium`, `standard`, `processing`) y `parse_grade` |

Política de redondeo: se convierte o multiplica **una vez** con la constante exacta y se redondea **una vez** (`ROUND_HALF_UP`); nunca se encadenan conversiones (lb → kg → lb), se parte siempre del valor ingresado. Los límites de columna (`NUMERIC(14,3)`, `NUMERIC(16,2)`) los exigen los esquemas de entrada, no estos módulos.

## Feature `auth`

### domain
- `schemas.py` — `RoleBase/Create/Response`, `UserBase/Create/Response` (`password`: mín. 8 caracteres y máx. 72 bytes UTF-8, tipo `Password`, porque bcrypt trunca en silencio más allá de 72 bytes), `LoginRequest` (username ≥3, mismo tipo `Password`), `LoginResponse`, `RefreshTokenRequest`.
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
- `../dependencies.py` — `get_auth_service` (construye `AuthService` con los repositorios Postgres sobre la sesión del `UnitOfWork`), `get_current_user` y `require_admin` (autenticado + rol administrador, sin excepciones de arranque).

## Cómo añadir una feature nueva (p. ej. `sales`)

1. `domain/schemas.py` y `domain/repository_ports.py` (Protocols).
2. `application/services.py` con la lógica; solo depender de puertos.
3. `infrastructure/postgres/{models,repositories}.py`; importar los modelos en `migrations/env.py` y generar la migración (`alembic revision --autogenerate`, revisarla a mano).
4. `dependencies.py` análogo al de auth para inyectar el servicio (recibir la sesión con `UnitOfWork`).
5. `presentation/routes.py` y registrar el router en `main.py`.

## Estado de los módulos

| Módulo | Estado |
|---|---|
| auth | Completo (login, refresh con rotación, logout, roles/usuarios solo admin; primer admin por CLI) |
| inventory | Completo (lotes, cosechas, resumen) |
| sales | Archivos vacíos |
| expenses | Archivos vacíos |

## Feature `inventory`

Misma estructura hexagonal que `auth`:

- `domain/` — `schemas.py` (lotes, cosechas, resumen) y `repository_ports.py` (`PlotRepository`, `HarvestRepository`).
- `application/services.py` — `InventoryService` y `Actor(id, is_admin)`. El servicio **no depende de auth**: recibe un `Actor`. Aplica la propiedad (ajeno → `LookupError` → 404), las validaciones y calcula el resumen.
- `infrastructure/postgres/` — tablas `plots` (única por `owner_id`+`name`) `harvests` (índice `plot_id, harvested_on`) y `plot_costs` (índice `plot_id, incurred_on`), y sus repositorios. Las tablas están en la migración `0001_baseline`.
- `dependencies.py` — `get_inventory_service` (repositorios Postgres sobre la sesión del `UnitOfWork`) y `get_actor`, que convierte el usuario autenticado de `auth` en un `Actor`.
- `presentation/routes.py` — montado en `/inventory`.

Números en `inventory` (ADR-011): `InventoryService` calcula el resumen en `Decimal` exacto y redondea una sola vez, al salir, los totales y razones del resumen (`total_kg`, `yield_kg_per_ha`, `total_cost`, `cost_per_kg`, desgloses) a 2 decimales con `ROUND_HALF_UP`. El único punto de contrato numérico es `JsonDecimal` en `domain/schemas.py`: un `float` del JSON entra como `Decimal(str(x))` (nunca `Decimal(0.1)` con ruido binario) y sale como número JSON, con la misma forma de siempre; el CSV no cambia. Las columnas siguen siendo `Numeric(10,2)` (`area_ha`), `Numeric(12,2)` (`quantity_kg`) y `Numeric(14,2)` (`amount`): el almacenamiento en kg con 3 decimales (`NUMERIC(14,3)`) llega con la migración de stock, no está hecho.

Pruebas: `tests/test_inventory_services.py`, `tests/test_inventory_decimal.py` (y `test_inventory_decimal_pg.py`, contra PostgreSQL) y `tests/test_inventory_api.py` (repositorios en memoria en `tests/fakes_inventory.py`; el usuario se simula con la cabecera `X-User`).

### Plantas individuales (dentro de `inventory`)

- `domain/plant_schemas.py`, `domain/plant_ports.py` (`PlantRepository`, `ObservationRepository`).
- `application/plant_service.py` — `PlantService` compone `InventoryService`: el acceso al lote (propiedad, admin solo lectura) lo decide `InventoryService.access_plot`, así hay una sola regla de acceso.
- Tablas `plants` (única por `plot_id, row_num, col_num`; `status` actual desnormalizado) y `plant_observations` (historial; `created_at` con microsegundos desde Python para ordenar de forma estable observaciones del mismo día). Se borran en cascada con el lote.
- Las dimensiones de la cuadrícula **no se guardan**: se derivan de `max(row)`/`max(col)`. Así `plots` no cambia y no hace falta migración.
- Altas masivas por bloques (`insert` ORM con lotes de 2.000). El contador `plots.plant_count` se mantiene sincronizado.
- Pruebas: `tests/test_plants_service.py`, `tests/test_plants_api.py` y `tests/test_inventory_integration.py`, que ejecuta los **repositorios SQL reales sobre SQLite en memoria** (consultas, unicidad, cascadas). No sustituye una prueba con PostgreSQL: las pruebas `pg` (migraciones, transacciones, concurrencia) están descritas en [DESARROLLO.md](DESARROLLO.md).
