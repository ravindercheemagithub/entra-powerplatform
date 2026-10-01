#!/usr/bin/env python3
"""
Layout preview: renders the generated screen YAML as positioned HTML boxes at
1366 x 768, so overlaps and clipping are visible without opening Studio.
Not a Power Fx engine -- it evaluates only X/Y/Width/Height arithmetic and shows
literal texts. Output: ../preview/index.html  (python3 preview.py)
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
W, H = 1366, 768
COLORS = {
    "gTheme.Primary": "#0f6cbd", "gTheme.PrimaryHover": "#115ea3", "gTheme.PrimaryLight": "#ebf3fc", "gTheme.TopBar": "#1b1a19",
    "gTheme.Bg": "#f3f2f1", "gTheme.Card": "#ffffff", "gTheme.Border": "#e1dfdd", "gTheme.Text": "#323130", "gTheme.Muted": "#605e5c",
    "gTheme.Success": "#107c10", "gTheme.SuccessLight": "#dff6dd", "gTheme.Danger": "#d13438", "gTheme.DangerLight": "#fde7e9",
    "gTheme.Warning": "#986f0b", "gTheme.WarningLight": "#fff4ce", "RGBA(255, 255, 255, 1)": "#ffffff",
}
SAMPLE = {
    "gOperations": ["App registration", "Expose an API", "App roles", "Role assignments", "Enterprise application", "Security group", "My requests"],
    "gSteps": ["Basics", "Expose an API & claims", "App roles & groups", "Enterprise app & owners", "Review + submit"],
}


def num(expr: str, ctx: dict) -> float:
    e = str(expr).lstrip("=")
    for k, v in ctx.items():
        e = e.replace(k, str(v))
    if not re.fullmatch(r"[0-9.+\-*/() ]+", e):
        return 0.0
    try:
        return float(eval(e))  # arithmetic only (checked above)
    except Exception:
        return 0.0


def color(expr: str | None, default: str) -> str:
    if not expr:
        return default
    e = expr.lstrip("=")
    if e in COLORS:
        return COLORS[e]
    m = re.search(r"(gTheme\.\w+|RGBA\([^)]*\))\s*\)?$", e)  # last colour in an If(...) = the 'else' branch
    if m and m.group(1) in COLORS:
        return COLORS[m.group(1)]
    if "RGBA(0, 0, 0, 0)" in e:
        return "transparent"
    return default


def literal(expr: str | None) -> str | None:
    if not expr:
        return None
    e = expr.lstrip("=")
    m = re.fullmatch(r'"((?:[^"]|"")*)"', e)
    return m.group(1).replace('""', '"') if m else None


def visible(props: dict, state: dict) -> bool:
    v = str(props.get("Visible", "=true")).lstrip("=")
    if v == "false":
        return False
    m = re.fullmatch(r"varStep = (\d)", v)
    if m:
        return int(m.group(1)) == state.get("step", 1)
    m = re.fullmatch(r'varOp = "(\w+)"', v)
    if m:
        return m.group(1) == state.get("op")
    if v in ("IsBlank(varApp)",):
        return not state.get("app", True)
    if v.startswith("CountRows(") and v.endswith("= 0"):
        return False  # empty-state labels: assume data
    if v == 'varNewTeam.Mode = "new"':
        return False
    return True


def render(nodes: list, ctx: dict, state: dict, out: list, depth=0, ox=0.0, oy=0.0) -> None:
    for node in nodes:
        (name, spec), = node.items()
        p = spec.get("Properties") or {}
        if not visible(p, state):
            continue
        x, y = ox + num(p.get("X", 0), ctx), oy + num(p.get("Y", 0), ctx)
        w, h = num(p.get("Width", 0), ctx), num(p.get("Height", 0), ctx)
        ctl = spec["Control"].split("/")[-1]
        text = literal(p.get("Text")) or literal(p.get("HintText")) or ""
        bg = color(p.get("Fill"), "transparent")
        fg = color(p.get("Color"), "#323130")
        border = color(p.get("BorderColor"), "transparent") if num(p.get("BorderThickness", 0), ctx) or ctl in ("TextInput", "DropDown", "ComboBox") else "transparent"
        size = num(p.get("Size", 11), ctx) * 1.3
        bold = "600" if "Semibold" in str(p.get("FontWeight", "")) else "400"
        if ctl in ("TextInput", "DropDown", "ComboBox"):
            text = text or literal(p.get("Default")) or literal(p.get("InputTextPlaceholder")) or ""
            bg = "#ffffff"; fg = "#a19f9d"; border = "#8a8886"
        if ctl == "Gallery":
            label = f'<span class="g">{html.escape(name)}</span>'
            out.append(f'<div class="c" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;outline:1px dashed #c8c6c4">{label}</div>')
            ts = num(p.get("TemplateSize", 50), ctx)
            wrap = int(num(p.get("WrapCount", 1), ctx) or 1)
            items = p.get("Items", "")
            key = str(items).lstrip("=")
            samples = SAMPLE.get(key, [""] * 4)
            tw = w / wrap
            for i, sample in enumerate(samples[: int(h // ts) * wrap]):
                cx, cy = x + (i % wrap) * tw, y + (i // wrap) * ts
                tctx = dict(ctx, **{"Parent.TemplateWidth": tw, "Parent.TemplateHeight": ts})
                kids = []
                render(spec.get("Children") or [], tctx, dict(state, sample=sample), kids, depth + 1, cx, cy)
                out.extend(kids)
            continue
        if ctl in ("Label",) and not text and p.get("Text"):
            t = str(p["Text"]).lstrip("=")
            text = state.get("sample") if t.startswith("ThisItem.Title") and state.get("sample") else f"‹{name}›"
        style = (f"left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{bg};color:{fg};border:1px solid {border};"
                 f"font-size:{size}px;font-weight:{bold}")
        if ctl == "Button":
            style += ";border-radius:4px;justify-content:center"
        if ctl in ("CheckBox", "Toggle", "Radio"):
            text = ("☐ " if ctl == "CheckBox" else "◉ " if ctl == "Radio" else "⏽ ") + (text or name)
        if ctl == "Icon":
            text = "◆"
        if ctl == "HtmlViewer":
            text = f"[{name}: HTML summary]"; style += ";align-items:flex-start;color:#605e5c"
        out.append(f'<div class="c" title="{html.escape(name)}" style="{style}">{html.escape(text)}</div>')
        if spec.get("Children"):
            render(spec["Children"], dict(ctx, **{"Parent.Width": w, "Parent.Height": h}), state, out, depth + 1, x, y)


def screen(name: str, state: dict) -> str:
    nodes = yaml.safe_load((ROOT / "screens" / f"{name}.pa.yaml").read_text())
    out: list[str] = []
    render(nodes, {"Parent.Width": W, "Parent.Height": H}, state, out)
    label = name + (f" · step {state['step']}" if name == "scrNewApp" else f" · {state['op']}" if name == "scrAppChange" else "")
    return f'<h2>{label}</h2><div class="s">{"".join(out)}</div>'


def main() -> None:
    parts = [screen("scrHome", {})]
    parts += [screen("scrNewApp", {"step": n}) for n in range(1, 6)]
    parts += [screen("scrNewGroup", {})]
    parts += [screen("scrAppChange", {"op": op, "app": True}) for op in ("exposeApi", "addAppRoles", "assignGroups", "createSP")]
    parts += [screen("scrMyRequests", {})]
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Layout preview</title><style>
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#e5e5e5;margin:20px}}
h2{{font-size:14px;margin:24px 0 6px}}
.s{{position:relative;width:{W}px;height:{H}px;background:#f3f2f1;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.2)}}
.c{{position:absolute;box-sizing:border-box;display:flex;align-items:center;overflow:hidden;white-space:nowrap;padding:0 4px;line-height:1.2}}
.g{{position:absolute;right:2px;bottom:0;font-size:9px;color:#a19f9d}}
</style></head><body>{''.join(parts)}</body></html>"""
    (ROOT / "preview").mkdir(exist_ok=True)
    (ROOT / "preview" / "index.html").write_text(doc)
    print("wrote", ROOT / "preview" / "index.html")


if __name__ == "__main__":
    main()
