// Older browsers, the owner's phone among them (iOS 15, Safari 15.6): the console keeps working there, with two concessions
// and nothing changed for a capable browser.
//
// 1. GFM markdown (tables, strikethrough, task lists, autolinks) comes from remark-gfm, whose autolink code holds a regular
//    expression with a lookbehind. Safari learnt lookbehind in 16.4; an older Safari cannot even parse the file, and one
//    unreadable file kills every script of the page. So that package is transpiled with the app (next.config.ts), which
//    turns the literal into a RegExp(...) call that only runs when the plugin runs, and the plugin runs only where the
//    browser understands lookbehind. Everywhere else the markdown renders plain, tables and all the rest as text.
// 2. The array and object methods Safari gained after 15 are added by lib/compat-boot.ts, inline in <head>, before the app
//    starts. A browser that has them is left alone.
import remarkGfm from "remark-gfm";

export const lookbehindOk = (): boolean => { try { new RegExp("(?<=a)b"); return true; } catch { return false; } };

/** The markdown plugins for this browser: GFM where the browser can read its code, none where it cannot. */
export const GFM: any[] = typeof window === "undefined" || lookbehindOk() ? [remarkGfm] : [];
