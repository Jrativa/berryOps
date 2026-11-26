import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CostSheet } from "./cost-sheet";

function setup(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  const onClose = vi.fn();
  render(<CostSheet open onClose={onClose} onSubmit={onSubmit} />);
  return {
    onSubmit,
    onClose,
    amount: screen.getByLabelText(/Monto/),
    save: screen.getByRole("button", { name: "Registrar" }),
  };
}

describe("CostSheet", () => {
  it("acepta coma decimal y envía la categoría elegida", async () => {
    const { onSubmit, onClose, amount, save } = setup();
    await userEvent.type(amount, "1250,75");
    await userEvent.selectOptions(screen.getByLabelText("Categoría"), "fertilizer");
    await userEvent.click(save);
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ amount: 1250.75, category: "fertilizer", notes: null }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("no deja guardar con monto vacío o cero", async () => {
    const { onSubmit, amount, save } = setup();
    expect(save).toBeDisabled();
    await userEvent.type(amount, "0");
    expect(save).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("muestra el error del servidor y no cierra", async () => {
    const { onClose, amount, save } = setup(vi.fn().mockRejectedValue(new Error("boom")));
    await userEvent.type(amount, "10");
    await userEvent.click(save);
    expect(onClose).not.toHaveBeenCalled();
    expect(await screen.findByText(/\S/, { selector: "p.text-danger" })).toBeInTheDocument();
  });
});
