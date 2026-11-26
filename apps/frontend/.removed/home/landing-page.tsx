import { Navbar } from "./navbar";
import { Hero } from "./hero";
import { Features } from "./features";
import { Stats } from "./stats";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <main>
        <Hero />
        <Stats />
        <Features />
      </main>
      <Footer />
    </div>
  );
}
