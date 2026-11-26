import {
  Boxes,
  LineChart,
  CloudSun,
  BarChart3,
  Leaf,
  ShieldCheck,
} from "lucide-react";
import { Card, CardContent } from "@/shared/ui/card";

const features = [
  {
    icon: Boxes,
    title: "Inventario en Tiempo Real",
    description:
      "Rastrea niveles de stock, rendimientos de cosecha y suministros en todas tus operaciones en tiempo real.",
  },
  {
    icon: LineChart,
    title: "Pronosticos Inteligentes",
    description:
      "Predicciones impulsadas por IA que te ayudan a planificar la demanda y el rendimiento de tus cultivos.",
  },
  {
    icon: CloudSun,
    title: "Integracion Climatica",
    description:
      "Datos meteorologicos automatizados para optimizar decisiones de siembra, cosecha y almacenamiento.",
  },
  {
    icon: BarChart3,
    title: "Panel de Analiticas",
    description:
      "Analiticas y reportes completos para entender el rendimiento de tu finca de un vistazo.",
  },
  {
    icon: Leaf,
    title: "Gestion de Cultivos",
    description:
      "Administra ciclos de cultivo, rastrea etapas de crecimiento y monitorea condiciones del campo.",
  },
  {
    icon: ShieldCheck,
    title: "Listo para Cumplimiento",
    description:
      "Herramientas integradas para regulaciones de seguridad alimentaria y certificaciones organicas.",
  },
];

export function Features() {
  return (
    <section id="features" className="py-20 lg:py-32 bg-midnight/[0.02]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-midnight tracking-tight">
            Todo lo que necesitas para gestionar tu finca
          </h2>
          <p className="mt-4 text-lg text-midnight/60">
            Herramientas poderosas disenadas especificamente para operaciones agricolas modernas.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card
              key={feature.title}
              className="bg-cream border-midnight/5 hover:border-midnight/10 hover:shadow-lg transition-all duration-300 group"
            >
              <CardContent className="pt-6">
                <div className="w-12 h-12 rounded-lg bg-dusty/10 flex items-center justify-center mb-4 group-hover:bg-dusty/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-dusty" />
                </div>
                <h3 className="text-lg font-semibold text-midnight mb-2">
                  {feature.title}
                </h3>
                <p className="text-midnight/60 leading-relaxed">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
