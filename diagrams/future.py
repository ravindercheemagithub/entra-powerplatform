#!/usr/bin/env python3
"""
Future extension (not built yet): raise a ServiceNow normal change automatically
after the two approvals, and run ER-02 only when the change reaches Implement.

    python3 future.py      # writes entra-powerplatform-future.drawio

Kept in its own file on purpose: the main diagrams show what is built today.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio import (  # noqa: E402
    Doc, Page, Sequence,
    BLUE, BLUE_FILL, GREEN, GREEN_FILL, PURPLE, PURPLE_FILL,
    ORANGE, ORANGE_FILL, GREY, GREY_FILL, RED, RED_FILL, INK,
)
from generate import sp_list, title, small, SITE, AMBER, AMBER_FILL  # noqa: E402

SN = "#293E40"          # ServiceNow dark green-grey, used only for ServiceNow boxes
SN_FILL = "#EEF5F0"
NEW = "#CA5010"         # orange outline = new in this extension


def page_components() -> Page:
    p = Page("F1 Future - ServiceNow components", 1720, 1000)
    title(p, "Future extension &mdash; ServiceNow normal change after approval",
          "Not built yet. Orange outline = new. After the manager and the Entra ID team approve, a normal change is "
          "raised automatically; ER-02 runs only once the change reaches Implement, and closes it afterwards.",
          w=1500)

    p.container("Power Platform environment &middot; Entra Self-Service", 40, 110, 1000, 640, stroke=BLUE,
                fill=BLUE_FILL)
    p.container("SharePoint site " + SITE, 60, 150, 280, 560, stroke="#03787C", fill="#FFFFFF")
    l_req = sp_list(p, "<b>EntraRequests</b><br>" + small("+ ChangeNumber &middot; ChangeSysId<br>"
                    "+ ChangeState &middot; Status PendingChange"), 175, 200)
    sp_list(p, "<b>EntraSettings</b><br>" + small("+ ServiceNowUrl &middot; ChangeAssignmentGroup<br>"
            "+ ChangeMode (gated | record)"), 175, 420)
    p.node(small("New Status value <b>PendingChange</b> between PendingEntraApproval and Approved"),
           80, 600, 240, 50, stroke=NEW, fill=ORANGE_FILL)

    p.container("Power Automate &middot; owner: flow account", 370, 150, 650, 560, stroke=BLUE, fill="#FFFFFF")
    er1 = p.icon("pauto", "<b>ER-01 Approvals</b><br>" + small("changed: last step sets<br>Status = PendingChange"),
                 420, 200)
    er5 = p.icon("pauto", "<b>ER-05 Raise change</b><br>" + small("new &middot; trigger: PendingChange<br>writes ChangeNumber back"), 640, 200)
    er6 = p.icon("pauto", "<b>ER-06 Change sync</b><br>" + small("new &middot; every 15 min<br>mirrors ChangeState"), 640, 400)
    er2 = p.icon("pauto", "<b>ER-02 Execute</b><br>" + small("unchanged &middot; trigger: Approved"), 420, 400)
    for x, y in [(632, 192), (632, 392)]:
        p.node("", x, y, 72, 72, stroke=NEW, fill="none")
    sn_conn = p.node("<b>ServiceNow connector</b><br>" + small("Premium &middot; integration user<br>"
                     "(or HTTP + OAuth to the Change API)"), 840, 290, 160, 80, stroke=NEW, fill=ORANGE_FILL)
    p.note(small("Same Premium licence as ER-02 (flow owner). Connection owned by the flow account."),
           400, 640, 600, 30, align="center")

    p.container("ServiceNow instance", 1090, 110, 590, 640, stroke=SN, fill=SN_FILL)
    chg = p.node("<b>change_request</b> &middot; type Normal<br>" + small(
        "POST /api/sn_chg_rest/change/normal"), 1130, 170, 280, 60, stroke=SN)
    p.table("Fields set by ER-05", [
        "short_description: Entra app registration APPCAT-ENV-BOR-name",
        "description: RequestSummary (what was approved)",
        "justification &middot; requested_by (requester)",
        "assignment_group &middot; cmdb_ci (from appCatID)",
        "implementation / backout / test plan (template)",
        "start_date, end_date: next change window",
        "work_notes: manager + Entra approvals, who and when",
        "correlation_id: REQ-... (request id)",
    ], 1130, 260, 520, SN)
    p.table("Change states ER-06 reacts to", [
        "Assess / Authorize (CAB) ....... keep waiting",
        "Scheduled ...................... keep waiting",
        "Implement ...................... Status = Approved &#8594; ER-02",
        "Canceled / rejected ............ Status = Rejected",
        "after ER-02 .................... Review &middot; close_code",
    ], 1130, 520, 520, SN, mono=True)

    p.edge(l_req, er1, "Submitted &#8594; approvals", GREEN, entry=(0, 0.5), exit=(1, 0.5))
    p.arrow(476, 216, 640, 216, "PendingChange", NEW)
    p.arrow(696, 216, 1130, 200, "create normal change", NEW, points=[(1060, 216), (1060, 200)])
    p.arrow(696, 416, 1130, 214, "read state &middot; close", NEW, points=[(1075, 416), (1075, 214)])
    p.arrow(640, 430, 476, 430, "Status = Approved", NEW, above=False)

    p.container("Microsoft Entra ID", 40, 780, 1000, 100, stroke=PURPLE, fill=PURPLE_FILL)
    p.note("ER-02 creates the app registration, enterprise app and role assignments exactly as today. "
           "Only <b>when</b> it runs changes.", 60, 815, 960, 40, color=INK)
    p.arrow(448, 500, 448, 780, "Graph", PURPLE)

    p.sticky("<b>Two modes</b> (EntraSettings.ChangeMode).<br><b>gated</b>: ER-02 waits for CAB and the change "
             "window (change reaches Implement).<br><b>record</b>: the in-app approvals are enough; the change is "
             "raised, ER-02 runs at once, and the change is closed for the audit trail.", 1090, 780, 590, 100)
    p.sticky("<b>Decide with change management:</b> assignment group, CI mapping from appCatID, change window, "
             "and whether production (appEnv P) is gated while D/L/T are record-only.", 40, 900, 1000, 60)
    return p


def page_sequence() -> Page:
    p = Page("F2 Future - ServiceNow sequence", 1720, 1400)
    title(p, "Future extension &mdash; sequence with a gated normal change",
          "From the Entra ID team's approval to the closed change. Steps before that are unchanged.", w=1300)
    s = Sequence(p, [
        ("er1", "ER-01 Approvals", "azure"),
        ("sp", "EntraRequests", "data"),
        ("er5", "ER-05 Raise change", "azure"),
        ("sn", "ServiceNow", "ext"),
        ("cab", "Change approvers", "actor"),
        ("er6", "ER-06 Change sync", "azure"),
        ("er2", "ER-02 Execute", "azure"),
        ("req", "Requester", "actor"),
    ], x0=40, gap=205, y0=80)
    s.msg("er1", "sp", "Entra team approved &#8594; Status = PendingChange")
    s.msg("sp", "er5", "trigger: Status = PendingChange")
    s.msg("er5", "sn", "POST change/normal  (summary, CI, window, plans, correlation_id)", color=NEW)
    s.msg("sn", "er5", "number CHG00xxxxx &middot; sys_id", ret=True)
    s.msg("er5", "sp", "ChangeNumber &middot; ChangeSysId &middot; ChangeState = Assess")
    s.msg("er5", "req", "email: change CHG00xxxxx raised for your request")
    s.msg("sn", "cab", "normal change approvals (CAB / change manager)")
    s.msg("cab", "sn", "Approve &#8594; Scheduled &#8594; Implement in the window", ret=True)
    with s.block("loop  every 15 min while PendingChange", "sp", "er6", color=ORANGE):
        s.msg("er6", "sn", "GET change by sys_id &#8594; state", color=NEW)
        s.msg("er6", "sp", "ChangeState (mirrors ServiceNow)")
    with s.block("alt  change canceled or rejected", "sp", "req", color=RED):
        s.msg("er6", "sp", "Status = Rejected &middot; reason from the change", color=RED)
        s.msg("er6", "req", "email: change was not approved", color=RED)
    with s.block("alt  state = Implement", "sp", "req", color=GREEN):
        s.msg("er6", "sp", "Status = Approved  (written by the flow account)", color=GREEN)
        s.msg("sp", "er2", "trigger: Status = Approved &#8594; Graph calls as today")
        s.msg("er2", "sp", "Completed or Failed &middot; ResultJson")
    s.msg("er6", "sn", "next run: work notes = ResultJson &#8594; state Review &middot; "
                       "close_code successful / unsuccessful", color=NEW)
    s.msg("er6", "req", "email: complete, change CHG00xxxxx closed")
    s.gap()
    s.note("<b>ER-02's guard still holds:</b> only the flow account can set Approved, so a change can't be "
           "skipped by editing the list.", "er6", w=440, h=44)
    s.note("<b>record mode:</b> ER-05 sets Status = Approved right after creating the change; ER-06 then only "
           "closes changes.", "er1", w=420, h=44)
    s.finish()
    return p


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "entra-powerplatform-future.drawio"
    Doc(out).add(page_components(), page_sequence()).write()
