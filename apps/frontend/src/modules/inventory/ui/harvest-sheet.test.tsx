import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { HarvestSheet } from "./harvest-sheet";

function setup() {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();
  render(<HarvestSheet open onClose={onClose} onSubmit={onSubmit} />);
  return {
    onSubmit,
    onClose,
    kg: screen.getByLabelText("Cantidad"),
    save: screen.getByRole("button", { name: "Registrar" }),
  };
}

describe("HarvestSheet", () => {
  it("acepta coma decimal", async () => {
    const { onSubmit, onClose, kg, save } = setup();
    await userEvent.type(kg, "12,5");
    await userEvent.click(save);
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ quantity_kg: 12.5, grade: "standard" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("no permite guardar sin cantidad o con cantidad cero", async () => {
    const { onSubmit, kg, save } = setup();
    expect(save).toBeDisabled();
    await userEvent.type(kg, "0");
    expect(save).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("muestra el error del servidor y no cierra", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("boom"));
    const onClose = vi.fn();
    render(<HarvestSheet open onClose={onClose} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Cantidad"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));
    expect(onClose).not.toHaveBeenCalled();
    expect(await screen.findByText(/\S/, { selector: "p.text-danger" })).toBeInTheDocument();
  });
});
