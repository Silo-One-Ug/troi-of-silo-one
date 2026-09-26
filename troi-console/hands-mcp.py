#!/usr/bin/env python3
"""The native hands as MCP tools (stdio), one resident process per brain session: element handles, compiled
lookups and the Electron switch stay warm, so an action is one round trip. Listed in the repo's .mcp.json as
"hands"; the brain sees mcp__hands__<tool>. Everything returns text; errors come back as a line starting "no:"
so the model reads the reason instead of a stack trace. stdout is the transport: nothing here may print."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hands as H                                                    # noqa: E402
from mcp.server.mcpserver import MCPServer                           # noqa: E402

srv = MCPServer(name="hands", instructions=(
    "The Mac's apps, addressed by name through the accessibility tree. Use inspect or find to learn the names, then press, set, menu or type; "
    "the answer already contains what changed, so do not screenshot to check. Risky controls (delete, send, pay, quit…) are not pressed: the tool files an "
    "approval for the owner and says so. Passwords are never written. Prefer these over cursor.sh; use click only for what has no name."))


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


def _run(fn, *args, **kw):
    try:
        r = fn(*args, **kw)
        return r if isinstance(r, str) else _j(r)
    except H.HandsError as e:
        return "no: " + str(e)
    except Exception as e:                                             # a PyObjC or AX surprise: still a sentence, never a trace
        return f"no: {type(e).__name__}: {e}"


@srv.tool(name="apps", description="Running apps, front first (name, bundle id, pid). Use these names in the other tools; 'front' is the frontmost app.")
def apps() -> str:
    return _run(H.apps_text)


@srv.tool(name="launch", description="Open an app by name (or bundle id) and wait until it has a window; if it is already running it is brought to the front.")
def launch(app: str) -> str:
    return _run(H.launch, app)


@srv.tool(name="focus", description="Bring a running app to the front.")
def focus(app: str = "front") -> str:
    return _run(lambda: H.focus(H.resolve(app)))


@srv.tool(name="windows", description="An app's windows: id, title, focused/main/minimized, frame in points.")
def windows(app: str = "front") -> str:
    return _run(lambda: H.windows_text(H.resolve(app)))


@srv.tool(name="inspect", description="The interface of an app's front window (or a window id) as an indented tree: id, role, label, value, state, actions, frame. "
                                     "Interactive elements and structure by default; all_elements for everything. The ids feed read, press, set and perform.")
def inspect(app: str = "front", window: str = "", depth: int = 8, all_elements: bool = False, max_lines: int = 400) -> str:
    return _run(lambda: H.inspect_text(H.resolve(app), window or None, depth, all_elements, max_lines))


@srv.tool(name="find", description="Elements in an app's windows whose title, description, value, placeholder or identifier contain the text (case-insensitive), "
                                  "optionally of one role (button, field, checkbox, row, link, menuitem…). Best match first.")
def find(app: str, text: str = "", role: str = "", limit: int = 25) -> str:
    return _run(lambda: H.find_text(H.resolve(app), text, role, limit))


@srv.tool(name="read", description="Everything about one element by id: role, label, value, enabled/focused/selected, actions, frame, window, attributes.")
def read(id: str) -> str:
    return _run(lambda: H.describe(H.REG.el(id)))


@srv.tool(name="press", description="Press the control called text in the app (a button, tab, checkbox, row, link, menu button…): finds it by label, presses it, "
                                   "and returns its state and the front window afterwards. Risky labels are filed for the owner's approval instead.")
def press(app: str, text: str, role: str = "") -> str:
    return _run(lambda: H.press(H.resolve(app), text, role))


@srv.tool(name="set", description="Put a value into a field, checkbox, slider or pop-up: target is an element id or its label; the new value is read back. "
                                 "Password fields are refused.")
def set_value(app: str, target: str, value: str) -> str:
    return _run(lambda: H.set_value(H.resolve(app), target, value))


@srv.tool(name="perform", description="Any action an element offers (see read): Press, Confirm, Cancel, ShowMenu, Increment, Decrement, Raise, Pick.")
def perform(id: str, action: str) -> str:
    return _run(lambda: H.perform_checked(H.REG.el(id), action))


@srv.tool(name="menu", description="The app's menus. With no path: the menu bar titles. With 'File' or 'View > Sort By': the items there (✓ marks, shortcuts, disabled). "
                                  "With a full path to an item, e.g. 'File > Export as PDF…': chooses it. Works in every app, Electron included.")
def menu(app: str = "front", path: str = "") -> str:
    return _run(lambda: H.menu(H.resolve(app), path))


@srv.tool(name="type", description="Insert text at the focused field: through the accessibility API when the field allows it, else as keystrokes. "
                                  "Refuses password fields. Focus the field first (press it, or set its value directly).")
def type_text(text: str) -> str:
    return _run(H.type_text, text)


@srv.tool(name="key", description="One keystroke: return, tab, esc, space, delete, up/down/left/right, home, end, f1-f12, a letter or digit, with cmd/shift/alt/ctrl, e.g. 'cmd+s'. "
                                 "Destructive shortcuts (cmd+q, cmd+w, cmd+delete…) are refused. A bare return/enter is checked against what it would press "
                                 "(a risky default button is filed for approval) and refused when the front app shows nothing to check; press the button by name instead.")
def key(combo: str) -> str:
    return _run(H.key, combo)


@srv.tool(name="click", description="The pointer, for what has no name: click/double/right at x,y in screen points. With space='share' the numbers are pixels of the frame the owner is sharing (share.sh), mapped onto the shared window or display. With space='screenshot' the numbers are pixels of a "
                                   "look-screen.sh screenshot and are converted. The element under the point is checked for risky labels first.")
def click(x: float, y: float, kind: str = "click", space: str = "points") -> str:
    return _run(H.click, x, y, kind, space)


@srv.tool(name="wait", description="Wait until an element with this text (and optional role) appears in the app — a sheet's button, a window title, a status — up to timeout seconds.")
def wait(app: str, text: str, role: str = "", timeout: float = 10.0) -> str:
    return _run(lambda: H.wait_for(H.resolve(app), text, role, timeout))


@srv.tool(name="doctor", description="Is the accessibility API available to this process, what is in front, and how fast a look is.")
def doctor() -> str:
    return _run(H.doctor)


if __name__ == "__main__":
    srv.run("stdio")
