"""
Tiny helpers that emit Power Apps Studio "paste code" YAML (pa.yaml format).

Each screen file holds ONE root container (cntRoot_<Screen>). In Studio:
create the blank screen, then right-click the screen in the Tree view > Paste
(or Ctrl+V with the screen selected) after copying the file contents.

Classic controls, no version pins: Studio uses the current version of each
control when none is given. Formulas use English-locale separators (, and ;).
"""
from __future__ import annotations

import re

FONT = "Font.'Segoe UI'"


def _scalar(value: str, indent: int) -> str:
    """A Power Fx formula as a YAML scalar: plain when safe, block literal otherwise."""
    formula = value if value.startswith("=") else "=" + value
    unsafe = "\n" in formula or ": " in formula or " #" in formula or formula.endswith(":") or "\t" in formula
    if not unsafe:
        return " " + formula
    pad = " " * (indent + 2)
    return " |-\n" + "\n".join(pad + line for line in formula.split("\n"))


def emit(nodes: list[dict], indent: int = 0) -> str:
    out: list[str] = []
    for node in nodes:
        (name, spec), = node.items()
        p = " " * indent
        out.append(f"{p}- {name}:")
        out.append(f"{p}    Control: {spec['Control']}")
        if spec.get("Variant"):
            out.append(f"{p}    Variant: {spec['Variant']}")
        props = spec.get("Properties") or {}
        if props:
            out.append(f"{p}    Properties:")
            for k, v in props.items():
                out.append(f"{p}      {k}:{_scalar(str(v), indent + 6)}")
        children = spec.get("Children") or []
        if children:
            out.append(f"{p}    Children:")
            out.append(emit(children, indent + 6))
    return "\n".join(out)


def node(name: str, control: str, props: dict, children: list | None = None, variant: str | None = None) -> dict:
    spec: dict = {"Control": control, "Properties": props}
    if variant:
        spec["Variant"] = variant
    if children:
        spec["Children"] = children
    return {name: spec}


def q(text: str) -> str:
    """A Power Fx string literal."""
    return '"' + text.replace('"', '""') + '"'


# --------------------------------------------------------------------------- controls

def label(name, text, x, y, w, h=24, size=11, bold=False, color="gTheme.Text", **extra):
    props = {"Text": text, "X": x, "Y": y, "Width": w, "Height": h, "Size": size, "Font": FONT, "Color": color,
             "FontWeight": "FontWeight.Semibold" if bold else "FontWeight.Normal", "PaddingLeft": "0", "PaddingRight": "0"}
    props.update(extra)
    return node(name, "Label", props)


def text_input(name, default, hint, x, y, w, h=36, multiline=False, **extra):
    props = {"Default": default, "HintText": hint, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT,
             "Color": "gTheme.Text", "Fill": "gTheme.Card", "BorderColor": "gTheme.Border", "BorderThickness": 1,
             "HoverBorderColor": "gTheme.Primary", "FocusedBorderColor": "gTheme.Primary", "FocusedBorderThickness": 2,
             "PaddingLeft": 10, "RadiusTopLeft": 4, "RadiusTopRight": 4, "RadiusBottomLeft": 4, "RadiusBottomRight": 4}
    if multiline:
        props["Mode"] = "TextMode.MultiLine"
    props.update(extra)
    return node(name, "Classic/TextInput", props)


def button(name, text, on_select, x, y, w, h=34, kind="primary", **extra):
    if kind == "primary":
        style = {"Fill": "gTheme.Primary", "Color": "RGBA(255, 255, 255, 1)", "HoverFill": "gTheme.PrimaryHover",
                 "PressedFill": "gTheme.PrimaryHover", "BorderThickness": 0, "HoverColor": "RGBA(255, 255, 255, 1)"}
    elif kind == "secondary":
        style = {"Fill": "gTheme.Card", "Color": "gTheme.Primary", "HoverFill": "gTheme.PrimaryLight", "PressedFill": "gTheme.PrimaryLight",
                 "BorderColor": "gTheme.Primary", "BorderThickness": 1, "HoverColor": "gTheme.PrimaryHover", "HoverBorderColor": "gTheme.PrimaryHover"}
    else:  # subtle
        style = {"Fill": "RGBA(0, 0, 0, 0)", "Color": "gTheme.Text", "HoverFill": "gTheme.Bg", "PressedFill": "gTheme.Bg",
                 "BorderColor": "gTheme.Border", "BorderThickness": 1, "HoverColor": "gTheme.Text", "HoverBorderColor": "gTheme.Muted"}
    props = {"Text": text, "OnSelect": on_select, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT,
             "FontWeight": "FontWeight.Semibold", "RadiusTopLeft": 4, "RadiusTopRight": 4, "RadiusBottomLeft": 4, "RadiusBottomRight": 4}
    props.update(style)
    props.update(extra)
    return node(name, "Classic/Button", props)


def link(name, text, on_select, x, y, w, h=24, **extra):
    return label(name, text, x, y, w, h, size=11, bold=True, color="gTheme.Primary", OnSelect=on_select, **extra)


def rect(name, x, y, w, h, fill="gTheme.Card", border="gTheme.Border", thickness=1, **extra):
    props = {"X": x, "Y": y, "Width": w, "Height": h, "Fill": fill, "BorderColor": border, "BorderThickness": thickness}
    props.update(extra)
    return node(name, "Rectangle", props)


def icon(name, ic, x, y, w=24, h=24, color="gTheme.Muted", on_select=None, **extra):
    props = {"Icon": ic, "X": x, "Y": y, "Width": w, "Height": h, "Color": color, "PaddingTop": 2, "PaddingBottom": 2,
             "PaddingLeft": 2, "PaddingRight": 2}
    if on_select:
        props["OnSelect"] = on_select
    props.update(extra)
    return node(name, "Classic/Icon", props)


def dropdown(name, items, default, x, y, w, h=36, **extra):
    props = {"Items": items, "Default": default, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT,
             "Color": "gTheme.Text", "Fill": "gTheme.Card", "BorderColor": "gTheme.Border", "BorderThickness": 1,
             "ChevronBackground": "gTheme.Card", "ChevronFill": "gTheme.Muted", "HoverFill": "gTheme.PrimaryLight",
             "SelectionFill": "gTheme.Primary", "PaddingLeft": 10}
    props.update(extra)
    return node(name, "Classic/DropDown", props)


def combobox(name, items, display, search, x, y, w, h=36, multi=False, placeholder="Search", **extra):
    props = {"Items": items, "DisplayFields": display, "SearchFields": search, "SelectMultiple": "true" if multi else "false",
             "IsSearchable": "true", "InputTextPlaceholder": placeholder if placeholder.startswith("If(") else q(placeholder), "X": x, "Y": y, "Width": w, "Height": h,
             "Size": 11, "Font": FONT, "Color": "gTheme.Text", "Fill": "gTheme.Card", "BorderColor": "gTheme.Border",
             "BorderThickness": 1, "ChevronBackground": "gTheme.Card", "ChevronFill": "gTheme.Muted",
             "SelectionFill": "gTheme.Primary", "HoverFill": "gTheme.PrimaryLight"}
    props.update(extra)
    return node(name, "Classic/ComboBox", props)


def checkbox(name, text, default, x, y, w, h=32, **extra):
    props = {"Text": text, "Default": default, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT,
             "Color": "gTheme.Text", "CheckboxBorderColor": "gTheme.Muted", "CheckmarkFill": "RGBA(255, 255, 255, 1)",
             "CheckboxBackgroundFill": "If(Self.Value, gTheme.Primary, gTheme.Card)"}
    props.update(extra)
    return node(name, "Classic/CheckBox", props)


def toggle(name, default, x, y, w=220, h=32, **extra):
    props = {"Default": default, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT, "Color": "gTheme.Text",
             "TrueFill": "gTheme.Primary", "FalseFill": "gTheme.Border", "TrueText": q("Yes"), "FalseText": q("No")}
    props.update(extra)
    return node(name, "Classic/Toggle", props)


def radio(name, items, default, x, y, w, h=36, horizontal=True, **extra):
    props = {"Items": items, "Default": default, "X": x, "Y": y, "Width": w, "Height": h, "Size": 11, "Font": FONT,
             "Color": "gTheme.Text", "RadioSize": 18, "RadioSelectionFill": "gTheme.Primary", "RadioBorderColor": "gTheme.Muted",
             "Layout": "Layout.Horizontal" if horizontal else "Layout.Vertical"}
    props.update(extra)
    return node(name, "Classic/Radio", props)


def html(name, html_text, x, y, w, h, **extra):
    props = {"HtmlText": html_text, "X": x, "Y": y, "Width": w, "Height": h, "Font": FONT, "Size": 11, "Color": "gTheme.Text"}
    props.update(extra)
    return node(name, "HtmlViewer", props)


def gallery(name, items, x, y, w, h, template_size, children, wrap=1, on_select=None, padding=0, **extra):
    props = {"Items": items, "X": x, "Y": y, "Width": w, "Height": h, "TemplateSize": template_size,
             "TemplatePadding": padding, "WrapCount": wrap, "ShowScrollbar": "true", "BorderThickness": 0}
    if on_select:
        props["OnSelect"] = on_select
    props.update(extra)
    return node(name, "Gallery", props, children, variant="Vertical")


def container(name, x, y, w, h, children, fill="RGBA(0, 0, 0, 0)", **extra):
    props = {"X": x, "Y": y, "Width": w, "Height": h, "Fill": fill, "BorderThickness": 0, "DropShadow": "DropShadow.None"}
    props.update(extra)
    return node(name, "GroupContainer", props, children, variant="ManualLayout")


def field_label(name, text, x, y, w, required=False):
    t = text + (" *" if required else "")
    return label(name, q(t), x, y, w, 20, size=10, bold=True, color="gTheme.Text")


def hint(name, text, x, y, w, h=20, **extra):
    return label(name, text, x, y, w, h, size=9, color="gTheme.Muted", **extra)


def frame(sfx: str, title: str, subtitle: str, crumbs: str) -> list[dict]:
    """Top bar, breadcrumb, title and subtitle shared by every screen."""
    return [
        rect(f"recTopBar_{sfx}", 0, 0, "Parent.Width", 48, fill="gTheme.TopBar", thickness=0),
        label(f"lblBrand_{sfx}", q("Entra Self-Service"), 20, 0, 300, 48, size=13, bold=True, color="RGBA(255, 255, 255, 1)",
              OnSelect="Navigate(scrHome, ScreenTransition.Fade)"),
        label(f"lblUser_{sfx}", "gMe.Name", "Parent.Width - 340", 0, 320, 48, size=10, color="RGBA(255, 255, 255, 1)", Align="Align.Right"),
        label(f"lblCrumb_{sfx}", crumbs, 24, 58, "Parent.Width - 48", 22, size=9, color="gTheme.Primary",
              OnSelect="Navigate(scrHome, ScreenTransition.Fade)"),
        label(f"lblTitle_{sfx}", title, 24, 80, "Parent.Width - 48", 34, size=18, bold=True),
        label(f"lblSubtitle_{sfx}", subtitle, 24, 112, "Parent.Width - 48", 22, size=10, color="gTheme.Muted"),
    ]


STATUS_TEXT = ('Switch({s}, "PendingManagerApproval", "Awaiting manager", "PendingEntraApproval", "Awaiting Entra team", '
               '"InProgress", "In progress", {s})')
STATUS_FILL = ('Switch({s}, "Completed", gTheme.SuccessLight, "Failed", gTheme.DangerLight, "Rejected", gTheme.DangerLight, '
               '"InProgress", gTheme.PrimaryLight, "Approved", gTheme.PrimaryLight, gTheme.WarningLight)')
STATUS_COLOR = ('Switch({s}, "Completed", gTheme.Success, "Failed", gTheme.Danger, "Rejected", gTheme.Danger, '
                '"InProgress", gTheme.Primary, "Approved", gTheme.Primary, gTheme.Warning)')


def status_badge(name, status_expr, x, y, w=150, h=24):
    s = status_expr
    return label(name, STATUS_TEXT.format(s=s), x, y, w, h, size=9, bold=True, color=STATUS_COLOR.format(s=s),
                 Fill=STATUS_FILL.format(s=s), Align="Align.Center", PaddingLeft="6", PaddingRight="6")


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s)


def timer(name, on_end, start, duration=3000, **extra):
    """Invisible repeating timer: polls the request list while a flow processes a request."""
    props = {"Duration": duration, "Repeat": "true", "AutoStart": "false", "Start": start, "OnTimerEnd": on_end,
             "Visible": "false", "X": 0, "Y": 0, "Width": 10, "Height": 10}
    props.update(extra)
    return node(name, "Timer", props)
