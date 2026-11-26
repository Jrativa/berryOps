import { api } from "@/core/api/axios.instance";

import { downloadFile } from "./download";

describe("downloadFile", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pide el archivo con el token (vía api), lo nombra según el servidor y libera la URL", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue({
      data: new Blob(["a,b"]),
      headers: { "content-disposition": 'attachment; filename="cosechas_inicio_2026-01-01.csv"' },
    });
    URL.createObjectURL = vi.fn(() => "blob:fake");
    URL.revokeObjectURL = vi.fn();
    let downloaded = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloaded = this.download;
    });

    await downloadFile("/inventory/export/harvests", { from: "2026-01-01", plot: undefined });

    expect(get).toHaveBeenCalledWith(
      "/inventory/export/harvests",
      expect.objectContaining({ responseType: "blob", params: { from: "2026-01-01", plot: undefined } }),
    );
    expect(downloaded).toBe("cosechas_inicio_2026-01-01.csv");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:fake");
  });

  it("propaga el error si el servidor rechaza la descarga", async () => {
    vi.spyOn(api, "get").mockRejectedValue(new Error("403"));
    await expect(downloadFile("/inventory/export/costs")).rejects.toThrow("403");
  });
});
