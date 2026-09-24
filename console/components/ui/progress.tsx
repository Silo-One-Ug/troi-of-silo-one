"use client";
import * as P from "@radix-ui/react-progress";
import { cn } from "@/lib/utils";
export function Progress({ value = 0, className }: { value?: number; className?: string }) {
  return <P.Root className={cn("h-2 w-full overflow-hidden rounded-full bg-surface", className)} value={value}><P.Indicator className="h-full bg-primary transition-transform duration-500" style={{ transform: `translateX(-${100 - Math.max(0, Math.min(100, value))}%)` }} /></P.Root>;
}
