const stats = [
  { value: "2,840+", label: "Toneladas Cosechadas" },
  { value: "156", label: "Campos Activos" },
  { value: "12", label: "Paises Atendidos" },
  { value: "98%", label: "Tiempo en Linea" },
];

export function Stats() {
  return (
    <section className="py-16 lg:py-24 border-y border-midnight/5">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-midnight tracking-tight">
            Produccion de Arandanos en Cifras
          </h2>
          <p className="mt-4 text-lg text-midnight/60">
            Metricas reales de nuestra red de fincas asociadas alrededor del mundo.
          </p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl sm:text-4xl lg:text-5xl font-bold text-midnight tracking-tight">
                {stat.value}
              </div>
              <p className="mt-2 text-sm sm:text-base text-midnight/60">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
