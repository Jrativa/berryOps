# Frontend

Stack: React 19 · TypeScript 6 · Vite 8 · Tailwind CSS 4 · shadcn/ui sobre Radix · Zustand 5 · React Router 7 · axios · i18next / react-i18next · lucide-react. Gestor de paquetes: **pnpm**.

## Diseño (principios de apple-design)

Paleta de arándanos intacta (`cream`, `midnight`, `dusty`, `purple`, `purple-dark`) en `src/index.css`; los tokens derivados (`surface`, `hairline`, `glass`) salen de ella.

- **Respuesta:** `Button` reacciona al presionar (`whileTap`, scale .97), no al soltar.
- **Springs sin rebote por defecto** (`shared/lib/motion.ts`: `spring`, `springSnappy`, `springBouncy`); el rebote se reserva para inercia.
- **Materiales:** barra superior `.glass` (blur + saturación) con divisor que aparece solo al hacer scroll; tarjeta `.glass-dark` sobre la foto del login.
- **Tipografía:** pila del sistema, tracking negativo en títulos grandes y 0 en cuerpo.
- **Accesibilidad:** `MotionConfig reducedMotion="user"`, `prefers-reduced-transparency`, `prefers-contrast`, error de login en región `aria-live`, foco visible, `lang` sincronizado con el idioma.

## Árbol de código

```
frontend/src/
├── main.tsx / App.tsx        Entrada, MotionConfig y rutas (/, /login, /home protegida)
├── core/api/axios.instance.ts  Cliente + refresh con rotación
├── i18n/                     en / es (todas las cadenas, incluida la home)
├── modules/
│   ├── auth/  application/authStore.ts · infrastructure/api.ts (login, logout) · ui/Login*.tsx
│   ├── home/ui/              navbar.tsx · home-page.tsx
│   └── inventory/            infrastructure/api.ts · application/inventoryStore.ts · ui/*
└── shared/  lib/{utils,motion,format}.ts · ui/{button,input,spinner,language-toggle,sheet,segmented-control,form-field}.tsx
```

## Rutas

| Ruta | Acceso |
|---|---|
| `/` y cualquier otra | redirige a `/home` si hay sesión, si no a `/login` |
| `/login` | público; con sesión redirige a `/home` |
| `/home` | protegida |
| `/inventory` | protegida: resumen de producción |
| `/inventory/plots/:id` | protegida: detalle de un lote con pestañas Cosechas, Plantas y Costos (`?tab=plants\|costs`); cada pestaña exporta su CSV (`shared/lib/download.ts`) |

## Sesión

`authStore` restaura `user` desde sessionStorage al cargar. `logout()` cierra la sesión local al instante y revoca en segundo plano el refresh token (`POST /auth/logout`). El interceptor de axios envía `{refresh_token}` a `/auth/refresh`, guarda los dos tokens nuevos y no reintenta en 401 de login/refresh.

La home enlaza al inventario; ventas, gastos y (para admin) usuarios y roles siguen como "Próximamente".

## Módulo de inventario

- **Resumen (`/inventory`):** selector de periodo (30 días / 12 meses / todo), tres cifras (kg cosechados, rendimiento kg/ha, última cosecha), gráfica de producción por mes, reparto por calidad y lista de lotes. Sin lotes muestra un estado vacío con la acción de crear el primero.
- **Detalle de lote:** pestañas **Cosechas** / **Plantas** (la pestaña va en la URL: `?tab=plants`). Cosechas: total, lista con borrado, edición del lote y archivado/eliminación con confirmación en dos pasos.
- **Registrar cosecha:** hoja modal (cantidad, fecha de hoy por defecto, calidad, notas). Acepta coma decimal. La cosecha aparece **al instante** (actualización optimista) y se revierte si el servidor falla.
- **Estado:** `inventoryStore` (Zustand). Los errores 400 del backend se muestran tal cual; el resto, con un mensaje genérico traducido.
- **Gráficas (dataviz):** SVG propio, un solo tono de la paleta, barras con extremo redondeado de 4 px, cuadrícula discreta, etiqueta directa solo en el máximo, tooltip al pasar o enfocar cada barra y tabla equivalente para lectores de pantalla. Los meses sin cosecha se muestran como hueco.
- **`Sheet`:** entra y sale por el mismo camino, se cierra arrastrando el asa según la velocidad del gesto, atrapa el foco y se cierra con Esc.

### Plantas del lote (pestaña Plantas)

- **Alta:** se indica filas × columnas y se crean todas las plantas como sanas ("Ampliar cuadrícula" añade solo las que faltan). Con un lote de miles de plantas solo se registran las que cambian.
- **Mapa** (`plant-grid.tsx`): una celda por planta; eventos delegados en el contenedor y celdas memorizadas para soportar miles. "Sana" usa un tinte suave de la paleta para que las excepciones destaquen; atención, enferma y muerta tienen su color, y además icono y nombre en leyenda, lista y texto accesible de cada celda.
- **Interacción:** clic abre la planta; leyenda = filtro (atenúa el resto); búsqueda por fila y columna; "Seleccionar varias" con clic o arrastre de ratón, y clic en el número de una fila/columna para seleccionarla completa; barra flotante para registrar un estado a todas. Teclado: flechas, Enter/Espacio.
- **Planta:** hoja con estado actual, formulario de observación (estado, notas, fecha) e historial. El mapa y las cifras (plantas, requieren atención, mortalidad) se actualizan al instante y se revierten si el servidor falla; las cifras se derivan de la lista cargada.
- **Lista "Plantas que requieren atención":** equivalente al mapa que no depende del color (ordenada por gravedad, primeras 50).
- Estado en `plantsStore` (Zustand).

## Scripts

| Comando | Acción |
|---|---|
| `pnpm dev` | servidor Vite (5173) |
| `pnpm build` | `tsc -b && vite build` |
| `pnpm lint` | ESLint |
| `pnpm preview` | sirve el build |
