import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { PlantBrief } from "../infrastructure/api";
import { PlantGrid } from "./plant-grid";

const ROWS = 3;
const COLS = 4;
const plants: PlantBrief[] = Array.from({ length: ROWS * COLS }, (_, i) => ({
  id: `p${i}`,
  row: Math.floor(i / COLS) + 1,
  col: (i % COLS) + 1,
  status: "healthy",
}));

function setup(props: Partial<React.ComponentProps<typeof PlantGrid>> = {}) {
  const onOpen = vi.fn();
  const onToggle = vi.fn();
  render(
    <PlantGrid
      plants={plants}
      rows={ROWS}
      columns={COLS}
      selected={new Set()}
      filter={null}
      selecting={false}
      onOpen={onOpen}
      onToggle={onToggle}
      {...props}
    />,
  );
  return { onOpen, onToggle };
}

describe("PlantGrid", () => {
  it("dibuja una celda por planta", () => {
    setup();
    expect(screen.getAllByRole("gridcell")).toHaveLength(ROWS * COLS);
  });

  it("tocar el número de una fila selecciona solo esa fila", async () => {
    const { onToggle } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Seleccionar fila 2" }));
    expect(onToggle).toHaveBeenCalledWith(["p4", "p5", "p6", "p7"]);
  });

  it("tocar el número de una columna selecciona solo esa columna", async () => {
    const { onToggle } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Seleccionar columna 3" }));
    expect(onToggle).toHaveBeenCalledWith(["p2", "p6", "p10"]);
  });

  it("fuera del modo selección, tocar una celda abre la planta", async () => {
    const { onOpen, onToggle } = setup();
    await userEvent.click(document.getElementById("cell-2-3")!);
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ row: 2, col: 3 }));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it("en modo selección, Enter con el teclado alterna la celda del cursor", async () => {
    const { onOpen, onToggle } = setup({ selecting: true });
    screen.getByRole("grid").focus();
    await userEvent.keyboard("{ArrowRight}{ArrowDown}{Enter}");
    expect(onToggle).toHaveBeenCalledWith(["p5"]);
    expect(onOpen).not.toHaveBeenCalled();
  });
});
