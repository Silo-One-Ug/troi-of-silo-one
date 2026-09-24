#!/usr/bin/env python3
"""read.py: a file the Read tool cannot open, printed as text for the agent. Standard library only, plus the Mac's own
converters (textutil, pdftotext) where they exist.

  read.py <file> [--sheet NAME] [--rows N] [--max-chars N]

  .xlsx .xlsm             every sheet (or the one named), as a table: N rows each (200 by default), dates as dates
  .csv .tsv               the table, N rows
  .pptx                   the text of every slide
  .docx .doc .rtf .odt    the text, through the Mac's textutil
  .html .webarchive       the same
  .pdf                    the text, through pdftotext (brew install poppler); Read opens PDFs itself as well
  anything else           printed as it is, as text

The output is capped (60,000 characters by default): one result never floods the conversation. A file the owner
points at with @ in the console, or uploads there (data/blobs/uploads/), is read with this when Read cannot.
"""
import csv
import datetime as dt
import io
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
DATE_IDS = set(range(14, 23)) | set(range(27, 37)) | {45, 46, 47} | set(range(50, 59))   # Excel's built-in date and time formats


def cell_text(v, width=80):
    s = str(v).replace("\n", " ").replace("|", "\\|").strip()
    return s if len(s) <= width else s[: width - 1] + "…"


def table(rows, rows_cap):
    """Rows of cells as a Markdown table: the first row is the header; empty trailing columns are dropped."""
    rows = [list(r) for r in rows[:rows_cap]]
    if not rows:
        return "(empty)\n"
    width = max((max((i + 1 for i, c in enumerate(r) if str(c).strip()), default=0) for r in rows), default=0) or 1
    rows = [(r + [""] * width)[:width] for r in rows]
    head = [cell_text(c) or f"col{i + 1}" for i, c in enumerate(rows[0])]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(cell_text(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(out) + "\n"


# ---- xlsx: the sheets' XML, straight from the zip
def col_index(ref):
    n = 0
    for ch in ref:
        if ch.isalpha(): n = n * 26 + (ord(ch.upper()) - 64)
        else: break
    return n


def excel_date(serial):
    try:
        d = dt.datetime(1899, 12, 30) + dt.timedelta(seconds=round(float(serial) * 86400))   # to the second: 14:30 stays 14:30
    except (ValueError, OverflowError):
        return str(serial)
    return d.strftime("%Y-%m-%d") if d.hour == 0 and d.minute == 0 and d.second == 0 else d.strftime("%Y-%m-%d %H:%M")


def number(v):
    try:
        f = float(v)
    except ValueError:
        return v
    return str(int(f)) if f.is_integer() and abs(f) < 1e15 else f"{f:.10g}"


def xlsx_sheets(z):
    """(name, path-in-zip) for every sheet, in the workbook's order."""
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {}
    try:
        for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            rels[rel.get("Id")] = rel.get("Target", "")
    except KeyError:
        pass
    out = []
    for sh in wb.find("m:sheets", NS) or []:
        target = rels.get(sh.get(f"{{{NS['r']}}}id"), "")
        path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        out.append((sh.get("name", "Sheet"), path))
    return out


def xlsx_date_styles(z):
    """Which cell styles (cellXfs indexes) are dates or times."""
    try:
        st = ET.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return set()
    custom = {}
    for nf in (st.find("m:numFmts", NS) or []):
        code = (nf.get("formatCode") or "").lower()
        code = re.sub(r'"[^"]*"|\[[^\]]*\]', "", code)          # literal text and colour/locale tags do not count
        if re.search(r"y|d|h|s", code) and not re.search(r"[#0]", code):
            custom[int(nf.get("numFmtId", -1))] = True
    dates = set()
    for i, xf in enumerate(st.find("m:cellXfs", NS) or []):
        fid = int(xf.get("numFmtId", 0) or 0)
        if fid in DATE_IDS or custom.get(fid):
            dates.add(i)
    return dates


def xlsx_shared(z):
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]


def xlsx_rows(z, path, shared, dates, rows_cap):
    rows, tag_c, tag_v, tag_is, tag_t, tag_row = [], f"{{{NS['m']}}}c", f"{{{NS['m']}}}v", f"{{{NS['m']}}}is", f"{{{NS['m']}}}t", f"{{{NS['m']}}}row"
    with z.open(path) as fh:
        for _, el in ET.iterparse(fh):
            if el.tag != tag_row:
                continue
            cells = {}
            for c in el.findall(tag_c):
                i = col_index(c.get("r", "")) or (max(cells) + 1 if cells else 1)
                kind, style = c.get("t", "n"), int(c.get("s", 0) or 0)
                v = c.find(tag_v); text = v.text if v is not None else None
                if kind == "s" and text is not None:
                    val = shared[int(text)] if int(text) < len(shared) else ""
                elif kind == "inlineStr":
                    val = "".join(t.text or "" for t in c.iter(tag_t))
                elif kind == "b":
                    val = "TRUE" if text == "1" else "FALSE"
                elif kind in ("str", "e"):
                    val = text or ""
                elif text is None:
                    val = ""
                else:
                    val = excel_date(text) if style in dates else number(text)
                cells[i] = val
            if cells and any(str(v).strip() for v in cells.values()):    # a row of nothing (a formula with no cached value) is left out
                width = max(cells)
                rows.append([cells.get(i, "") for i in range(1, width + 1)])
            el.clear()
            if len(rows) >= rows_cap:
                break
    return rows


def read_xlsx(p, sheet, rows_cap):
    out = []
    with zipfile.ZipFile(p) as z:
        shared, dates = xlsx_shared(z), xlsx_date_styles(z)
        sheets = xlsx_sheets(z)
        if sheet:
            sheets = [s for s in sheets if s[0].lower() == sheet.lower()] or [s for s in sheets if sheet.lower() in s[0].lower()]
            if not sheets:
                return f"no sheet called {sheet!r}; the sheets are: " + ", ".join(n for n, _ in xlsx_sheets(z)) + "\n"
        for name, path in sheets:
            try:
                rows = xlsx_rows(z, path, shared, dates, rows_cap + 1)
            except KeyError:
                rows = []
            more = " (first %d rows)" % rows_cap if len(rows) > rows_cap else ""
            out.append(f"## Sheet: {name}{more}\n\n" + table(rows, rows_cap))
    return "\n".join(out)


# ---- pptx: the runs of text on every slide
def read_pptx(p):
    out = []
    with zipfile.ZipFile(p) as z:
        slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for i, n in enumerate(slides, 1):
            root = ET.fromstring(z.read(n))
            paras = []
            for para in root.iter(f"{{{NS['a']}}}p"):
                t = "".join(r.text or "" for r in para.iter(f"{{{NS['a']}}}t")).strip()
                if t: paras.append(t)
            out.append(f"## Slide {i}\n\n" + ("\n".join(paras) if paras else "(no text)") + "\n")
    return "\n".join(out) if out else "(no slides)\n"


# ---- csv
def read_csv(p, rows_cap):
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel_tab if p.suffix.lower() == ".tsv" else csv.excel
    rows = []
    for r in csv.reader(io.StringIO(text), dialect):
        rows.append(r)
        if len(rows) > rows_cap: break
    more = " (first %d rows)" % rows_cap if len(rows) > rows_cap else ""
    return f"## {p.name}{more}\n\n" + table(rows, rows_cap)


# ---- the Mac's converters
def via(cmd, missing):
    if not shutil.which(cmd[0]):
        return f"{cmd[0]} is not installed ({missing})\n"
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.stdout if r.returncode == 0 and r.stdout.strip() else (r.stderr.strip() or "(nothing could be read)") + "\n"


def read(path, sheet=None, rows_cap=200):
    p = Path(path).expanduser()
    if not p.exists():
        return f"no such file: {p}\n"
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(p, sheet, rows_cap)
    if ext in (".csv", ".tsv"):
        return read_csv(p, rows_cap)
    if ext == ".pptx":
        return read_pptx(p)
    if ext in (".docx", ".doc", ".rtf", ".rtfd", ".odt", ".html", ".htm", ".webarchive", ".wordml"):
        return via(["textutil", "-convert", "txt", "-stdout", str(p)], "it ships with macOS")
    if ext == ".pdf":
        return via(["pdftotext", "-layout", str(p), "-"], "brew install poppler; the Read tool opens PDFs itself too")
    if ext in (".xls", ".numbers", ".pages", ".key"):
        return f"{ext} is not readable here: export it as {'xlsx or csv' if ext in ('.xls', '.numbers') else 'docx or pdf'} first\n"
    try:
        return p.read_text(errors="replace")
    except Exception as e:
        return f"could not read {p.name}: {e}\n"


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    sheet, rows_cap, max_chars, files = None, 200, 60000, []
    i = 0
    while i < len(a):
        if a[i] == "--sheet" and i + 1 < len(a): sheet = a[i + 1]; i += 2
        elif a[i] == "--rows" and i + 1 < len(a): rows_cap = max(1, int(a[i + 1])); i += 2
        elif a[i] == "--max-chars" and i + 1 < len(a): max_chars = max(1000, int(a[i + 1])); i += 2
        else: files.append(a[i]); i += 1
    for f in files:
        out = read(f, sheet, rows_cap)
        if len(files) > 1:
            print(f"# {f}\n")
        if len(out) > max_chars:
            out = out[:max_chars] + f"\n… cut at {max_chars} characters ({len(out)} in all); --max-chars raises it, --rows lowers the rows per sheet\n"
        sys.stdout.write(out if out.endswith("\n") else out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
