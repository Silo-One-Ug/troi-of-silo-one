"use client";
import * as T from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";
export const Tabs = T.Root;
export function TabsList({ className, ...p }: React.ComponentProps<typeof T.List>) { return <T.List className={cn("flex gap-1 border-b border-border", className)} {...p} />; }
export function TabsTrigger({ className, ...p }: React.ComponentProps<typeof T.Trigger>) { return <T.Trigger className={cn("rounded-sm px-3 py-1.5 text-sm text-muted-foreground data-[state=active]:bg-accent data-[state=active]:font-medium data-[state=active]:text-accent-foreground", className)} {...p} />; }
export function TabsContent({ className, ...p }: React.ComponentProps<typeof T.Content>) { return <T.Content className={cn("pt-3", className)} {...p} />; }
