import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
function coreUrl() { try { const o = typeof window !== "undefined" ? localStorage.getItem("silo.core") : ""; if (o) return o; } catch {} return process.env.NEXT_PUBLIC_CORE_URL || "http://127.0.0.1:8000"; }
export const CORE = coreUrl();                                   // NEXT_PUBLIC_CORE_URL at build time; localStorage "silo.core" overrides it in a browser (development)
export const CORE_WS = CORE.replace(/^http/, "ws");
