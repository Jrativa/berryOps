# Glossary

Domain terms, with the Spanish term used in the UI. The code has so far been written without most of these words
(see the "Status" column): the plan in [plan/foundations-inventory-sales.md](plan/foundations-inventory-sales.md)
introduces them.

Status: **implemented** = exists in code today; **planned** = decided, not built.

## Production (implemented unless noted)

| English | Spanish (UI) | Meaning | Status |
|---|---|---|---|
| Plot / crop lot | lote de cultivo (`plot`) | A piece of land with plants. Table `plots`. In the code and API, "lote" in `/inventory/plots` always means this | implemented |
| Harvest | cosecha | A weighed quantity picked from one plot on one date, with a grade. It is **not** a sale. Table `harvests` | implemented |
| Variety | variedad | Cultivar of blueberry (e.g. Biloxi). Today a free-text column `plots.variety`, one per plot; a catalog with several varieties per plot is planned | free text implemented; catalog planned |
| Grade | calidad | Quality class of harvested fruit: `premium`, `standard`, `processing` (UI: Premium, Estándar, Proceso). A fixed enum, not a per-organization catalog | implemented on harvests; planned as a stock and sales dimension |
| Plant, observation | planta, observación | Individual plant in a plot grid (row x column) with a current status and a history of observations | implemented |
| Cost | costo / gasto | Money spent on a plot (fertilizer, pesticide, irrigation, labor, other) | implemented |

## Stock and sales (all planned)

| English | Spanish (UI) | Meaning |
|---|---|---|
| Stock lot | lote de stock | A quantity of fruit of one farm + variety + grade + harvest date, tracked for availability and FIFO. **Not the same as a plot** (lote de cultivo). One harvest creates one stock lot |
| Ledger (movement) | movimiento | Append-only record of a stock change (entry, dispatch, shrinkage, ...). The ledger is the truth; the lot's on-hand quantity is a projection |
| Opening balance | saldo inicial | One-time stock entry per variety and grade that starts the ledger (historic harvests are not converted) |
| Sale / shipment (**cargamento**) | venta, cargamento, despacho | A truckload dispatched to a buyer, in kg or lb, possibly several varieties and grades. **"Cargamento" is a sale, not a harvest.** The code never used the word; the sales lifecycle ADR-010 defines it. "Despacho" is the act of dispatching, which is the only moment stock leaves |
| Order (draft) | pedido (borrador) | A sale that has not touched stock yet |
| Reservation | reserva | Stock set aside for a sale without leaving the warehouse. Shown in one highlighted style in the UI |
| Dispatch | despacho | Turns a draft or reserved sale into a confirmed sale and deducts stock (`sale_dispatch` movements) |
| Customer / buyer | cliente / comprador | The organization buying; belongs to the organization, not to a farm |
| Shrinkage | merma | Weight lost between harvest and sale (moisture, handling). Recorded with a reason; reduces stock |
| Discard | descarte | Fruit thrown away (spoiled, rejected). Recorded with a reason; reduces stock |
| Adjustment | ajuste | A correction of stock to match reality, requested by an operator and approved by an admin or owner |
| Physical count | conteo físico | Counting stock per lot; differences produce adjustment requests |
| Return | devolución | Goods coming back after dispatch; restocked into the original lots or discarded |
| Revenue vs collected | ingresos vs cobrado | Revenue (net) = dispatched sales minus returns, by sale date. Collected = active payments, by payment date. They differ when buyers pay later |
| Outstanding balance | saldo / por cobrar | Total minus returns minus payments. Status is unpaid, partial or paid; "overdue" when the promised payment date has passed |

## Units and money

| English | Spanish (UI) | Meaning | Status |
|---|---|---|---|
| Pound / kilogram | libra (lb) / kg | Canonical storage is **kg**. 1 lb = 0.45359237 kg (exact by definition). The user chooses the display unit; default lb | conversion implemented in `core/units` (T0.5, not yet wired to routes); today the API and DB use kg only; the unit preference is planned |
| Currency scale | escala de moneda | Decimals of the organization's currency (COP = 0), an integer 0..3 | rounding implemented in `core/money` (T0.5, not yet wired); the per-organization setting is planned |

## Tenancy and access (all planned)

| English | Spanish (UI) | Meaning |
|---|---|---|
| Organization | organización | The tenant: a family business. Owns all data; carries currency and time zone |
| Farm | granja (finca) | A place inside an organization, with plots and stock |
| Membership | membresía | Link between a user and an organization, with a role (owner, admin, operator, viewer) and the `financial_access` flag |
| Financial access | acceso financiero | Flag, settable only by an owner, that lets a non-owner see costs, cost totals and financial reports |
| Platform superuser | superusuario de plataforma | Maintainer account provisioned by CLI; read-only support access to one organization at a time, audited |

Today the only access concept is a global **role** (`roles` table) where names in `ADMIN_ROLE_NAMES` act as
administrators, and each plot has an `owner_id`.
