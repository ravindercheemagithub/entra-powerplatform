#!/usr/bin/env python3
"""
drawio.py -- a small library for generating professional multi-page .drawio
files with the official Azure icon set.

Why a library and not hand-written XML: a diagram is never right the first
time. Coordinates move, labels collide, a reviewer asks for one more box. If
the diagram is a Python function you re-run it; if it is 4000 lines of XML you
start again. The output is plain, uncompressed mxGraph XML, so everything stays
editable by hand in draw.io afterwards.

    from drawio import Page, Sequence, Doc, BLUE, GREEN, PURPLE, GREY, INK

    def page_context():
        p = Page("1 System context", 1400, 800)
        p.note("<b style='font-size:16px'>Title</b><br>One line of framing.", 40, 20, 900, 50, font=12)
        box = p.container("Azure subscription", 60, 100, 500, 400, stroke=BLUE, fill=BLUE_FILL)
        fn  = p.icon("func", "Function App", 120, 160)
        db  = p.icon("cosmos", "Cosmos DB", 320, 160)
        p.edge(fn, db, "reads and writes", GREEN)
        return p

    Doc("out.drawio").add(page_context()).write()

Requires only the Python standard library.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

# ---------------------------------------------------------------------------
# Palette -- Microsoft's own product colours, at print-safe contrast.
#
# Use colour to mean something and nothing else: one hue per domain (compute,
# identity, data, ...), plus red reserved for failure. A diagram where every
# box is a different colour has no hierarchy left to spend.
# ---------------------------------------------------------------------------
BLUE = "#0078D4";   BLUE_FILL = "#EAF3FB"      # Azure / compute / the platform
GREEN = "#107C10";  GREEN_FILL = "#EAF6EA"     # data, storage, success paths
PURPLE = "#5C2D91"; PURPLE_FILL = "#F1ECF7"    # identity, Entra, directory
ORANGE = "#CA5010"; ORANGE_FILL = "#FDF1EA"    # retries, warnings, expiry
GREY = "#605E5C";   GREY_FILL = "#F3F2F1"      # external actors, supporting cast
RED = "#A4262C";    RED_FILL = "#FDE7E9"       # refusals and failures only
INK = "#323130"                                # all body text
NOTE_FILL = "#FFF8DC"; NOTE_STROKE = "#D9B300" # sticky notes

# ---------------------------------------------------------------------------
# Azure icons -- draw.io's built-in Azure2 library, referenced by path.
#
# These resolve inside draw.io itself (no network fetch, no embedded base64),
# so the file stays small and a reader can right-click > Edit Image to swap one.
# See references/icons.md for the full catalogue and how to verify a new path.
# ---------------------------------------------------------------------------
AZ = "img/lib/azure2/"
ICON = {
    # identity
    "entra": AZ + "identity/Azure_Active_Directory.svg",
    "appreg": AZ + "identity/App_Registrations.svg",
    "entapp": AZ + "identity/Enterprise_Applications.svg",
    "groups": AZ + "identity/Groups.svg",
    "users": AZ + "identity/Users.svg",
    "umi": AZ + "identity/Managed_Identities.svg",
    # compute
    "func": AZ + "compute/Function_Apps.svg",
    "vm": AZ + "compute/Virtual_Machines.svg",
    "aks": AZ + "containers/Kubernetes_Services.svg",
    "aci": AZ + "containers/Container_Instances.svg",
    "acr": AZ + "containers/Container_Registries.svg",
    "batch": AZ + "compute/Batch_Accounts.svg",
    # app hosting
    "webapp": AZ + "app_services/App_Services.svg",
    "plan": AZ + "app_services/App_Service_Plans.svg",
    "staticapp": AZ + "app_services/App_Service_Certificates.svg",
    # data
    "cosmos": AZ + "databases/Azure_Cosmos_DB.svg",
    "sql": AZ + "databases/SQL_Database.svg",
    "sqlserver": AZ + "databases/SQL_Server.svg",
    "redis": AZ + "databases/Cache_Redis.svg",
    "synapse": AZ + "databases/Azure_Synapse_Analytics.svg",
    "datafactory": AZ + "databases/Data_Factory.svg",
    "storage": AZ + "storage/Storage_Accounts.svg",
    "blob": AZ + "storage/Blob_Block.svg",
    "datalake": AZ + "storage/Data_Lake_Storage_Gen1.svg",
    # integration / messaging
    "apim": AZ + "integration/API_Management_Services.svg",
    "servicebus": AZ + "integration/Service_Bus.svg",
    "eventgrid": AZ + "integration/Event_Grid_Topics.svg",
    "eventhub": AZ + "analytics/Event_Hubs.svg",
    "logicapp": AZ + "integration/Logic_Apps.svg",
    "queue": AZ + "storage/Queues_Storage.svg",
    # networking
    "frontdoor": AZ + "networking/Front_Doors.svg",
    "appgw": AZ + "networking/Application_Gateways.svg",
    "loadbalancer": AZ + "networking/Load_Balancers.svg",
    "vnet": AZ + "networking/Virtual_Networks.svg",
    "firewall": AZ + "networking/Firewalls.svg",
    "dns": AZ + "networking/DNS_Zones.svg",
    "cdn": AZ + "networking/CDN_Profiles.svg",
    "privatelink": AZ + "networking/Private_Link.svg",
    # security
    "keyvault": AZ + "security/Key_Vaults.svg",
    "defender": AZ + "security/Security_Center.svg",
    # devops / observability
    "appinsights": AZ + "devops/Application_Insights.svg",
    "monitor": AZ + "management_governance/Monitor.svg",
    "loganalytics": AZ + "analytics/Log_Analytics_Workspaces.svg",
    "devops": AZ + "devops/Azure_DevOps.svg",
    "pipelines": AZ + "devops/Azure_Pipelines.svg",
    # management / general
    "rg": AZ + "general/Resource_Groups.svg",
    "sub": AZ + "general/Subscriptions.svg",
    "browser": AZ + "general/Browser.svg",
    "user": AZ + "general/User.svg",
    "devices": AZ + "general/Devices.svg",
    "policy": AZ + "management_governance/Policy.svg",
    "blueprints": AZ + "management_governance/Blueprints.svg",
    # ai / ml
    "openai": AZ + "ai_machine_learning/Cognitive_Services.svg",
    "ml": AZ + "ai_machine_learning/Machine_Learning_Service_Workspaces.svg",
    "search": AZ + "ai_machine_learning/Cognitive_Search.svg",
}


class Page:
    """One tab in the .drawio file. Coordinates are absolute, origin top-left."""

    def __init__(self, name: str, width: int = 1400, height: int = 900):
        self.name = name
        self.diagram = ET.Element("diagram", {"id": re.sub(r"[^a-z0-9-]", "-", name.lower())[:40], "name": name})
        model = ET.SubElement(self.diagram, "mxGraphModel", {
            "dx": "1400", "dy": "900", "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1",
            "connect": "1", "arrows": "1", "fold": "1", "page": "1", "pageScale": "1",
            "pageWidth": str(width), "pageHeight": str(height), "math": "0", "shadow": "0",
        })
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", {"id": "0"})
        ET.SubElement(self.root, "mxCell", {"id": "1", "parent": "0"})
        self.n = 0

    def _id(self, prefix="c"):
        self.n += 1
        return f"{prefix}{self.n}"

    # -- vertices ------------------------------------------------------------
    def box(self, label, x, y, w, h, style, parent="1", id=None):
        """Escape hatch for any mxGraph style string not covered by the helpers."""
        cid = id or self._id()
        c = ET.SubElement(self.root, "mxCell",
                          {"id": cid, "value": label, "style": style, "vertex": "1", "parent": parent})
        ET.SubElement(c, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})
        return cid

    def container(self, label, x, y, w, h, stroke=GREY, fill=GREY_FILL, dashed=False, parent="1", id=None):
        """A labelled region: a subscription, a resource group, a tenant, a tier.

        The title sits top-left, so keep the top ~30px of the interior clear --
        an edge routed through there collides with the heading.
        """
        style = (f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
                 f"verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontStyle=1;fontSize=13;fontColor={INK};"
                 f"container=1;collapsible=0;{'dashed=1;' if dashed else ''}")
        return self.box(label, x, y, w, h, style, parent, id)

    def node(self, label, x, y, w=150, h=50, fill="#FFFFFF", stroke=INK, parent="1", id=None, bold=False, font=12):
        """A plain box. Use for settings blocks, config, anything without an icon."""
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
                 f"fontSize={font};fontColor={INK};{'fontStyle=1;' if bold else ''}")
        return self.box(label, x, y, w, h, style, parent, id)

    def icon(self, key, label, x, y, w=56, h=56, parent="1", id=None, font=11):
        """An Azure service, drawn with its official icon and a caption below.

        The caption is part of the shape, so it extends roughly 20px per line
        BELOW y+h. Leave room for it, or the next row collides with the text.
        """
        style = (f"image;aspect=fixed;html=1;points=[];align=center;fontSize={font};image={ICON[key]};"
                 f"labelBackgroundColor=none;verticalLabelPosition=bottom;verticalAlign=top;fontColor={INK};")
        return self.box(label, x, y, w, h, style, parent, id)

    def note(self, text, x, y, w, h, parent="1", color=GREY, font=11, align="left"):
        """Free text with no frame: page titles, captions, asides."""
        style = (f"text;html=1;align={align};verticalAlign=top;whiteSpace=wrap;fontSize={font};"
                 f"fontColor={color};spacing=2;")
        return self.box(text, x, y, w, h, style, parent)

    def sticky(self, text, x, y, w, h, parent="1"):
        """A folded-corner note. Reserve these for the two or three things a
        reader would otherwise get wrong -- they draw the eye, so overusing
        them costs you the emphasis."""
        style = ("shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;"
                 f"fillColor={NOTE_FILL};strokeColor={NOTE_STROKE};fontSize=11;align=left;verticalAlign=top;"
                 f"spacing=6;fontColor={INK};size=14;")
        return self.box(text, x, y, w, h, style, parent)

    def decision(self, label, x, y, w=170, h=80, parent="1", fill=BLUE_FILL, stroke=BLUE):
        style = (f"rhombus;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
                 f"fontSize=11;fontColor={INK};")
        return self.box(label, x, y, w, h, style, parent)

    def terminal(self, label, x, y, fill=GREEN_FILL, stroke=GREEN, w=140, h=44, parent="1"):
        """A rounded start/end/outcome pill for flowcharts and state machines."""
        style = (f"rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth=1.5;fontSize=12;fontStyle=1;fontColor={INK};")
        return self.box(label, x, y, w, h, style, parent)

    def state(self, label, x, y, w=170, h=60, fill=BLUE_FILL, stroke=BLUE, parent="1"):
        style = (f"rounded=1;arcSize=30;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
                 f"strokeWidth=2;fontSize=13;fontStyle=1;fontColor={INK};")
        return self.box(label, x, y, w, h, style, parent)

    def dot(self, x, y, size=24, fill=INK, parent="1"):
        """Initial / final pseudo-state for a state machine."""
        return self.box("", x, y, size, size, f"ellipse;fillColor={fill};strokeColor={fill};", parent)

    def table(self, title, rows, x, y, w, stroke=GREY, fill="#FFFFFF", row_h=22, font=10,
              mono=False, parent="1", wide_row_h=36, wide_at=80):
        """A titled stack of one-line facts: schemas, settings, comparisons.

        Rows longer than `wide_at` characters get a taller slot so they wrap
        instead of clipping -- clipped text in a diagram is a bug, not a style.
        """
        plain = [re.sub("<[^>]+>", "", r) for r in rows]
        heights = [row_h if len(t) <= wide_at else wide_row_h for t in plain]
        h = 30 + sum(heights)
        cid = self.box(title, x, y, w, h,
                       f"swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;"
                       f"resizeParent=0;resizeLast=0;collapsible=0;marginBottom=0;whiteSpace=wrap;html=1;"
                       f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontSize=12;fontColor={INK};"
                       f"swimlaneFillColor={fill};", parent)
        yy = 30
        family = "fontFamily=Courier New;" if mono else ""
        for text, rh in zip(rows, heights):
            self.box(text, 0, yy, w, rh,
                     f"text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=8;"
                     f"spacingRight=6;overflow=hidden;whiteSpace=wrap;html=1;fontSize={font};fontColor={INK};{family}",
                     cid)
            yy += rh
        return cid

    # -- edges ---------------------------------------------------------------
    def edge(self, src, dst, label="", color=INK, dashed=False, parent="1", style_extra="",
             entry=None, exit=None, points=None):
        """Connects two shapes by id. draw.io reroutes these when you drag a
        shape, which is why connecting by id beats fixed coordinates wherever
        both ends are real shapes.

        entry/exit are (x, y) fractions of the target/source shape: (0,0.5) is
        the left edge mid-height, (0.5,1) the bottom centre. Pin them when the
        default attachment point makes the line take an ugly route.
        """
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
                 f"endArrow=blockThin;endFill=1;strokeColor={color};strokeWidth=1.5;fontSize=10;fontColor={INK};"
                 f"labelBackgroundColor=#FFFFFF;{'dashed=1;' if dashed else ''}{style_extra}")
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        if exit:
            style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        c = ET.SubElement(self.root, "mxCell", {"id": self._id("e"), "value": label, "style": style,
                                                "edge": "1", "parent": parent, "source": src, "target": dst})
        g = ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
        if points:
            arr = ET.SubElement(g, "Array", {"as": "points"})
            for px, py in points:
                ET.SubElement(arr, "mxPoint", {"x": str(px), "y": str(py)})
        return c

    def free_edge(self, x1, y1, x2, y2, label="", color=INK, dashed=False, parent="1",
                  points=None, label_pos=None, style_extra=""):
        """An edge with absolute endpoints, for when one or both ends is not a
        shape -- sequence-diagram messages, or an arrow that must leave a
        specific point on a container.

        draw.io places the label at the geometric MIDPOINT of the whole path.
        With multi-segment routes, work out where that lands before assuming
        the label is clear; `points` is how you steer it into open space.
        """
        style = (f"html=1;endArrow=blockThin;endFill=1;strokeColor={color};strokeWidth=1.5;fontSize=10;"
                 f"fontColor={INK};labelBackgroundColor=#FFFFFF;{'dashed=1;' if dashed else ''}{style_extra}")
        c = ET.SubElement(self.root, "mxCell", {"id": self._id("e"), "value": label, "style": style,
                                               "edge": "1", "parent": parent})
        g = ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
        ET.SubElement(g, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
        ET.SubElement(g, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
        if points:
            arr = ET.SubElement(g, "Array", {"as": "points"})
            for px, py in points:
                ET.SubElement(arr, "mxPoint", {"x": str(px), "y": str(py)})
        if label_pos:
            ET.SubElement(g, "mxPoint", {"x": str(label_pos[0]), "y": str(label_pos[1]), "as": "offset"})
        return c

    def arrow(self, x1, y1, x2, y2, label="", color=INK, dashed=False, points=None,
              above=True, parent="1"):
        """Orthogonal free_edge with the label sitting above the line -- the
        default you want for component diagrams, where labels below a line
        tend to land on whatever is underneath."""
        extra = "edgeStyle=orthogonalEdgeStyle;rounded=1;" + ("verticalAlign=bottom;" if above else "verticalAlign=top;")
        return self.free_edge(x1, y1, x2, y2, label, color, dashed, parent, points, style_extra=extra)


class Sequence:
    """UML sequence diagram.

    Participants are declared up front but DRAWN at finish(), so each lifeline
    is exactly as tall as the messages needed -- no guessing a height, no
    lifelines running off the page or stopping short.

        s = Sequence(p, [("user", "Engineer", "actor"),
                         ("api", "Function App", "azure"),
                         ("db", "Cosmos DB", "data")])
        s.msg("user", "api", "POST /orders")
        s.self_msg("api", "validate payload")
        s.msg("api", "db", "insert")
        s.msg("db", "api", "id", ret=True)
        with s.block("alt  payment authorised", "api", "db"):
            s.msg("api", "pay", "capture")
        s.finish()

    kinds: actor | azure | entra | data | ext  (colour only)
    """

    KIND_FILL = {"azure": BLUE_FILL, "entra": PURPLE_FILL, "data": GREEN_FILL, "ext": GREY_FILL}
    KIND_STROKE = {"azure": BLUE, "entra": PURPLE, "data": GREEN, "ext": GREY}

    def __init__(self, page: Page, participants, x0=60, gap=200, y0=70):
        self.p = page
        self.participants = participants
        self.x0, self.gap_x, self.y0 = x0, gap, y0
        self.x = {key: x0 + i * gap + 60 for i, (key, _, _) in enumerate(participants)}
        self.y = y0 + 70
        self.deferred = []

    def finish(self):
        """Draw the lifelines, then the messages on top of them."""
        height = self.y + 30 - self.y0
        for i, (key, label, kind) in enumerate(self.participants):
            x = self.x0 + i * self.gap_x
            if kind == "actor":
                self.p.box(label, x + 45, self.y0 - 10, 30, 50,
                           "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
                           f"outlineConnect=0;strokeColor={INK};fontSize=11;")
                # a vertical dashed edge: a rotated 'line' shape renders as a dot in draw.io
                self.p.free_edge(x + 60, self.y0 + 45, x + 60, self.y0 + height, "", GREY, True,
                                 style_extra="endArrow=none;strokeWidth=1;")
            else:
                self.p.box(label, x, self.y0, 120, height,
                           "shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;"
                           "collapsible=0;recursiveResize=0;outlineConnect=0;size=40;"
                           f"fillColor={self.KIND_FILL[kind]};strokeColor={self.KIND_STROKE[kind]};strokeWidth=1.5;"
                           f"fontSize=11;fontStyle=1;fontColor={INK};")
        for fn, args in self.deferred:
            fn(*args)

    def msg(self, src, dst, label, dy=34, ret=False, color=INK):
        """One message. `ret=True` draws the dashed open-arrow return."""
        x1, x2 = self.x[src], self.x[dst]
        extra = "verticalAlign=bottom;" + ("endArrow=open;endFill=0;" if ret else "")
        self.deferred.append((self.p.free_edge, (x1, self.y, x2, self.y, label, color, ret, "1", None, None, extra)))
        self.y += dy

    def self_msg(self, who, label, dy=44):
        """A participant acting on itself: validation, a local decision."""
        x = self.x[who]
        self.deferred.append((self.p.free_edge,
                              (x, self.y, x, self.y + 22, label, INK, False, "1",
                               [(x + 40, self.y), (x + 40, self.y + 22)], None,
                               "align=left;verticalAlign=middle;spacingLeft=48;")))
        self.y += dy

    @contextmanager
    def block(self, label, x_from_key, x_to_key, color=GREY):
        """A UML fragment -- alt / opt / loop -- around the messages inside it.

            with s.block("alt  ledger accepts", "settle", "ledger", color=GREEN):
                s.msg("settle", "ledger", "POST /entries")
                s.msg("ledger", "settle", "201", ret=True)

        Prefer this over calling frame() by hand: it reserves room for the
        frame's title before the first message and adds breathing room after
        the last one. Message labels sit ABOVE their line, so a frame drawn
        flush against the first message puts its title straight through that
        label -- which is exactly the bug this exists to prevent.
        """
        y0 = self.y
        self.y += 40          # the title box is 22px and the first label sits above its line
        yield
        self.frame(label, y0, self.y, x_from_key, x_to_key, color)
        self.y += 12

    def frame(self, label, y_from, y_to, x_from_key, x_to_key, color=GREY):
        """Draw a fragment box over an explicit y range. `block()` is usually
        what you want; use this when the range is not a simple nesting."""
        x1 = self.x[x_from_key] - 80
        x2 = self.x[x_to_key] + 80
        title_w = min(len(re.sub("<[^>]+>", "", label)) * 6 + 24, x2 - x1 - 40)
        self.p.box(label, x1, y_from, x2 - x1, y_to - y_from,
                   f"shape=umlFrame;whiteSpace=wrap;html=1;width={title_w};height=22;fillColor=none;"
                   f"strokeColor={color};fontSize=10;fontStyle=1;fontColor={color};dashed=1;")

    def gap(self, dy=16):
        self.y += dy

    def note(self, text, key, w=230, h=36, dx=20):
        """A sticky pinned beside a lifeline, for a caveat the messages cannot carry."""
        self.deferred.append((self.p.sticky, (text, self.x[key] + dx, self.y - 8, w, h)))
        self.y += h + 10


class Doc:
    """Collects pages and writes the .drawio file."""

    def __init__(self, path):
        self.path = Path(path)
        self.pages = []

    def add(self, *pages):
        self.pages.extend(pages)
        return self

    def write(self):
        mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device", "version": "24.7.0"})
        for page in self.pages:
            mxfile.append(page.diagram)
        xml = minidom.parseString(ET.tostring(mxfile, encoding="unicode")).toprettyxml(indent="  ")
        self.path.write_text(xml, encoding="utf-8")
        print(f"wrote {self.path} ({len(xml) // 1024} KB, {len(self.pages)} pages)")
        return self.path
