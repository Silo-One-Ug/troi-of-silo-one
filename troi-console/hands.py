#!/usr/bin/env python3
"""the agent's native hands: every app's interface addressed by name through the Mac's accessibility tree, from one
resident process. No screenshot to find a button, no coordinates to miss it, and the result is read back from the
element itself. The brain reaches this as MCP tools (hands.sh mcp, see hands-mcp.py); people and scripts use the CLI.

  hands.py apps                              running apps, front first
  hands.py launch <app>                      open an app by name and wait for its window
  hands.py focus <app>                       bring an app to the front
  hands.py windows [app]                     its windows: id, title, focused, frame
  hands.py inspect [app] [--all] [--depth N] the interface of its front window as a tree with ids
  hands.py find <app> <text> [--role R]      elements whose title, description, value or identifier match
  hands.py read <id>                         everything about one element
  hands.py press <app> <text> [--role R]     press the control called <text> (AXPress), then read it back
  hands.py set <app> <target> <value>        put a value into a field (<target> is an id or its label)
  hands.py perform <id> <action>             any action the element offers (Press, Confirm, Cancel, ShowMenu, Increment…)
  hands.py menu <app> [File > Export…]       list a menu, or press an item by its path
  hands.py type <text>                       insert text at the focused field (accessibility first, keystrokes second)
  hands.py key <combo>                       return, tab, esc, arrows, or cmd+s, cmd+shift+t…
  hands.py click <x> <y> [--double|--right] [--screenshot]   the pointer, for what has no name (points; --screenshot
                                             converts pixels of a look-screen.sh screenshot to points)
  hands.py wait <app> <text> [--timeout S]   wait for an element to appear (a sheet, a button, a title)
  hands.py doctor                            is the accessibility API available, and how fast is it

Guards, always on, shared with cursor.py: a control whose label is risky (delete, remove, trash, pay, buy, send,
submit, allow, install, reset, quit…) is not pressed: an approval request is filed for the owner instead; secure
fields (passwords) are never written to; destructive shortcuts are refused; everything is logged to data/logs/hands.log.
"""
import json, re, subprocess, sys, time, glob, os
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import paths as P                                                    # noqa: E402
from cursor import RISKY, BLOCKED_KEYS, AGENT, OWNER, ask_owner       # noqa: E402  one source of truth for the guards

import AppKit, Quartz                                                 # noqa: E402
from ApplicationServices import (                                     # noqa: E402
    AXIsProcessTrusted, AXUIElementCreateApplication, AXUIElementCreateSystemWide, AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeNames, AXUIElementCopyActionNames, AXUIElementPerformAction, AXUIElementSetAttributeValue,
    AXUIElementIsAttributeSettable, AXUIElementCopyElementAtPosition, AXUIElementSetMessagingTimeout, AXUIElementGetPid,
    AXValueGetType, AXValueGetValue)

LOGF = P.LOGS / "hands.log"
ERRORS = {-25200: "failure", -25201: "illegal argument", -25202: "the element is gone (invalid)", -25203: "the app did not answer in time",
          -25204: "attribute unsupported", -25205: "action unsupported", -25206: "notification unsupported", -25207: "not implemented",
          -25211: "the accessibility API is disabled for this process", -25212: "no value", -25213: "parameterized attribute unsupported"}
SHOWN = {"AXWindow", "AXSheet", "AXDialog", "AXDrawer", "AXPopover", "AXToolbar", "AXTabGroup", "AXTable", "AXOutline", "AXList", "AXBrowser",
         "AXWebArea", "AXMenuBar", "AXMenu"}                        # structure worth a line even though it does nothing itself
INTERACTIVE = {"AXButton", "AXTextField", "AXTextArea", "AXCheckBox", "AXRadioButton", "AXPopUpButton", "AXMenuButton", "AXSlider", "AXTab",
               "AXLink", "AXComboBox", "AXRow", "AXCell", "AXMenuItem", "AXMenuBarItem", "AXDisclosureTriangle", "AXIncrementor", "AXColorWell",
               "AXDateField", "AXTimeField", "AXStaticText", "AXHeading", "AXImage", "AXSwitch", "AXToggle", "AXSearchField", "AXProgressIndicator",
               "AXValueIndicator", "AXDockItem"}
SECRET = re.compile(r"password|passcode|passphrase|\bpin\b|secret|otp|one-time code", re.I)
SCREENSHOT_MAX = 1600                                               # look-screen.sh resizes the long side of its screenshots to this
KEYS = {"return": 36, "enter": 76, "tab": 48, "space": 49, "delete": 51, "backspace": 51, "forwarddelete": 117, "esc": 53, "escape": 53,
        "left": 123, "right": 124, "down": 125, "up": 126, "home": 115, "end": 119, "pageup": 116, "pagedown": 121, "f1": 122, "f2": 120,
        "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
        "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16,
        "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31,
        "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50}
FLAGS = {"cmd": Quartz.kCGEventFlagMaskCommand, "shift": Quartz.kCGEventFlagMaskShift, "alt": Quartz.kCGEventFlagMaskAlternate, "ctrl": Quartz.kCGEventFlagMaskControl}


def log(line):
    try:
        LOGF.parent.mkdir(parents=True, exist_ok=True)
        with LOGF.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except OSError:
        pass


class HandsError(Exception):
    pass


# ---- the accessibility tree ------------------------------------------------------------------------------------
def _get(el, attr):
    """One attribute; (value, error). Never raises."""
    try:
        e, v = AXUIElementCopyAttributeValue(el, attr, None)
    except Exception:
        return None, -25200
    return (v if e == 0 else None), e


def _s(v, n=80):
    """A value as short text."""
    if v is None:
        return ""
    if isinstance(v, (bool, int, float)):
        return str(v)
    t = str(v).replace("\n", "⏎")
    return t if len(t) <= n else t[:n - 1] + "…"


def _unwrap(v):
    """AXValue boxes (points, sizes, rects, ranges) as plain numbers."""
    try:
        t = AXValueGetType(v)
        ok, x = AXValueGetValue(v, t, None)
        if not ok:
            return None
        if t == 1: return {"x": round(x.x), "y": round(x.y)}
        if t == 2: return {"w": round(x.width), "h": round(x.height)}
        if t == 3: return {"x": round(x.origin.x), "y": round(x.origin.y), "w": round(x.size.width), "h": round(x.size.height)}
        if t == 4: return {"at": int(x.location), "len": int(x.length)}
    except Exception:
        return None
    return None


def _frame(el):
    p, _ = _get(el, "AXPosition"); s, _ = _get(el, "AXSize")
    p = _unwrap(p) if p is not None else None; s = _unwrap(s) if s is not None else None
    return {**p, **s} if p and s else None


def _actions(el):
    try:
        e, a = AXUIElementCopyActionNames(el, None)
        return [str(x) for x in a] if e == 0 and a else []
    except Exception:
        return []


def _label(el, role=None):
    """What a person would call it: the title, else the description, else the value of a static text, else the identifier."""
    role = role or _s(_get(el, "AXRole")[0])
    for a in ("AXTitle", "AXDescription"):
        v = _s(_get(el, a)[0], 120)
        if v.strip():
            return v.strip()
    if role in ("AXStaticText", "AXHeading", "AXLink", "AXMenuItem", "AXMenuBarItem"):
        v = _s(_get(el, "AXValue")[0], 120)
        if v.strip():
            return v.strip()
    for a in ("AXPlaceholderValue", "AXIdentifier", "AXHelp"):
        v = _s(_get(el, a)[0], 120)
        if v.strip():
            return v.strip()
    if role in ("AXRow", "AXCell"):                                  # a row is called what its texts say
        texts = []
        def dig(x, d):
            if d > 4 or len(texts) > 6: return
            r = _s(_get(x, "AXRole")[0])
            if r in ("AXStaticText", "AXTextField", "AXLink"):
                t = _s(_get(x, "AXValue")[0], 60) or _s(_get(x, "AXTitle")[0], 60)
                if t.strip(): texts.append(t.strip())
            for k in (_get(x, "AXChildren")[0] or []): dig(k, d + 1)
        dig(el, 0)
        return " · ".join(texts)
    return ""


class Registry:
    """Element handles by short id (e12) for the life of this process, stable for the same element."""
    def __init__(self):
        self.by_id, self.by_key, self.n = {}, {}, 0

    def _key(self, el):
        try:
            return hash(el)
        except TypeError:
            return id(el)

    def id(self, el):
        k = self._key(el)
        if k in self.by_key:
            return self.by_key[k]
        self.n += 1; i = f"e{self.n}"
        self.by_id[i] = el; self.by_key[k] = i
        return i

    def el(self, i):
        el = self.by_id.get(str(i).strip())
        if el is None:
            raise HandsError(f"no element {i}: ids come from inspect/find in this session; run inspect again")
        if _get(el, "AXRole")[1] == -25202:
            raise HandsError(f"element {i} is gone (the window or view changed); run inspect again")
        return el


REG = Registry()
_TOUCHED = set()                                                    # pids whose Electron/Chromium tree we switched on
_TIMEOUT_SET = set()


def trusted():
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def running():
    """GUI apps, front first: dicts with name, bundle, pid, active, hidden."""
    ws = AppKit.NSWorkspace.sharedWorkspace(); front = ws.frontmostApplication()
    out = []
    for a in ws.runningApplications():
        if a.activationPolicy() != 0:
            continue
        out.append({"name": str(a.localizedName() or ""), "bundle": str(a.bundleIdentifier() or ""), "pid": int(a.processIdentifier()),
                    "active": bool(front and a.processIdentifier() == front.processIdentifier()), "hidden": bool(a.isHidden()), "_app": a})
    out.sort(key=lambda d: (not d["active"], d["name"].lower()))
    return out


def resolve(app):
    """A running app from a name ('front' = the frontmost), a bundle id, a pid, or a unique substring."""
    apps = running()
    if not apps:
        raise HandsError("no GUI apps are running")
    q = (app or "front").strip()
    if q.lower() in ("front", "frontmost", "focused", "active", ""):
        return apps[0]
    if q.isdigit():
        for a in apps:
            if a["pid"] == int(q): return a
    ql = q.lower()
    for key in ("name", "bundle"):
        for a in apps:
            if a[key].lower() == ql: return a
    hits = [a for a in apps if ql in a["name"].lower() or ql in a["bundle"].lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise HandsError(f"{q} is not running (running: {', '.join(a['name'] for a in apps)}); launch it first")
    raise HandsError(f"{q} matches several apps: {', '.join(a['name'] for a in hits)}")


def app_element(a):
    el = AXUIElementCreateApplication(a["pid"])
    if a["pid"] not in _TIMEOUT_SET:
        try: AXUIElementSetMessagingTimeout(el, 1.5)                  # a stalled app answers "did not answer in time", not a hang
        except Exception: pass
        _TIMEOUT_SET.add(a["pid"])
    return el


def _onscreen_pids():
    try:
        return {int(w.get("kCGWindowOwnerPID")) for w in Quartz.CGWindowListCopyWindowInfo(1 | 16, 0) if w.get("kCGWindowLayer", 0) == 0}
    except Exception:
        return set()


def windows(a):
    """The app's AX windows. Electron and Chromium apps build their tree only when asked: ask once, then look again."""
    el = app_element(a)
    wins, e = _get(el, "AXWindows")
    if not wins and a["pid"] not in _TOUCHED and a["pid"] in _onscreen_pids():
        for flag in ("AXManualAccessibility", "AXEnhancedUserInterface"):
            try: AXUIElementSetAttributeValue(el, flag, True)
            except Exception: pass
        _TOUCHED.add(a["pid"]); time.sleep(0.6)
        wins, e = _get(el, "AXWindows")
    if e not in (0, -25212):
        raise HandsError(f"{a['name']}: cannot list windows ({ERRORS.get(e, e)})")
    focused, _ = _get(el, "AXFocusedWindow")
    out = []
    for w in (wins or []):
        out.append({"id": REG.id(w), "title": _s(_get(w, "AXTitle")[0], 120), "focused": bool(focused is not None and w == focused),
                    "main": bool(_get(w, "AXMain")[0]), "minimized": bool(_get(w, "AXMinimized")[0]), "frame": _frame(w), "_el": w})
    out.sort(key=lambda d: (not d["focused"], not d["main"], d["minimized"]))
    return out


def front_window(a):
    ws = windows(a)
    if not ws:
        raise HandsError(f"{a['name']} has no window to look at (WezTerm exposes none; Electron apps need a moment after the first touch)")
    return ws[0]["_el"]


def node_line(el, depth=0, role=None):
    role = role or _s(_get(el, "AXRole")[0]); sub = _s(_get(el, "AXSubrole")[0])
    label = _label(el, role); parts = [REG.id(el), role + (f"/{sub[2:]}" if sub and sub != role else "")]
    if label:
        parts.append(json.dumps(label))
    if role in ("AXTextField", "AXTextArea", "AXComboBox", "AXSearchField", "AXSlider", "AXIncrementor", "AXPopUpButton", "AXDateField", "AXTimeField") or sub == "AXSecureTextField":
        v = _get(el, "AXValue")[0]
        parts.append("=" + (json.dumps(_s(v, 60)) if sub != "AXSecureTextField" else "•••"))
    if role in ("AXCheckBox", "AXRadioButton", "AXSwitch", "AXToggle", "AXMenuItem", "AXTab"):
        v = _get(el, "AXValue")[0]
        if v is not None and str(v) in ("1", "True", "2"): parts.append("✓")
    if role == "AXTab" or role == "AXRow":
        if _get(el, "AXSelected")[0]: parts.append("selected")
    en = _get(el, "AXEnabled")[0]
    if en is not None and not en: parts.append("disabled")
    if _get(el, "AXFocused")[0]: parts.append("focused")
    acts = [x[2:] for x in _actions(el) if x not in ("AXScrollToVisible",)]
    if acts: parts.append("[" + ",".join(acts) + "]")
    fr = _frame(el)
    if fr and role not in ("AXWindow",): parts.append(f"@{fr['x']},{fr['y']} {fr['w']}x{fr['h']}")
    return "  " * depth + " ".join(parts)


def walk(root, depth=8, all_elements=False, max_nodes=2500, budget_s=2.5):
    """Lines for the tree under root: interactive elements and structure by default, everything with all_elements."""
    lines, n, t0, cut = [], [0], time.time(), [False]
    def rec(el, d):
        if d > depth or n[0] >= max_nodes or time.time() - t0 > budget_s:
            cut[0] = True; return
        n[0] += 1
        role = _s(_get(el, "AXRole")[0])
        show = all_elements or role in INTERACTIVE or role in SHOWN or d == 0
        if role in ("AXStaticText", "AXImage") and not all_elements and not _label(el, role):
            show = False
        if show:
            lines.append(node_line(el, d, role))
        kids, _ = _get(el, "AXChildren")
        for k in (kids or []):
            rec(k, d + 1)
    rec(root, 0)
    if cut[0]:
        lines.append(f"… (cut at depth {depth} / {max_nodes} nodes / {budget_s}s; narrow it with find, or inspect a window id)")
    return lines


def _match_text(el, role, q):
    ql = q.lower()
    for a in ("AXTitle", "AXDescription", "AXValue", "AXIdentifier", "AXPlaceholderValue", "AXHelp"):
        v = _get(el, a)[0]
        if v is not None and not isinstance(v, (list, tuple)) and ql in _s(v, 300).lower():
            return True
    if role in ("AXRow", "AXCell") and ql in _label(el, role).lower():
        return True
    return False


def norm_role(r):
    if not r: return ""
    r = r.strip()
    if r.lower().startswith("ax"): r = r[2:]
    canon = {"button": "AXButton", "textfield": "AXTextField", "field": "AXTextField", "text": "AXStaticText", "statictext": "AXStaticText",
             "textarea": "AXTextArea", "checkbox": "AXCheckBox", "radio": "AXRadioButton", "radiobutton": "AXRadioButton", "popup": "AXPopUpButton",
             "popupbutton": "AXPopUpButton", "menubutton": "AXMenuButton", "slider": "AXSlider", "tab": "AXTab", "link": "AXLink", "row": "AXRow",
             "cell": "AXCell", "menuitem": "AXMenuItem", "window": "AXWindow", "sheet": "AXSheet", "dialog": "AXDialog", "combobox": "AXComboBox",
             "table": "AXTable", "outline": "AXOutline", "list": "AXList", "image": "AXImage", "switch": "AXSwitch", "heading": "AXHeading"}
    return canon.get(r.lower().replace(" ", ""), "AX" + r[0].upper() + r[1:])


def find(a, text="", role="", limit=25, roots=None, depth=25, max_nodes=4000):
    """Elements in the app's windows (front first) matching text and/or role, best first."""
    role = norm_role(role); q = (text or "").strip()
    if not q and not role:
        raise HandsError("find needs a text or a role")
    roots = roots or [w["_el"] for w in windows(a)] or []
    if not roots:
        raise HandsError(f"{a['name']} has no window to search")
    hits, n, t0 = [], [0], time.time()
    def rec(el, d):
        if d > depth or n[0] >= max_nodes or len(hits) >= limit * 4 or time.time() - t0 > 3.0: return
        n[0] += 1
        r = _s(_get(el, "AXRole")[0])
        if (not role or r == role) and (not q or _match_text(el, r, q)):
            hits.append((el, r, d))
        kids, _ = _get(el, "AXChildren")
        for k in (kids or []): rec(k, d + 1)
    for root in roots:
        rec(root, 0)
    def score(h):
        el, r, d = h; lab = _label(el, r).lower(); ql = q.lower()
        exact = 0 if ql and lab == ql else 1 if ql and lab.startswith(ql) else 2
        inter = 0 if r in INTERACTIVE and r not in ("AXStaticText", "AXImage") else 1
        en = 0 if _get(el, "AXEnabled")[0] is not False else 1
        return (exact, inter, en, d)
    hits.sort(key=score)
    return [(el, r) for el, r, d in hits[:limit]]


def pick(a, text, role=""):
    """The one element meant by a label: exact and enabled wins; ambiguity is reported, not guessed."""
    hits = find(a, text, role, limit=8)
    if not hits:
        raise HandsError(f"nothing called {text!r}{' of role ' + norm_role(role) if role else ''} in {a['name']}'s windows; inspect it to see the names")
    el, r = hits[0]
    lab = _label(el, r)
    others = [f"{REG.id(x)} {rr} {json.dumps(_label(x, rr))}" for x, rr in hits[1:4] if _label(x, rr).lower() == lab.lower() and rr == r]
    if others and lab.lower() != (text or "").lower():
        pass
    return el, r


def describe(el):
    role = _s(_get(el, "AXRole")[0]); d = {"id": REG.id(el), "role": role, "subrole": _s(_get(el, "AXSubrole")[0]) or None, "label": _label(el, role),
         "title": _s(_get(el, "AXTitle")[0], 200) or None, "description": _s(_get(el, "AXDescription")[0], 200) or None,
         "value": None, "enabled": _get(el, "AXEnabled")[0], "focused": _get(el, "AXFocused")[0], "selected": _get(el, "AXSelected")[0],
         "actions": _actions(el), "frame": _frame(el), "children": len(_get(el, "AXChildren")[0] or [])}
    v = _get(el, "AXValue")[0]
    d["value"] = "•••" if d["subrole"] == "AXSecureTextField" else (_s(v, 400) if v is not None and not isinstance(v, (list, tuple)) else None)
    for k in ("enabled", "focused", "selected"):
        if d[k] is not None: d[k] = bool(d[k])
    win, _ = _get(el, "AXWindow")
    if win is not None: d["window"] = _s(_get(win, "AXTitle")[0], 120)
    e, pid = AXUIElementGetPid(el, None)
    if e == 0:
        for a in running():
            if a["pid"] == pid: d["app"] = a["name"]
    try:
        e, names = AXUIElementCopyAttributeNames(el, None)
        d["attributes"] = [str(x) for x in names] if e == 0 and names else []
    except Exception:
        d["attributes"] = []
    return {k: v for k, v in d.items() if v not in (None, [], "")}


# ---- guards ----------------------------------------------------------------------------------------------------
def is_secret(el):
    role = _s(_get(el, "AXRole")[0]); sub = _s(_get(el, "AXSubrole")[0])
    if sub == "AXSecureTextField" or role == "AXSecureTextField":
        return True
    text = " ".join(_s(_get(el, a)[0], 200) for a in ("AXTitle", "AXDescription", "AXPlaceholderValue", "AXIdentifier"))
    win, _ = _get(el, "AXWindow")
    if win is not None: text += " " + _s(_get(win, "AXTitle")[0], 200)
    return bool(SECRET.search(text)) and role in ("AXTextField", "AXTextArea", "AXComboBox", "AXSearchField")


def guard(el, role, what):
    """A risky control is not pressed: the request goes to the owner (console card + Telegram) and can be replayed as a click on approval."""
    label = _label(el, role); value = _s(_get(el, "AXValue")[0], 120) if role in ("AXButton", "AXMenuItem", "AXStaticText") else ""
    if not (RISKY.search(label) or RISKY.search(value)):
        return None
    fr = _frame(el) or {}
    x, y = int(fr.get("x", 0) + fr.get("w", 0) / 2), int(fr.get("y", 0) + fr.get("h", 0) / 2)
    r = ask_owner("click", f"{role} '{label}'", what, {"kind": "click", "x": x, "y": y})
    log(f"{what}: RISKY {role} '{label}' -> approval {r.get('pending', r.get('error'))}")
    return {"ok": False, "pending": r.get("pending"), "needs_approval": True,
            "done": f"'{label}' is a risky control ({role}); a request is waiting for {OWNER}'s approval (console card / Telegram). Tell {OWNER} it is waiting; do not press it another way.",
            "error": r.get("error", "")}


def _what_key_presses(name):
    """What a bare Return, Enter or Space would activate right now: the focused control when it is one, else (Return and
    Enter only) the default button of the front window or of a sheet on it. None when nothing would be pressed."""
    fe = focused_element()
    if fe is not None:
        r = _s(_get(fe, "AXRole")[0])
        if r in ("AXButton", "AXMenuItem", "AXCheckBox", "AXRadioButton", "AXLink", "AXPopUpButton"):
            return fe, r
        if name == "space" or r == "AXTextArea":                   # space types in a field; a text area takes Return as a newline
            return None, ""
    if name == "space":
        return None, ""
    app, _ = _get(AXUIElementCreateSystemWide(), "AXFocusedApplication")
    win = _get(app, "AXFocusedWindow")[0] if app is not None else None
    if win is None:
        return None, ""
    b = _get(win, "AXDefaultButton")[0]
    if b is not None:
        return b, "AXButton"
    for ch in (_get(win, "AXChildren")[0] or []):                  # a confirmation sheet hangs off the window
        if _s(_get(ch, "AXRole")[0]) == "AXSheet":
            b = _get(ch, "AXDefaultButton")[0]
            if b is not None:
                return b, "AXButton"
    return None, ""


def key_guard(name, why):
    """The guard for keys that press things: a Return in a dialog whose default button is risky files a request instead."""
    el, r = _what_key_presses(name)
    return guard(el, r, why) if el is not None else None


# ---- actions ---------------------------------------------------------------------------------------------------
HARMLESS = {"AXRaise", "AXCancel", "AXShowMenu", "AXIncrement", "AXDecrement", "AXScrollToVisible", "AXShowDefaultUI", "AXShowAlternateUI"}


def perform_checked(el, action):
    """perform, for the agent: any action that activates something passes the same guard as press. Confirm on a window or
    a sheet presses its default button, so that button is the one checked."""
    name = action if action.startswith("AX") else "AX" + action[0].upper() + action[1:]
    r = _s(_get(el, "AXRole")[0])
    if name not in HARMLESS:
        target, tr = el, r
        if name == "AXConfirm" and r in ("AXWindow", "AXSheet"):
            b = _get(el, "AXDefaultButton")[0]
            if b is not None: target, tr = b, "AXButton"
        g = guard(target, tr, f"perform {name[2:]} on {_label(el, r)!r}")
        if g: return g
    perform(el, name)
    return {"ok": True, "did": f"{name[2:]} on {_label(el, r)!r}", "now": readback(el, r)}


def perform(el, action):
    if not action.startswith("AX"):
        action = "AX" + action[0].upper() + action[1:]
    acts = _actions(el)
    if action not in acts:
        raise HandsError(f"{_s(_get(el, 'AXRole')[0])} '{_label(el)}' offers {', '.join(x[2:] for x in acts) or 'no actions'}, not {action[2:]}")
    e = AXUIElementPerformAction(el, action)
    if e != 0:
        raise HandsError(f"{action[2:]} failed: {ERRORS.get(e, e)}")
    return True


def readback(el, role, a=None):
    """What changed: the element's value and state, and the front window after the action."""
    time.sleep(0.15)
    now = {}
    v = _get(el, "AXValue")[0]
    if v is not None and not isinstance(v, (list, tuple)): now["value"] = _s(v, 120)
    for k in ("AXEnabled", "AXFocused", "AXSelected"):
        x = _get(el, k)[0]
        if x is not None: now[k[2:].lower()] = bool(x)
    try:
        if a:
            ws = windows(a)
            if ws: now["front_window"] = ws[0]["title"]
    except HandsError:
        pass
    return now


def press(a, text, role=""):
    el, r = pick(a, text, role)
    if r in ("AXTextField", "AXTextArea", "AXSearchField", "AXComboBox") and "AXPress" not in _actions(el):
        raise HandsError(f"'{_label(el, r)}' is a field, not a button: use set or type")
    g = guard(el, r, f"press {text!r} in {a['name']}")
    if g: return g
    acts = _actions(el)
    action = "AXPress" if "AXPress" in acts else "AXConfirm" if "AXConfirm" in acts else "AXShowMenu" if "AXShowMenu" in acts and r == "AXMenuButton" else None
    if not action:
        if r in ("AXRow", "AXCell", "AXTab") and AXUIElementIsAttributeSettable(el, "AXSelected", None)[1]:
            e = AXUIElementSetAttributeValue(el, "AXSelected", True)
            if e: raise HandsError(f"could not select it: {ERRORS.get(e, e)}")
            action = "select"
            fr = _frame(el)
            if fr and r in ("AXRow", "AXCell"):                     # a sidebar or list acts on a real click, not on the selection alone
                _click_at(fr["x"] + fr["w"] / 2, fr["y"] + fr["h"] / 2, "click"); action = "click"
        else:
            raise HandsError(f"{r} '{_label(el, r)}' cannot be pressed (actions: {', '.join(x[2:] for x in acts) or 'none'}); try perform with one of those, or click its frame")
    else:
        perform(el, action)
    lab = _label(el, r); log(f"{action[2:] if action.startswith('AX') else action} {r} '{lab}' in {a['name']}")
    return {"ok": True, "did": f"{action[2:].lower() if action.startswith('AX') else action}ed {r} '{lab}' in {a['name']}", "id": REG.id(el), "now": readback(el, r, a)}


def set_value(a, target, value):
    el = REG.el(target) if re.fullmatch(r"e\d+", str(target).strip()) else pick(a, target, "")[0]
    r = _s(_get(el, "AXRole")[0])
    if is_secret(el):
        raise HandsError("that is a password field; the agent never writes secrets")
    if r in ("AXCheckBox", "AXRadioButton", "AXSwitch", "AXToggle", "AXPopUpButton"):
        g = guard(el, r, f"set {_label(el, r)!r} in {a['name']}")
        if g: return g
    e, ok = AXUIElementIsAttributeSettable(el, "AXValue", None)
    if e or not ok:
        raise HandsError(f"{r} '{_label(el, r)}' does not take a value here; focus it and use type, or press it")
    v = value
    if r in ("AXCheckBox", "AXRadioButton", "AXSwitch", "AXToggle") and str(value).lower() in ("on", "off", "true", "false", "1", "0"):
        v = 1 if str(value).lower() in ("on", "true", "1") else 0
    elif r in ("AXSlider", "AXIncrementor") and re.fullmatch(r"-?\d+(\.\d+)?", str(value)):
        v = float(value)
    e = AXUIElementSetAttributeValue(el, "AXValue", v)
    if e:
        raise HandsError(f"could not set it: {ERRORS.get(e, e)}")
    log(f"set {r} '{_label(el, r)}' in {a['name']} = {_s(value, 60)!r}")
    return {"ok": True, "did": f"set {r} '{_label(el, r)}'", "id": REG.id(el), "now": readback(el, r, a)}


def menu(a, path=""):
    el = app_element(a); bar, e = _get(el, "AXMenuBar")
    if bar is None:
        raise HandsError(f"{a['name']} has no menu bar ({ERRORS.get(e, e)})")
    def items(container):
        out = []
        for it in (_get(container, "AXChildren")[0] or []):
            r = _s(_get(it, "AXRole")[0]); t = _s(_get(it, "AXTitle")[0], 120)
            if r == "AXMenu":                                          # a menu's children are its items; look through it
                out += items(it); continue
            if not t.strip(): continue                                 # separators
            out.append((it, r, t))
        return out
    def shortcut(it):
        ch = _s(_get(it, "AXMenuItemCmdChar")[0]); mods = _get(it, "AXMenuItemCmdModifiers")[0]
        if not ch: return ""
        m = int(mods or 0); s = ("^" if m & 4 else "") + ("⌥" if m & 2 else "") + ("⇧" if m & 1 else "") + ("" if m & 8 else "⌘")
        return s + ch
    node = bar; trail = []
    parts = [p.strip() for p in re.split(r"\s*>\s*", path) if p.strip()] if path else []
    for i, part in enumerate(parts):
        cands = items(node); pl = part.lower().rstrip("…").rstrip(".")
        hit = next((c for c in cands if c[2].lower().rstrip("…").rstrip(".") == pl), None) or next((c for c in cands if c[2].lower().startswith(pl)), None) \
            or next((c for c in cands if pl in c[2].lower()), None)
        if not hit:
            raise HandsError(f"no menu item {part!r} under {' > '.join(trail) or 'the menu bar'} (items: {', '.join(c[2] for c in cands)[:400]})")
        node = hit[0]; trail.append(hit[2])
        sub = [k for k in (_get(node, "AXChildren")[0] or []) if _s(_get(k, "AXRole")[0]) == "AXMenu"]
        if i == len(parts) - 1 and not sub:                            # a leaf: press it
            if _get(node, "AXEnabled")[0] is False:
                raise HandsError(f"{' > '.join(trail)} is disabled right now")
            g = guard(node, "AXMenuItem", f"menu {' > '.join(trail)} in {a['name']}")
            if g: return g
            perform(node, "AXPress"); log(f"menu {' > '.join(trail)} in {a['name']}")
            return {"ok": True, "did": f"chose {' > '.join(trail)} in {a['name']}", "now": readback(node, "AXMenuItem", a)}
    lines = []
    for it, r, t in items(node):
        mark = "✓ " if _s(_get(it, "AXMenuItemMarkChar")[0]) else ""
        dis = "" if _get(it, "AXEnabled")[0] is not False else "  (disabled)"
        has_sub = any(_s(_get(k, "AXRole")[0]) == "AXMenu" for k in (_get(it, "AXChildren")[0] or []))
        sc = shortcut(it)
        lines.append(f"{mark}{t}{' ▸' if has_sub else ''}{('  ' + sc) if sc else ''}{dis}")
    return {"ok": True, "menu": " > ".join(trail) or "menu bar", "items": lines}


def focused_element():
    el, e = _get(AXUIElementCreateSystemWide(), "AXFocusedUIElement")
    return el


def type_text(text):
    if not text:
        raise HandsError("nothing to type")
    el = focused_element(); where = ""
    if el is not None:
        r = _s(_get(el, "AXRole")[0]); where = f"{r} '{_label(el, r)}'"
        if is_secret(el):
            raise HandsError("the focused field is a password field; the agent never types secrets")
    if "\n" in text or "\r" in text:
        g = key_guard("return", f"type text with a line break into {where or 'the focused app'}")
        if g: return g
    if el is not None:
        e, ok = AXUIElementIsAttributeSettable(el, "AXSelectedText", None)
        if e == 0 and ok and AXUIElementSetAttributeValue(el, "AXSelectedText", text) == 0:
            log(f"type {len(text)} chars into {where} (accessibility)")
            return {"ok": True, "did": f"inserted {len(text)} characters into {where}", "how": "accessibility", "now": readback(el, r)}
    _keystrokes(text); log(f"type {len(text)} chars into {where or 'the focused app'} (keystrokes)")
    out = {"ok": True, "did": f"typed {len(text)} characters into {where or 'the focused app'}", "how": "keystrokes"}
    if el is not None: out["now"] = readback(el, r)
    return out


def _keystrokes(text):
    for i in range(0, len(text), 20):
        chunk = text[i:i + 20]
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(None, 0, down)
            Quartz.CGEventKeyboardSetUnicodeString(ev, len(chunk), chunk)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.02)


def key(combo):
    k = combo.lower().strip().replace("option", "alt").replace("command", "cmd").replace("control", "ctrl").replace("opt+", "alt+").replace(" ", "")
    if k in BLOCKED_KEYS:
        log(f"key {k}: BLOCKED"); raise HandsError(f"{k} is a destructive shortcut; refused")
    parts = k.split("+"); name = parts[-1]; mods = parts[:-1]
    if name not in KEYS:
        raise HandsError(f"unknown key {name!r}; known: return, tab, esc, space, delete, arrows, home, end, f1-f12, letters, digits")
    bad = [m for m in mods if m not in FLAGS]
    if bad:
        raise HandsError(f"unknown modifier {bad[0]!r}; use cmd, shift, alt, ctrl")
    if not mods and name in ("return", "enter", "space"):
        g = key_guard(name, f"key {k}")
        if g: return g
    flags = 0
    for m in mods: flags |= FLAGS[m]
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, KEYS[name], down)
        if flags: Quartz.CGEventSetFlags(ev, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    time.sleep(0.03); log(f"key {k}")
    return {"ok": True, "did": f"pressed {k}"}


def screen_scale():
    """Points per screenshot pixel: look-screen.sh scales the long side of the main display to 1600 px."""
    f = AppKit.NSScreen.mainScreen().frame().size
    return {"points": {"w": int(f.width), "h": int(f.height)}, "factor": round(max(f.width, f.height) / SCREENSHOT_MAX, 4)}


def click(x, y, kind="click", space="points"):
    if space == "screenshot":
        k = screen_scale()["factor"]; x, y = x * k, y * k
    x, y = float(x), float(y)
    e, el = AXUIElementCopyElementAtPosition(AXUIElementCreateSystemWide(), x, y, None)
    label = ""
    if e == 0 and el is not None:
        r = _s(_get(el, "AXRole")[0]); label = f"{r} '{_label(el, r)}'"
        g = guard(el, r, f"{kind} at {int(x)},{int(y)}")
        if g: return g
    _click_at(x, y, kind)
    log(f"{kind} at {int(x)},{int(y)} on {label or '?'}")
    return {"ok": True, "did": f"{kind}ed at {int(x)},{int(y)}" + (f" on {label}" if label else ""), "points": [int(x), int(y)]}


def _click_at(x, y, kind="click"):
    """The pointer itself, in screen points; the guards live in the callers."""
    types = {"click": (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft),
             "double": (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp, Quartz.kCGMouseButtonLeft),
             "right": (Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp, Quartz.kCGMouseButtonRight)}
    if kind not in types:
        raise HandsError("kind must be click, double or right")
    down, up, button = types[kind]
    mv = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, (x, y), button); Quartz.CGEventPost(Quartz.kCGHIDEventTap, mv); time.sleep(0.03)
    for n in (1, 2) if kind == "double" else (1,):
        for t in (down, up):
            ev = Quartz.CGEventCreateMouseEvent(None, t, (x, y), button)
            if n == 2: Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, 2)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.05)


def wait_for(a, text, role="", timeout=10.0):
    t0 = time.time()
    while True:
        try:
            hits = find(a, text, role, limit=1)
        except HandsError:
            hits = []
        if hits:
            el, r = hits[0]
            return {"ok": True, "found": node_line(el, 0, r), "after_s": round(time.time() - t0, 2)}
        if time.time() - t0 > timeout:
            raise HandsError(f"{text!r} did not appear in {a['name']} within {timeout}s")
        time.sleep(0.15)


def focus(a):
    app = a["_app"]; app.activateWithOptions_(1 << 1)                 # NSApplicationActivateIgnoringOtherApps
    for _ in range(20):
        time.sleep(0.05)
        if app.isActive(): break
    log(f"focus {a['name']}: {app.isActive()}")
    return {"ok": bool(app.isActive()), "did": f"{a['name']} is in front" if app.isActive() else f"{a['name']} did not come to the front", "front_window": (windows(a) or [{}])[0].get("title", "")}


def app_path(name):
    """The .app for a name or bundle id, without launching anything."""
    ws = AppKit.NSWorkspace.sharedWorkspace()
    if "." in name and " " not in name:
        u = ws.URLForApplicationWithBundleIdentifier_(name)
        if u: return str(u.path())
    nl = name.lower().rstrip(".app") if name.lower().endswith(".app") else name.lower()
    dirs = ["/Applications", str(Path.home() / "Applications"), "/System/Applications", "/System/Applications/Utilities", "/System/Library/CoreServices/Applications"]
    exact, partial = [], []
    for d in dirs:
        for p in glob.glob(os.path.join(d, "*.app")):
            b = os.path.basename(p)[:-4].lower()
            (exact if b == nl else partial if nl in b else []).append(p)
    if exact: return exact[0]
    if len(partial) == 1: return partial[0]
    if partial: raise HandsError(f"{name!r} matches several apps: {', '.join(os.path.basename(p)[:-4] for p in partial)}")
    return None


def launch(name, wait_s=10.0):
    try:
        a = resolve(name)
        return {"ok": True, "did": f"{a['name']} is already running", **focus(a)}
    except HandsError:
        pass
    p = app_path(name)
    if not p:
        raise HandsError(f"no app called {name!r} in the Applications folders")
    r = subprocess.run(["open", "-a", p], capture_output=True, text=True, timeout=15)
    if r.returncode:
        raise HandsError(f"open failed: {(r.stderr or r.stdout).strip()}")
    t0 = time.time(); a = None
    while time.time() - t0 < wait_s:
        time.sleep(0.25)
        try:
            a = resolve(os.path.basename(p)[:-4]); break
        except HandsError:
            continue
    if not a:
        raise HandsError(f"{os.path.basename(p)} did not start within {wait_s}s")
    while time.time() - t0 < wait_s:                                   # and a window, so the next call has something to look at
        try:
            if windows(a): break
        except HandsError:
            pass
        time.sleep(0.25)
    log(f"launch {a['name']} ({round(time.time() - t0, 2)}s)")
    ws = windows(a) if a else []
    return {"ok": True, "did": f"launched {a['name']}", "after_s": round(time.time() - t0, 2), "front_window": ws[0]["title"] if ws else "", "windows": len(ws)}


def doctor():
    t = time.time(); apps = running(); w = None
    try:
        w = windows(apps[0]) if apps else None
    except HandsError:
        pass
    return {"ok": trusted(), "accessibility_trusted": trusted(), "front": apps[0]["name"] if apps else None, "gui_apps": len(apps),
            "front_windows": len(w or []), "ms": round((time.time() - t) * 1000), "log": str(LOGF), "screen": screen_scale()}


# ---- text for the model and the terminal ------------------------------------------------------------------------
def apps_text():
    return "\n".join(f"{'▶' if a['active'] else ' '} {a['name']}  ({a['bundle']}, pid {a['pid']}{', hidden' if a['hidden'] else ''})" for a in running())


def windows_text(a):
    ws = windows(a)
    if not ws: return f"{a['name']} has no windows"
    return "\n".join(f"{w['id']} {json.dumps(w['title'])}{' focused' if w['focused'] else ''}{' main' if w['main'] else ''}{' minimized' if w['minimized'] else ''}"
                     + (f" @{w['frame']['x']},{w['frame']['y']} {w['frame']['w']}x{w['frame']['h']}" if w['frame'] else "") for w in ws)


def inspect_text(a, window=None, depth=8, all_elements=False, max_lines=400):
    root = REG.el(window) if window else front_window(a)
    lines = walk(root, depth=depth, all_elements=all_elements)
    head = f"{a['name']} — {json.dumps(_s(_get(root, 'AXTitle')[0], 120))} ({len(lines)} elements shown; ids are for read/press/set/perform)"
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"… {len(lines) - max_lines} more lines; use find, or inspect with a smaller depth"]
    return head + "\n" + "\n".join(lines)


def find_text(a, text="", role="", limit=25):
    hits = find(a, text, role, limit)
    if not hits: return f"nothing matching {text!r}{' of role ' + norm_role(role) if role else ''} in {a['name']}'s windows"
    return "\n".join(node_line(el, 0, r) for el, r in hits)


def _out(obj):
    if isinstance(obj, str): print(obj)
    else: print(json.dumps(obj, ensure_ascii=False))


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__); return 0
    cmd, a = argv[0], argv[1:]
    flags = {x for x in a if x.startswith("--")}; opt = {}
    rest = []
    i = 0
    while i < len(a):
        if a[i] in ("--depth", "--role", "--timeout") and i + 1 < len(a): opt[a[i][2:]] = a[i + 1]; i += 2; continue
        if a[i].startswith("--"): i += 1; continue
        rest.append(a[i]); i += 1
    try:
        if cmd == "doctor": _out(doctor())
        elif cmd == "apps": print(apps_text())
        elif cmd == "launch": _out(launch(rest[0]))
        elif cmd == "focus": _out(focus(resolve(rest[0])))
        elif cmd == "windows": print(windows_text(resolve(rest[0] if rest else "front")))
        elif cmd == "inspect": print(inspect_text(resolve(rest[0] if rest else "front"), window=rest[1] if len(rest) > 1 else None, depth=int(opt.get("depth", 8)), all_elements="--all" in flags))
        elif cmd == "find": print(find_text(resolve(rest[0]), " ".join(rest[1:]), opt.get("role", "")))
        elif cmd == "read": _out(describe(REG.el(rest[0])))
        elif cmd == "press": _out(press(resolve(rest[0]), " ".join(rest[1:]), opt.get("role", "")))
        elif cmd == "set": _out(set_value(resolve(rest[0]), rest[1], " ".join(rest[2:])))
        elif cmd == "perform": _out(perform_checked(REG.el(rest[0]), rest[1]))
        elif cmd == "key-check":                                    # for cursor.py: would this bare key press something risky?
            el, r = _what_key_presses(rest[0] if rest else "return")
            fr = (_frame(el) or {}) if el is not None else {}
            _out({"ok": True, "role": r, "label": _label(el, r) if el is not None else "", "risky": bool(el is not None and RISKY.search(_label(el, r) or "")),
                  "x": int(fr.get("x", 0) + fr.get("w", 0) / 2), "y": int(fr.get("y", 0) + fr.get("h", 0) / 2)})
        elif cmd == "menu": _out(menu(resolve(rest[0]), " ".join(rest[1:])))
        elif cmd == "type": _out(type_text(" ".join(rest)))
        elif cmd == "key": _out(key(rest[0]))
        elif cmd == "click": _out(click(float(rest[0]), float(rest[1]), "double" if "--double" in flags else "right" if "--right" in flags else "click", "screenshot" if "--screenshot" in flags else "points"))
        elif cmd == "wait": _out(wait_for(resolve(rest[0]), " ".join(rest[1:]), opt.get("role", ""), float(opt.get("timeout", 10))))
        elif cmd == "scale": _out(screen_scale())
        else: print(__doc__); return 1
        return 0
    except HandsError as e:
        _out({"ok": False, "error": str(e)}); return 1
    except (IndexError, ValueError):
        print(__doc__); return 1


if __name__ == "__main__":
    if not trusted():
        _out({"ok": False, "error": "the accessibility API is not available to this process: System Settings > Privacy & Security > Accessibility, for the app that launched the agent (Terminal)"}); sys.exit(1)
    sys.exit(main(sys.argv[1:]))
