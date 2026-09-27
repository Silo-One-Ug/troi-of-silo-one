#!/usr/bin/env python3
"""The devices around the Mac (Silo One, 2026-09-27): displays, sound in and out, Bluetooth, USB, printers.

  devices.py list                 everything below, in one look
  devices.py audio                the sound devices, and which are the defaults for output and input
  devices.py out "<name>"         the default output to a device by name (the owner's word: "play through my AirPods")
  devices.py in "<name>"          the default input (the microphone)
  devices.py bluetooth            what is connected, with battery levels when the device tells them
  devices.py fix-sound [--go]     the diagnosis of "my AirPods are connected but the sound isn't coming through them": what the
                                  output is, what it could be; --go routes it (the owner's word)
  devices.py displays | usb | printers

Sound through CoreAudio directly (ctypes, no extra Python); the rest through system_profiler and lpstat. Reading changes
nothing; only `out`, `in` and `fix-sound --go` change anything, and only the sound's route. Stdlib only.
"""
import ctypes
import json
import struct
import subprocess
import sys
from ctypes import POINTER, byref, c_char_p, c_long, c_uint32, c_void_p, create_string_buffer

ca = ctypes.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")


class Addr(ctypes.Structure):
    _fields_ = [("sel", c_uint32), ("scope", c_uint32), ("elem", c_uint32)]


ca.AudioObjectGetPropertyDataSize.argtypes = [c_uint32, POINTER(Addr), c_uint32, c_void_p, POINTER(c_uint32)]
ca.AudioObjectGetPropertyData.argtypes = [c_uint32, POINTER(Addr), c_uint32, c_void_p, POINTER(c_uint32), c_void_p]
ca.AudioObjectSetPropertyData.argtypes = [c_uint32, POINTER(Addr), c_uint32, c_void_p, c_uint32, c_void_p]
cf.CFStringGetCString.argtypes = [c_void_p, c_char_p, c_long, c_uint32]
cf.CFRelease.argtypes = [c_void_p]


def fcc(s):
    return int.from_bytes(s.encode(), "big")


SYS, GLOBAL, INPUT, OUTPUT = 1, fcc("glob"), fcc("inpt"), fcc("outp")
K_DEVICES, K_OUT, K_IN, K_NAME, K_UID, K_TRAN, K_STREAMS = fcc("dev#"), fcc("dOut"), fcc("dIn "), fcc("lnam"), fcc("uid "), fcc("tran"), fcc("stm#")
TRANSPORT = {"bltn": "built in", "blue": "Bluetooth", "bthl": "Bluetooth", "usb ": "USB", "aggr": "aggregate", "vrtl": "virtual", "airp": "AirPlay", "cont": "Continuity", "hdmi": "HDMI", "dprt": "DisplayPort", "thun": "Thunderbolt", "pci ": "PCI"}


def get(obj, sel, scope=GLOBAL):
    addr = Addr(sel, scope, 0); size = c_uint32(0)
    if ca.AudioObjectGetPropertyDataSize(obj, byref(addr), 0, None, byref(size)) != 0 or size.value == 0:
        return b""
    buf = create_string_buffer(size.value)
    if ca.AudioObjectGetPropertyData(obj, byref(addr), 0, None, byref(size), buf) != 0:
        return b""
    return buf.raw[:size.value]


def cfstr(raw):
    if len(raw) < 8:
        return ""
    ptr = struct.unpack("Q", raw[:8])[0]
    if not ptr:
        return ""
    buf = create_string_buffer(1024)
    ok = cf.CFStringGetCString(ptr, buf, 1024, 0x08000100)
    cf.CFRelease(ptr)
    return buf.value.decode("utf-8", "replace") if ok else ""


def audio_devices():
    raw = get(SYS, K_DEVICES)
    ids = list(struct.unpack(f"{len(raw) // 4}I", raw)) if raw else []
    out_id = struct.unpack("I", get(SYS, K_OUT))[0] if get(SYS, K_OUT) else 0
    in_id = struct.unpack("I", get(SYS, K_IN))[0] if get(SYS, K_IN) else 0
    devs = []
    for d in ids:
        tr = get(d, K_TRAN); tr = struct.unpack("I", tr)[0].to_bytes(4, "big").decode("ascii", "replace") if len(tr) == 4 else ""
        devs.append({"id": d, "name": cfstr(get(d, K_NAME)), "uid": cfstr(get(d, K_UID)), "transport": TRANSPORT.get(tr, tr.strip()),
                     "output": len(get(d, K_STREAMS, OUTPUT)) >= 4, "input": len(get(d, K_STREAMS, INPUT)) >= 4, "default_out": d == out_id, "default_in": d == in_id})
    return devs


def set_default(sel, dev_id):
    addr = Addr(sel, GLOBAL, 0); v = c_uint32(dev_id)
    return ca.AudioObjectSetPropertyData(SYS, byref(addr), 0, None, 4, byref(v)) == 0


def find(devs, name, want):
    q = name.lower().strip()
    cands = [d for d in devs if d[want] and (d["name"].lower() == q or q in d["name"].lower())]
    exact = [d for d in cands if d["name"].lower() == q]
    return (exact or cands)[0] if cands else None


def profiler(kind):
    try:
        out = subprocess.run(["system_profiler", kind, "-json"], capture_output=True, text=True, timeout=40).stdout
        return json.loads(out).get(kind, [])
    except Exception:
        return []


def bluetooth():
    items = profiler("SPBluetoothDataType")
    d = items[0] if items else {}
    def rows(lst, connected):
        out = []
        for entry in lst or []:
            for name, info in (entry.items() if isinstance(entry, dict) else []):
                info = info or {}
                batt = {k.replace("device_batteryLevel", "").replace("device_battery", "").lower() or "battery": v for k, v in info.items() if "battery" in k.lower()}
                out.append({"name": name, "connected": connected, "kind": info.get("device_minorType") or info.get("device_minorClassOfDevice_string") or "", "battery": batt})
        return out
    return rows(d.get("device_connected"), True) + rows(d.get("device_not_connected"), False)


def displays():
    out = []
    for gpu in profiler("SPDisplaysDataType"):
        for disp in gpu.get("spdisplays_ndrvs", []) or []:
            out.append({"name": disp.get("_name", "display"), "resolution": disp.get("_spdisplays_pixels") or disp.get("_spdisplays_resolution", ""), "main": disp.get("spdisplays_main") == "spdisplays_yes", "connection": disp.get("spdisplays_connection_type", "")})
    return out


def usb():
    out = []
    def walk(items, depth=0):
        for it in items or []:
            name = it.get("_name", "")
            if name and depth > 0 and not re.search(r"hub", name, re.I):
                out.append({"name": name, "vendor": it.get("manufacturer", "")})
            walk(it.get("_items"), depth + 1)
    walk(profiler("SPUSBDataType"))
    return out


def printers():
    try:
        out = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        out = ""
    return [{"name": m.group(1), "state": m.group(2)} for m in re.finditer(r"^printer (\S+) is (\w+)", out, re.M)]


def cmd_audio():
    devs = audio_devices()
    for d in devs:
        if not (d["output"] or d["input"]):
            continue
        tags = [t for t, on in (("output", d["output"]), ("input", d["input"])) if on]
        mark = "  <- output" if d["default_out"] else ""
        mark += "  <- input" if d["default_in"] else ""
        print(f"  {d['name']:<36} {d['transport']:<11} {'/'.join(tags):<12}{mark}")
    return 0


def cmd_route(which, name):
    devs = audio_devices(); want = "output" if which == "out" else "input"
    d = find(devs, name, want)
    if not d:
        print(f"no {want} device called {name}; devices.py audio lists them"); return 2
    if (d["default_out"] if which == "out" else d["default_in"]):
        print(f"{d['name']} is the {want} already"); return 0
    ok = set_default(K_OUT if which == "out" else K_IN, d["id"])
    print(f"the {want} is {d['name']} now" if ok else f"CoreAudio refused to make {d['name']} the {want}"); return 0 if ok else 1


def cmd_fix_sound(go):
    devs = audio_devices(); cur = next((d for d in devs if d["default_out"]), None)
    bt = [d for d in devs if d["output"] and d["transport"] == "Bluetooth"]
    print(f"the sound goes to: {cur['name'] if cur else 'nothing'} ({cur['transport'] if cur else ''})")
    if not bt:
        print("no Bluetooth speaker or headphones are connected as an audio device; if the AirPods are in the ears, they have not connected: Bluetooth in the menu bar, or the case open beside the Mac")
        return 0
    other = [d for d in bt if not d["default_out"]]
    if not other:
        print(f"the Bluetooth device ({bt[0]['name']}) is already the output; if there is still no sound: the volume on the device, or the app playing to a fixed device")
        return 0
    print(f"connected but not the output: {', '.join(d['name'] for d in other)}")
    if go:
        return cmd_route("out", other[0]["name"])
    print(f"devices.py out \"{other[0]['name']}\" routes the sound there (fix-sound --go does the same)"); return 0


def cmd_list():
    print("displays"); [print(f"  {d['name']}  {d['resolution']}{'  (main)' if d['main'] else ''}") for d in displays()]
    print("sound"); cmd_audio()
    print("bluetooth"); bts = bluetooth()
    for b in bts:
        if b["connected"]:
            print(f"  {b['name']:<30} connected {b['kind']}" + (("  battery " + ", ".join(f"{k} {v}" for k, v in b["battery"].items())) if b["battery"] else ""))
    off = [b["name"] for b in bts if not b["connected"]]
    if off:
        print("  paired, not connected: " + ", ".join(off[:8]) + (f" and {len(off) - 8} more" if len(off) > 8 else ""))
    print("usb"); us = usb(); [print(f"  {u['name']}" + (f"  ({u['vendor']})" if u["vendor"] else "")) for u in us[:12]] if us else print("  nothing beyond the hubs")
    print("printers"); ps = printers(); [print(f"  {p['name']}  {p['state']}") for p in ps] if ps else print("  none set up")
    return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "list":
        return cmd_list()
    if a[0] == "audio":
        return cmd_audio()
    if a[0] in ("out", "in") and len(a) > 1:
        return cmd_route(a[0], " ".join(a[1:]))
    if a[0] == "bluetooth":
        for b in bluetooth():
            print(f"  {b['name']:<30} {'connected' if b['connected'] else 'not connected'} {b['kind']}" + (("  battery " + ", ".join(f"{k} {v}" for k, v in b["battery"].items())) if b["battery"] else ""))
        return 0
    if a[0] == "fix-sound":
        return cmd_fix_sound("--go" in a)
    if a[0] == "displays":
        for d in displays():
            print(f"  {d['name']}  {d['resolution']}{'  (main)' if d['main'] else ''}  {d['connection']}")
        return 0
    if a[0] == "usb":
        for u in usb():
            print(f"  {u['name']}" + (f"  ({u['vendor']})" if u["vendor"] else ""))
        return 0
    if a[0] == "printers":
        for p in printers():
            print(f"  {p['name']}  {p['state']}")
        return 0
    print("devices.py list | audio | out <name> | in <name> | bluetooth | fix-sound [--go] | displays | usb | printers"); return 2


import re  # noqa: E402  (used by usb and printers)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
