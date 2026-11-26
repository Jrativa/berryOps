import { api } from "@/core/api/axios.instance";

/** Descarga un archivo que exige autenticación: un enlace directo no enviaría el token. */
export async function downloadFile(path: string, params?: Record<string, string | undefined>): Promise<void> {
  const res = await api.get<Blob>(path, { params, responseType: "blob" });
  const disposition: string = res.headers["content-disposition"] ?? "";
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? "export.csv";

  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
