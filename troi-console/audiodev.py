#!/usr/bin/env python3
"""audiodev: list CoreAudio devices, or create the two meeting devices (aggregate input, multi-output).
   python audiodev.py list
   python audiodev.py create <mic-uid> <blackhole-uid> <output-uid>
Runs with a PyObjC-enabled Python (the ring's .venv-ring)."""
import ctypes, sys
import objc
from Foundation import NSDictionary

ca = ctypes.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
cf.CFRelease.argtypes = [ctypes.c_void_p]


class Addr(ctypes.Structure):
    _fields_ = [("sel", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("elem", ctypes.c_uint32)]


def fcc(s): return int.from_bytes(s.encode(), "big")


SYS, GLOBAL, INPUT, OUTPUT = 1, fcc("glob"), fcc("inpt"), fcc("outp")
kDevices, kDefaultOut, kUID, kName, kStreamCfg = fcc("dev#"), fcc("dOut"), fcc("uid "), fcc("lnam"), fcc("slay")


def get(obj, sel, scope=GLOBAL):
    a = Addr(sel, scope, 0); size = ctypes.c_uint32(0)
    if ca.AudioObjectGetPropertyDataSize(obj, ctypes.byref(a), 0, None, ctypes.byref(size)) != 0 or size.value == 0:
        return None
    buf = ctypes.create_string_buffer(size.value)
    if ca.AudioObjectGetPropertyData(obj, ctypes.byref(a), 0, None, ctypes.byref(size), buf) != 0:
        return None
    return buf.raw


def cfstr(obj, sel):
    raw = get(obj, sel)
    if not raw: return "?"
    ref = ctypes.c_void_p.from_buffer_copy(raw).value
    out = ctypes.create_string_buffer(512); cf.CFStringGetCString(ref, out, 512, 0x08000100); cf.CFRelease(ref)
    return out.value.decode("utf-8", "replace")


def channels(obj, scope):
    raw = get(obj, kStreamCfg, scope)
    if not raw: return 0
    n = int.from_bytes(raw[:4], "little"); total = 0
    for i in range(n):                       # AudioBuffer: uint32 channels, uint32 bytes, void* data (16 bytes with padding)
        off = 8 + i * 16; total += int.from_bytes(raw[off:off + 4], "little")
    return total


def devices():
    raw = get(SYS, kDevices) or b""
    return [int.from_bytes(raw[i:i + 4], "little") for i in range(0, len(raw), 4)]


def default_output_uid():
    raw = get(SYS, kDefaultOut); return cfstr(int.from_bytes(raw[:4], "little"), kUID) if raw else "?"


def create(name, uid, subs, main, stacked):
    if any(cfstr(d, kUID) == uid for d in devices()): return f"exists: {name}"
    desc = NSDictionary.dictionaryWithDictionary_({
        "name": name, "uid": uid, "subdevices": [{"uid": s} for s in subs], "master": main, "stacked": 1 if stacked else 0})
    new_id = ctypes.c_uint32(0)
    r = ca.AudioHardwareCreateAggregateDevice(ctypes.c_void_p(objc.pyobjc_id(desc)), ctypes.byref(new_id))
    return f"created: {name} (id {new_id.value})" if r == 0 else f"FAILED {name}: OSStatus {r}"


a = sys.argv[1:]
if not a or a[0] == "list":
    print("default output uid:", default_output_uid())
    for d in devices():
        print(f"{cfstr(d, kUID):<42} in:{channels(d, INPUT)} out:{channels(d, OUTPUT)}  {cfstr(d, kName)}")
elif a[0] == "create" and len(a) == 4:
    mic, bh, out = a[1:]
    print(create("Meeting In", "cj-meeting-in", [mic, bh], mic, False))
    print(create("Meeting Out", "cj-meeting-out", [out, bh], out, True))
else:
    print(__doc__)
