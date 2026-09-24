"use client";
// The views, as a list: the Mac's five full-screen surfaces (the face, the hands board, the files and apps galaxies,
// the vault), each one tap away. The phone's way in; the desktop bar reaches them directly.
import Link from "next/link";
import { ChevronRight, FolderOpen, Hand, LayoutGrid, Orbit, Smile } from "lucide-react";
import { cn } from "@/lib/utils";

export const VIEWS = [
  { href: "/face", title: "Face", note: "Its state, as a living globe", Icon: Smile, tone: "text-sky-300 bg-sky-400/15" },
  { href: "/hands", title: "Hands board", note: "Pictures, notes and models on a glass board", Icon: Hand, tone: "text-emerald-300 bg-emerald-400/15" },
  { href: "/files", title: "Files", note: "Your folders as a galaxy", Icon: FolderOpen, tone: "text-amber-300 bg-amber-400/15" },
  { href: "/apps", title: "Apps", note: "Every app on the Mac, as stars", Icon: LayoutGrid, tone: "text-violet-300 bg-violet-400/15" },
  { href: "/vault", title: "Vault", note: "Its memory: folders and notes as a wall of cards", Icon: Orbit, tone: "text-pink-300 bg-pink-400/15" },
] as const;

export function Views() {
  return (
    <div className="mx-auto grid w-full max-w-md gap-3">
      <p className="px-1 text-[13px] text-muted-foreground">Each view fills the screen. Pinch and drag in the galaxies; the pill at the bottom brings you back.</p>
      <div className="hairline divide-y divide-border overflow-hidden rounded-2xl">
        {VIEWS.map(({ href, title, note, Icon, tone }) => (
          <Link key={href} href={href} className="flex items-center gap-4 px-4 py-3.5 transition-colors active:bg-surface">
            <span className={cn("grid h-10 w-10 shrink-0 place-items-center rounded-xl", tone)}><Icon className="h-5 w-5" /></span>
            <span className="min-w-0 flex-1"><span className="block text-[16px] font-medium">{title}</span><span className="block truncate text-[13px] text-muted-foreground">{note}</span></span>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </Link>))}
      </div>
    </div>
  );
}
