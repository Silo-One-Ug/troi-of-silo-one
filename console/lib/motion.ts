// Framer Motion presets (docs/DESIGN.md): short, ease-out, a 6px rise, never a bounce.
import type { HTMLMotionProps } from "framer-motion";
type Preset = Pick<HTMLMotionProps<"div">, "initial" | "animate" | "exit" | "transition">;
export const rise: Preset = { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: 6 }, transition: { duration: 0.22, ease: [0.2, 0.8, 0.2, 1] } };
export const fade: Preset = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.18 } };
