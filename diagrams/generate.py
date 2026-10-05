#!/usr/bin/env python3
"""
Architecture diagrams for Entra self-service on Power Platform (single tenant).

    python3 generate.py                 # writes entra-powerplatform.drawio
    python3 preview.py entra-powerplatform.drawio   # renders it in a browser

One function per page. Edit here and re-run; hand edits to the .drawio are
overwritten on the next run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio import (  # noqa: E402
    AZ, ICON, Doc, Page, Sequence,
    BLUE, BLUE_FILL, GREEN, GREEN_FILL, PURPLE, PURPLE_FILL,
    ORANGE, ORANGE_FILL, GREY, GREY_FILL, RED, RED_FILL, INK,
)

ICON.update({
    "papps": AZ + "power_platform/PowerApps.svg",
    "pauto": AZ + "power_platform/PowerAutomate.svg",
    "dataverse": AZ + "power_platform/Dataverse.svg",
    "pplat": AZ + "power_platform/PowerPlatform.svg",
    "connector": AZ + "integration/Logic_Apps_Custom_Connector.svg",
    "roles": AZ + "identity/Custom_Azure_AD_Roles.svg",
    "tenant": AZ + "identity/Tenant_Properties.svg",
    "cert": "img/lib/mscae/Certificate.svg",
    "user": AZ + "identity/Users.svg",   # general/User.svg does not exist in Azure2
})

APP_REG = "18723-Q-M365-Automation-AppProvisioning"
SITE = "/teams/m365automationqa"
SP_TEAL = "#03787C"      # SharePoint brand teal, used only for SharePoint stencils
AMBER, AMBER_FILL = "#C19C00", "#FFF4CE"


def stencil(p, shape, label, x, y, w, h, color, font=11):
    """draw.io's built-in Office stencils (SharePoint, Approvals, Outlook)."""
    style = (f"sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor={color};"
             f"labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;align=center;"
             f"shape={shape};fontSize={font};fontColor={INK};")
    return p.box(label, x, y, w, h, style)


def sp_list(p, label, x, y):
    return stencil(p, "mxgraph.office.concepts.list_library", label, x, y, 50, 46, SP_TEAL, font=10)


def title(p, head, sub, w=1100):
    p.note(f"<b style='font-size:16px'>{head}</b><br>{sub}", 40, 20, w, 50, font=12)


def small(text):
    return f"<font style='font-size:10px'>{text}</font>"


# ---------------------------------------------------------------------------
def page_glance() -> Page:
    p = Page("1 At a glance", 1400, 640)
    title(p, "Entra self-service on Power Platform &mdash; at a glance",
          "A team asks for an app registration in a Power App; two people approve; a flow creates it in Entra ID.")
    stages = [
        ("papps", "Ask", "The requester fills in a wizard in the Power App: app name, appCatID, owning team, roles, groups."),
        ("pauto", "Lock", "Flow ER-01 makes the request read-only, so what gets approved can't change afterwards."),
        ("users", "Approve", "The requester's manager approves, then the Entra ID team. A self-approval counts as a rejection."),
        ("pauto", "Create", "Flow ER-02 calls Microsoft Graph as the platform app and creates everything that was approved."),
        ("entra", "Stamp", "Every app, enterprise app and group carries the appCatID, request ID and owning team."),
    ]
    centres = [170, 430, 690, 950, 1210]
    for i, ((key, head, body), cx) in enumerate(zip(stages, centres), start=1):
        p.note(f"STEP {i}", cx - 40, 110, 80, 20, color=BLUE, font=10, align="center")
        p.icon(key, "", cx - 36, 140, 72, 72)
        p.note(f"<b style='font-size:14px'>{head}</b>", cx - 110, 226, 220, 24, font=13, align="center", color=INK)
        p.note(body, cx - 115, 254, 230, 90, font=11, align="center", color=INK)
    for a, b in zip(centres, centres[1:]):
        p.free_edge(a + 46, 176, b - 46, 176, "", color=GREY,
                    style_extra="edgeStyle=orthogonalEdgeStyle;strokeWidth=2;endArrow=blockThin;")
    p.node("<b>Where things live</b><br>" + small(
        "Power Apps canvas app &middot; SharePoint site " + SITE + " (4 lists) &middot; "
        "3 Power Automate flows &middot; 1 Entra app registration with a certificate"),
        60, 380, 600, 60, fill=GREY_FILL, stroke=GREY)
    p.node("<b>Licences</b><br>" + small(
        "App and ER-01 use Standard connectors (covered by Microsoft 365). ER-02 and ER-03 use a Premium "
        "connector: one Power Automate Premium licence for the flow owner."),
        700, 380, 640, 60, fill=GREY_FILL, stroke=GREY)
    p.sticky("<b>Nobody gets Entra admin rights.</b> Requesters, managers and even the flow owner can be "
             "read-only in Entra. Only the platform app registration holds Graph permissions, and only the flows "
             "can use it.", 60, 470, 600, 70)
    p.sticky("<b>Two approvals, one snapshot.</b> Approvers see a summary of the locked snapshot "
             "(ApprovedPayloadJson), and ER-02 executes only that snapshot, never the editable copy.",
             700, 470, 640, 70)
    return p


# ---------------------------------------------------------------------------
def page_context() -> Page:
    p = Page("2 Components", 1720, 1060)
    title(p, "Components &mdash; single tenant",
          "People on the left, the Power Platform environment in the middle, Entra ID on the right. "
          "Everything is in one Entra tenant.", w=1300)

    # people
    p.container("People", 40, 110, 200, 760, stroke=GREY)
    req = p.icon("users", "Requester<br>" + small("any member of a team"), 112, 170)
    mgr = p.icon("user", "Manager<br>" + small("from Entra 'Manager'"), 112, 380)
    team = p.icon("users", "Entra ID team<br>" + small("EntraApproverEmails"), 112, 540)
    adm = p.icon("user", "Entra admin<br>" + small("one-time setup"), 112, 720)

    # power platform
    p.container("Power Platform environment &middot; Entra Self-Service", 280, 110, 900, 760,
                stroke=BLUE, fill=BLUE_FILL)
    p.container("Power Apps", 300, 150, 170, 280, stroke=BLUE, fill="#FFFFFF")
    app = p.icon("papps", "Entra Self-Service<br>canvas app<br>" + small("5 screens"), 357, 200)
    p.note(small("Connectors as the user:<br>SharePoint &middot; Office 365 Users"), 312, 370, 150, 40, align="center")

    p.container("SharePoint site " + SITE, 500, 150, 260, 690, stroke=SP_TEAL, fill="#FFFFFF")
    l_req = sp_list(p, "<b>EntraRequests</b><br>" + small("one item per request"), 605, 200)
    l_apps = sp_list(p, "<b>EntraCatalogApps</b><br>" + small("apps your groups own"), 605, 350)
    l_grp = sp_list(p, "<b>EntraCatalogGroups</b><br>" + small("groups you can pick"), 605, 500)
    sp_list(p, "<b>EntraSettings</b><br>" + small("item 1 &middot; read by every flow"), 605, 680)

    p.container("Power Automate &middot; owner: flow account", 790, 150, 370, 690, stroke=BLUE, fill="#FFFFFF")
    er1 = p.icon("pauto", "<b>ER-01 Approvals</b><br>" + small("Standard connectors"), 850, 200)
    er2 = p.icon("pauto", "<b>ER-02 Execute</b><br>" + small("Premium &middot; concurrency 1"), 850, 350)
    er3 = p.icon("pauto", "<b>ER-03 Catalog sync</b><br>" + small("Premium &middot; hourly"), 850, 500)
    appr = stencil(p, "mxgraph.office.concepts.email_approved", "Approvals<br>" + small("Outlook &middot; Teams"),
                   1045, 202, 50, 50, BLUE, font=11)
    conn = p.icon("connector", "HTTP with Microsoft<br>Entra ID (preauthorized)<br>" + small("client certificate"),
                  1042, 410)
    p.note(small("Office 365 Users (Get manager) &middot; Outlook (mail) &middot; SharePoint &mdash; "
                 "all as the flow account"), 805, 760, 340, 40, align="center")

    # entra
    p.container("Microsoft Entra ID &middot; single tenant", 1220, 110, 460, 760, stroke=PURPLE, fill=PURPLE_FILL)
    graph = p.node("<b>Microsoft Graph</b><br>" + small("graph.microsoft.com/v1.0"), 1250, 410, 180, 56,
                   stroke=PURPLE)
    reg = p.icon("appreg", "<b>Platform app registration</b><br>" + small(APP_REG + "<br>"
                 "5 Graph application permissions<br>certificate credential"), 1312, 600)
    o_app = p.icon("appreg", "App registrations<br>" + small("App ID URI &middot; scopes &middot; roles"), 1560, 170)
    o_sp = p.icon("entapp", "Enterprise apps<br>" + small("assignment required"), 1560, 330)
    o_grp = p.icon("groups", "Security groups<br>" + small("team + role groups"), 1560, 490)
    o_ra = p.icon("roles", "App role<br>assignments", 1560, 650)

    # people -> app -> SharePoint
    p.arrow(168, 215, 357, 215, "uses the app", BLUE)
    p.edge(app, l_req, "Patch: new request", GREEN, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(605, 373, 470, 345, "reads", GREEN, dashed=True, points=[(530, 373), (530, 345)])
    p.arrow(605, 523, 530, 385, "", GREEN, dashed=True, points=[(530, 523)])
    # SharePoint <-> flows
    p.arrow(655, 206, 850, 206, "&#8594; item created &nbsp; &#8592; lock &middot; status", GREEN)
    p.arrow(850, 222, 655, 222, "", GREEN)
    st = p.arrow(655, 240, 850, 368, "Status = Approved", GREEN, points=[(768, 240), (768, 368)])
    st.set("style", st.get("style") + "startArrow=blockThin;startFill=1;")
    p.arrow(850, 392, 655, 392, "catalog new app / group", GREEN, above=False)
    p.arrow(850, 528, 655, 528, "upsert both catalog lists", GREEN)
    # flows -> approvals -> people
    p.edge(er1, appr, "start and wait", BLUE, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(1095, 227, 168, 408, "approval: manager first, then the Entra ID team", BLUE, dashed=True,
            points=[(1170, 227), (1170, 905), (205, 905), (205, 408)])
    p.arrow(205, 760, 168, 568, "", BLUE, dashed=True, points=[(205, 568)])
    # flows -> Graph
    p.arrow(906, 378, 1042, 430, "", PURPLE, points=[(985, 378), (985, 430)])
    p.arrow(906, 528, 1042, 446, "", PURPLE, points=[(985, 528), (985, 446)])
    p.edge(conn, graph, "token + Graph call", PURPLE, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(1098, 452, 1312, 628, "signs in as", PURPLE, dashed=True, points=[(1200, 452), (1200, 628)])
    for tgt_y in (198, 358, 518, 678):
        p.arrow(1430, 438, 1560, tgt_y, "", PURPLE, points=[(1490, 438), (1490, tgt_y)])
    p.note(small("every object stamped<br><b>appCatID &middot; requestId &middot; managedBy</b>"),
           1480, 760, 190, 40, align="center", color=PURPLE)
    # admin
    p.arrow(168, 748, 1340, 745, "one-time: create, upload certificate, grant admin consent", PURPLE, dashed=True,
            points=[(220, 748), (220, 940), (1340, 940)])

    p.sticky("<b>The Graph permissions belong to the app, not to people.</b> The flow owner can be read-only in "
             "Entra; ER-02 and ER-03 call Graph through a connection that signs in as the platform app with its "
             "certificate.", 40, 970, 620, 70)
    p.sticky("<b>Anyone who can edit ER-02 or ER-03 can use that connection.</b> Keep the flows in their own "
             "environment, with only the Entra ID team as co-owners.", 690, 970, 560, 70)
    return p


# ---------------------------------------------------------------------------
def page_identity() -> Page:
    p = Page("3 Who runs as whom", 1600, 980)
    title(p, "Identity &mdash; who each call runs as",
          "Three kinds of identity. Only the third one can change Entra ID.", w=1100)

    # lane 1: user
    p.container("&#9312; The requester (delegated, their own rights)", 40, 100, 1520, 200, stroke=GREY)
    u = p.icon("users", "Requester", 100, 170)
    a = p.icon("papps", "Power App", 380, 170)
    s1 = sp_list(p, "EntraRequests<br>" + small("item-level security"), 680, 175)
    o365 = p.icon("users", "Office 365 Users<br>" + small("profile, photo"), 980, 170)
    p.edge(u, a, "opens the app (signed in)", GREY, entry=(0, 0.5), exit=(1, 0.5))
    p.edge(a, s1, "SharePoint connector as the user", GREEN, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(436, 186, 1008, 170, "reads own profile", GREY, dashed=True, points=[(436, 150), (1008, 150)])
    p.node("<b>What a requester can do</b><br>" + small(
        "Create items, see only their own, read the catalog lists. After ER-01 locks a request "
        "they can no longer edit it. No Entra rights needed."), 1180, 150, 350, 110, fill="#FFFFFF", stroke=GREY)

    # lane 2: flow owner
    p.container("&#9313; The flow owner (connections created by the flow account)", 40, 330, 1520, 200,
                stroke=BLUE, fill=BLUE_FILL)
    fa = p.icon("user", "Flow account<br>" + small("owns ER-01/02/03"), 100, 400)
    f1 = p.icon("pauto", "ER-01 / ER-02 / ER-03", 380, 400)
    s2 = sp_list(p, "SharePoint<br>" + small("site owner"), 680, 405)
    ap = stencil(p, "mxgraph.office.concepts.email_approved", "Approvals &middot; Outlook<br>"
                 + small("Teams"), 983, 402, 50, 50, BLUE)
    p.edge(fa, f1, "owns + licensed", BLUE, entry=(0, 0.5), exit=(1, 0.5))
    p.edge(f1, s2, "lock, status, catalog", GREEN, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(436, 416, 1008, 402, "approvals and mail", BLUE, dashed=True, points=[(436, 378), (1008, 378)])
    p.node("<b>What the flow account needs</b><br>" + small(
        "Site owner on the SharePoint site (to break inheritance). Power Automate Premium for ER-02/ER-03. "
        "<b>No Entra role</b>; read-only is fine."), 1180, 380, 350, 110, fill="#FFFFFF", stroke=BLUE)

    # lane 3: application
    p.container("&#9314; The platform app (application permissions, used only by ER-02 / ER-03)", 40, 560, 1520, 300,
                stroke=PURPLE, fill=PURPLE_FILL)
    f2 = p.icon("pauto", "ER-02 / ER-03", 100, 640)
    c = p.icon("connector", "HTTP with Microsoft<br>Entra ID (preauthorized)", 380, 640)
    tok = p.icon("entra", "Entra token endpoint<br>" + small("login.microsoftonline.com"), 680, 640)
    g = p.node("<b>Microsoft Graph</b><br>" + small("checks the token's roles"), 940, 640, 180, 56, stroke=PURPLE)
    p.edge(f2, c, "Invoke an HTTP request", PURPLE, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(436, 656, 680, 656, "&#9312; client credentials, assertion signed with the certificate", PURPLE)
    p.arrow(680, 682, 436, 682, "&#9313; access token: aud graph &middot; roles = 5 permissions", PURPLE, above=False)
    p.arrow(436, 692, 1030, 696, "&#9314; Graph call with the token", PURPLE,
            points=[(470, 692), (470, 770), (1030, 770)])
    p.node("<b>Connection fields</b><br><font style='font-family:monospace;font-size:10px'>"
           "Auth type: Log in using a Client Certificate Auth<br>"
           "Resource URI: https://graph.microsoft.com<br>"
           "Base Resource URL: https://graph.microsoft.com<br>"
           "Tenant: &lt;Directory (tenant) ID&gt;<br>"
           "Client ID: &lt;appId of the platform app&gt;<br>"
           "Client certificate: .pfx + password</font>", 1160, 600, 380, 140, fill="#FFFFFF", stroke=PURPLE)
    p.note(small("Graph permissions (admin-consented): Application.ReadWrite.All &middot; "
                 "AppRoleAssignment.ReadWrite.All &middot; Group.ReadWrite.All &middot; Directory.Read.All &middot; "
                 "User.Read.All"), 380, 800, 760, 30, color=PURPLE)

    p.sticky("<b>Don't pick 'Log in with Microsoft Entra ID'</b> on the connection: that calls Graph as the flow "
             "account, and a read-only account gets <i>Insufficient privileges</i>.", 40, 885, 620, 60)
    p.sticky("<b>The certificate stays inside the connection.</b> Flow editors can use it but can't read it; "
             "run history never shows it.", 690, 885, 520, 60)
    return p


# ---------------------------------------------------------------------------
def page_seq_approvals() -> Page:
    p = Page("4 Sequence - submit and approve", 1700, 1500)
    title(p, "Sequence &mdash; submit and approve (ER-01)",
          "From the Submit button to Status = Approved, including both ways a request is rejected.")
    s = Sequence(p, [
        ("req", "Requester", "actor"),
        ("app", "Power App", "azure"),
        ("sp", "EntraRequests", "data"),
        ("er1", "ER-01 Approvals", "azure"),
        ("o365", "Office 365 Users", "ext"),
        ("appr", "Approvals", "azure"),
        ("mgr", "Manager", "actor"),
        ("team", "Entra ID team", "actor"),
    ], x0=40, gap=205, y0=80)
    s.msg("req", "app", "fill in the wizard, Submit")
    s.self_msg("app", "validate all sections &middot; build PayloadJson")
    s.msg("app", "sp", "Patch item: Status = Submitted, PayloadJson")
    s.msg("sp", "er1", "trigger: item created (Status = Submitted)")
    s.msg("er1", "sp", "break inheritance &middot; Owners Full Control &middot; requester Read")
    s.msg("er1", "sp", "Get locked item")
    s.msg("sp", "er1", "PayloadJson (now read-only for the requester)", ret=True)
    s.msg("er1", "o365", "Get manager (V2) for the requester")
    s.msg("o365", "er1", "manager, or failure &#8594; FallbackApproverEmail", ret=True)
    s.msg("er1", "sp", "PendingManagerApproval &middot; ApprovedPayloadJson &middot; RequestSummary")
    s.msg("er1", "appr", "start and wait: assigned to the manager")
    s.msg("appr", "mgr", "Outlook / Teams approval card")
    s.msg("mgr", "appr", "Approve or Reject + comment")
    s.msg("appr", "er1", "outcome &middot; responder &middot; comment", ret=True)
    s.self_msg("er1", "responder = requester? &#8594; treat as Reject")
    with s.block("alt  manager rejects", "req", "er1", color=RED):
        s.msg("er1", "sp", "ManagerDecision = Rejected &middot; Status = Rejected", color=RED)
        s.msg("er1", "req", "email: rejected by your manager", color=RED)
    with s.block("alt  manager approves", "req", "team", color=GREEN):
        s.msg("er1", "sp", "ManagerDecision = Approved &middot; Status = PendingEntraApproval")
        s.msg("er1", "appr", "start and wait: assigned to EntraApproverEmails")
        s.msg("appr", "team", "approval card (first to respond)")
        s.msg("team", "appr", "Approve or Reject")
        s.msg("appr", "er1", "outcome", ret=True)
        s.msg("er1", "sp", "EntraDecision &middot; Status = Approved (or Rejected)", color=GREEN)
        s.msg("er1", "req", "email: approved and being applied")
    s.gap()
    s.note("<b>Status = Approved is written by the flow account.</b> That is what ER-02 checks before it runs "
           "anything.", "sp", w=440, h=40)
    s.finish()
    return p


# ---------------------------------------------------------------------------
def page_seq_execute() -> Page:
    p = Page("5 Sequence - create app registration", 1700, 1560)
    title(p, "Sequence &mdash; ER-02 creates an app registration",
          "Every Graph call goes through the client-certificate connection; the token is fetched once and reused.")
    s = Sequence(p, [
        ("sp", "EntraRequests", "data"),
        ("er2", "ER-02 Execute", "azure"),
        ("conn", "HTTP with Entra ID", "azure"),
        ("tok", "Entra token endpoint", "entra"),
        ("graph", "Microsoft Graph", "entra"),
        ("cat", "Catalog lists", "data"),
        ("req", "Requester", "actor"),
    ], x0=40, gap=230, y0=80)
    s.msg("sp", "er2", "trigger: Status = Approved (one run at a time)")
    s.self_msg("er2", "guard: Editor = flow account &middot; both decisions Approved")
    s.msg("er2", "sp", "Status = InProgress")
    s.msg("er2", "conn", "Invoke an HTTP request")
    s.msg("conn", "tok", "client credentials &middot; certificate assertion")
    s.msg("tok", "conn", "token: aud graph &middot; 5 roles (cached)", ret=True)
    s.msg("conn", "graph", "GET /users/{requester}  &#8594; object id")
    with s.block("alt  owning team is new", "er2", "cat", color=GREY):
        s.msg("er2", "graph", "POST /groups  (owners, appCatID in description)")
        s.msg("er2", "cat", "create EntraCatalogGroups row")
    with s.block("else  existing team", "er2", "graph", color=GREY):
        s.msg("er2", "graph", "POST /users/{id}/checkMemberGroups")
        s.msg("graph", "er2", "member? (no &#8594; Failed)", ret=True)
    s.msg("er2", "graph", "POST /applications  (tags, notes, roles, redirect URIs, claims)")
    s.msg("graph", "er2", "id &middot; appId &middot; appRoles[]", ret=True)
    with s.block("opt  expose an API", "er2", "graph", color=GREY):
        s.msg("er2", "graph", "PATCH /applications/{id}  identifierUris + scopes")
    with s.block("loop  each owner", "er2", "graph", color=GREY):
        s.msg("er2", "graph", "POST /applications/{id}/owners/$ref")
    with s.block("loop  until 201 (new app replicating)", "er2", "graph", color=ORANGE):
        s.msg("er2", "graph", "POST /servicePrincipals  {appId, tags}")
    with s.block("loop  each role &#215; group", "er2", "cat", color=GREY):
        s.msg("er2", "graph", "POST /groups  (only for new groups)")
        s.msg("er2", "graph", "POST /servicePrincipals/{sp}/appRoleAssignedTo")
    s.msg("er2", "cat", "create EntraCatalogApps row")
    s.msg("er2", "sp", "Status = Completed &middot; ResultJson &middot; CompletedAt", color=GREEN)
    s.msg("er2", "req", "email: your request is complete", color=GREEN)
    s.gap()
    s.note("<b>Any failure inside Try</b> jumps to Catch: Status = Failed, ErrorMessage, ResultJson (what was "
           "already created), email to the requester and the Entra ID team.", "er2", w=520, h=48)
    s.finish()
    return p


# ---------------------------------------------------------------------------
def page_flow_er01() -> Page:
    p = Page("6 Flow - ER-01 Approvals", 1300, 1240)
    title(p, "Flowchart &mdash; ER-01 Approvals",
          "Standard connectors only. Every rejection exits to the right; the approved path runs straight down.")
    W = 300
    X = 400
    t0 = p.terminal("Item created &middot; Status = Submitted", X + 40, 90, BLUE_FILL, BLUE, w=220)
    n1 = p.node("<b>Lock</b><br>" + small("break inheritance &middot; Owners Full Control &middot; requester Read"),
                X, 170, W, 56, stroke=BLUE)
    n2 = p.node("<b>Snapshot</b><br>" + small("Get locked item &#8594; Payload &middot; Summary"), X, 260, W, 56,
                stroke=BLUE)
    d1 = p.decision("Manager found<br>in Entra?", X + 65, 350)
    fb = p.node("Use FallbackApproverEmail", 800, 370, 220, 40, stroke=ORANGE, fill=ORANGE_FILL)
    n3 = p.node("<b>Status = PendingManagerApproval</b><br>" + small("ApprovedPayloadJson &middot; ManagerEmail"),
                X, 460, W, 56, stroke=BLUE)
    n4 = p.node("<b>Approval: manager</b><br>" + small("start and wait &middot; first to respond"), X, 550, W, 56,
                stroke=BLUE)
    d2 = p.decision("Approved and<br>not by the requester?", X + 65, 640)
    r1 = p.terminal("Rejected &middot; email requester", 800, 658, RED_FILL, RED, w=240)
    n5 = p.node("<b>Status = PendingEntraApproval</b><br>" + small("notify Entra team (Teams, optional)"),
                X, 750, W, 56, stroke=BLUE)
    n6 = p.node("<b>Approval: Entra ID team</b><br>" + small("EntraApproverEmails &middot; first to respond"),
                X, 840, W, 56, stroke=BLUE)
    d3 = p.decision("Approved and<br>not by the requester?", X + 65, 930)
    r2 = p.terminal("Rejected &middot; email requester", 800, 948, RED_FILL, RED, w=240)
    ok = p.terminal("Status = Approved &#8594; starts ER-02", X + 20, 1060, GREEN_FILL, GREEN, w=260)

    p.edge(t0, n1); p.edge(n1, n2); p.edge(n2, d1)
    p.edge(d1, n3, "yes")
    p.edge(d1, fb, "no", ORANGE)
    p.edge(fb, n3, "", ORANGE, exit=(0.5, 1), entry=(1, 0.5), points=[(910, 488)])
    p.edge(n3, n4); p.edge(n4, d2)
    p.edge(d2, n5, "yes"); p.edge(d2, r1, "no", RED)
    p.edge(n5, n6); p.edge(n6, d3)
    p.edge(d3, ok, "yes", GREEN); p.edge(d3, r2, "no", RED)

    p.sticky("<b>Why lock before snapshot.</b> The requester can edit the item until step 1 runs. Reading "
             "PayloadJson again after the lock gives a copy nobody but site owners can change.", 40, 170, 320, 90)
    p.sticky("<b>Self-approval rule.</b> If the responder's email equals the requester's, the outcome is "
             "Reject, even if they clicked Approve.", 40, 640, 320, 74)
    p.note(small("Rejected requests keep ManagerDecision / EntraDecision, who and when, and the comment."),
           800, 1010, 300, 40)
    return p


# ---------------------------------------------------------------------------
def page_flow_er02() -> Page:
    p = Page("7 Flow - ER-02 Execute", 1500, 1300)
    title(p, "Flowchart &mdash; ER-02 Execute",
          "Premium. Runs one request at a time. Guards first, then one scope per request type, then role assignments.")
    X, W = 470, 320
    t0 = p.terminal("Item changed &middot; Status = Approved", X + 50, 90, BLUE_FILL, BLUE, w=220)
    d0 = p.decision("Set by the flow account<br>and both decisions<br>Approved?", X + 60, 165, w=200, h=90)
    stop = p.terminal("Terminate: nothing runs", 960, 188, RED_FILL, RED, w=220)

    p.container("Try (scope)", 300, 275, 870, 775, stroke=BLUE, fill=BLUE_FILL)
    n1 = p.node("<b>Status = InProgress</b><br>" + small("Graph: GET requester id &middot; base tags &middot; group meta"),
                X, 330, W, 56, stroke=BLUE)
    d1 = p.decision("Change to an<br>existing app?", X + 75, 420)
    d2 = p.decision("Requester in the team<br>or an owner, and<br>appCatID matches?", 820, 410, w=200, h=100)
    f1 = p.terminal("Failed: not your app", 1200, 438, RED_FILL, RED, w=200)
    sw = p.node("<b>Switch: RequestType</b>", X, 540, W, 40, stroke=BLUE, bold=False)
    cases = [
        ("createAppRegistration", "team group &middot; app &middot; expose API &middot; owners &middot; enterprise app"),
        ("createGroup", "security group with owners &amp; members"),
        ("exposeApi", "add App ID URI &middot; scopes"),
        ("addAppRoles", "add roles &middot; queue role groups"),
        ("assignGroupsToAppRoles", "queue assignments &middot; enterprise app if missing"),
        ("createServicePrincipal", "enterprise app (fails if one exists)"),
    ]
    xs = [315, 455, 595, 735, 875, 1015]
    case_ids = []
    for (name, what), cx in zip(cases, xs):
        case_ids.append(p.node(f"<b style='font-size:10px'>Do {name}</b><br>" + small(what),
                               cx, 620, 136, 90, stroke=BLUE, font=10))
    n2 = p.node("<b>Role assignments</b> (shared by 3 cases)<br>" + small(
        "for each queued item: create the group if new &#8594; POST appRoleAssignedTo"), X - 40, 770, W + 80, 56,
        stroke=BLUE)
    n3 = p.node("<b>Default access?</b><br>" + small("new app, assignment required, no roles &#8594; team gets "
                                                    "Default Access"), X - 40, 860, W + 80, 56, stroke=BLUE)
    done = p.terminal("Completed &middot; ResultJson &middot; email requester", X + 10, 960, GREEN_FILL, GREEN, w=300)

    p.container("Catch (run after Try: failed / timed out)", 300, 1090, 870, 120, stroke=RED, fill=RED_FILL)
    p.node("<b>Failed</b> &middot; ErrorMessage = first failed action &middot; ResultJson = what was already "
           "created &middot; email requester + Entra ID team", 330, 1130, 810, 50, stroke=RED)

    p.edge(t0, d0)
    p.edge(d0, stop, "no", RED)
    p.edge(d0, n1, "yes")
    p.edge(n1, d1)
    p.edge(d1, d2, "yes")
    p.edge(d2, f1, "no", RED)
    p.edge(d2, sw, "yes", exit=(0.5, 1), entry=(1, 0.5), points=[(920, 560)])
    p.edge(d1, sw, "no")
    for cid, cx in zip(case_ids, xs):
        p.edge(sw, cid, "", BLUE, exit=(0.5, 1), entry=(0.5, 0), points=[(630, 600), (cx + 68, 600)])
    for cid, cx in zip(case_ids, xs):
        p.edge(cid, n2, "", GREY, exit=(0.5, 1), entry=(0.5, 0), points=[(cx + 68, 745), (630, 745)])
    p.edge(n2, n3); p.edge(n3, done, "", GREEN)
    p.arrow(1000, 1050, 1000, 1090, "any action fails", RED, dashed=True, above=False)

    p.sticky("<b>Why the guard.</b> A site owner editing Status by hand is not the flow account, so the run "
             "stops before any Graph call.", 40, 160, 240, 100)
    p.sticky("<b>Retries.</b> Enterprise app creation retries until the new app has replicated; role "
             "assignment retries 4&#215; with backoff.", 1200, 620, 260, 90)
    p.sticky("<b>Not idempotent.</b> Re-running a failed createAppRegistration creates a second app; "
             "ResultJson lists what to clean up first.", 1200, 1110, 260, 90)
    return p


# ---------------------------------------------------------------------------
def page_flow_er03() -> Page:
    p = Page("8 Flow - ER-03 Catalog sync", 1300, 1020)
    title(p, "Flowchart &mdash; ER-03 Catalog sync",
          "Hourly. Reads Entra ID, writes the two catalog lists the app uses for its pickers. Never changes Entra.")
    X, W = 380, 360
    t0 = p.terminal("Recurrence &middot; every hour", X + 70, 90, BLUE_FILL, BLUE, w=220)
    n1 = p.node("<b>GET /applications</b><br>" + small("$filter = tags/any(t: t eq 'managedBy:&lt;tag&gt;')"),
                X, 170, W, 56, stroke=PURPLE)
    p.container("For each app", X - 30, 260, W + 60, 330, stroke=BLUE, fill=BLUE_FILL)
    p.note(small("concurrency 1"), X + W - 80, 266, 100, 20, align="right")
    a1 = p.node("team id from the <b>team:</b> tag &#8594; transitive members", X, 300, W, 44, stroke=PURPLE)
    a2 = p.node("owners &middot; enterprise app id", X, 370, W, 44, stroke=PURPLE)
    a3 = p.node("<b>Upsert EntraCatalogApps</b><br>" + small("roles, scopes, TeamMemberUpns, OwnerUpns"),
                X, 440, W, 56, stroke=GREEN)
    a4 = p.node("ensure the team has an EntraCatalogGroups row", X, 520, W, 44, stroke=GREEN)
    n2 = p.node("<b>Get all EntraCatalogGroups rows</b>", X, 620, W, 44, stroke=GREEN)
    p.container("For each group", X - 30, 690, W + 60, 200, stroke=BLUE, fill=BLUE_FILL)
    p.note(small("concurrency 5"), X + W - 80, 696, 100, 20, align="right")
    b1 = p.node("GET group &middot; transitive members &middot; owners", X, 730, W, 44, stroke=PURPLE)
    b2 = p.node("<b>Update row</b><br>" + small("appCatID parsed from the description &middot; Member/OwnerUpns"),
                X, 800, W, 56, stroke=GREEN)
    end = p.dot(X + W / 2 - 12, 920)
    for a, b in [(t0, n1), (n1, a1), (a1, a2), (a2, a3), (a3, a4), (a4, n2), (n2, b1), (b1, b2), (b2, end)]:
        p.edge(a, b)
    p.node("<b>UPN lists format</b><br><font style='font-family:monospace;font-size:10px'>"
           ";alex@contoso.com;sam@contoso.com;</font><br>" + small("lower case, ';' at both ends, so the app "
           "can test <i>\";\" &amp; upn &amp; \";\" in TeamMemberUpns</i>"), 820, 300, 400, 90, stroke=GREY,
           fill=GREY_FILL)
    p.sticky("<b>Onboarding an existing group:</b> add a row to EntraCatalogGroups with just Title and GroupId, "
             "then run ER-03 manually. It fills in members, owners and appCatID.", 820, 620, 400, 74)
    p.sticky("<b>Deleted group?</b> GET returns 404 and that iteration fails. Add a branch with run-after "
             "'has failed' to flag or delete the row.", 820, 760, 400, 64)
    return p


# ---------------------------------------------------------------------------
def page_lifecycle() -> Page:
    p = Page("9 Request lifecycle", 1500, 760)
    title(p, "Request lifecycle &mdash; EntraRequests.Status",
          "Transitions name who makes them. Only the flow account moves a request past Submitted.")
    start = p.dot(40, 228)
    sub = p.state("Submitted", 110, 210, fill=GREY_FILL, stroke=GREY, w=150)
    pm = p.state("PendingManager<br>Approval", 340, 210, fill=AMBER_FILL, stroke=AMBER, w=160)
    pe = p.state("PendingEntra<br>Approval", 590, 210, fill=AMBER_FILL, stroke=AMBER, w=160)
    ap = p.state("Approved", 840, 210, fill=BLUE_FILL, stroke=BLUE, w=150)
    ip = p.state("InProgress", 1070, 210, fill=BLUE_FILL, stroke=BLUE, w=150)
    co = p.state("Completed", 1290, 110, fill=GREEN_FILL, stroke=GREEN, w=150)
    fa = p.state("Failed", 1290, 330, fill=RED_FILL, stroke=RED, w=150)
    rj = p.state("Rejected", 470, 420, fill=RED_FILL, stroke=RED, w=150)
    p.edge(start, sub)
    p.edge(sub, pm, "ER-01<br>lock + snapshot")
    p.edge(pm, pe, "manager<br>approves")
    p.edge(pe, ap, "Entra team<br>approves")
    p.edge(ap, ip, "ER-02<br>guard passes")
    p.edge(ip, co, "all Graph calls<br>succeed", GREEN, exit=(1, 0.3), entry=(0, 0.5))
    p.edge(ip, fa, "a call fails<br>(Catch)", RED, exit=(1, 0.7), entry=(0, 0.5))
    p.edge(pm, rj, "manager rejects<br>or self-approves", RED, exit=(0.5, 1), entry=(0.25, 0))
    p.edge(pe, rj, "team rejects<br>or self-approves", RED, exit=(0.5, 1), entry=(0.75, 0))
    p.edge(fa, ap, "retry: flow account sets Approved again", ORANGE, dashed=True,
           exit=(0.5, 1), entry=(0.5, 1), points=[(1365, 520), (915, 520)])
    p.table("Who writes Status", [
        "Requester (Power App) .... Submitted",
        "ER-01 (flow account) ..... PendingManagerApproval, PendingEntraApproval, Approved, Rejected",
        "ER-02 (flow account) ..... InProgress, Completed, Failed",
        "Site owners .............. can edit, but ER-02 ignores edits not made by the flow account",
    ], 40, 580, 760, GREY, mono=True)
    p.sticky("<b>Versioning is the audit trail.</b> EntraRequests keeps 500 versions, so every status change, "
             "decision and who made it is recorded on the item.", 840, 600, 420, 70)
    return p


# ---------------------------------------------------------------------------
def page_data() -> Page:
    p = Page("10 Data model", 1700, 1040)
    title(p, "Data model &mdash; SharePoint lists, payload and Entra stamps",
          "Internal column names shown. Bold = written once and never changed by users.", w=1200)
    p.container("SharePoint site " + SITE, 40, 100, 1040, 900, stroke=SP_TEAL, fill="#F2FAFA")
    req = p.table("EntraRequests &middot; one item per request", [
        "<b>Title</b>: REQ-2610-K7M4X2 (request id, indexed)",
        "<b>RequestType</b>: choice, 6 types &middot; <b>Status</b>: choice, 8 states",
        "AppCatId &middot; TargetDisplayName &middot; TargetObjectId (change requests)",
        "Justification &middot; TicketReference",
        "PayloadJson: written by the app (editable until ER-01 locks)",
        "<b>ApprovedPayloadJson</b>: snapshot after the lock, the only thing ER-02 runs",
        "RequestSummary: text approvers see",
        "ManagerEmail, ManagerName &middot; ManagerDecision (choice) &middot; ...By &middot; ...At &middot; ...Comment",
        "EntraDecision (choice) &middot; EntraDecisionBy &middot; EntraDecisionAt &middot; EntraComment",
        "ResultJson: ids created &middot; ErrorMessage &middot; CompletedAt",
        "<b>Created By</b> (built in): the requester, can't be faked",
    ], 60, 150, 640, SP_TEAL)
    apps = p.table("EntraCatalogApps &middot; written by ER-02 / ER-03", [
        "Title &middot; <b>ObjectId</b> &middot; <b>AppId</b> &middot; AppCatId",
        "TeamGroupId &middot; TeamGroupName (from team: / teamName: tags)",
        "ServicePrincipalId &middot; IdentifierUri",
        "AppRolesJson &middot; ScopesJson",
        "TeamMemberUpns &middot; OwnerUpns (;upn;upn;)",
        "LastSynced",
    ], 60, 560, 480, SP_TEAL)
    grp = p.table("EntraCatalogGroups &middot; groups users can pick", [
        "Title &middot; <b>GroupId</b> &middot; AppCatId (from description)",
        "Description",
        "OwnerUpns &middot; MemberUpns (;upn;upn;)",
        "LastSynced",
    ], 570, 560, 490, SP_TEAL)
    p.table("EntraSettings &middot; exactly one item (ID 1)", [
        "TenantId &middot; GraphClientId &middot; ManagedByTag",
        "ServiceAccountUpn (lower case, checked by ER-02)",
        "EntraApproverEmails &middot; FallbackApproverEmail",
        "KeyVaultName &middot; PfxSecretName &middot; PfxPasswordSecretName (plain HTTP option only)",
        "PowerAppUrl (link in approval cards)",
    ], 60, 790, 640, SP_TEAL)
    p.node("<b>Permissions</b><br>" + small(
        "EntraRequests: item-level (read/edit own), then ER-01 locks each item: Owners Full Control, requester "
        "Read.<br>Catalog lists: members Read.<br>EntraSettings: owners only."), 730, 790, 330, 120,
        stroke=SP_TEAL)
    p.edge(req, apps, "TargetObjectId = ObjectId", GREY, dashed=True, exit=(0.3, 1), entry=(0.4, 0))

    p.container("PayloadJson &middot; createAppRegistration", 1110, 100, 560, 440, stroke=BLUE, fill=BLUE_FILL)
    p.table("payload", [
        "displayName &middot; description &middot; signInAudience",
        "owningGroup { mode: new|existing, id, displayName, ownerIds }",
        "redirectUrisWeb &middot; redirectUrisSpa (';' separated)",
        "exposeApi { enabled, identifierUriTemplate, scopes[] }",
        "optionalClaimsIdToken &middot; optionalClaimsAccessToken &middot; groupMembershipClaims",
        "appRoles[] { value, displayName, description, allowedMemberTypes,",
        "    assignGroups[] { mode, id, displayName, ownerIds } }",
        "createServicePrincipal &middot; appRoleAssignmentRequired",
        "additionalOwnerIds &middot; tags ('key=value;...')",
    ], 1130, 150, 520, BLUE, mono=True)
    p.note(small("Other types: createGroup, exposeApi, addAppRoles, assignGroupsToAppRoles, createServicePrincipal "
                 "(see docs/03 &sect;3.5). No field identifies the requester; ER-02 uses Created By."),
           1130, 470, 520, 50)

    p.container("Stamped on every object Entra creates", 1110, 570, 560, 430, stroke=PURPLE, fill=PURPLE_FILL)
    p.table("app registration &middot; tags", [
        "appCatID:&lt;id&gt; &middot; team:&lt;group id&gt; &middot; teamName:&lt;name&gt;",
        "createdBy:&lt;upn&gt; &middot; createdById:&lt;oid&gt; &middot; createdTimestamp",
        "lastUpdatedBy &middot; lastUpdatedTimestamp &middot; requestId:REQ-...",
        "managedBy:&lt;ManagedByTag&gt; &middot; optional key:value tags",
    ], 1130, 615, 520, PURPLE, mono=True)
    p.table("app registration &middot; notes", [
        "appCatID=...; requestId=...; createdBy=...; managedBy=...",
    ], 1130, 785, 520, PURPLE, mono=True)
    p.table("group &middot; end of description", [
        "[appCatID=...; requestId=...; createdBy=...; managedBy=...]",
    ], 1130, 865, 520, PURPLE, mono=True)
    p.note(small("Enterprise apps get the same tags plus WindowsAzureActiveDirectoryIntegratedApp. "
                 "ER-03 finds managed apps by the managedBy tag."), 1130, 940, 520, 40, color=PURPLE)
    return p


# ---------------------------------------------------------------------------
def page_security() -> Page:
    p = Page("11 Security and permissions", 1700, 920)
    title(p, "Security &mdash; who can do what, and the guards in the flows",
          "Least privilege for people; one tightly held app identity for Graph.", w=1200)
    p.table("People and their access", [
        "<b>Requester</b>: SharePoint Member &middot; uses the app &middot; no Entra role",
        "<b>Manager</b>: answers approvals only (Outlook / Teams)",
        "<b>Entra ID team</b>: second approval &middot; site Owner &middot; flow co-owners",
        "<b>Flow account</b>: owns the flows &middot; site Owner &middot; Power Automate Premium &middot; Entra read-only",
        "<b>Entra admin</b>: one-time admin consent for the platform app",
        "<b>Power Platform admin</b>: environment, DLP policy, Dataverse for Approvals",
    ], 40, 100, 780, GREY)
    p.table("Platform app &middot; Microsoft Graph application permissions", [
        "<b>Application.ReadWrite.All</b>: app registrations, enterprise apps, URIs, scopes, roles, owners, tags",
        "<b>AppRoleAssignment.ReadWrite.All</b>: assign groups to app roles",
        "<b>Group.ReadWrite.All</b>: create security groups with owners and members",
        "<b>Directory.Read.All</b>: checkMemberGroups, transitive members for the catalog",
        "<b>User.Read.All</b>: requester object id, owners and members",
        "Credential: <b>certificate only</b> (no client secret) &middot; admin consent required",
    ], 860, 100, 800, PURPLE)
    p.table("SharePoint permissions", [
        "Site Owners: Entra ID team + flow account (Full Control)",
        "Site Members: everyone who may raise requests (Edit)",
        "EntraRequests: item-level &middot; read and edit own items only",
        "Each request after ER-01: inheritance broken &middot; Owners Full Control &middot; requester Read",
        "Catalog lists: Members Read &middot; EntraSettings: Owners only",
    ], 40, 330, 780, SP_TEAL)
    p.table("Power Platform governance", [
        "Dedicated environment 'Entra Self-Service' &middot; makers = Entra ID team only",
        "DLP: SharePoint, Approvals, Office 365 Users, Outlook, Teams, HTTP with Entra ID (+ HTTP, Key Vault)",
        "App shared as User (never Co-owner) &middot; flows: Entra ID team as co-owners only",
        "Connection 'HTTP with Entra ID' (cert) owned by the flow account, not shared further",
    ], 860, 330, 800, BLUE)

    p.container("Guards along the request path", 40, 540, 1620, 240, stroke=BLUE, fill=BLUE_FILL)
    guards = [
        ("papps", "&#9312; Created By", "The requester is the item's built-in Created By. Nothing in the payload "
         "names them."),
        ("pauto", "&#9313; Lock + snapshot", "ER-01 makes the item read-only, then copies PayloadJson into "
         "ApprovedPayloadJson."),
        ("users", "&#9314; Two approvals", "Manager, then Entra ID team. A responder equal to the requester counts "
         "as Reject."),
        ("pauto", "&#9315; Editor check", "ER-02 runs only if the last editor is the flow account and both "
         "decisions are Approved."),
        ("groups", "&#9316; Ownership", "Changes to an existing app need team membership or ownership, and a "
         "matching appCatID."),
        ("entra", "&#9317; Stamping", "Every object carries appCatID, requestId, createdBy, managedBy for "
         "audit and sync."),
    ]
    for i, (key, head, body) in enumerate(guards):
        cx = 180 + i * 260
        p.icon(key, "", cx - 28, 590, 56, 56)
        p.note(f"<b style='font-size:12px'>{head}</b>", cx - 120, 660, 240, 22, align="center", color=INK)
        p.note(body, cx - 120, 686, 240, 80, font=11, align="center", color=INK)
    for i in range(5):
        a = 180 + i * 260
        p.free_edge(a + 40, 618, a + 260 - 40, 618, "", GREY,
                    style_extra="edgeStyle=orthogonalEdgeStyle;strokeWidth=2;endArrow=blockThin;")

    p.sticky("<b>The one real risk.</b> Whoever can edit ER-02 or ER-03 can make any Graph call the platform "
             "app is allowed to make. Treat flow co-ownership like an Entra admin role.", 40, 810, 560, 70)
    p.sticky("<b>Rotate the certificate yearly.</b> Upload the new one to the app registration, update the "
             "connection, then remove the old one. If other automations share the app, give this solution its "
             "own certificate.", 630, 810, 620, 70)
    p.sticky("<b>Audit:</b> EntraRequests versions, flow run history, Entra audit log (initiated by the "
             "platform app).", 1280, 810, 380, 70)
    return p


# ---------------------------------------------------------------------------
def page_deploy() -> Page:
    p = Page("12 Deployment and build order", 1700, 900)
    title(p, "Deployment &mdash; what exists, and the order to build it",
          "Three places to configure: Entra ID, the SharePoint site, and the Power Platform environment.", w=1200)

    p.container("Microsoft Entra ID tenant", 40, 100, 520, 560, stroke=PURPLE, fill=PURPLE_FILL)
    p.icon("appreg", "<b>Platform app registration</b><br>" + small("18723-Q-M365-<br>Automation-AppProvisioning<br>"
           "certificate &middot; 5 Graph permissions"), 160, 160)
    p.icon("user", "<b>Flow account</b><br>" + small("member user<br>M365 + Power Automate Premium"), 160, 340)
    p.icon("users", "<b>Requesters</b><br>" + small("Manager attribute set<br>(for Get manager)"), 160, 500)
    p.node("<b>Copy for later</b><br><font style='font-family:monospace;font-size:10px'>"
           "Directory (tenant) ID<br>Application (client) ID<br>.pfx + password</font>", 330, 160, 200, 80,
           stroke=PURPLE)
    p.node("<b>Check in Entra</b><br>" + small("API permissions: 'Granted for &lt;tenant&gt;'<br>"
           "Certificates: your thumbprint<br>Conditional Access: no sign-in frequency on the flow account"),
           330, 330, 200, 110, stroke=PURPLE)

    p.container("SharePoint site " + SITE, 590, 100, 500, 560, stroke=SP_TEAL, fill="#F2FAFA")
    for i, (name, note) in enumerate([
        ("EntraRequests", "item-level security &middot; versioning 500"),
        ("EntraCatalogApps", "members Read"),
        ("EntraCatalogGroups", "members Read"),
        ("EntraSettings", "owners only &middot; item ID 1"),
    ]):
        sp_list(p, f"<b>{name}</b><br>" + small(note), 670, 160 + i * 120)
    p.node("<b>sharepoint/provision.ps1</b><br>" + small("creates all 4 lists, columns, indexes, permissions and "
           "the settings item (PnP PowerShell)"), 840, 160, 220, 90, stroke=SP_TEAL)
    p.node("<b>Site groups</b><br>" + small("Owners: Entra ID team + flow account<br>Members: requesters"),
           840, 300, 220, 70, stroke=SP_TEAL)

    p.container("Power Platform environment &middot; Entra Self-Service (solution)", 1120, 100, 540, 560,
                stroke=BLUE, fill=BLUE_FILL)
    p.icon("papps", "<b>Entra Self-Service</b><br>" + small("paste 5 pa.yaml screens &middot; publish &middot; "
           "share as User").replace(" &middot; publish", "<br>publish"), 1220, 160)
    p.icon("pauto", "<b>ER-01 &middot; ER-02 &middot; ER-03</b><br>" + small("built from docs/04 &middot; "
           "owner = flow account").replace(" &middot; owner", "<br>owner"), 1220, 330)
    p.icon("dataverse", "<b>Dataverse</b><br>" + small("required by Approvals"), 1220, 490)
    p.table("Connections (flow account)", [
        "SharePoint &middot; Office 365 Users",
        "Approvals &middot; Office 365 Outlook",
        "Microsoft Teams (optional)",
        "<b>HTTP with Entra ID</b>: client certificate",
    ], 1380, 160, 260, BLUE)
    p.node("<b>Licences</b><br>" + small("Users: Microsoft 365 (Standard connectors)<br>Flow account: "
           "Power Automate Premium"), 1380, 330, 260, 70, stroke=BLUE)

    p.sticky("<b>Build order</b><br>"
             "&#9312; <b>Entra admin</b>: app registration, upload the .crt, add 5 permissions, grant admin consent "
             "(docs/01)<br>"
             "&#9313; <b>Site owner</b>: run provision.ps1, or create the lists by hand (docs/02)<br>"
             "&#9314; Fill the EntraSettings item: tenant, client ID, ServiceAccountUpn, approvers, fallback<br>"
             "&#9315; <b>Power Apps</b>: add data sources, paste formulas and screens, publish (docs/03)<br>"
             "&#9316; <b>Power Automate</b>, as the flow account: create connections, build ER-01, ER-02, ER-03 "
             "(docs/04)<br>"
             "&#9317; Copy the app's web link into EntraSettings.PowerAppUrl<br>"
             "&#9318; Test: one request per type, plus a rejection and a self-approval (docs/05)",
             40, 690, 820, 170)
    p.sticky("<b>Test the Graph connection first.</b> In a scratch flow: Invoke an HTTP request "
             "<code>GET /v1.0/organization</code>. A 403 means consent is missing; AADSTS700027 means the "
             "certificate doesn't match.", 900, 690, 560, 80)
    p.sticky("<b>Move to production</b> by exporting the solution; connections are re-created in the "
             "target environment.", 900, 790, 560, 60)
    return p


# ---------------------------------------------------------------------------
def page_compare() -> Page:
    p = Page("13 Option - Graph connection", 1700, 900)
    title(p, "Option &mdash; how ER-02 / ER-03 authenticate to Graph",
          "Both use the same app registration and certificate. They differ in where the certificate lives.",
          w=1200)
    q = p.decision("Where should the<br>certificate live?", 760, 90, w=200, h=90)
    a = p.terminal("A &middot; in the connection (recommended)", 300, 200, GREEN_FILL, GREEN, w=320)
    b = p.terminal("B &middot; in Key Vault, read by the flow", 1100, 200, BLUE_FILL, BLUE, w=320)
    p.edge(q, a, "", GREEN, exit=(0, 0.5), entry=(0.5, 0), points=[(460, 135)])
    p.edge(q, b, "", BLUE, exit=(1, 0.5), entry=(0.5, 0), points=[(1260, 135)])
    p.table("A &middot; HTTP with Microsoft Entra ID (preauthorized)", [
        "Connector: HTTP with Microsoft Entra ID (preauthorized), Premium",
        "Auth type: Log in using a Client Certificate Auth",
        "Certificate: uploaded once into the connection",
        "Each Graph call: Invoke an HTTP request, relative URL /v1.0/...",
        "Extra connectors: none",
        "Response body arrives as text: wrap in json() if fields come back empty",
        "Limit: 100 calls per minute per connection",
        "Fails as: connection error at save time if tenant / client ID / cert are wrong",
    ], 40, 280, 520, GREEN)
    p.table("Identical either way", [
        "App registration " + APP_REG,
        "Same 5 Graph application permissions + admin consent",
        "Same certificate (.pfx for Power Automate, .crt in Entra)",
        "Same Graph requests and JSON bodies (powerautomate/actions)",
        "Same Premium licence for the flow owner",
        "Same risk: flow editors can use the identity",
        "ER-01, the app and SharePoint: unchanged",
    ], 590, 280, 520, GREY)
    p.table("B &middot; HTTP action + Azure Key Vault", [
        "Connector: HTTP (built in), Premium",
        "Auth: Active Directory OAuth &middot; Credential Type = Certificate",
        "Certificate: Key Vault secrets (base64 .pfx + password)",
        "Each flow: Get PFX + Get PFX password (secure outputs) first",
        "Extra: Azure subscription, Key Vault, Key Vault Secrets User role",
        "Authentication set on each of the 14 HTTP actions",
        "Limit: no connector throttle to worry about",
        "Fails as: 401 at run time if the secret or password is wrong",
    ], 1140, 280, 520, BLUE)
    p.sticky("<b>Pick A unless</b> you already run Key Vault for Power Platform secrets, or you need one "
             "certificate shared across many flows and environments with central rotation.", 40, 560, 620, 70)
    p.sticky("<b>Not options:</b> 'HTTP With Microsoft Entra ID' (v2), the Microsoft Entra ID connector and the "
             "App Registrations connector all act as the signed-in user, or are read-only.", 700, 560, 620, 70)
    return p


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "entra-powerplatform.drawio"
    Doc(out).add(
        page_glance(), page_context(), page_identity(), page_seq_approvals(), page_seq_execute(),
        page_flow_er01(), page_flow_er02(), page_flow_er03(), page_lifecycle(), page_data(),
        page_security(), page_deploy(), page_compare(),
    ).write()
