#!/usr/bin/env python3
"""grafana.py: Grafana, read-only, through its HTTP API with the TROI service account (a Viewer). Stdlib only.

  grafana.py check                                   the connection: version, the account, the org, the data sources it can see
  grafana.py alerts [--all] [--json]                 the alerts firing now (pending too with --all), grouped by rule: labels, values, since when
  grafana.py rules [--json]                          every alert rule, its state and health
  grafana.py silences                                the silences in force
  grafana.py query '<PromQL>' [--range 1h] [--step 60] [--ds NAME|UID] [--show] [--title "..."]   numbers from Prometheus: a table, or a chart on the board
  grafana.py logs '<LogQL>' [--since 15m] [--limit 100] [--ds NAME|UID]                          lines from Loki
  grafana.py dashboards [words]                      the dashboards (uid, title, folder)
  grafana.py panel <dashboard uid> <panel id> [--range 6h] [--show] [--title "..."]               a panel as a picture (the image renderer) or its numbers redrawn
  grafana.py watch                                   one pass of the alert watch (the pulse runs it every minute): what began FIRING and what RESOLVED

The address, the time zone and the data sources live in data/grafana.json; the token is the Keychain item `grafana`
(the Keys card in Modes, or `keychain.py set grafana`). Everything here reads. A silence, an annotation or a rule change
is not this tool's to make: propose it to the owner.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import keychain as KC  # noqa: E402

HERE = Path(__file__).resolve().parent
CFG_PATH = P.DATA / "grafana.json"
WATCH = P.CACHE / "grafana-watch.json"
UA = {"User-Agent": "Troi/1.0 (read-only; grafana.py)", "Accept": "application/json"}
DEFAULTS = {"url": "https://grafana.commuza.com", "org": 1, "tz": "Africa/Kampala", "datasources": {}, "watch": {"every": 60, "pending": False}}
PNG = b"\x89PNG\r\n\x1a\n"


class GrafanaError(Exception):
    pass


def cfg():
    c = dict(DEFAULTS)
    try:
        c.update(json.loads(CFG_PATH.read_text()))
    except Exception:
        pass
    return c


def save_cfg(c):
    try:
        CFG_PATH.write_text(json.dumps(c, indent=2) + "\n")
    except OSError:
        pass


def token():
    return KC.get("grafana")


def api(path, method="GET", body=None, raw=False, auth=True, timeout=25):
    """One call. JSON in and out, or the raw bytes (a rendered panel). Plain words for what went wrong."""
    url = cfg()["url"].rstrip("/") + path
    headers = dict(UA)
    if auth:
        t = token()
        if not t:
            raise GrafanaError("no Grafana token in the Keychain yet: paste it in the Keys card in Modes, or run troi-console/keychain.py set grafana")
        headers["Authorization"] = "Bearer " + t
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    if raw:
        headers["Accept"] = "image/png,*/*"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
            return payload if raw else (json.loads(payload) if payload.strip() else None)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            raise GrafanaError("Grafana refused the token (401): it may have expired or been revoked")
        if e.code == 403:
            raise GrafanaError(f"the TROI account may not do that (403): {msg}")
        if e.code == 404:
            raise GrafanaError(f"not there (404): {path.split('?')[0]}")
        raise GrafanaError(f"Grafana said {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise GrafanaError(f"Grafana is not reachable: {e.reason}")
    except json.JSONDecodeError:
        raise GrafanaError("Grafana answered with something that is not JSON (a login page? the address may be wrong)")


# ---- time, labels, values
def local(ts):
    """An ISO time from Grafana, in the owner's zone, short."""
    if not ts:
        return "?"
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        try:
            from zoneinfo import ZoneInfo
            d = d.astimezone(ZoneInfo(cfg().get("tz") or "UTC"))
        except Exception:
            d = d.astimezone()
        return d.strftime("%b %d %H:%M")
    except Exception:
        return str(ts)[:16]


def where(labels):
    """The place an alert points at: node, then instance without its port, then job."""
    for k in ("node", "nodename", "host", "hostname", "instance", "pod", "container", "job"):
        v = labels.get(k)
        if v:
            return re.sub(r":\d+$", "", str(v))
    return ""


def values_of(s):
    """The numbers in Grafana's `[ var='A' labels={…} value=95.59 ]` strings."""
    return [float(x) for x in re.findall(r"value=([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", str(s or ""))]


def fmt_num(v):
    if v is None:
        return "?"
    return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.3g}"


# ---- the pieces
def health():
    return api("/api/health", auth=False)


def me():
    try:
        return api("/api/user")
    except GrafanaError:
        return None


def datasources(refresh=False):
    """The data sources the account can use: the list if it may read it, otherwise the ones the alert rules and dashboards name."""
    c = cfg()
    if c.get("datasources") and not refresh:
        return c["datasources"]
    found = {}
    try:
        for d in api("/api/datasources") or []:
            found[d["name"]] = {"uid": d["uid"], "type": d.get("type", ""), "default": bool(d.get("isDefault"))}
    except GrafanaError:
        try:                                            # a Viewer cannot list them: the alert rules say which ones they use
            rules = api("/api/ruler/grafana/api/v1/rules") or {}
            for groups in rules.values():
                for g in groups:
                    for r in g.get("rules", []):
                        for q in (r.get("grafana_alert") or {}).get("data", []):
                            uid = q.get("datasourceUid")
                            if uid and uid not in ("__expr__", "-100"):
                                typ = ((q.get("model") or {}).get("datasource") or {}).get("type", "")
                                found.setdefault(uid, {"uid": uid, "type": typ, "default": False})
        except GrafanaError:
            pass
        try:                                            # and the dashboards' panels
            for d in (api("/api/search?type=dash-db&limit=30") or [])[:30]:
                dash = (api(f"/api/dashboards/uid/{d['uid']}") or {}).get("dashboard") or {}
                for p in panels_of(dash):
                    ds = p.get("datasource")
                    if isinstance(ds, dict) and ds.get("uid") and not str(ds["uid"]).startswith("$"):
                        found.setdefault(ds["uid"], {"uid": ds["uid"], "type": ds.get("type", ""), "default": False})
        except GrafanaError:
            pass
    c["datasources"] = found
    save_cfg(c)
    return found


def resolve_ds(want, kind):
    """A data source by name or uid; else the default of that kind; else the only one of that kind."""
    ds = datasources()
    if want:
        for name, d in ds.items():
            if want in (name, d.get("uid")):
                return d["uid"], d.get("type") or kind
        return want, kind                                # a uid we have not seen: try it
    kinds = [d for d in ds.values() if (d.get("type") or "").lower() == kind]
    for d in kinds:
        if d.get("default"):
            return d["uid"], kind
    if kinds:
        return kinds[0]["uid"], kind
    if not ds:
        raise GrafanaError(f"no data sources known yet; grafana.py check first, or name one with --ds")
    raise GrafanaError(f"no {kind} data source known; name one with --ds (grafana.py check lists them)")


def panels_of(dash):
    out = []
    for p in dash.get("panels", []) or []:
        out.append(p)
        if p.get("type") == "row":
            out.extend(p.get("panels", []) or [])
    return out


def rule_groups():
    d = api("/api/prometheus/grafana/api/v1/rules") or {}
    return (d.get("data") or {}).get("groups", [])


ISSUE_STATES = {"Alerting": "FIRING", "NoData": "NO DATA", "Error": "ERROR", "Pending": "PENDING"}


def instances(include_pending=False):
    """Every alert instance that matters: firing, in error, without data (pending too when asked), with what it says."""
    out = []
    for g in rule_groups():
        for r in g.get("rules", []):
            if r.get("type") != "alerting":
                continue
            for a in r.get("alerts", []) or []:
                st = a.get("state", "")
                if st not in ISSUE_STATES or (st == "Pending" and not include_pending):
                    continue
                labels = {k: v for k, v in (a.get("labels") or {}).items() if k not in ("grafana_folder",)}
                ann = a.get("annotations") or {}
                vals = values_of(a.get("value"))
                out.append({"rule": r.get("name", "?"), "folder": g.get("file", ""), "state": ISSUE_STATES[st], "raw_state": st, "labels": labels,
                            "severity": labels.get("severity", ""), "where": where(labels), "summary": ann.get("summary") or ann.get("description") or "",
                            "description": ann.get("description", ""), "runbook": ann.get("runbook_url", ""), "value": vals[0] if vals else None,
                            "since": a.get("activeAt", ""), "key": r.get("name", "?") + "|" + json.dumps(sorted(labels.items()))})
    return out


def alerts(include_pending=False):
    lines = []
    items = instances(include_pending)
    if not items:
        return ["No alert is firing."]
    by_rule = {}
    for a in items:
        by_rule.setdefault(a["rule"], []).append(a)
    for rule, group in by_rule.items():
        head = group[0]
        lines.append(f"{head['state']}  {rule}" + (f" [{head['severity']}]" if head["severity"] else "") + (f"  ({head['folder']})" if head["folder"] else ""))
        if head["summary"]:
            lines.append("  " + head["summary"].strip().replace("\n", " ")[:220])
        for a in group:
            spot = a["where"] or ", ".join(f"{k}={v}" for k, v in list(a["labels"].items())[:3])
            lines.append(f"  - {spot}" + (f" · value {fmt_num(a['value'])}" if a["value"] is not None else "") + f" · since {local(a['since'])}")
    return lines


def rules():
    lines = []
    for g in rule_groups():
        for r in g.get("rules", []):
            if r.get("type") != "alerting":
                continue
            n = len(r.get("alerts", []) or [])
            firing = sum(1 for a in r.get("alerts", []) or [] if a.get("state") == "Alerting")
            lines.append(f"{(r.get('state') or '?'):9} {r.get('name', '?')}  ({g.get('file', '')}/{g.get('name', '')}, every {g.get('interval', '?')}s, health {r.get('health', '?')}"
                         + (f", {firing} firing of {n}" if n else "") + ")")
    return lines or ["No alert rules."]


def silences():
    out = []
    for s in api("/api/alertmanager/grafana/api/v2/silences") or []:
        if (s.get("status") or {}).get("state") != "active":
            continue
        m = ", ".join(f"{x.get('name')}{'=~' if x.get('isRegex') else '='}{x.get('value')}" for x in s.get("matchers", []))
        out.append(f"silence {s.get('id', '')[:8]}: {m} · by {s.get('createdBy', '?')} · until {local(s.get('endsAt'))}" + (f" · {s.get('comment')}" if s.get("comment") else ""))
    return out or ["No silence is in force."]


def ds_query(queries, rng_from, rng_to="now"):
    res = api("/api/ds/query", "POST", {"from": rng_from, "to": rng_to, "queries": queries}, timeout=60) or {}
    frames, errors = [], []
    for ref, r in (res.get("results") or {}).items():
        if r.get("error"):
            errors.append(f"{ref}: {r['error']}")
        frames.extend(r.get("frames") or [])
    if errors and not frames:
        raise GrafanaError("; ".join(errors))
    return frames


def series_of(frames):
    """Time series out of Grafana frames: name, times (ms), values."""
    out = []
    for f in frames:
        fields = (f.get("schema") or {}).get("fields") or []
        vals = (f.get("data") or {}).get("values") or []
        ti = next((i for i, fl in enumerate(fields) if fl.get("type") == "time"), None)
        for i, fl in enumerate(fields):
            if i == ti or fl.get("type") not in ("number",):
                continue
            labels = fl.get("labels") or {}
            out.append({"name": series_name(labels, fl), "t": vals[ti] if ti is not None and ti < len(vals) else [], "v": vals[i] if i < len(vals) else []})
    return out


def series_name(labels, field=None):
    """A short name for a series: the container or the instance when the labels say, else the labels that tell them apart."""
    cfgd = (field or {}).get("config") or {}
    if cfgd.get("displayName"):
        return str(cfgd["displayName"])[:80]
    if labels.get("name"):
        n = re.sub(r"\.\d+\.[a-z0-9]{20,}$", "", str(labels["name"]))      # a swarm task's suffix, off
        n = re.sub(r"^commuza[-_]", "", n)
        return n[:60] + (f" @ {labels['instance']}" if labels.get("instance") and "instance" not in n else "")
    skip = {"__name__", "job", "id", "image", "container_label_com_docker_swarm_task_id"}
    parts = [f"{k}={v}" for k, v in labels.items() if k not in skip]
    return (", ".join(parts) or cfgd.get("displayNameFromDS") or (field or {}).get("name") or "value")[:80]


def query(expr, rng="1h", step=None, ds=None, show=False, title=None):
    uid, typ = resolve_ds(ds, "prometheus")
    q = {"refId": "A", "datasource": {"uid": uid, "type": typ or "prometheus"}, "expr": expr, "range": True, "instant": False, "format": "time_series", "maxDataPoints": 300}
    if step:
        q["intervalMs"] = int(float(step) * 1000)
    ser = series_of(ds_query([q], f"now-{rng}"))
    if not ser:
        return ["No data for that query."]
    lines = [f"{'series':44} {'last':>10} {'min':>10} {'max':>10} {'avg':>10}"]
    for s in ser[:40]:
        nums = [v for v in s["v"] if isinstance(v, (int, float))]
        if not nums:
            continue
        lines.append(f"{s['name'][:44]:44} {fmt_num(nums[-1]):>10} {fmt_num(min(nums)):>10} {fmt_num(max(nums)):>10} {fmt_num(sum(nums) / len(nums)):>10}")
    if len(ser) > 40:
        lines.append(f"… and {len(ser) - 40} more series")
    if show:
        lines.append(show_chart(ser[:6], title or expr[:60], rng))
    return lines


def show_chart(ser, title, rng):
    """The series as a line chart on the board, through show.py."""
    if not ser or not ser[0]["t"]:
        return "nothing to draw"
    n = len(ser[0]["t"]); stride = max(1, n // 80)
    rows = []
    for i in range(0, n, stride):
        t = ser[0]["t"][i]
        row = {"t": datetime.fromtimestamp(t / 1000).strftime("%H:%M" if rng.endswith(("m", "h")) else "%d %H:%M")}
        for s in ser:
            v = s["v"][i] if i < len(s["v"]) else None
            if isinstance(v, (int, float)):
                row[s["name"]] = round(v, 3)
        rows.append(row)
    tree = {"type": "chart", "kind": "line", "x": "t", "series": [s["name"] for s in ser], "data": rows, "title": title, "dots": 0, "legend": len(ser) > 1}
    # a panel with this title that is already up is redrawn in place (a live view); otherwise a new tile flows in
    r = subprocess.run([sys.executable, str(HERE / "show.py"), "board", title[:60], "set", json.dumps(tree)], capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return f"redrawn on the board: \"{title[:60]}\""
    r = subprocess.run([sys.executable, str(HERE / "show.py"), json.dumps(tree), "--board", "--title", title[:60], "--w", "0.38"], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr).strip() or "sent to the board"


def logs(expr, since="15m", limit=100, ds=None):
    uid, typ = resolve_ds(ds, "loki")
    q = {"refId": "A", "datasource": {"uid": uid, "type": typ or "loki"}, "expr": expr, "queryType": "range", "maxLines": int(limit)}
    frames = ds_query([q], f"now-{since}")
    rows = []
    for f in frames:
        fields = (f.get("schema") or {}).get("fields") or []
        vals = (f.get("data") or {}).get("values") or []
        names = [fl.get("name", "") for fl in fields]
        ti = next((i for i, fl in enumerate(fields) if fl.get("type") == "time"), None)
        li = next((i for i, nm in enumerate(names) if nm in ("Line", "line", "body")), None)
        if ti is None or li is None:
            continue
        for k in range(min(len(vals[ti]), len(vals[li]))):
            rows.append((vals[ti][k], str(vals[li][k])))
    rows.sort(key=lambda r: r[0])
    if not rows:
        hints = []
        try:                                                # the labels Loki knows, and the values of the ones the query named
            lb = api(f"/api/datasources/proxy/uid/{uid}/loki/api/v1/labels") or {}
            names = [x for x in (lb.get("data") or []) if not x.startswith("__")]
            if names:
                hints.append("Loki's labels here: " + ", ".join(names[:30]) + ".")
            asked = [m for m in re.findall(r"(\w+)\s*(?:=~?|!~?=?)\s*\"", expr) if m in names] or [n for n in ("service_name", "node", "level") if n in names]
            for n in asked[:3]:
                vals = (api(f"/api/datasources/proxy/uid/{uid}/loki/api/v1/label/{urllib.parse.quote(n)}/values") or {}).get("data") or []
                if vals:
                    hints.append(f"{n} takes: " + ", ".join(sorted(vals)[:25]) + ("…" if len(vals) > 25 else "") + ".")
        except GrafanaError:
            pass
        return ["No log lines for that query in the last " + since + "."] + hints
    return [f"{datetime.fromtimestamp(t / 1000).strftime('%H:%M:%S')}  {line[:400]}" for t, line in rows[-int(limit):]]


def dashboards(q=""):
    items = api(f"/api/search?type=dash-db&limit=100&query={urllib.parse.quote(q)}") or []
    return [f"{d.get('uid', ''):16} {d.get('title', '')}" + (f"  ({d['folderTitle']})" if d.get("folderTitle") else "") for d in items] or ["No dashboard by that name."]


def panel(uid, pid, rng="6h", show=False, title=None):
    d = api(f"/api/dashboards/uid/{uid}") or {}
    dash, meta = d.get("dashboard") or {}, d.get("meta") or {}
    p = next((x for x in panels_of(dash) if str(x.get("id")) == str(pid)), None)
    if not p:
        return [f"no panel {pid} on {dash.get('title', uid)}; its panels: " + ", ".join(f"{x.get('id')}={x.get('title', '')!r}" for x in panels_of(dash) if x.get("type") != "row")]
    name = title or f"{dash.get('title', '')} · {p.get('title', '')}".strip(" ·")
    out_dir = P.blob_dir("board") / "grafana"; out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{uid}-{pid}-{time.strftime('%Y%m%d-%H%M%S')}.png"
    try:
        c = cfg()
        png = api(f"/render/d-solo/{uid}/{meta.get('slug') or 'd'}?orgId={c.get('org', 1)}&panelId={pid}&from=now-{rng}&to=now&width=1200&height=600&tz={urllib.parse.quote(c.get('tz') or 'UTC')}", raw=True, timeout=90)
        if png[:8] != PNG:
            raise GrafanaError("the renderer sent no picture")
        width = int.from_bytes(png[16:20], "big") if len(png) > 24 else 0
        if width < 1000:                                    # Grafana's own "no image renderer installed" card is a small PNG, not the panel
            raise GrafanaError("no image renderer is installed on this Grafana")
        png_path.write_bytes(png)
        lines = [f"panel picture: {png_path}"]
        if show:
            r = subprocess.run([str(HERE / "show-image.sh"), str(png_path), name], capture_output=True, text=True, timeout=30)
            lines.append((r.stdout or r.stderr).strip())
        return lines
    except GrafanaError as e:
        targets = p.get("targets") or []
        expr = next((t.get("expr") for t in targets if t.get("expr")), None)
        if not expr:
            return [f"no picture ({e}) and the panel has no query to redraw"]
        expr = interpolate(expr, rng)
        dsu = (p.get("datasource") or {}).get("uid") if isinstance(p.get("datasource"), dict) else None
        return [f"no rendered picture ({e}); the panel's numbers instead:", f"  {expr}"] + query(expr, rng, ds=dsu, show=show, title=name)


def interpolate(expr, rng):
    """A dashboard's variables, resolved the way a whole dashboard would: the range, Grafana's intervals, and any
    picked variable widened to everything (the dashboard is not here to pick one)."""
    expr = re.sub(r"\$\{?__range\}?", rng, expr)
    expr = re.sub(r"\$\{?__rate_interval\}?", "5m", expr)
    expr = re.sub(r"\$\{?__interval\}?", "1m", expr)
    expr = re.sub(r"(\w+)\s*=\s*\"\$\{?\w+(?::\w+)?\}?\"", r'\1=~".*"', expr)      # label="$var" -> label=~".*"
    expr = re.sub(r"\$\{?\w+(?::\w+)?\}?", ".*", expr)                            # any other $var inside a matcher
    return expr


def watch():
    """One pass: what began firing and what resolved since the last pass. The first pass is a baseline."""
    try:
        prev = json.loads(WATCH.read_text())
        seen = prev.get("seen") or {}
        first = False
    except Exception:
        seen, first = {}, True
    now = {a["key"]: a for a in instances(cfg().get("watch", {}).get("pending", False))}
    WATCH.parent.mkdir(parents=True, exist_ok=True)
    WATCH.write_text(json.dumps({"seen": now, "t": time.time()}))
    if first:
        return []
    new = [now[k] for k in now if k not in seen]
    gone = [seen[k] for k in seen if k not in now]
    lines = []
    if len(new) > 4:
        names = sorted({a["rule"] for a in new}); spots = sorted({a["where"] for a in new if a["where"]})
        lines.append(f"{len(new)} alerts began at once: {', '.join(names)[:240]}" + (f"; on {', '.join(spots)[:160]}" if spots else ""))
    else:
        for a in new:
            lines.append(f"{a['state']}: {a['rule']}" + (f" [{a['severity']}]" if a["severity"] else "") + (f" on {a['where']}" if a["where"] else "")
                         + (f", value {fmt_num(a['value'])}" if a["value"] is not None else "") + (f" · {a['summary'].strip().replace(chr(10), ' ')[:180]}" if a["summary"] else "")
                         + f" · since {local(a['since'])}")
    for a in gone:
        lines.append(f"RESOLVED: {a['rule']}" + (f" on {a['where']}" if a["where"] else "") + f" (had fired since {local(a['since'])})")
    return lines


def check():
    lines = []
    h = health() or {}
    lines.append(f"Grafana {h.get('version', '?')} at {cfg()['url']} · database {h.get('database', '?')}")
    if not token():
        lines.append("no token in the Keychain yet: paste it in the Keys card in Modes, or run troi-console/keychain.py set grafana")
        return lines
    u = me()
    if u:
        lines.append(f"signed in as {u.get('login') or u.get('name')} (org {u.get('orgId', '?')}" + (", admin" if u.get("isGrafanaAdmin") else "") + ")")
    try:
        org = api("/api/org") or {}
        lines.append(f"org: {org.get('name', '?')}")
    except GrafanaError as e:
        lines.append(str(e))
    ds = datasources(refresh=True)
    if ds:
        lines.append("data sources: " + ", ".join(f"{n} ({d.get('type') or 'type unknown'}{', default' if d.get('default') else ''})" for n, d in ds.items()))
    else:
        lines.append("data sources: none visible to this account yet")
    try:
        items = instances()
        lines.append(f"alerts firing now: {len(items)}" + (" · " + "; ".join(f"{a['rule']} on {a['where']}" for a in items[:5]) if items else ""))
    except GrafanaError as e:
        lines.append(f"alerts: {e}")
    return lines


def main(argv):
    ap = argparse.ArgumentParser(description="Grafana, read-only")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    a = sub.add_parser("alerts"); a.add_argument("--all", action="store_true"); a.add_argument("--json", action="store_true")
    r = sub.add_parser("rules"); r.add_argument("--json", action="store_true")
    sub.add_parser("silences")
    q = sub.add_parser("query"); q.add_argument("expr"); q.add_argument("--range", default="1h"); q.add_argument("--step"); q.add_argument("--ds"); q.add_argument("--show", action="store_true"); q.add_argument("--title")
    lg = sub.add_parser("logs"); lg.add_argument("expr"); lg.add_argument("--since", default="15m"); lg.add_argument("--limit", type=int, default=100); lg.add_argument("--ds")
    d = sub.add_parser("dashboards"); d.add_argument("words", nargs="?", default="")
    pn = sub.add_parser("panel"); pn.add_argument("uid"); pn.add_argument("pid"); pn.add_argument("--range", default="6h"); pn.add_argument("--show", action="store_true"); pn.add_argument("--title")
    sub.add_parser("watch")
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "check":
            out = check()
        elif ns.cmd == "alerts":
            out = [json.dumps(instances(ns.all), indent=1)] if ns.json else alerts(ns.all)
        elif ns.cmd == "rules":
            out = [json.dumps(rule_groups(), indent=1)] if ns.json else rules()
        elif ns.cmd == "silences":
            out = silences()
        elif ns.cmd == "query":
            out = query(ns.expr, ns.range, ns.step, ns.ds, ns.show, ns.title)
        elif ns.cmd == "logs":
            out = logs(ns.expr, ns.since, ns.limit, ns.ds)
        elif ns.cmd == "dashboards":
            out = dashboards(ns.words)
        elif ns.cmd == "panel":
            out = panel(ns.uid, ns.pid, ns.range, ns.show, ns.title)
        elif ns.cmd == "watch":
            out = watch() or ["nothing new"]
        else:
            print(__doc__); return 0
    except GrafanaError as e:
        print(f"Grafana: {e}"); return 1
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
