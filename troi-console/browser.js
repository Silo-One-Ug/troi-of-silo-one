// browser.js — the bridge between the agent's Chrome and the console's Browser pane.
// The agent's browser is a Chrome of its own (its own profile, a debugging port) that the
// Playwright tools drive over CDP. This script connects to the same Chrome and:
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
const CACHE = path.join(process.env.TROI_DATA || path.join(__dirname, "..", "data"), "cache");
const WATCH = path.join(CACHE, ".browser-watch");
const SHOT = path.join(CACHE, "browser.jpg");
const INFO = path.join(CACHE, "browser.json");
const CMDS = path.join(CACHE, "browser-cmds.jsonl");
fs.mkdirSync(CACHE, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));
const fresh = (p, s) => { try { return Date.now() - fs.statSync(p).mtimeMs < s * 1000; } catch (e) { return false; } };

async function connect() {
  for (;;) {
    try { const b = await chromium.connectOverCDP(CDP, { timeout: 5000 }); return b; }
    catch (e) { await sleep(2000); }
  }
}

async function main() {
  const browser = await connect();
  let ctx = browser.contexts()[0] || await browser.newContext();
  let current = null;
  const adopt = p => { current = p; p.on("close", () => { if (current === p) current = null; }); };
  ctx.on("page", adopt);
  const pages = ctx.pages(); if (pages.length) adopt(pages[pages.length - 1]);
  browser.on("disconnected", () => { fs.writeFileSync(INFO, JSON.stringify({ url: "", title: "", gone: true, t: Date.now() })); process.exit(0); });

  async function page() {
    if (current && !current.isClosed()) return current;
    const ps = ctx.pages().filter(p => !p.isClosed());
    if (ps.length) { adopt(ps[ps.length - 1]); return current; }
    adopt(await ctx.newPage()); await current.goto("about:blank"); return current;
  }
  // the page the agent is working in is the one that changed last
  ctx.on("page", p => p.on("framenavigated", f => { if (f === p.mainFrame()) current = p; }));
  ctx.pages().forEach(p => p.on("framenavigated", f => { if (f === p.mainFrame()) current = p; }));

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

  let busy = false, lastShot = 0;
  for (;;) {
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
        fs.writeFileSync(INFO, JSON.stringify({ url: p.url(), title: await p.title().catch(() => ""), w: vp.w, h: vp.h, t: Date.now() }));
      } catch (e) {}
      busy = false; lastShot = Date.now();
    }
    await sleep(60);
  }
}
main().catch(e => { fs.appendFileSync(path.join(CACHE, "browser.log"), new Date().toISOString() + " fatal: " + (e.message || e) + "\n"); process.exit(1); });
