import type { Transition, Variants } from "motion/react";

/**
 * Springs de la interfaz. Se describen con duración visual + rebote (equivalente
 * a "response" + "damping ratio"). Por defecto no hay rebote (amortiguamiento
 * crítico); el rebote se reserva para interacciones que arrastran inercia.
 */
export const spring: Transition = { type: "spring", bounce: 0, duration: 0.4 };
export const springSnappy: Transition = { type: "spring", bounce: 0, duration: 0.3 };
export const springBouncy: Transition = { type: "spring", bounce: 0.2, duration: 0.4 };

/** Entrada escalonada de bloques: aparecen desde abajo con el mismo spring. */
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export const riseIn: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: spring },
};
