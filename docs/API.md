# Referencia de la API

> Legacy document (Spanish). Being replaced by English docs as areas are rewritten; see docs/README.md.

Base: `http://localhost:8000` · Swagger interactivo: `/docs` · OpenAPI: `/openapi.json`

| Método | Ruta | Descripción | Body | Respuesta |
|---|---|---|---|---|
| GET | `/` | Mensaje de bienvenida | — | `{message}` |
| POST | `/auth/roles/` | Crear rol (siempre exige un administrador autenticado) | `RoleCreate` | `RoleResponse` |
| POST | `/auth/users/` | Registrar usuario (siempre exige un administrador autenticado) | `UserCreate` | `UserResponse` |
| GET | `/auth/users/{username}` | Obtener el propio perfil (Bearer). Otro `username`, exista o no, responde el mismo 404 | — | `UserResponse` / 404 |
| POST | `/auth/login` | Iniciar sesión | `LoginRequest` | `LoginResponse` |
| POST | `/auth/refresh` | Renovar access token (rota el refresh token) | `RefreshTokenRequest` | `LoginResponse`* |
| POST | `/auth/logout` | Cerrar sesión (revoca el refresh token; idempotente) | `RefreshTokenRequest` | 204 |

\* Devuelve también `username` y `role`.

## Esquemas

```jsonc
RoleCreate      { "name": str, "description"?: str }
RoleResponse    { "id": uuid, "name": str, "description"?: str }
UserCreate      { "username": str, "email": email, "full_name": str,
                  "role_id": uuid, "created_by"?: str, "password": str(8..72 bytes UTF-8) }
UserResponse    { "id": uuid, "username", "email", "full_name", "role_id",
                  "created_by"?, "is_active": bool, "created_at": datetime }
LoginRequest    { "username": str(min 3), "password": str(8..72 bytes UTF-8) }
LoginResponse   { "access_token", "token_type": "bearer", "refresh_token",
                  "username", "role" }
RefreshTokenRequest { "refresh_token": str }
```

## Códigos de error

Toda respuesta de error (salvo la validación 422 de FastAPI) tiene la forma `{"detail": str, "code": str}`; `details` es opcional. `detail` es el mensaje para personas (el frontend lo lee) y `code` el identificador para máquinas: `BAD_REQUEST` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `HTTP_ERROR` (otros). Los errores de validación del cuerpo o los parámetros (422) conservan la forma de FastAPI (`detail` es una lista, sin `code`).

Los errores de integridad de la base de datos se traducen sin exponer texto de la BD: clave duplicada → 409 `CONFLICT`; referencia inexistente o en uso → 422 `INVALID_REFERENCE`; restricción `CHECK` → 422 `CONSTRAINT_VIOLATION`.

| Situación | Código | `detail` |
|---|---|---|
| Rol duplicado / email ya registrado | 400 | mensaje del `ValueError` |
| Credenciales incorrectas | 401 | "Usuario o contraseña incorrectos" |
| Usuario inactivo | 400 | "Usuario inactivo" |
| Refresh token inválido/expirado | 401 | "Refresh token inválido o expirado" |
| Sin permisos de administrador | 403 | "Se requieren permisos de administrador" |
| Contraseña < 8 caracteres o > 72 bytes UTF-8 (crear usuario y login) | 422 | lista de errores de FastAPI (sin `code`) |
| Usuario no encontrado | 404 | "Usuario no encontrado" |
| Nombre de usuario duplicado | 409 | "Ya existe un registro con esos datos" (`CONFLICT`) |
| `role_id` inexistente | 422 | "Referencia a un recurso que no existe o que sigue en uso" (`INVALID_REFERENCE`) |

## Autenticación

El access token es un JWT (`sub` = id de usuario, `exp`). Se envía como `Authorization: Bearer <token>`. Lo exigen `/auth/users/{username}`, `/auth/roles/` y `/auth/users/` (estos dos, además, con rol de administrador; no hay excepción de arranque). Sin token o con token inválido: 401. El primer administrador no se crea por la API sino con el CLI `bootstrap` ([DESARROLLO.md](DESARROLLO.md)).

La contraseña admite como máximo 72 bytes UTF-8 (bcrypt truncaría el resto en silencio); más es 422 al crear el usuario y también en el login.

## Refresh tokens

- Se guardan **hasheados** (SHA-256) en `user_sessions`; el valor en claro solo lo tiene el cliente.
- **Rotación:** cada `/auth/refresh` revoca el token usado y devuelve uno nuevo.
- **Detección de reutilización:** presentar un token ya revocado revoca todas las sesiones del usuario.
- **Admin:** rol cuyo nombre (sin distinguir mayúsculas) esté en `ADMIN_ROLE_NAMES` (por defecto `admin,administrador`).

## Inventario (`/inventory`, todos requieren Bearer token)

Cada usuario ve y modifica solo lo suyo. Un recurso ajeno responde **404** (no se revela su existencia). Un admin puede consultar (no modificar) los datos de cualquiera; en `GET /inventory/plots` y `GET /inventory/summary` puede filtrar con `?owner=<uuid>`, y para un usuario normal ese parámetro se ignora.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/inventory/plots?include_inactive=` | Lotes del usuario (por defecto solo activos) |
| POST | `/inventory/plots` | Crear lote → 201. Nombre único por usuario |
| GET / PATCH | `/inventory/plots/{id}` | Ver / editar lote |
| DELETE | `/inventory/plots/{id}` | Sin cosechas ni costos: se elimina. Con alguno de los dos: se **archiva** (`is_active=false`) |
| GET | `/inventory/plots/{id}/harvests` | Cosechas del lote, más recientes primero |
| POST | `/inventory/plots/{id}/harvests` | Registrar cosecha → 201 |
| PATCH / DELETE | `/inventory/harvests/{id}` | Editar / borrar cosecha |
| GET | `/inventory/summary?from=&to=` | Total kg, nº de cosechas, rendimiento kg/ha, última cosecha, y desglose por lote, mes y calidad. Incluye `total_cost`, `cost_per_kg` (`null` sin producción en el periodo) y `by_category`; cada lote de `by_plot` trae `total_cost` y `cost_per_kg`, y aparecen también los lotes que solo tuvieron costos |
| GET | `/inventory/plots/{id}/costs` | Costos del lote, más recientes primero |
| POST | `/inventory/plots/{id}/costs` | Registrar costo `{incurred_on, category, amount>0, notes?}` → 201. Categorías: `fertilizer`, `pesticide`, `irrigation`, `labor`, `other`. No admite fechas futuras ni lotes archivados. El monto no lleva moneda |
| PATCH / DELETE | `/inventory/costs/{id}` | Editar / borrar costo |
| GET | `/inventory/export/harvests?from=&to=&plot=` | CSV (`fecha,lote,variedad,cantidad_kg,calidad,notas`). `plot` limita a un lote; sin él, todos los del usuario |
| GET | `/inventory/export/costs?from=&to=&plot=` | CSV (`fecha,lote,categoria,monto,notas`) |
| GET | `/inventory/plots/{id}/plants/export` | CSV (`fila,columna,estado,observaciones,ultima_observacion,ultimas_notas`), una fila por planta |

**CSV:** UTF-8 con BOM (Excel respeta tildes), separador coma, decimales con punto. Los textos libres que empiezan por `= + - @` se prefijan con `'` para que Excel no los ejecute como fórmula. Las descargas exigen el Bearer token, por eso el frontend las baja con `fetch` autenticado y no con un enlace.


```jsonc
PlotCreate     { "name": str(1-100), "variety": str, "area_ha": float(>0), "planting_date"?: date,
                 "plant_count"?: int, "notes"?: str(<=500) }
HarvestCreate  { "harvested_on": date, "quantity_kg": float(>0), "grade": "premium|standard|processing", "notes"?: str }
```

Los campos numéricos (`area_ha`, `quantity_kg`, `amount` y los totales del resumen) siguen siendo **números JSON**; internamente se calculan en `Decimal` y los totales y razones del resumen se redondean a 2 decimales (`ROUND_HALF_UP`) al salir. Los endpoints nuevos usarán cadenas decimales ([adr/011-decimal-money-and-units.md](adr/011-decimal-money-and-units.md)); aún no existen.

Reglas (400): fecha de siembra o de cosecha futura, cosecha anterior a la siembra del lote, lote archivado, nombre de lote repetido, `from` posterior a `to`.
El rendimiento global se calcula sobre la superficie de los lotes que produjeron en el periodo.

### Plantas individuales

Cada lote puede tener su mapa de plantas (fila × columna) con su estado actual y un **historial de observaciones**. Mismas reglas de propiedad que el resto del inventario (ajeno → 404; admin solo lectura; lote archivado → 400 al escribir).

Estados: `healthy` (sana), `attention` (vigilar), `sick` (enferma), `dead` (muerta).

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/inventory/plots/{id}/plants/generate` | Body `{rows, columns}` (1–500 cada uno, máx. 50.000 plantas). Crea las posiciones que falten, todas `healthy`; es idempotente y conserva las existentes. Devuelve `{created, total}` y sincroniza `plant_count` del lote |
| GET | `/inventory/plots/{id}/plants?status=` | Lista ligera `{id,row,col,status}` para dibujar el mapa |
| GET | `/inventory/plots/{id}/plants/summary` | `{rows, columns, total, counts{estado→n}, mortality_rate}` |
| GET | `/inventory/plots/{id}/plants/by-position?row=&col=` | Planta en una posición (404 si no existe) |
| POST | `/inventory/plots/{id}/plants` | Añade una planta suelta `{row, col}` → 201 |
| POST | `/inventory/plots/{id}/plants/observations` | Registra el mismo estado en varias plantas: `{plant_ids[1..1000], status, notes?, observed_on?}` → `{updated}`. Todo o nada: si alguna no es del lote, 404 y no cambia nada |
| GET | `/inventory/plants/{id}` | Detalle con `observations` (más reciente primero) |
| POST | `/inventory/plants/{id}/observations` | `{status, notes?, observed_on?}` → 201. Actualiza el estado actual |
| DELETE | `/inventory/plants/{id}` | Elimina la planta y su historial |

`observed_on` es hoy por defecto y no puede ser futura. Cada observación guarda quién la registró (`recorded_by`).
