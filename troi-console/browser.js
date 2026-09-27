// browser.js — the bridge between the agent's browser and the console's Browser pane.
// The agent's browser is Arc (shared with the owner) or a Chrome of its own, on a debugging port, that the
// Playwright tools drive over CDP (browser-mcp.sh picks it). This script connects to the same browser and:
//   - while the console is watching (data/cache/.browser-watch is fresh), writes a JPEG of the
//     current page to cache/browser.jpg a few times a second, plus cache/browser.json
//     (url, title, viewport), so the pane can show the page as it changes;
//   - carries the pane's clicks, typing, scrolling and navigation back into the page
//     (cache/browser-cmds.jsonl, appended by the console server, consumed here).
// Started by start.sh. Standard node plus playwright-core (npm i playwright-core, here).
const fs = require("fs");
const path = require("path");
const { chromium } = require(path.join(__dirname, "node_modules", "playwright-core"));

const CDP = process.env.TROI_CDP || "http://127.0.0.1:9223";
const APP = process.env.TROI_BROWSER_APP || "Google Chrome";          // which app the console's "Window" button brings forward
const CACHE = path.join(process.env.TROI_DATA || path.join(__dirname, "..", "data"), "cache");
// the console and the agent's own pages live in the same browser when it is Arc: never mirror them, never take them as the working page
const ours = u => /^https?:\/\/(localhost|127\.0\.0\.1):(3100|8796|8794|8790)\b/.test(u || "");
const WATCH = path.join(CACHE, ".browser-watch");
const SHOT = path.join(CACHE, "browser.jpg");
const INFO = path.join(CACHE, "browser.json");
const CMDS = path.join(CACHE, "browser-cmds.jsonl");
fs.mkdirSync(CACHE, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));
const fresh = (p, s) => { try { return Date.now() - fs.statSync(p).mtimeMs < s * 1000; } catch (e) { return false; } };

// the agent's browser, brought back when it is wanted and gone: while the console's Browser page watches, or a click or an
// address is waiting, browser-mcp.sh open starts it again (the agent's own Chrome; an Arc in the old mode); at most every 30 s.
// Quit by the owner and wanted by nobody, it stays quit.
let lastLaunch = 0;
function wanted() { try { return fresh(WATCH, 6) || (fs.existsSync(CMDS) && fs.statSync(CMDS).size > 0); } catch (e) { return false; } }
function relaunch() {
  if (Date.now() - lastLaunch < 30000) return;
  lastLaunch = Date.now();
  try {
    const { execFile } = require("child_process");
    execFile(path.join(__dirname, "browser-mcp.sh"), ["open"], { timeout: 60000 }, (err, out) => { try { fs.appendFileSync(path.join(CACHE, "browser.log"), new Date().toISOString() + " relaunch: " + (err ? "failed: " + err.message : String(out || "").trim()) + "\n"); } catch (e) {} });
  } catch (e) {}
}
async function connect() {
  let failed = 0;
  for (;;) {
    try { const b = await chromium.connectOverCDP(CDP, { timeout: 5000 }); return b; }
    catch (e) { failed++; if (failed >= 2 && wanted()) relaunch(); await sleep(2000); }
  }
}

async function main() {
  const browser = await connect();
  let ctx = browser.contexts()[0] || await browser.newContext();
  let current = null, gone = false;
  const adopt = p => { if (ours(p.url())) return; current = p; p.on("close", () => { if (current === p) current = null; }); };
  ctx.on("page", adopt);
  const pages = ctx.pages().filter(p => !ours(p.url())); if (pages.length) adopt(pages[pages.length - 1]);
  // the browser quit (Arc closed by the owner, say): note it for the pane and connect again when it is back
  browser.on("disconnected", () => { gone = true; try { fs.writeFileSync(INFO, JSON.stringify({ url: "", title: "", app: APP, gone: true, t: Date.now() })); } catch (e) {} });

  async function page() {
    if (current && !current.isClosed()) return current;
    const ps = ctx.pages().filter(p => !p.isClosed() && !ours(p.url()));
    if (ps.length) { adopt(ps[ps.length - 1]); return current; }
    current = await ctx.newPage(); current.on("close", () => { current = null; }); await current.goto("about:blank"); return current;
  }
  // the page the agent is working in is the one that changed last (never the console's own tab)
  const follow = p => p.on("framenavigated", f => { if (f === p.mainFrame() && !ours(p.url())) current = p; });
  ctx.on("page", follow); ctx.pages().forEach(follow);

  const logline = t => fs.appendFileSync(path.join(CACHE, "browser.log"), new Date().toISOString() + " " + t + "\n");
  async function run(cmd) {
    const p = await page();
    logline("cmd " + JSON.stringify(cmd));
    try {
      switch (cmd.op) {
        case "click": await p.mouse.click(cmd.x, cmd.y, { clickCount: cmd.count || 1 }); break;
        case "move": await p.mouse.move(cmd.x, cmd.y); break;
        case "scroll": await p.mouse.move(cmd.x || 400, cmd.y || 300); await p.mouse.wheel(0, cmd.dy || 0); break;
        case "type": await p.keyboard.type(String(cmd.text || ""), { delay: 8 }); break;
        case "key": await p.keyboard.press(String(cmd.key || "")); break;
        case "goto": { let u = String(cmd.url || "").trim(); if (!/^[a-z]+:/i.test(u)) u = /\s|^[^.]+$/.test(u) ? "https://www.google.com/search?q=" + encodeURIComponent(u) : "https://" + u; await p.goto(u, { waitUntil: "domcontentloaded", timeout: 30000 }); break; }
        case "back": await p.goBack({ timeout: 15000 }).catch(() => {}); break;
        case "forward": await p.goForward({ timeout: 15000 }).catch(() => {}); break;
        case "reload": await p.reload({ timeout: 30000 }).catch(() => {}); break;
        case "newtab": adopt(await ctx.newPage()); if (cmd.url) await current.goto(cmd.url, { waitUntil: "domcontentloaded" }); break;
      }
    } catch (e) { logline(cmd.op + " failed: " + (e.message || e)); }
  }

  let busy = false, lastShot = 0, lastInfo = 0;
  while (!gone) {
    // the page's address and title every second, watched or not: the pane knows what the agent is on before it asks for frames
    if (Date.now() - lastInfo > 1000) {
      lastInfo = Date.now();
      try {
        const ps = ctx.pages().filter(p => !p.isClosed() && !ours(p.url()));
        const p = current && !current.isClosed() ? current : ps[ps.length - 1];
        fs.writeFileSync(INFO, JSON.stringify({ url: p ? p.url() : "", title: p ? await p.title().catch(() => "") : "", app: APP, t: Date.now() }));
      } catch (e) {}
    }
    // commands first: the pane's clicks and keys
    try {
      if (fs.existsSync(CMDS)) {
        const lines = fs.readFileSync(CMDS, "utf8").split("\n").filter(Boolean); fs.writeFileSync(CMDS, "");
        for (const l of lines) { try { await run(JSON.parse(l)); } catch (e) {} }
      }
    } catch (e) {}
    // frames while someone is watching
    if (fresh(WATCH, 6) && !busy && Date.now() - lastShot > 350) {
      busy = true;
      try {
        const p = await page();
        const vp = await p.evaluate(() => ({ w: innerWidth, h: innerHeight })).catch(() => ({ w: 1280, h: 900 }));
        const buf = await p.screenshot({ type: "jpeg", quality: 55, timeout: 4000 });
        fs.writeFileSync(SHOT + ".tmp", buf); fs.renameSync(SHOT + ".tmp", SHOT);
        fs.writeFileSync(INFO, JSON.stringify({ url: p.url(), title: await p.title().catch(() => ""), app: APP, w: vp.w, h: vp.h, t: Date.now() }));
      } catch (e) {}
      busy = false; lastShot = Date.now();
    }
    await sleep(60);
  }
}
(async () => {                                                        // for as long as the agent runs: reconnect whenever the browser comes back
  for (;;) {
    try { await main(); } catch (e) { fs.appendFileSync(path.join(CACHE, "browser.log"), new Date().toISOString() + " bridge: " + (e.message || e) + "\n"); }
    await sleep(2000);
  }
})();
