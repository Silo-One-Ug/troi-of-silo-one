import { cn } from "@/lib/utils";
export function Badge({ tone = "note", className, ...p }: React.HTMLAttributes<HTMLSpanElement> & { tone?: "ok" | "note" | "warn" }) {
  return <span className={cn("pill", tone === "ok" ? "pill-ok" : tone === "warn" ? "pill-warn" : "pill-note", className)} {...p} />;
}
