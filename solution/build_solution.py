#!/usr/bin/env python3
"""
Builds an importable, UNMANAGED Power Platform solution with these cloud flows:

    SP-00 Create lists     (instant)   creates the SharePoint lists from lists-schema.json
    ER-01 Approvals        (automated) lock, manager approval, Entra team approval
    ER-02 Execute          (automated) Microsoft Graph calls through HTTP with Microsoft Entra ID
    ER-03 Catalog sync     (scheduled) refreshes the catalog lists
    ER-04 Onboard group    (automated) adds an existing group to the catalog for its members/owners
    ER-05 Find app         (automated) Search on the change screen: returns an app only to its authorized owner
    ER-06 Tag owning group (automated) replaces an app's team:user\\<id> tag with team:group\\<id>
    ER-07 Requeue approved (instant)   Entra ID team only: re-saves Approved requests so ER-02 runs them

plus five connection references and one environment variable (the SharePoint site URL).

    python3 build_solution.py            # writes src/ and, if pac is available, dist/*.zip

The flows follow docs/04-POWER-AUTOMATE.md step for step, with option A (HTTP with Microsoft
Entra ID, client-certificate connection) for Graph. Lists are addressed by name.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "src"
DIST = HERE / "dist"

SOLUTION = "EntraSelfService"
SOLUTION_LABEL = "Entra Self-Service"
VERSION = "1.4.1.0"
PREFIX = "esp"
PUBLISHER = "EntraSelfService"

SITE_PARAM = f"SharePoint site URL ({PREFIX}_SiteUrl)"
SITE = f"@parameters('{SITE_PARAM}')"

# connection key in the flow -> (connector api name, connection reference logical name, display name)
CONN = {
    "shared_sharepointonline": ("shared_sharepointonline", f"{PREFIX}_sharedsharepointonline_entra", "Entra Self-Service: SharePoint"),
    "shared_office365users": ("shared_office365users", f"{PREFIX}_sharedoffice365users_entra", "Entra Self-Service: Office 365 Users"),
    "shared_approvals": ("shared_approvals", f"{PREFIX}_sharedapprovals_entra", "Entra Self-Service: Approvals"),
    "shared_office365": ("shared_office365", f"{PREFIX}_sharedoffice365_entra", "Entra Self-Service: Office 365 Outlook"),
    "shared_webcontents": ("shared_webcontents", f"{PREFIX}_sharedwebcontents_entra", "Entra Self-Service: HTTP with Microsoft Entra ID (Graph, client certificate)"),
}

# Stable ids so a rebuild updates the same flows on re-import.
FLOW_IDS = {
    "SP-00 Create lists": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0001",
    "ER-01 Approvals": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0002",
    "ER-02 Execute": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0003",
    "ER-03 Catalog sync": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0004",
    "ER-04 Onboard group": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0005",
    "ER-05 Find app": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0006",
    "ER-06 Tag owning group": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0007",
    "ER-07 Requeue approved": "4d0a1a52-6c1e-4b8a-9a33-0e5f0b8d0008",
}

ID = "@int(triggerOutputs()?['body/ID'])"
TITLE = "@triggerOutputs()?['body/Title']"
GRAPH = "https://graph.microsoft.com/v1.0"
JSON_HDR = {"Content-Type": "application/json"}
NOMETA = {"Accept": "application/json;odata=nometadata"}
VERBOSE = {"Accept": "application/json;odata=verbose", "Content-Type": "application/json;odata=verbose"}
MERGE = {**VERBOSE, "IF-MATCH": "*", "X-HTTP-Method": "MERGE"}


def body_file(name: str) -> str:
    return (ROOT / "powerautomate" / "actions" / f"{name}.json").read_text().strip()


INVALID_NAME_CHARS = set('?<>%&\\/:*#"\'')


def key(name: str) -> str:
    bad = INVALID_NAME_CHARS & set(name)
    assert not bad, f"action name {name!r} contains characters Power Automate rejects: {''.join(sorted(bad))}"
    return name.replace(" ", "_")


# ---------------------------------------------------------------------------
# A sequence of actions: each action runs after the previous one in the same container.
# ---------------------------------------------------------------------------
class Seq:
    def __init__(self):
        self.actions: dict[str, dict] = {}
        self.last: str | None = None

    def add(self, name: str, action: dict, run_after: dict | None = None) -> "Seq":
        k = key(name)
        assert k not in self.actions, f"duplicate action {name}"
        action = dict(action)
        if run_after is not None:
            action["runAfter"] = run_after
        else:
            action["runAfter"] = {self.last: ["Succeeded"]} if self.last else {}
        self.actions[k] = action
        self.last = k
        return self

    # -- connectors --------------------------------------------------------
    def op(self, name, conn, operation, params, kind="OpenApiConnection", run_after=None, extra=None):
        a = {"type": kind, "inputs": {"host": {"apiId": f"/providers/Microsoft.PowerApps/apis/{CONN[conn][0]}",
                                                "connectionName": conn, "operationId": operation},
                                       "parameters": params,
                                       "authentication": "@parameters('$authentication')"}}
        if extra:
            a["inputs"].update(extra)
        return self.add(name, a, run_after)

    def sp_get_item(self, name, table, id_):
        return self.op(name, "shared_sharepointonline", "GetItem", {"dataset": SITE, "table": table, "id": id_})

    def sp_get_items(self, name, table, filt=None, top=None):
        p = {"dataset": SITE, "table": table}
        if filt:
            p["$filter"] = filt
        if top:
            p["$top"] = top
        return self.op(name, "shared_sharepointonline", "GetItems", p)

    def sp_patch(self, name, table, id_, fields, run_after=None):
        p = {"dataset": SITE, "table": table, "id": id_}
        p.update({f"item/{k}": v for k, v in fields.items()})
        return self.op(name, "shared_sharepointonline", "PatchItem", p, run_after=run_after)

    def sp_post(self, name, table, fields):
        p = {"dataset": SITE, "table": table}
        p.update({f"item/{k}": v for k, v in fields.items()})
        return self.op(name, "shared_sharepointonline", "PostItem", p)

    def sp_http(self, name, method, uri, headers, body=None, run_after=None):
        p = {"dataset": SITE, "parameters/method": method, "parameters/uri": uri, "parameters/headers": headers}
        if body is not None:
            p["parameters/body"] = body
        return self.op(name, "shared_sharepointonline", "HttpRequest", p, run_after=run_after)

    def graph(self, name, method, url, body=None, headers=None, retry=None):
        p = {"request/method": method, "request/url": url}
        h = dict(headers or {})
        if method in ("POST", "PATCH"):
            h.update(JSON_HDR)
        if h:
            p["request/headers"] = h
        if body is not None:
            p["request/body"] = body
        extra = {"retryPolicy": retry} if retry else None
        return self.op(name, "shared_webcontents", "InvokeHttp", p, extra=extra)

    def mail(self, name, to, subject, body_):
        return self.op(name, "shared_office365", "SendEmailV2", {
            "emailMessage/To": to, "emailMessage/Subject": subject, "emailMessage/Body": body_,
            "emailMessage/Importance": "Normal"})

    def approval(self, name, title, assigned, details, link, requestor):
        return self.op(name, "shared_approvals", "StartAndWaitForAnApproval", {
            "approvalType": "Basic",
            "WebhookApprovalCreationInput/title": title,
            "WebhookApprovalCreationInput/assignedTo": assigned,
            "WebhookApprovalCreationInput/details": details,
            "WebhookApprovalCreationInput/itemLink": link,
            "WebhookApprovalCreationInput/itemLinkDescription": "Open Entra Self-Service",
            "WebhookApprovalCreationInput/requestor": requestor,
            "WebhookApprovalCreationInput/enableNotifications": True,
            "WebhookApprovalCreationInput/enableReassignment": True,
        }, kind="OpenApiConnectionWebhook")

    # -- built-ins ---------------------------------------------------------
    def compose(self, name, inputs, run_after=None):
        return self.add(name, {"type": "Compose", "inputs": inputs}, run_after)

    def init_var(self, name, var, typ, value):
        return self.add(name, {"type": "InitializeVariable",
                               "inputs": {"variables": [{"name": var, "type": typ, "value": value}]}})

    def set_var(self, name, var, value):
        return self.add(name, {"type": "SetVariable", "inputs": {"name": var, "value": value}})

    def append_var(self, name, var, value):
        return self.add(name, {"type": "AppendToArrayVariable", "inputs": {"name": var, "value": value}})

    def select(self, name, frm, mapping):
        return self.add(name, {"type": "Select", "inputs": {"from": frm, "select": mapping}})

    def filter(self, name, frm, where):
        return self.add(name, {"type": "Query", "inputs": {"from": frm, "where": where}})

    def delay(self, name, seconds):
        return self.add(name, {"type": "Wait", "inputs": {"interval": {"count": seconds, "unit": "Second"}}})

    def terminate(self, name, status, code=None, message=None):
        inputs = {"runStatus": status}
        if status == "Failed":
            inputs["runError"] = {"code": code, "message": message}
        return self.add(name, {"type": "Terminate", "inputs": inputs})

    def cond(self, name, expression, yes: Seq | None = None, no: Seq | None = None, run_after=None):
        a = {"type": "If", "expression": expression, "actions": (yes or Seq()).actions,
             "else": {"actions": (no or Seq()).actions}}
        return self.add(name, a, run_after)

    def foreach(self, name, items, body: Seq, concurrency=1):
        a = {"type": "Foreach", "foreach": items, "actions": body.actions}
        if concurrency:
            a["runtimeConfiguration"] = {"concurrency": {"repetitions": concurrency}}
        return self.add(name, a)

    def until(self, name, expression, body: Seq, count, timeout):
        return self.add(name, {"type": "Until", "expression": expression,
                               "limit": {"count": count, "timeout": timeout}, "actions": body.actions})

    def scope(self, name, body: Seq, run_after=None):
        return self.add(name, {"type": "Scope", "actions": body.actions}, run_after)

    def switch(self, name, on, cases: dict[str, Seq]):
        return self.add(name, {"type": "Switch", "expression": on,
                               "cases": {f"Case_{c}": {"case": c, "actions": s.actions} for c, s in cases.items()},
                               "default": {"actions": {}}})


def eq(a, b):
    return {"and": [{"equals": [a, b]}]}


def is_true(expr):
    return eq(expr, True)


def flow(triggers: dict, actions: Seq, conns: list[str]) -> dict:
    return {
        "properties": {
            "connectionReferences": {
                c: {"runtimeSource": "embedded", "connection": {"connectionReferenceLogicalName": CONN[c][1]},
                    "api": {"name": CONN[c][0]}} for c in conns},
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "contentVersion": "1.0.0.0",
                "parameters": {
                    "$connections": {"defaultValue": {}, "type": "Object"},
                    "$authentication": {"defaultValue": {}, "type": "SecureObject"},
                    SITE_PARAM: {"defaultValue": "", "type": "String",
                                 "metadata": {"schemaName": f"{PREFIX}_SiteUrl",
                                              "description": "SharePoint site that holds the Entra self-service lists"}},
                },
                "triggers": triggers,
                "actions": actions.actions,
            },
            "templateName": "",
        },
        "schemaVersion": "1.0.0.0",
    }


def sp_trigger(operation, table, condition, runs=None):
    t = {"type": "OpenApiConnection", "recurrence": {"interval": 1, "frequency": "Minute"},
         "splitOn": "@triggerOutputs()?['body/value']",
         "inputs": {"host": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                             "connectionName": "shared_sharepointonline", "operationId": operation},
                    "parameters": {"dataset": SITE, "table": table},
                    "authentication": "@parameters('$authentication')"},
         "conditions": [{"expression": condition}]}
    if runs:
        t["runtimeConfiguration"] = {"concurrency": {"runs": runs}}
    return t


APPROVER_LIST = "replace(replace(body('Get_settings')?['EntraApproverEmails'], decodeUriComponent('%0D'), ''), decodeUriComponent('%0A'), ';')"
LINK = "@{body('Get_settings')?['PowerAppUrl']}"
REQ_UPN = "last(split(triggerOutputs()?['body/Author/Claims'], '|'))"


# ---------------------------------------------------------------------------
# SP-00 Create lists
# ---------------------------------------------------------------------------
def sp00() -> dict:
    schema = json.loads((ROOT / "sharepoint" / "lists-schema.json").read_text())
    L = "items('Apply_to_each_list')"
    s = Seq()
    s.compose("Schema", schema)

    created = Seq()
    created.sp_http("Create list", "POST", "_api/web/lists", VERBOSE,
                    f"{{\"__metadata\":{{\"type\":\"SP.List\"}},\"BaseTemplate\":100,\"Title\":\"@{{{L}?['title']}}\",\"Description\":\"@{{{L}?['description']}}\",\"EnableVersioning\":true}}")
    created.sp_http("Set version limit", "POST", f"_api/web/lists/getbytitle('@{{{L}?['title']}}')", MERGE,
                    "{\"__metadata\":{\"type\":\"SP.List\"},\"MajorVersionLimit\":500}")
    created.sp_http("Rename Title", "POST", f"_api/web/lists/getbytitle('@{{{L}?['title']}}')/fields/getbyinternalnameortitle('Title')", MERGE,
                    f"{{\"__metadata\":{{\"type\":\"SP.Field\"}},\"Title\":\"@{{{L}?['titleDisplayName']}}\",\"Indexed\":@{{{L}?['titleIndexed']}}}}")
    field = Seq().sp_http("Add field", "POST", f"_api/web/lists/getbytitle('@{{{L}?['title']}}')/fields/createfieldasxml", VERBOSE,
                          "{\"parameters\":{\"__metadata\":{\"type\":\"SP.XmlSchemaFieldCreationInformation\"},\"SchemaXml\":\"@{items('Apply_to_each_field')}\",\"Options\":24}}")
    created.foreach("Apply to each field", f"@{L}?['fields']", field)

    per_list = Seq()
    per_list.sp_http("Get list", "GET", f"_api/web/lists/getbytitle('@{{{L}?['title']}}')?$select=Id", NOMETA)
    per_list.cond("List missing", eq("@outputs('Get_list')?['statusCode']", 404), yes=created,
                  run_after={"Get_list": ["Succeeded", "Failed"]})
    s.foreach("Apply to each list", "@outputs('Schema')?['lists']", per_list)

    s.sp_http("Get settings item", "GET", "_api/web/lists/getbytitle('EntraSettings')/items?$top=1&$select=Id", NOMETA)
    make = Seq().sp_http("Create settings item", "POST", "_api/web/lists/getbytitle('EntraSettings')/items", VERBOSE,
                         "{\"__metadata\":{\"type\":\"SP.Data.EntraSettingsListItem\"},\"Title\":\"settings\",\"ManagedByTag\":\"entra-pp\",\"PfxSecretName\":\"entra-pp-graph-pfx\",\"PfxPasswordSecretName\":\"entra-pp-graph-pfx-password\"}")
    s.cond("No settings item", is_true("@empty(body('Get_settings_item')?['value'])"), yes=make)

    trig = {"manual": {"type": "Request", "kind": "Button",
                       "inputs": {"schema": {"type": "object", "properties": {}, "required": []}}}}
    return flow(trig, s, ["shared_sharepointonline"])


# ---------------------------------------------------------------------------
# ER-01 Approvals
# ---------------------------------------------------------------------------
SUMMARY = ("@concat('**', triggerOutputs()?['body/RequestType/Value'], '** – ', triggerOutputs()?['body/TargetDisplayName'], decodeUriComponent('%0A%0A'), "
           "'Request: ', triggerOutputs()?['body/Title'], ' · appCatID: ', triggerOutputs()?['body/AppCatId'], decodeUriComponent('%0A%0A'), "
           "'Requested by: ', triggerOutputs()?['body/Author/DisplayName'], ' (', triggerOutputs()?['body/Author/Email'], ')', decodeUriComponent('%0A%0A'), "
           "if(empty(outputs('Payload')?['owningGroup']), '', concat('Owning team: ', outputs('Payload')?['owningGroup']?['displayName'], if(equals(outputs('Payload')?['owningGroup']?['mode'], 'new'), ' (new group)', ''), decodeUriComponent('%0A%0A'))), "
           "if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), concat('Expose API: ', outputs('Payload')?['exposeApi']?['identifierUriTemplate'], ', ', string(length(coalesce(outputs('Payload')?['exposeApi']?['scopes'], json('[]')))), ' scope(s)', decodeUriComponent('%0A%0A')), ''), "
           "if(empty(body('Select_roles_text')), '', concat(join(body('Select_roles_text'), decodeUriComponent('%0A')), decodeUriComponent('%0A%0A'))), "
           "'Justification: ', triggerOutputs()?['body/Justification'])")


def outcome(approval):
    return (f"@if(equals(toLower(coalesce(first(body('{approval}')?['responses'])?['responder']?['email'], '')), "
            f"toLower(triggerOutputs()?['body/Author/Email'])), 'Reject', body('{approval}')?['outcome'])")


def er01() -> dict:
    s = Seq()
    s.sp_get_item("Get settings", "EntraSettings", 1)
    s.sp_http("Ensure requester", "POST", "_api/web/ensureuser",
              {"Accept": "application/json;odata=nometadata", "Content-Type": "application/json;odata=nometadata"},
              "{\"logonName\": \"@{triggerOutputs()?['body/Author/Claims']}\"}")
    s.sp_http("Get owner group", "GET", "_api/web/associatedownergroup?$select=Id", NOMETA)
    item = "_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})"
    s.sp_http("Break inheritance", "POST", f"{item}/breakroleinheritance(copyRoleAssignments=false,clearSubscopes=true)", NOMETA)
    s.sp_http("Grant owners", "POST", f"{item}/roleassignments/addroleassignment(principalid=@{{body('Get_owner_group')?['Id']}},roledefid=1073741829)", NOMETA)
    s.sp_http("Grant requester read", "POST", f"{item}/roleassignments/addroleassignment(principalid=@{{body('Ensure_requester')?['Id']}},roledefid=1073741826)", NOMETA)
    s.sp_get_item("Get locked item", "EntraRequests", ID)
    s.compose("Payload", "@json(body('Get_locked_item')?['PayloadJson'])")
    s.op("Get manager", "shared_office365users", "Manager_V2", {"id": f"@{REQ_UPN}"})
    s.compose("Manager email", "@if(equals(actions('Get_manager')?['status'], 'Succeeded'), coalesce(body('Get_manager')?['mail'], body('Get_manager')?['userPrincipalName']), body('Get_settings')?['FallbackApproverEmail'])",
              run_after={"Get_manager": ["Succeeded", "Failed"]})
    s.compose("Manager name", "@if(equals(actions('Get_manager')?['status'], 'Succeeded'), body('Get_manager')?['displayName'], 'Fallback approver')")
    s.select("Select roles text", "@coalesce(outputs('Payload')?['appRoles'], json('[]'))",
             "@concat('- App role ', item()?['value'], ' (', string(length(coalesce(item()?['assignGroups'], json('[]')))), ' group(s))')")
    s.compose("Summary", SUMMARY)
    s.sp_patch("Update pending manager", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "PendingManagerApproval", "ManagerEmail": "@outputs('Manager_email')",
        "ManagerName": "@outputs('Manager_name')", "ApprovedPayloadJson": "@body('Get_locked_item')?['PayloadJson']",
        "RequestSummary": "@outputs('Summary')"})
    s.approval("Manager approval",
               "@concat('Entra request ', triggerOutputs()?['body/Title'], ': ', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'])",
               "@outputs('Manager_email')", "@outputs('Summary')", LINK, "@triggerOutputs()?['body/Author/Email']")
    s.compose("Manager outcome", outcome("Manager_approval"))
    s.sp_patch("Update manager decision", "EntraRequests", ID, {
        "Title": TITLE,
        "ManagerDecision/Value": "@if(equals(outputs('Manager_outcome'), 'Approve'), 'Approved', 'Rejected')",
        "ManagerDecisionBy": "@first(body('Manager_approval')?['responses'])?['responder']?['email']",
        "ManagerDecisionAt": "@utcNow()",
        "ManagerComment": "@first(body('Manager_approval')?['responses'])?['comments']",
        "Status/Value": "@if(equals(outputs('Manager_outcome'), 'Approve'), 'PendingEntraApproval', 'Rejected')"})

    rejected = Seq().mail(
        "Mail manager rejected", "@triggerOutputs()?['body/Author/Email']",
        "@concat('Your Entra request ', triggerOutputs()?['body/Title'], ' was rejected by your manager')",
        "@concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was rejected by your manager.<br>Rejected by: ', coalesce(first(body('Manager_approval')?['responses'])?['responder']?['displayName'], ''), '<br>Comment: ', coalesce(first(body('Manager_approval')?['responses'])?['comments'], '(none)'), if(equals(body('Manager_approval')?['outcome'], 'Approve'), '<br><br>Note: a request cannot be approved by the person who raised it.', ''), '<br><br><a href=\"', body('Get_settings')?['PowerAppUrl'], '\">Open Entra Self-Service</a>')")

    approved = Seq()
    approved.approval("Entra approval",
                      "@concat('Entra team approval – ', triggerOutputs()?['body/Title'], ': ', triggerOutputs()?['body/TargetDisplayName'])",
                      f"@{APPROVER_LIST}",
                      "@concat(outputs('Summary'), decodeUriComponent('%0A%0A'), 'Manager approval: ', coalesce(first(body('Manager_approval')?['responses'])?['responder']?['displayName'], ''))",
                      LINK, "@triggerOutputs()?['body/Author/Email']")
    approved.compose("Entra outcome", outcome("Entra_approval"))
    approved.sp_patch("Update entra decision", "EntraRequests", ID, {
        "Title": TITLE,
        "EntraDecision/Value": "@if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')",
        "EntraDecisionBy": "@first(body('Entra_approval')?['responses'])?['responder']?['email']",
        "EntraDecisionAt": "@utcNow()",
        "EntraComment": "@first(body('Entra_approval')?['responses'])?['comments']",
        "Status/Value": "@if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')"})
    approved.mail(
        "Mail requester", "@triggerOutputs()?['body/Author/Email']",
        "@if(equals(outputs('Entra_outcome'), 'Approve'), concat('Your Entra request ', triggerOutputs()?['body/Title'], ' is approved and being applied'), concat('Your Entra request ', triggerOutputs()?['body/Title'], ' was rejected by the Entra ID team'))",
        "@if(equals(outputs('Entra_outcome'), 'Approve'), concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was approved by your manager and the Entra ID team. It is being applied now; you will get another email when it is complete.<br><br><a href=\"', body('Get_settings')?['PowerAppUrl'], '\">Open Entra Self-Service</a>'), concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was rejected by the Entra ID team.<br>Rejected by: ', coalesce(first(body('Entra_approval')?['responses'])?['responder']?['displayName'], ''), '<br>Comment: ', coalesce(first(body('Entra_approval')?['responses'])?['comments'], '(none)'), '<br><br><a href=\"', body('Get_settings')?['PowerAppUrl'], '\">Open Entra Self-Service</a>'))")

    s.cond("Manager approved", eq("@outputs('Manager_outcome')", "Approve"), yes=approved, no=rejected)

    trig = {"When_an_item_is_created": sp_trigger("GetOnNewItems", "EntraRequests",
                                                  "@and(equals(triggerBody()?['Status']?['Value'], 'Submitted'), not(contains(createArray('onboardGroup', 'lookupApp', 'tagOwnerGroup'), triggerBody()?['RequestType']?['Value'])))")}
    return flow(trig, s, ["shared_sharepointonline", "shared_office365users", "shared_approvals", "shared_office365"])


# ---------------------------------------------------------------------------
# ER-02 Execute
# ---------------------------------------------------------------------------
ROLE_MAP = {"id": "@guid()", "value": "@item()?['value']", "displayName": "@item()?['displayName']",
            "description": "@item()?['description']", "allowedMemberTypes": "@split(item()?['allowedMemberTypes'], ',')",
            "isEnabled": True}
SCOPE_MAP = {"id": "@guid()", "value": "@item()?['value']", "type": "@item()?['type']",
             "adminConsentDisplayName": "@item()?['adminConsentDisplayName']",
             "adminConsentDescription": "@item()?['adminConsentDescription']",
             "userConsentDisplayName": "@item()?['adminConsentDisplayName']",
             "userConsentDescription": "@item()?['adminConsentDescription']", "isEnabled": True}


def fail_item(seq: Seq, fail_name, stop_name, message, code):
    seq.sp_patch(fail_name, "EntraRequests", ID, {"Title": TITLE, "Status/Value": "Failed", "ErrorMessage": message})
    seq.terminate(stop_name, "Failed", code, message)
    return seq


def graph_until_ok(seq: "Seq", name: str, method: str, url: str, body: str, ok_status: int, flag: str,
                   fail_name: str, stop_name: str, fail_message: str, attempts: int = 6, delay: int = 10,
                   on_give_up: "Seq | None" = None) -> "Seq":
    """Graph objects take a few seconds to replicate after creation, and calls against them can return
    404/400 meanwhile. The connector retry policy only retries 408/429/5xx, so retry here: up to
    `attempts` calls, `delay` seconds apart; 'already exist(s)' counts as success.
    Inside an Apply to each pass `on_give_up` (e.g. set an error variable): Terminate can't be nested in a loop."""
    k = key(name)
    seq.set_var(f"Reset {flag}", flag, "no")
    body_seq = Seq()
    body_seq.graph(name, method, url, body, retry={"type": "none"})
    body_seq.cond(f"{name} ok",
                  is_true(f"@or(equals(outputs('{k}')?['statusCode'], {ok_status}), contains(string(outputs('{k}')?['body']), 'already exist'))"),
                  yes=Seq().set_var(f"Set {flag}", flag, "yes"),
                  no=Seq().delay(f"{name} retry delay", delay),
                  run_after={k: ["Succeeded", "Failed"]})
    seq.until(f"Until {name}", f"@equals(variables('{flag}'), 'yes')", body_seq, attempts, "PT10M")
    seq.cond(f"{name} gave up", eq(f"@variables('{flag}')", "no"),
             yes=on_give_up or fail_item(Seq(), fail_name, stop_name, fail_message, "GraphRetryExhausted"))
    return seq


# ---------------------------------------------------------------------------
# Ownership: an app registration belongs to whoever its team tag names.
#   team:user\<user object id>    the user who created it (no owning group chosen)
#   team:group\<group object id>  every member of that group
#   team:<group object id>        the 1.2 format, treated as a group
# Owners of the app registration object itself are not used: the platform never adds any.
# ---------------------------------------------------------------------------
APP_SELECT = "id,appId,displayName,tags,identifierUris,appRoles,api"
GUID_CHECK = "@and(equals(length({q}), 36), equals(length(split({q}, '-')), 5))"


def find_app(seq: "Seq", p: str, query: str, var: str, fail_name: str, stop_name: str) -> "Seq":
    """Looks the app up by Application (client) ID, then by Object ID; stores it in `var` (object)."""
    by_app = f"HTTP {p} by appId"
    by_obj = f"HTTP {p} by object id"
    seq.graph(by_app, "GET", f"{GRAPH}/applications?$filter=appId eq '@{{{query}}}'&$select={APP_SELECT}")
    obj = Seq().graph(by_obj, "GET", f"{GRAPH}/applications?$filter=id eq '@{{{query}}}'&$select={APP_SELECT}")
    obj.cond(f"{p} found by object id", eq(f"@empty(body('{key(by_obj)}')?['value'])", False),
             yes=Seq().set_var(f"Set {p} from object id", var, f"@first(body('{key(by_obj)}')?['value'])"),
             no=fail_item(Seq(), fail_name, stop_name,
                          f"@concat('No app registration has the Application (client) ID or Object ID ', {query}, '.')", "AppNotFound"))
    seq.cond(f"{p} found by appId", eq(f"@empty(body('{key(by_app)}')?['value'])", False),
             yes=Seq().set_var(f"Set {p} from appId", var, f"@first(body('{key(by_app)}')?['value'])"),
             no=obj)
    return seq


def owner_check(seq: "Seq", p: str, tags: str, user_id: str, flag: str) -> str:
    """Adds the actions that decide whether `user_id` is an authorized owner of an app with `tags`.
    `flag` is a string variable initialized to 'no' at the top of the flow. Returns the expression to test."""
    tt, gi, gf, chk = f"{p} team tags", f"{p} group values", f"{p} group ids", f"HTTP {p} check groups"
    seq.filter(tt, f"@coalesce({tags}, json('[]'))", "@startsWith(item(), 'team:')")
    seq.select(gi, f"@body('{key(tt)}')",
               "@if(startsWith(item(), 'team:group\\'), substring(item(), 11), if(startsWith(item(), 'team:user\\'), '', substring(item(), 5)))")
    seq.filter(gf, f"@body('{key(gi)}')", "@not(empty(item()))")
    seq.set_var(f"Reset {flag} {p}", flag, "no")
    grp = Seq().graph(chk, "POST", f"{GRAPH}/users/@{{{user_id}}}/checkMemberGroups",
                      f"{{\"groupIds\": @{{take(body('{key(gf)}'), 20)}}}}")
    grp.cond(f"{p} member of a team group", {"and": [{"greater": [f"@length(body('{key(chk)}')?['value'])", 0]}]},
             yes=Seq().set_var(f"Set {flag} {p}", flag, "yes"))
    seq.cond(f"{p} has team groups", {"and": [{"greater": [f"@length(body('{key(gf)}'))", 0]}]}, yes=grp)
    return (f"@or(contains(body('{key(tt)}'), concat('team:user\\', toLower({user_id}))), "
            f"equals(variables('{flag}'), 'yes'))")


def queue(role_loop, group_loop, filt):
    return {"roleId": f"@{{first(body('{filt}'))?['id']}}", "roleValue": f"@{{items('{role_loop}')?['value']}}",
            "mode": f"@{{items('{group_loop}')?['mode']}}", "id": f"@{{items('{group_loop}')?['id']}}",
            "displayName": f"@{{items('{group_loop}')?['displayName']}}",
            "description": f"@{{items('{group_loop}')?['description']}}",
            "ownerIds": f"@{{items('{group_loop}')?['ownerIds']}}"}


NL = "decodeUriComponent('%0A')"


def log(seq: "Seq", name: str, text: str) -> "Seq":
    """Adds a line to the step log (varLog) that becomes the request's CompletionNotes. `text` is an expression."""
    return seq.append_var(name, "varLog", f"@{text}")


def log_failed(seq: "Seq", name: str, text: str) -> "Seq":
    """A step failed but the request carries on with the steps that don't depend on it."""
    log(seq, name, text)
    return seq.set_var(f"{name} flag", "varHadErrors", "yes")


def stop_try(seq: "Seq", name: str, message: str) -> "Seq":
    """Stops the request inside Try so that Catch runs (Terminate would skip Catch: no notes, no email).
    The message goes to the step log and to ErrorMessage; the Compose fails on purpose (json() of plain text)."""
    seq.set_var(f"Set {name} message", "varFailMessage", message)
    log(seq, f"Log {name}", "concat('Failed: ', variables('varFailMessage'))")
    return seq.compose(f"Throw {name}", "@json(concat('Stopped: ', variables('varFailMessage')))")


def er02() -> dict:
    s = Seq()
    s.sp_get_item("Get settings", "EntraSettings", 1)
    stop = Seq().terminate("Stop not approved", "Cancelled")
    s.cond("Approved by the flow", {"and": [
        {"equals": ["@toLower(last(split(triggerOutputs()?['body/Editor/Claims'], '|')))", "@toLower(body('Get_settings')?['ServiceAccountUpn'])"]},
        {"equals": ["@triggerOutputs()?['body/ManagerDecision/Value']", "Approved"]},
        {"equals": ["@triggerOutputs()?['body/EntraDecision/Value']", "Approved"]}]}, no=stop)
    s.sp_patch("Mark in progress", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "InProgress"})
    s.compose("Requester", f"@toLower({REQ_UPN})")
    s.compose("Payload", "@json(triggerOutputs()?['body/ApprovedPayloadJson'])")
    s.compose("Now", "@utcNow()")
    for var, typ, val in [("varTeamGroupId", "string", ""), ("varTeamGroupName", "string", ""), ("varSpId", "string", ""),
                          ("varGroupId", "string", ""), ("varRoleId", "string", ""), ("varAssignTodo", "array", []),
                          ("varAssignments", "array", []), ("varResult", "object", {}),
                          ("varExposeOk", "string", "no"), ("varAssignOk", "string", "no"),
                          ("varTeamTag", "string", ""), ("varGroupOwner", "string", "no"),
                          ("varLog", "array", []), ("varHadErrors", "string", "no"), ("varFailMessage", "string", ""),
                          ("varDefaultOk", "string", "no")]:
        s.init_var(f"Init {var}", var, typ, val)

    t = Seq()  # Try
    t.graph("HTTP Get requester", "GET", f"{GRAPH}/users/@{{outputs('Requester')}}?$select=id,displayName,userPrincipalName")
    t.compose("Base tags", "@createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId']), concat('createdBy:', outputs('Requester')), concat('createdById:', body('HTTP_Get_requester')?['id']), concat('createdTimestamp:', outputs('Now')), concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('managedBy:', body('Get_settings')?['ManagedByTag']), concat('requestId:', triggerOutputs()?['body/Title']))")
    t.compose("Group meta", "@concat(' [appCatID=', triggerOutputs()?['body/AppCatId'], '; requestId=', triggerOutputs()?['body/Title'], '; createdBy=', outputs('Requester'), '; managedBy=', body('Get_settings')?['ManagedByTag'], ']')")

    ta = Seq()  # Has target app? -> yes
    ta.graph("HTTP Get target app", "GET", f"{GRAPH}/applications/@{{triggerOutputs()?['body/TargetObjectId']}}?$select=id,appId,displayName,tags,identifierUris,api,appRoles")
    ta.filter("Filter team tag", "@body('HTTP_Get_target_app')?['tags']", "@startsWith(item(), 'team:')")
    ta.filter("Filter appcat tag", "@body('HTTP_Get_target_app')?['tags']", "@startsWith(item(), 'appCatID:')")
    ta.filter("Filter kept tags", "@body('HTTP_Get_target_app')?['tags']", "@not(or(startsWith(item(), 'lastUpdatedBy:'), startsWith(item(), 'lastUpdatedTimestamp:'), startsWith(item(), 'requestId:')))")
    is_owner = owner_check(ta, "Target", "body('HTTP_Get_target_app')?['tags']", "body('HTTP_Get_requester')?['id']", "varGroupOwner")
    not_owner = stop_try(Seq(), "not owner",
                         "Not an authorized owner: the app's team tag names neither you (team:user\\<your id>) nor a group you are a member of (team:group\\<group id>), or its appCatID differs. Nothing was changed.")
    ta.cond("Requester may change", is_true(f"@and({is_owner[1:]}, or(empty(body('Filter_appcat_tag')), empty(triggerOutputs()?['body/AppCatId']), equals(first(body('Filter_appcat_tag')), concat('appCatID:', triggerOutputs()?['body/AppCatId']))))"), no=not_owner)
    ta.compose("Updated tags", "@union(body('Filter_kept_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])), if(empty(body('Filter_appcat_tag')), createArray(concat('managedBy:', body('Get_settings')?['ManagedByTag'])), json('[]')), if(and(empty(body('Filter_appcat_tag')), not(empty(triggerOutputs()?['body/AppCatId']))), createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId'])), json('[]')))")
    ta.graph("HTTP Find target SP", "GET", f"{GRAPH}/servicePrincipals?$filter=appId eq '@{{body('HTTP_Get_target_app')?['appId']}}'&$select=id")
    ta.set_var("Set target SP", "varSpId", "@coalesce(first(body('HTTP_Find_target_SP')?['value'])?['id'], '')")
    t.cond("Has target app", eq("@empty(triggerOutputs()?['body/TargetObjectId'])", False), yes=ta)

    # -- createAppRegistration
    c1 = Seq()
    # The owning group is optional. With one: team:group\<id>, and the requester must be a member of it (groups are
    # created outside this platform). Without one: team:user\<requester object id>; hand it to a group later (ER-06).
    grp = Seq()
    grp.graph("HTTP Check team membership", "POST", f"{GRAPH}/users/@{{body('HTTP_Get_requester')?['id']}}/checkMemberGroups",
              "{\"groupIds\": [\"@{outputs('Payload')?['owningGroup']?['id']}\"]}")
    grp.cond("Is team member", {"and": [{"greater": ["@length(body('HTTP_Check_team_membership')?['value'])", 0]}]},
             no=stop_try(Seq(), "not team member", "You are not a member of the owning group. Nothing was created."))
    grp.graph("HTTP Get team group", "GET", f"{GRAPH}/groups/@{{outputs('Payload')?['owningGroup']?['id']}}?$select=id,displayName")
    grp.set_var("Set team id", "varTeamGroupId", "@body('HTTP_Get_team_group')?['id']")
    grp.set_var("Set team name", "varTeamGroupName", "@body('HTTP_Get_team_group')?['displayName']")
    grp.set_var("Set group team tag", "varTeamTag", "@concat('team:group\\', body('HTTP_Get_team_group')?['id'])")
    usr = Seq()
    usr.set_var("Set user team name", "varTeamGroupName", "@outputs('Requester')")
    usr.set_var("Set user team tag", "varTeamTag", "@concat('team:user\\', toLower(body('HTTP_Get_requester')?['id']))")
    c1.cond("Has owning group", is_true("@not(empty(outputs('Payload')?['owningGroup']?['id']))"), yes=grp, no=usr)
    c1.select("Select app roles", "@coalesce(outputs('Payload')?['appRoles'], json('[]'))", ROLE_MAP)
    c1.select("Select scopes", "@if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), coalesce(outputs('Payload')?['exposeApi']?['scopes'], json('[]')), json('[]'))", SCOPE_MAP)
    c1.select("Select id token claims", "@if(empty(outputs('Payload')?['optionalClaimsIdToken']), json('[]'), split(outputs('Payload')?['optionalClaimsIdToken'], ','))", {"name": "@item()", "essential": False})
    c1.select("Select access token claims", "@if(empty(outputs('Payload')?['optionalClaimsAccessToken']), json('[]'), split(outputs('Payload')?['optionalClaimsAccessToken'], ','))", {"name": "@item()", "essential": False})
    c1.filter("Filter optional tags", "@split(coalesce(outputs('Payload')?['tags'], ''), ';')", "@and(contains(item(), '='), greater(length(trim(item())), 2))")
    c1.select("Select optional tags", "@body('Filter_optional_tags')", "@concat(trim(first(split(item(), '='))), ':', trim(last(split(item(), '='))))")
    c1.compose("App tags", "@union(outputs('Base_tags'), createArray(variables('varTeamTag'), concat('teamName:', variables('varTeamGroupName'))), if(empty(outputs('Payload')?['appEnv']), json('[]'), createArray(concat('appEnv:', outputs('Payload')?['appEnv']))), if(empty(outputs('Payload')?['borShortName']), json('[]'), createArray(concat('borShortName:', outputs('Payload')?['borShortName']))), body('Select_optional_tags'))")
    c1.graph("HTTP Create application", "POST", f"{GRAPH}/applications", body_file("HTTP_Create_application"))
    c1.set_var("Result create app", "varResult", {
        "applicationObjectId": "@{body('HTTP_Create_application')?['id']}",
        "appId": "@{body('HTTP_Create_application')?['appId']}",
        "identifierUri": "",
        "servicePrincipalId": "", "teamGroupId": "@{variables('varTeamGroupId')}", "team": "@{variables('varTeamTag')}"})
    log(c1, "Log app created", "concat('Done: app registration ', body('HTTP_Create_application')?['displayName'], ' created (client ID ', body('HTTP_Create_application')?['appId'], ', object ID ', body('HTTP_Create_application')?['id'], '), owner tag ', variables('varTeamTag'), if(greater(length(body('Select_app_roles')), 0), concat(', ', string(length(body('Select_app_roles'))), ' app role(s)'), ''))")
    c1.delay("Wait for app replication", 15)
    expose = graph_until_ok(Seq(), "HTTP Expose API", "PATCH", f"{GRAPH}/applications/@{{body('HTTP_Create_application')?['id']}}",
                            body_file("HTTP_Expose_API"), 204, "varExposeOk", "", "", "",
                            on_give_up=log_failed(Seq(), "Log expose failed",
                                                  "concat('Failed: Application ID URI and scopes were not set (', coalesce(body('HTTP_Expose_API')?['error']?['message'], 'no answer after 6 attempts'), '). Use Expose an API on this app to add them.')"))
    expose.cond("Expose done", eq("@variables('varExposeOk')", "yes"),
                yes=log(Seq(), "Log expose done", "concat('Done: Application ID URI ', replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), ' and ', string(length(body('Select_scopes'))), ' scope(s) set')"))
    c1.cond("Expose API", is_true("@equals(outputs('Payload')?['exposeApi']?['enabled'], true)"), yes=expose)
    sp_try = Seq()
    sp_try.graph("HTTP Create SP", "POST", f"{GRAPH}/servicePrincipals", body_file("HTTP_Create_SP"), retry={"type": "none"})
    sp_try.cond("SP created", eq("@outputs('HTTP_Create_SP')?['statusCode']", 201),
                yes=Seq().set_var("Set SP id", "varSpId", "@body('HTTP_Create_SP')?['id']"),
                no=Seq().delay("Retry delay", 10),
                run_after={"HTTP_Create_SP": ["Succeeded", "Failed"]})
    make_sp = Seq().delay("Wait for replication", 10)
    make_sp.until("Do until SP", "@not(empty(variables('varSpId')))", sp_try, 6, "PT10M")
    make_sp.cond("SP done", eq("@empty(variables('varSpId'))", False),
                 yes=log(Seq(), "Log SP done", "concat('Done: enterprise application created (object ID ', variables('varSpId'), '), assignment required: ', if(equals(outputs('Payload')?['appRoleAssignmentRequired'], false), 'no', 'yes'))"),
                 no=log_failed(Seq(), "Log SP failed", "concat('Failed: enterprise application not created (', coalesce(body('HTTP_Create_SP')?['error']?['message'], concat('HTTP ', string(outputs('HTTP_Create_SP')?['statusCode']))), '). Use Enterprise application on this app to create it.')"))
    c1.cond("Create SP", is_true("@equals(outputs('Payload')?['createServicePrincipal'], true)"), yes=make_sp)
    groups = Seq().append_var("Queue new role assignment", "varAssignTodo", queue("For_each_new_role", "For_each_new_role_group", "Filter_created_role"))
    roles = Seq()
    roles.filter("Filter created role", "@body('HTTP_Create_application')?['appRoles']", "@equals(item()?['value'], items('For_each_new_role')?['value'])")
    roles.foreach("For each new role group", "@coalesce(items('For_each_new_role')?['assignGroups'], json('[]'))", groups)
    c1.foreach("For each new role", "@coalesce(outputs('Payload')?['appRoles'], json('[]'))", roles)
    c1.set_var("Result create app final", "varResult", {
        "applicationObjectId": "@{body('HTTP_Create_application')?['id']}",
        "appId": "@{body('HTTP_Create_application')?['appId']}",
        "identifierUri": "@{if(equals(variables('varExposeOk'), 'yes'), replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), '')}",
        "servicePrincipalId": "@{variables('varSpId')}", "teamGroupId": "@{variables('varTeamGroupId')}", "team": "@{variables('varTeamTag')}"})
    c1.sp_post("Catalog new app", "EntraCatalogApps", {
        "Title": "@outputs('Payload')?['displayName']", "ObjectId": "@body('HTTP_Create_application')?['id']",
        "AppId": "@body('HTTP_Create_application')?['appId']", "AppCatId": "@triggerOutputs()?['body/AppCatId']",
        "TeamGroupId": "@variables('varTeamGroupId')", "TeamGroupName": "@variables('varTeamGroupName')",
        "ServicePrincipalId": "@variables('varSpId')", "IdentifierUri": "@variables('varResult')?['identifierUri']",
        "AppRolesJson": "@string(body('HTTP_Create_application')?['appRoles'])", "ScopesJson": "@string(body('Select_scopes'))",
        "TeamMemberUpns": "@concat(';', outputs('Requester'), ';')",
        "LastSynced": "@utcNow()"})

    # -- exposeApi
    target = f"{GRAPH}/applications/@{{triggerOutputs()?['body/TargetObjectId']}}"
    c3 = Seq()
    c3.select("Select new scopes", "@coalesce(outputs('Payload')?['scopes'], json('[]'))", SCOPE_MAP)
    c3.graph("HTTP Patch expose", "PATCH", target, body_file("HTTP_Patch_expose"))
    c3.set_var("Result expose", "varResult", {
        "applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "appId": "@{body('HTTP_Get_target_app')?['appId']}",
        "identifierUri": "@{replace(outputs('Payload')?['identifierUriTemplate'], '{appId}', body('HTTP_Get_target_app')?['appId'])}"})
    log(c3, "Log expose added", "concat('Done: Application ID URI ', variables('varResult')?['identifierUri'], ' and ', string(length(body('Select_new_scopes'))), ' new scope(s) added')")

    # -- addAppRoles
    c4 = Seq()
    c4.select("Select new roles", "@coalesce(outputs('Payload')?['appRoles'], json('[]'))", ROLE_MAP)
    c4.graph("HTTP Patch roles", "PATCH", target, body_file("HTTP_Patch_roles"))
    log(c4, "Log roles added", "concat('Done: ', string(length(body('Select_new_roles'))), ' app role(s) added')")
    g4 = Seq().append_var("Queue added role assignment", "varAssignTodo", queue("For_each_added_role", "For_each_added_role_group", "Filter_added_role"))
    r4 = Seq()
    r4.filter("Filter added role", "@body('Select_new_roles')", "@equals(item()?['value'], items('For_each_added_role')?['value'])")
    r4.foreach("For each added role group", "@coalesce(items('For_each_added_role')?['assignGroups'], json('[]'))", g4)
    c4.foreach("For each added role", "@coalesce(outputs('Payload')?['appRoles'], json('[]'))", r4)
    sp4 = Seq().graph("HTTP Create SP for roles", "POST", f"{GRAPH}/servicePrincipals", body_file("HTTP_Create_SP_existing"))
    sp4.set_var("Set SP id roles", "varSpId", "@body('HTTP_Create_SP_for_roles')?['id']")
    log(sp4, "Log SP for roles", "concat('Done: enterprise application created (object ID ', variables('varSpId'), ')')")
    c4.cond("Needs SP for roles", is_true("@and(greater(length(variables('varAssignTodo')), 0), empty(variables('varSpId')))"), yes=sp4)
    c4.set_var("Result roles", "varResult", {"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}",
                                             "appId": "@{body('HTTP_Get_target_app')?['appId']}",
                                             "servicePrincipalId": "@{variables('varSpId')}"})

    # -- assignGroupsToAppRoles
    c5 = Seq()
    c5.select("Select assignment todo", "@coalesce(outputs('Payload')?['assignments'], json('[]'))", {
        "roleId": "@item()?['appRoleId']", "roleValue": "@item()?['appRoleValue']", "mode": "@item()?['mode']",
        "id": "@item()?['id']", "displayName": "@item()?['displayName']", "description": "@item()?['description']",
        "ownerIds": "@item()?['ownerIds']"})
    c5.set_var("Set assignment todo", "varAssignTodo", "@body('Select_assignment_todo')")
    sp5 = Seq().graph("HTTP Create SP for assign", "POST", f"{GRAPH}/servicePrincipals", body_file("HTTP_Create_SP_existing"))
    sp5.set_var("Set SP id assign", "varSpId", "@body('HTTP_Create_SP_for_assign')?['id']")
    log(sp5, "Log SP for assign", "concat('Done: enterprise application created (object ID ', variables('varSpId'), ')')")
    c5.cond("Needs SP for assign", is_true("@empty(variables('varSpId'))"), yes=sp5)
    c5.graph("HTTP Patch tags assign", "PATCH", target, body_file("HTTP_Patch_tags"))
    c5.set_var("Result assign", "varResult", {"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}",
                                              "servicePrincipalId": "@{variables('varSpId')}"})

    # -- createServicePrincipal
    c6 = Seq()
    c6.cond("SP already exists", eq("@empty(variables('varSpId'))", False),
            yes=stop_try(Seq(), "SP exists", "This app already has an enterprise application. Nothing was changed."))
    c6.graph("HTTP Create SP existing", "POST", f"{GRAPH}/servicePrincipals", body_file("HTTP_Create_SP_existing"))
    c6.set_var("Set SP id sp", "varSpId", "@body('HTTP_Create_SP_existing')?['id']")
    log(c6, "Log SP created", "concat('Done: enterprise application created (object ID ', variables('varSpId'), '), assignment required: ', if(equals(outputs('Payload')?['appRoleAssignmentRequired'], false), 'no', 'yes'))")
    c6.graph("HTTP Patch tags sp", "PATCH", target, body_file("HTTP_Patch_tags"))
    c6.set_var("Result sp", "varResult", {"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}",
                                          "servicePrincipalId": "@{body('HTTP_Create_SP_existing')?['id']}"})

    cases = {}
    for name, seq in [("createAppRegistration", c1), ("exposeApi", c3), ("addAppRoles", c4),
                      ("assignGroupsToAppRoles", c5), ("createServicePrincipal", c6)]:
        cases[name] = Seq().scope(f"Do {name}", seq)
    t.switch("Request type", "@triggerOutputs()?['body/RequestType/Value']", cases)

    # -- role assignments, shared. Each assignment is tried on its own and logged as Done or Failed; one failure
    # doesn't stop the others. Without an enterprise application they are all skipped (and logged).
    A = "items('Apply_to_each_assignment')"
    pair = f"{A}?['displayName'], ' -> role ', {A}?['roleValue']"
    assign = Seq()
    assign.set_var("Set group id", "varGroupId", f"@{A}?['id']")
    graph_until_ok(assign, "HTTP Assign role", "POST", f"{GRAPH}/servicePrincipals/@{{variables('varSpId')}}/appRoleAssignedTo",
                   body_file("HTTP_Assign_role"), 201, "varAssignOk", "", "", "",
                   on_give_up=log_failed(Seq(), "Log assign failed",
                                         f"concat('Failed: ', {pair}, ' (', coalesce(body('HTTP_Assign_role')?['error']?['message'], 'no answer after 6 attempts'), ')')"))
    assign.cond("Assignment ok", eq("@variables('varAssignOk')", "yes"),
                yes=log(Seq().append_var("Record assignment", "varAssignments", f"@concat({A}?['displayName'], ' -> ', {A}?['roleValue'])"),
                        "Log assign done", f"concat('Done: ', {pair})"))
    each = Seq()
    each.cond("Group id missing", is_true(f"@empty({A}?['id'])"),
              yes=log_failed(Seq(), "Log no group id", f"concat('Failed: ', {pair}, ' (the group has no Object ID: add it with Add existing group and pick it again)')"),
              no=assign)
    loop = Seq().foreach("Apply to each assignment", "@variables('varAssignTodo')", each)
    t.cond("Assignments skipped", is_true("@and(greater(length(variables('varAssignTodo')), 0), empty(variables('varSpId')))"),
           yes=log_failed(Seq(), "Log assignments skipped", "concat('Skipped: ', string(length(variables('varAssignTodo'))), ' role assignment(s), because there is no enterprise application to assign them on')"),
           no=loop)
    # Default access (appRoleId 0000…) lets the owner sign in when assignment is required and nobody holds a role.
    # Graph accepts it only for an app WITHOUT app roles, and the new enterprise app may not have replicated yet
    # (404 Request_ResourceNotFound), so it uses the retry pattern and a failure is logged, not fatal.
    default = Seq()
    graph_until_ok(default, "HTTP Assign default access", "POST", f"{GRAPH}/servicePrincipals/@{{variables('varSpId')}}/appRoleAssignedTo",
                   body_file("HTTP_Assign_default_access"), 201, "varDefaultOk", "", "", "",
                   on_give_up=log_failed(Seq(), "Log default access failed",
                                         "concat('Failed: default access for ', variables('varTeamGroupName'), ' (', coalesce(body('HTTP_Assign_default_access')?['error']?['message'], 'no answer after 6 attempts'), '). Use Role assignments, or assign it in Entra (Enterprise applications > the app > Users and groups).')"))
    default.cond("Default access done", eq("@variables('varDefaultOk')", "yes"),
                 yes=log(Seq(), "Log default access", "concat('Done: default access to the enterprise application for ', variables('varTeamGroupName'))"))
    needs_access = ("equals(triggerOutputs()?['body/RequestType/Value'], 'createAppRegistration'), empty(variables('varAssignments')), "
                    "not(equals(outputs('Payload')?['appRoleAssignmentRequired'], false)), not(empty(variables('varSpId')))")
    t.cond("Default access", is_true(f"@and({needs_access}, empty(coalesce(outputs('Payload')?['appRoles'], json('[]'))))"), yes=default)
    t.cond("Roles without holders", is_true(f"@and({needs_access}, not(empty(coalesce(outputs('Payload')?['appRoles'], json('[]')))))"),
           yes=log(Seq(), "Log nobody can sign in",
                   "'Note: assignment is required and no group holds any of the app roles yet, so nobody can sign in. Give a group a role with Role assignments.'"))

    t.compose("Completion notes", f"@join(variables('varLog'), {NL})")
    t.compose("Result json", "@string(setProperty(variables('varResult'), 'assignmentsText', join(variables('varAssignments'), '; ')))")
    links = ("'<br><br><a href=\"', body('Get_settings')?['PowerAppUrl'], '\">Open Entra Self-Service</a>'")
    done = Seq()
    done.sp_patch("Mark completed", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "Completed", "CompletedAt": "@utcNow()",
        "CompletionNotes": "@outputs('Completion_notes')", "ResultJson": "@outputs('Result_json')"})
    done.mail("Mail completed", "@triggerOutputs()?['body/Author/Email']",
              "@concat('Your Entra request ', triggerOutputs()?['body/Title'], ' is complete')",
              "@concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') is complete.<br><br><b>What was done</b><br>', "
              f"join(variables('varLog'), '<br>'), {links})")
    partial = Seq()
    partial.sp_patch("Mark partly failed", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "Failed", "CompletedAt": "@utcNow()",
        "ErrorMessage": "Some steps failed. The steps marked Done are in place; see the completion notes for what still needs doing.",
        "CompletionNotes": "@outputs('Completion_notes')", "ResultJson": "@outputs('Result_json')"})
    partial.mail("Mail partly failed", f"@concat(triggerOutputs()?['body/Author/Email'], ';', {APPROVER_LIST})",
                 "@concat('Entra request ', triggerOutputs()?['body/Title'], ' partly failed')",
                 "@concat('Request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') was only partly applied.<br><br><b>Steps</b><br>', "
                 f"join(variables('varLog'), '<br>'), '<br><br>The steps marked Done are in place. Do not resubmit the whole request: use the matching card (Expose an API, Enterprise application, Role assignments) for the failed steps.', {links})")
    t.cond("Had errors", eq("@variables('varHadErrors')", "yes"), yes=partial, no=done)
    s.scope("Try", t)

    c = Seq()
    c.filter("Failed actions", "@union(result('Do_createAppRegistration'), result('Do_exposeApi'), result('Do_addAppRoles'), result('Do_assignGroupsToAppRoles'), result('Do_createServicePrincipal'), result('Try'))",
             "@equals(item()?['status'], 'Failed')")
    c.compose("Error text", "@if(empty(variables('varFailMessage')), concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-02 run history')), variables('varFailMessage'))")
    # A stop_try failure is already in the log; any other failure is added here. Steps after it did not run.
    c.compose("Failure log", "@if(empty(variables('varFailMessage')), union(variables('varLog'), createArray(concat('Failed: ', outputs('Error_text')))), variables('varLog'))")
    c.compose("Failure notes", f"@concat(join(outputs('Failure_log'), {NL}), {NL}, 'Not run: every step after the failed one.')")
    c.sp_patch("Mark failed", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "Failed",
                                                     "ErrorMessage": "@outputs('Error_text')",
                                                     "CompletionNotes": "@outputs('Failure_notes')",
                                                     "ResultJson": "@string(variables('varResult'))"})
    c.mail("Mail failed", f"@concat(triggerOutputs()?['body/Author/Email'], ';', {APPROVER_LIST})",
           "@concat('Entra request ', triggerOutputs()?['body/Title'], ' failed')",
           "@concat('Request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') failed while being applied.<br><br>Error: ', outputs('Error_text'), '<br><br><b>Steps</b><br>', join(outputs('Failure_log'), '<br>'), '<br>Not run: every step after the failed one.<br><br>IDs of anything created: ', string(variables('varResult')), '<br><br><a href=\"', body('Get_settings')?['PowerAppUrl'], '\">Open Entra Self-Service</a>')")
    s.scope("Catch", c, run_after={"Try": ["Failed", "TimedOut"]})

    trig = {"When_an_item_is_created_or_modified": sp_trigger(
        "GetOnUpdatedItems", "EntraRequests", "@equals(triggerBody()?['Status']?['Value'], 'Approved')", runs=1)}
    return flow(trig, s, ["shared_sharepointonline", "shared_webcontents", "shared_office365"])


# ---------------------------------------------------------------------------
# ER-03 Catalog sync
# ---------------------------------------------------------------------------
def er03() -> dict:
    A = "items('Apply_to_each_app')"
    G = "items('Apply_to_each_catalog_group')"
    s = Seq()
    s.sp_get_item("Get settings", "EntraSettings", 1)
    s.init_var("Init varMembers", "varMembers", "string", "")
    s.graph("HTTP List managed apps", "GET",
            f"{GRAPH}/applications?$filter=tags/any(t:t eq 'managedBy:@{{body('Get_settings')?['ManagedByTag']}}')&$select=id,appId,displayName,tags,identifierUris,appRoles,api&$count=true&$top=999",
            headers={"ConsistencyLevel": "eventual"})

    team = Seq()
    team.graph("HTTP Team members", "GET", f"{GRAPH}/groups/@{{outputs('Team_id')}}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999")
    team.select("Select member upns", "@body('HTTP_Team_members')?['value']", "@toLower(item()?['userPrincipalName'])")
    team.set_var("Set members", "varMembers", "@concat(';', join(body('Select_member_upns'), ';'), ';')")
    team.sp_get_items("Get team row", "EntraCatalogGroups", "GroupId eq '@{outputs('Team_id')}'", 1)
    team.cond("Team row missing", is_true("@empty(body('Get_team_row')?['value'])"), yes=Seq().sp_post("Create team row", "EntraCatalogGroups", {
        "Title": "@if(empty(body('Filter_app_team_name')), outputs('Team_id'), substring(first(body('Filter_app_team_name')), 9))",
        "GroupId": "@outputs('Team_id')",
        "AppCatId": "@if(empty(body('Filter_app_appcat')), '', substring(first(body('Filter_app_appcat')), 9))",
        "LastSynced": "@utcNow()"}))

    row = {
        "Title": f"@{A}?['displayName']", "ObjectId": f"@{A}?['id']", "AppId": f"@{A}?['appId']",
        "AppCatId": "@if(empty(body('Filter_app_appcat')), '', substring(first(body('Filter_app_appcat')), 9))",
        "TeamGroupId": "@outputs('Team_id')",
        "TeamGroupName": "@if(empty(body('Filter_app_team_name')), '', substring(first(body('Filter_app_team_name')), 9))",
        "ServicePrincipalId": "@coalesce(first(body('HTTP_App_SP')?['value'])?['id'], '')",
        "IdentifierUri": f"@coalesce(first({A}?['identifierUris']), '')",
        "AppRolesJson": f"@string(coalesce({A}?['appRoles'], json('[]')))",
        "ScopesJson": f"@string(coalesce({A}?['api']?['oauth2PermissionScopes'], json('[]')))",
        "TeamMemberUpns": "@variables('varMembers')",
        "OwnerUpns": "@concat(';', join(body('Select_owner_upns'), ';'), ';')",
        "LastSynced": "@utcNow()"}

    app = Seq()
    app.filter("Filter app team", f"@{A}?['tags']", "@startsWith(item(), 'team:')")
    app.filter("Filter app team name", f"@{A}?['tags']", "@startsWith(item(), 'teamName:')")
    app.filter("Filter app appcat", f"@{A}?['tags']", "@startsWith(item(), 'appCatID:')")
    # team:group\<id> (or the 1.2 form team:<id>) -> group members; team:user\<object id> -> that user only.
    app.compose("Team tag", "@if(empty(body('Filter_app_team')), '', substring(first(body('Filter_app_team')), 5))")
    app.compose("Team id", "@if(startsWith(outputs('Team_tag'), 'group\\'), substring(outputs('Team_tag'), 6), if(startsWith(outputs('Team_tag'), 'user\\'), '', outputs('Team_tag')))")
    app.compose("Owner user id", "@if(startsWith(outputs('Team_tag'), 'user\\'), substring(outputs('Team_tag'), 5), '')")
    app.set_var("Reset members", "varMembers", "")
    app.cond("Has team", eq("@empty(outputs('Team_id'))", False), yes=team)
    owner = Seq().graph("HTTP Owner user", "GET", f"{GRAPH}/users/@{{outputs('Owner_user_id')}}?$select=userPrincipalName")
    owner.set_var("Set owner member", "varMembers", "@concat(';', toLower(body('HTTP_Owner_user')?['userPrincipalName']), ';')")
    app.cond("Has owner user", eq("@empty(outputs('Owner_user_id'))", False), yes=owner)
    app.graph("HTTP App owners", "GET", f"{GRAPH}/applications/@{{{A}?['id']}}/owners/microsoft.graph.user?$select=userPrincipalName")
    app.select("Select owner upns", "@body('HTTP_App_owners')?['value']", "@toLower(item()?['userPrincipalName'])")
    app.graph("HTTP App SP", "GET", f"{GRAPH}/servicePrincipals?$filter=appId eq '@{{{A}?['appId']}}'&$select=id")
    app.sp_get_items("Get app row", "EntraCatalogApps", f"ObjectId eq '@{{{A}?['id']}}'", 1)
    app.cond("App row missing", is_true("@empty(body('Get_app_row')?['value'])"),
             yes=Seq().sp_post("Create app row", "EntraCatalogApps", row),
             no=Seq().sp_patch("Update app row", "EntraCatalogApps", "@first(body('Get_app_row')?['value'])?['ID']", row))
    s.foreach("Apply to each app", "@body('HTTP_List_managed_apps')?['value']", app)

    s.sp_get_items("Get catalog groups", "EntraCatalogGroups", None, 5000)
    grp = Seq()
    grp.graph("HTTP Group", "GET", f"{GRAPH}/groups/@{{{G}?['GroupId']}}?$select=id,displayName,description")
    grp.graph("HTTP Group members", "GET", f"{GRAPH}/groups/@{{{G}?['GroupId']}}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999")
    grp.graph("HTTP Group owners", "GET", f"{GRAPH}/groups/@{{{G}?['GroupId']}}/owners/microsoft.graph.user?$select=userPrincipalName")
    grp.select("Select group member upns", "@body('HTTP_Group_members')?['value']", "@toLower(item()?['userPrincipalName'])")
    grp.select("Select group owner upns", "@body('HTTP_Group_owners')?['value']", "@toLower(item()?['userPrincipalName'])")
    grp.sp_patch("Update group row", "EntraCatalogGroups", f"@{G}?['ID']", {
        "Title": "@body('HTTP_Group')?['displayName']", "Description": "@body('HTTP_Group')?['description']",
        "AppCatId": "@if(contains(coalesce(body('HTTP_Group')?['description'], ''), '[appCatID='), first(split(last(split(body('HTTP_Group')?['description'], '[appCatID=')), ';')), '')",
        "MemberUpns": "@concat(';', join(body('Select_group_member_upns'), ';'), ';')",
        "OwnerUpns": "@concat(';', join(body('Select_group_owner_upns'), ';'), ';')",
        "LastSynced": "@utcNow()"})
    s.foreach("Apply to each catalog group", "@body('Get_catalog_groups')?['value']", grp, concurrency=5)

    trig = {"Recurrence": {"type": "Recurrence", "recurrence": {"frequency": "Hour", "interval": 1}}}
    return flow(trig, s, ["shared_sharepointonline", "shared_webcontents"])


# ---------------------------------------------------------------------------
# ER-04 Onboard group
# ---------------------------------------------------------------------------
def er04() -> dict:
    s = Seq()
    s.sp_get_item("Get settings", "EntraSettings", 1)
    s.sp_patch("Mark in progress", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "InProgress"})
    s.compose("Requester", f"@toLower({REQ_UPN})")
    # What the user typed in the app: the group's display name or its Object ID.
    s.compose("Group query", "@trim(coalesce(triggerOutputs()?['body/TargetDisplayName'], triggerOutputs()?['body/TargetObjectId'], ''))")
    s.init_var("Init varGroup", "varGroup", "object", {})

    t = Seq()
    t.graph("HTTP Get requester", "GET", f"{GRAPH}/users/@{{outputs('Requester')}}?$select=id")
    sel = "$select=id,displayName,description,securityEnabled"

    by_id = Seq()
    by_id.graph("HTTP Get group by id", "GET", f"{GRAPH}/groups/@{{toLower(outputs('Group_query'))}}?{sel}", retry={"type": "none"})
    by_id.cond("Found by id", eq("@outputs('HTTP_Get_group_by_id')?['statusCode']", 200),
               yes=Seq().set_var("Set group from id", "varGroup", "@body('HTTP_Get_group_by_id')"),
               no=fail_item(Seq(), "Fail id not found", "Stop id not found",
                            "@concat('No group with Object ID ', outputs('Group_query'), ' was found. Check the ID (Entra admin center > Groups > the group > Object ID).')",
                            "GroupNotFound"),
               run_after={"HTTP_Get_group_by_id": ["Succeeded", "Failed"]})

    # OData string literal: a single quote in the name is written as two single quotes.
    one_quote, two_quotes = "'" * 4, "'" * 6          # expression literals for ' and ''
    name_literal = f"encodeUriComponent(replace(outputs('Group_query'), {one_quote}, {two_quotes}))"
    by_name = Seq()
    by_name.graph("HTTP Find group by name", "GET", f"{GRAPH}/groups?$filter=displayName eq '@{{{name_literal}}}'&{sel}&$top=5")
    by_name.cond("No group with that name", is_true("@empty(body('HTTP_Find_group_by_name')?['value'])"),
                 yes=fail_item(Seq(), "Fail name not found", "Stop name not found",
                               "@concat('No group named ', outputs('Group_query'), ' was found. Check the exact name, or enter the group''s Object ID.')",
                               "GroupNotFound"))
    by_name.cond("Several groups with that name", {"and": [{"greater": ["@length(body('HTTP_Find_group_by_name')?['value'])", 1]}]},
                 yes=fail_item(Seq(), "Fail name ambiguous", "Stop name ambiguous",
                               "@concat(string(length(body('HTTP_Find_group_by_name')?['value'])), ' groups are named ', outputs('Group_query'), '. Enter the Object ID of the one you mean.')",
                               "GroupNameAmbiguous"))
    by_name.set_var("Set group from name", "varGroup", "@first(body('HTTP_Find_group_by_name')?['value'])")

    t.cond("Query is object id",
           is_true("@and(equals(length(outputs('Group_query')), 36), equals(length(split(outputs('Group_query'), '-')), 5))"),
           yes=by_id, no=by_name)
    t.compose("Group id", "@variables('varGroup')?['id']")
    t.graph("HTTP Check membership", "POST", f"{GRAPH}/users/@{{body('HTTP_Get_requester')?['id']}}/checkMemberGroups",
            "{\"groupIds\": [\"@{outputs('Group_id')}\"]}")
    t.graph("HTTP Group owners", "GET", f"{GRAPH}/groups/@{{outputs('Group_id')}}/owners/microsoft.graph.user?$select=id,userPrincipalName")
    t.cond("Member or owner", is_true("@or(not(empty(body('HTTP_Check_membership')?['value'])), contains(string(body('HTTP_Group_owners')?['value']), body('HTTP_Get_requester')?['id']))"),
           no=fail_item(Seq(), "Fail not member", "Stop not member",
                        "@concat('You are neither a member nor an owner of ', variables('varGroup')?['displayName'], '. Ask one of its owners to add you, or pick another group.')",
                        "NotMemberOrOwner"))
    t.cond("Security enabled", eq("@variables('varGroup')?['securityEnabled']", True),
           no=fail_item(Seq(), "Fail not security", "Stop not security",
                        "@concat(variables('varGroup')?['displayName'], ' is not a security group. Only security-enabled groups can be used for owning teams and app roles.')",
                        "NotSecurityGroup"))
    t.graph("HTTP Group members", "GET", f"{GRAPH}/groups/@{{outputs('Group_id')}}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999")
    t.select("Select member upns", "@body('HTTP_Group_members')?['value']", "@toLower(item()?['userPrincipalName'])")
    t.select("Select owner upns", "@body('HTTP_Group_owners')?['value']", "@toLower(item()?['userPrincipalName'])")
    row = {
        "Title": "@variables('varGroup')?['displayName']", "GroupId": "@outputs('Group_id')",
        "Description": "@variables('varGroup')?['description']",
        "AppCatId": "@if(contains(coalesce(variables('varGroup')?['description'], ''), '[appCatID='), first(split(last(split(variables('varGroup')?['description'], '[appCatID=')), ';')), '')",
        "MemberUpns": "@concat(';', join(body('Select_member_upns'), ';'), ';')",
        "OwnerUpns": "@concat(';', join(body('Select_owner_upns'), ';'), ';')",
        "LastSynced": "@utcNow()"}
    t.sp_get_items("Get catalog row", "EntraCatalogGroups", "GroupId eq '@{outputs('Group_id')}'", 1)
    t.cond("Row missing", is_true("@empty(body('Get_catalog_row')?['value'])"),
           yes=Seq().sp_post("Create catalog row", "EntraCatalogGroups", row),
           no=Seq().sp_patch("Update catalog row", "EntraCatalogGroups", "@first(body('Get_catalog_row')?['value'])?['ID']", row))
    t.sp_patch("Mark completed", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "Completed", "CompletedAt": "@utcNow()",
        "TargetDisplayName": "@variables('varGroup')?['displayName']", "TargetObjectId": "@outputs('Group_id')",
        "ResultJson": "@string(setProperty(setProperty(json('{}'), 'groupId', outputs('Group_id')), 'groupDisplayName', variables('varGroup')?['displayName']))"})
    s.scope("Try", t)

    c = Seq()
    c.filter("Failed actions", "@result('Try')", "@equals(item()?['status'], 'Failed')")
    c.compose("Error text", "@concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-04 run history'))")
    c.sp_patch("Mark failed", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "Failed", "ErrorMessage": "@outputs('Error_text')"})
    s.scope("Catch", c, run_after={"Try": ["Failed", "TimedOut"]})

    trig = {"When_an_item_is_created": sp_trigger(
        "GetOnNewItems", "EntraRequests",
        "@and(equals(triggerBody()?['Status']?['Value'], 'Submitted'), equals(triggerBody()?['RequestType']?['Value'], 'onboardGroup'))")}
    return flow(trig, s, ["shared_sharepointonline", "shared_webcontents"])


def instant_catch(seq: "Seq", flow_label: str) -> None:
    c = Seq()
    c.filter("Failed actions", "@result('Try')", "@equals(item()?['status'], 'Failed')")
    c.compose("Error text", f"@concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the {flow_label} run history'))")
    c.sp_patch("Mark failed", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "Failed", "ErrorMessage": "@outputs('Error_text')"})
    seq.scope("Catch", c, run_after={"Try": ["Failed", "TimedOut"]})


NOT_OWNER = ("@concat('Not authorized owner: ', variables('varApp')?['displayName'], ' is tagged ', "
             "coalesce(first(body('App_team_tags')), 'with no team'), '. Only that user, or a member of that group, can use it here.')")


# ---------------------------------------------------------------------------
# ER-05 Find app: the Search button on the change screen
# ---------------------------------------------------------------------------
def er05() -> dict:
    s = Seq()
    s.sp_patch("Mark in progress", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "InProgress"})
    s.compose("Requester", f"@toLower({REQ_UPN})")
    # What the user typed in the app: the Application (client) ID or the Object ID.
    s.compose("App query", "@toLower(trim(coalesce(triggerOutputs()?['body/TargetDisplayName'], triggerOutputs()?['body/TargetObjectId'], '')))")
    s.init_var("Init varApp", "varApp", "object", {})
    s.init_var("Init varGroupOwner", "varGroupOwner", "string", "no")

    t = Seq()
    t.cond("Query is a GUID", is_true(GUID_CHECK.format(q="outputs('App_query')")),
           no=fail_item(Seq(), "Fail not a GUID", "Stop not a GUID",
                        "Enter the app registration's Application (client) ID or Object ID, for example 00000000-0000-0000-0000-000000000000.", "NotAGuid"))
    t.graph("HTTP Get requester", "GET", f"{GRAPH}/users/@{{outputs('Requester')}}?$select=id")
    find_app(t, "App", "outputs('App_query')", "varApp", "Fail app not found", "Stop app not found")
    is_owner = owner_check(t, "App", "variables('varApp')?['tags']", "body('HTTP_Get_requester')?['id']", "varGroupOwner")
    t.cond("Requester is owner", is_true(is_owner), no=fail_item(Seq(), "Fail not owner", "Stop not owner", NOT_OWNER, "NotAuthorizedOwner"))
    t.graph("HTTP Find SP", "GET", f"{GRAPH}/servicePrincipals?$filter=appId eq '@{{variables('varApp')?['appId']}}'&$select=id")
    t.filter("Filter appcat tag", "@coalesce(variables('varApp')?['tags'], json('[]'))", "@startsWith(item(), 'appCatID:')")
    t.filter("Filter team name tag", "@coalesce(variables('varApp')?['tags'], json('[]'))", "@startsWith(item(), 'teamName:')")
    t.compose("App catid", "@if(empty(body('Filter_appcat_tag')), '', substring(first(body('Filter_appcat_tag')), 9))")
    t.compose("Result", {
        "objectId": "@{variables('varApp')?['id']}", "appId": "@{variables('varApp')?['appId']}",
        "displayName": "@{variables('varApp')?['displayName']}", "appCatId": "@{outputs('App_catid')}",
        "team": "@{coalesce(first(body('App_team_tags')), '')}",
        "teamName": "@{if(empty(body('Filter_team_name_tag')), '', substring(first(body('Filter_team_name_tag')), 9))}",
        "identifierUri": "@{coalesce(first(variables('varApp')?['identifierUris']), '')}",
        "servicePrincipalId": "@{coalesce(first(body('HTTP_Find_SP')?['value'])?['id'], '')}",
        "appRolesJson": "@{string(coalesce(variables('varApp')?['appRoles'], json('[]')))}",
        "scopesJson": "@{string(coalesce(variables('varApp')?['api']?['oauth2PermissionScopes'], json('[]')))}"})
    t.sp_patch("Mark completed", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "Completed", "CompletedAt": "@utcNow()",
        "TargetDisplayName": "@variables('varApp')?['displayName']", "TargetObjectId": "@variables('varApp')?['id']",
        "AppCatId": "@outputs('App_catid')", "ResultJson": "@string(outputs('Result'))"})
    s.scope("Try", t)
    instant_catch(s, "ER-05")

    trig = {"When_an_item_is_created": sp_trigger(
        "GetOnNewItems", "EntraRequests",
        "@and(equals(triggerBody()?['Status']?['Value'], 'Submitted'), equals(triggerBody()?['RequestType']?['Value'], 'lookupApp'))")}
    return flow(trig, s, ["shared_sharepointonline", "shared_webcontents"])


# ---------------------------------------------------------------------------
# ER-06 Tag owning group: replace the app's team tag (team:user\... or another group) with team:group\<id>
# ---------------------------------------------------------------------------
def er06() -> dict:
    s = Seq()
    s.sp_patch("Mark in progress", "EntraRequests", ID, {"Title": TITLE, "Status/Value": "InProgress"})
    s.compose("Requester", f"@toLower({REQ_UPN})")
    s.compose("Payload", "@json(coalesce(triggerOutputs()?['body/PayloadJson'], '{}'))")
    s.compose("App query", "@toLower(trim(coalesce(outputs('Payload')?['app'], triggerOutputs()?['body/TargetObjectId'], '')))")
    s.compose("Group query", "@toLower(trim(coalesce(outputs('Payload')?['group'], '')))")
    s.compose("Now", "@utcNow()")
    s.init_var("Init varApp", "varApp", "object", {})
    s.init_var("Init varGroupOwner", "varGroupOwner", "string", "no")

    t = Seq()
    app_guid = GUID_CHECK.format(q="outputs('App_query')")[1:]
    group_guid = GUID_CHECK.format(q="outputs('Group_query')")[1:]
    t.cond("Inputs are GUIDs", is_true(f"@and({app_guid}, {group_guid})"),
           no=fail_item(Seq(), "Fail not GUIDs", "Stop not GUIDs",
                        "Enter the app registration's Application (client) ID or Object ID and the group's Object ID (both look like 00000000-0000-0000-0000-000000000000).", "NotAGuid"))
    t.graph("HTTP Get requester", "GET", f"{GRAPH}/users/@{{outputs('Requester')}}?$select=id")
    find_app(t, "App", "outputs('App_query')", "varApp", "Fail app not found", "Stop app not found")
    is_owner = owner_check(t, "App", "variables('varApp')?['tags']", "body('HTTP_Get_requester')?['id']", "varGroupOwner")
    t.cond("Requester is owner", is_true(is_owner), no=fail_item(Seq(), "Fail not owner", "Stop not owner", NOT_OWNER, "NotAuthorizedOwner"))

    t.graph("HTTP Get group", "GET", f"{GRAPH}/groups/@{{outputs('Group_query')}}?$select=id,displayName,securityEnabled", retry={"type": "none"})
    t.cond("Group found", eq("@outputs('HTTP_Get_group')?['statusCode']", 200),
           no=fail_item(Seq(), "Fail group not found", "Stop group not found",
                        "@concat('No group has the Object ID ', outputs('Group_query'), '.')", "GroupNotFound"),
           run_after={"HTTP_Get_group": ["Succeeded", "Failed"]})
    t.cond("Group security enabled", eq("@body('HTTP_Get_group')?['securityEnabled']", True),
           no=fail_item(Seq(), "Fail not security", "Stop not security",
                        "@concat(body('HTTP_Get_group')?['displayName'], ' is not a security group. Only security groups can own app registrations.')", "NotSecurityGroup"))
    t.graph("HTTP Check new group", "POST", f"{GRAPH}/users/@{{body('HTTP_Get_requester')?['id']}}/checkMemberGroups",
            "{\"groupIds\": [\"@{body('HTTP_Get_group')?['id']}\"]}")
    t.graph("HTTP New group owners", "GET", f"{GRAPH}/groups/@{{body('HTTP_Get_group')?['id']}}/owners?$select=id")
    t.cond("Member of new group", is_true("@or(not(empty(body('HTTP_Check_new_group')?['value'])), contains(string(body('HTTP_New_group_owners')?['value']), body('HTTP_Get_requester')?['id']))"),
           no=fail_item(Seq(), "Fail not in group", "Stop not in group",
                        "@concat('You are neither a member nor an owner of ', body('HTTP_Get_group')?['displayName'], '. You can only hand an app registration to a group you belong to.')", "NotGroupMember"))

    keep = "@not(or(startsWith(item(), 'team:'), startsWith(item(), 'teamName:'), startsWith(item(), 'lastUpdatedBy:'), startsWith(item(), 'lastUpdatedTimestamp:'), startsWith(item(), 'requestId:')))"
    t.filter("Kept app tags", "@coalesce(variables('varApp')?['tags'], json('[]'))", keep)
    t.compose("Team tags", "@createArray(concat('team:group\\', body('HTTP_Get_group')?['id']), concat('teamName:', body('HTTP_Get_group')?['displayName']))")
    t.compose("New app tags", "@union(body('Kept_app_tags'), outputs('Team_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])))")
    t.graph("HTTP Patch app tags", "PATCH", f"{GRAPH}/applications/@{{variables('varApp')?['id']}}", "{\"tags\": @{outputs('New_app_tags')}}")
    t.graph("HTTP Find SP", "GET", f"{GRAPH}/servicePrincipals?$filter=appId eq '@{{variables('varApp')?['appId']}}'&$select=id,tags")
    sp = Seq()
    sp.filter("Kept SP tags", "@coalesce(first(body('HTTP_Find_SP')?['value'])?['tags'], json('[]'))",
              "@not(or(startsWith(item(), 'team:'), startsWith(item(), 'teamName:')))")
    sp.graph("HTTP Patch SP tags", "PATCH", f"{GRAPH}/servicePrincipals/@{{first(body('HTTP_Find_SP')?['value'])?['id']}}",
             "{\"tags\": @{union(body('Kept_SP_tags'), outputs('Team_tags'))}}")
    t.cond("Has SP", eq("@empty(body('HTTP_Find_SP')?['value'])", False), yes=sp)
    t.sp_patch("Mark completed", "EntraRequests", ID, {
        "Title": TITLE, "Status/Value": "Completed", "CompletedAt": "@utcNow()",
        "TargetDisplayName": "@variables('varApp')?['displayName']", "TargetObjectId": "@variables('varApp')?['id']",
        "ResultJson": "@string(setProperty(setProperty(setProperty(setProperty(setProperty(json('{}'), 'applicationObjectId', variables('varApp')?['id']), 'appId', variables('varApp')?['appId']), 'previousTeam', coalesce(first(body('App_team_tags')), '')), 'groupId', body('HTTP_Get_group')?['id']), 'groupDisplayName', body('HTTP_Get_group')?['displayName']))"})
    s.scope("Try", t)
    instant_catch(s, "ER-06")

    trig = {"When_an_item_is_created": sp_trigger(
        "GetOnNewItems", "EntraRequests",
        "@and(equals(triggerBody()?['Status']?['Value'], 'Submitted'), equals(triggerBody()?['RequestType']?['Value'], 'tagOwnerGroup'))")}
    return flow(trig, s, ["shared_sharepointonline", "shared_webcontents"])


# ---------------------------------------------------------------------------
# ER-07 Requeue approved: re-saves Approved requests as the flow account so ER-02 picks them up
# (e.g. requests approved while ER-02 was off). Only members of EntraApproverEmails may run it.
# ---------------------------------------------------------------------------
def er07() -> dict:
    s = Seq()
    s.sp_get_item("Get settings", "EntraSettings", 1)
    # Set by Power Automate for the signed-in user who pressed Run; not something the user can type.
    s.compose("Runner", "@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))")
    s.compose("Entra team", f"@concat(';', toLower(replace(replace({APPROVER_LIST}, ',', ';'), ' ', '')), ';')")
    s.cond("Runner is in the Entra ID team", is_true("@and(not(empty(outputs('Runner'))), contains(outputs('Entra_team'), concat(';', outputs('Runner'), ';')))"),
           no=Seq().terminate("Stop not authorized", "Failed", "NotAuthorized",
                              "Not authorized: only the people listed in EntraSettings.EntraApproverEmails can requeue requests."))
    s.compose("Request id", "@trim(coalesce(triggerBody()?['text'], ''))")
    one_q, two_q = "'" * 4, "'" * 6          # expression literals for ' and ''
    s.compose("Filter query",
              "@concat('Status eq ''Approved'' and ManagerDecision eq ''Approved'' and EntraDecision eq ''Approved''', "
              "if(empty(outputs('Request_id')), '', concat(' and Title eq ''', replace(outputs('Request_id'), "
              + one_q + ", " + two_q + "), " + one_q + ")))")
    s.sp_get_items("Get approved requests", "EntraRequests", "@outputs('Filter_query')", 500)
    s.init_var("Init varRequeued", "varRequeued", "array", [])
    s.init_var("Init varWrongEditor", "varWrongEditor", "string", "")
    R = "items('Requeue_each_request')"
    each = Seq()
    # Status stays Approved. CompletionNotes changes so SharePoint records an edit by the flow account, which is
    # exactly what ER-02's trigger and guard look for; ER-02 overwrites the notes when it finishes.
    each.sp_patch("Requeue item", "EntraRequests", f"@{R}?['ID']", {
        "Title": f"@{R}?['Title']", "Status/Value": "Approved",
        "CompletionNotes": "@concat('Requeued by ', outputs('Runner'), ' at ', utcNow(), ' (ER-07). Waiting for ER-02.')"})
    each.append_var("Record requeued", "varRequeued", f"@{R}?['Title']")
    each.cond("Edited as the flow account",
              is_true("@equals(toLower(last(split(coalesce(body('Requeue_item')?['Editor']?['Claims'], ''), '|'))), toLower(body('Get_settings')?['ServiceAccountUpn']))"),
              no=Seq().set_var("Set wrong editor", "varWrongEditor", "@last(split(coalesce(body('Requeue_item')?['Editor']?['Claims'], ''), '|'))"))
    s.foreach("Requeue each request", "@body('Get_approved_requests')?['value']", each)
    s.mail("Mail summary", "@outputs('Runner')",
           "@concat('Entra Self-Service: ', string(length(variables('varRequeued'))), ' request(s) requeued')",
           "@concat(if(empty(variables('varRequeued')), 'No approved requests were waiting', concat(string(length(variables('varRequeued'))), ' request(s) requeued for ER-02: ', join(variables('varRequeued'), ', '))), "
           "if(empty(outputs('Request_id')), '', concat(' (filter: ', outputs('Request_id'), ')')), '.<br><br>', "
           "if(empty(variables('varWrongEditor')), 'ER-02 processes them one at a time; watch Status change to InProgress, then Completed or Failed, in My requests.', "
           "concat('<b>Warning:</b> the items were saved as ', variables('varWrongEditor'), ', not as the flow account (', body('Get_settings')?['ServiceAccountUpn'], '), so ER-02 will ignore them. In ER-07 > Run only users, set the SharePoint connection to the flow account''s connection (not Provided by run-only user), then run ER-07 again.')))")
    trig = {"manual": {"type": "Request", "kind": "Button",
                       "inputs": {"schema": {"type": "object", "properties": {
                           "text": {"title": "Request ID (optional)", "type": "string", "x-ms-dynamically-added": True,
                                    "description": "e.g. REQ-2610-AB12CD. Leave empty to requeue every approved request that is waiting.",
                                    "x-ms-content-hint": "TEXT"}}, "required": []}}}}
    return flow(trig, s, ["shared_sharepointonline", "shared_office365"])

# ---------------------------------------------------------------------------
# Solution files
# ---------------------------------------------------------------------------
def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


DESCRIPTIONS = {
    "SP-00 Create lists": "One-time setup: creates the EntraRequests, EntraCatalogApps, EntraCatalogGroups and EntraSettings lists if they do not exist.",
    "ER-01 Approvals": "Locks a new request, then collects manager and Entra ID team approvals. Sets Status = Approved for ER-02.",
    "ER-02 Execute": "Applies an approved request in Entra ID through Microsoft Graph (HTTP with Microsoft Entra ID, client certificate).",
    "ER-03 Catalog sync": "Hourly: refreshes EntraCatalogApps and EntraCatalogGroups from Entra ID. Read-only in Entra.",
    "ER-04 Onboard group": "Finds an existing group by name or Object ID and adds it to EntraCatalogGroups when the requester is a member or owner. Read-only in Entra; no approval.",
    "ER-05 Find app": "Search on the change screen: finds an app registration by Application (client) ID or Object ID and returns it only to an authorized owner (team:user\\<id> or team:group\\<id> tag). Read-only in Entra; no approval.",
    "ER-07 Requeue approved": "Instant, Entra ID team only (EntraApproverEmails): re-saves Approved requests as the flow account so ER-02 runs them, e.g. after ER-02 was turned off.",
    "ER-06 Tag owning group": "Replaces an app registration's team tag with team:group\\<id> when the requester is its authorized owner and a member of that group. No approval.",
}


def workflow_data_xml(name: str, wid: str, file: str) -> str:
    d = xml_escape(DESCRIPTIONS[name])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<Workflow WorkflowId="{{{wid}}}" Name="{xml_escape(name)}" Description="{d}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <JsonFileName>/Workflows/{file}</JsonFileName>
  <Type>1</Type>
  <Subprocess>0</Subprocess>
  <Category>5</Category>
  <Mode>0</Mode>
  <Scope>4</Scope>
  <OnDemand>0</OnDemand>
  <TriggerOnCreate>0</TriggerOnCreate>
  <TriggerOnDelete>0</TriggerOnDelete>
  <AsyncAutodelete>0</AsyncAutodelete>
  <SyncWorkflowLogOnFailure>0</SyncWorkflowLogOnFailure>
  <StateCode>0</StateCode>
  <StatusCode>1</StatusCode>
  <RunAs>1</RunAs>
  <IsTransacted>1</IsTransacted>
  <IntroducedVersion>1.0.0.0</IntroducedVersion>
  <IsCustomizable>1</IsCustomizable>
  <BusinessProcessType>0</BusinessProcessType>
  <IsCustomProcessingStepAllowedForOtherPublishers>1</IsCustomProcessingStepAllowedForOtherPublishers>
  <ModernFlowType>0</ModernFlowType>
  <PrimaryEntity>none</PrimaryEntity>
  <LocalizedNames>
    <LocalizedName languagecode="1033" description="{xml_escape(name)}" />
  </LocalizedNames>
  <Descriptions>
    <Description languagecode="1033" description="{d}" />
  </Descriptions>
</Workflow>
"""


def solution_xml(workflow_ids: list[str]) -> str:
    roots = "\n".join(f'      <RootComponent type="29" id="{{{w}}}" behavior="0" />' for w in workflow_ids)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml version="9.2.24023.198" SolutionPackageVersion="9.2" languagecode="1033" generatedBy="CrmLive" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <SolutionManifest>
    <UniqueName>{SOLUTION}</UniqueName>
    <LocalizedNames>
      <LocalizedName description="{SOLUTION_LABEL}" languagecode="1033" />
    </LocalizedNames>
    <Descriptions>
      <Description description="Entra ID self-service: SharePoint list setup flow, approvals, Graph execution and catalog sync." languagecode="1033" />
    </Descriptions>
    <Version>{VERSION}</Version>
    <Managed>0</Managed>
    <Publisher>
      <UniqueName>{PUBLISHER}</UniqueName>
      <LocalizedNames>
        <LocalizedName description="Entra Self-Service" languagecode="1033" />
      </LocalizedNames>
      <Descriptions />
      <EMailAddress xsi:nil="true"></EMailAddress>
      <SupportingWebsiteUrl xsi:nil="true"></SupportingWebsiteUrl>
      <CustomizationPrefix>{PREFIX}</CustomizationPrefix>
      <CustomizationOptionValuePrefix>48231</CustomizationOptionValuePrefix>
      <Addresses />
    </Publisher>
    <RootComponents>
{roots}
    </RootComponents>
    <MissingDependencies />
  </SolutionManifest>
</ImportExportXml>
"""


def customizations_xml() -> str:
    refs = "\n".join(f"""    <connectionreference connectionreferencelogicalname="{logical}">
      <connectionreferencedisplayname>{xml_escape(display)}</connectionreferencedisplayname>
      <connectorid>/providers/Microsoft.PowerApps/apis/{api}</connectorid>
      <iscustomizable>1</iscustomizable>
      <promptingbehavior>0</promptingbehavior>
      <statecode>0</statecode>
      <statuscode>1</statuscode>
    </connectionreference>""" for api, logical, display in CONN.values())
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ImportExportXml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Entities />
  <Roles />
  <Workflows />
  <FieldSecurityProfiles />
  <Templates />
  <EntityMaps />
  <EntityRelationships />
  <OrganizationSettings />
  <optionsets />
  <CustomControls />
  <EntityDataProviders />
  <connectionreferences>
{refs}
  </connectionreferences>
  <Languages>
    <Language>1033</Language>
  </Languages>
</ImportExportXml>
"""


ENV_VAR_XML = f"""<environmentvariabledefinition schemaname="{PREFIX}_SiteUrl">
  <description default="Full URL of the SharePoint site that holds the EntraRequests, EntraCatalogApps, EntraCatalogGroups and EntraSettings lists, e.g. https://contoso.sharepoint.com/teams/m365automationqa (no trailing slash).">
    <label description="Full URL of the SharePoint site that holds the EntraRequests, EntraCatalogApps, EntraCatalogGroups and EntraSettings lists, e.g. https://contoso.sharepoint.com/teams/m365automationqa (no trailing slash)." languagecode="1033" />
  </description>
  <displayname default="SharePoint site URL">
    <label description="SharePoint site URL" languagecode="1033" />
  </displayname>
  <introducedversion>1.0.0.0</introducedversion>
  <iscustomizable>1</iscustomizable>
  <isrequired>1</isrequired>
  <secretstore>0</secretstore>
  <type>100000000</type>
</environmentvariabledefinition>
"""


def build():
    if SRC.exists():
        shutil.rmtree(SRC)
    (SRC / "Other").mkdir(parents=True)
    (SRC / "Workflows").mkdir()
    env_dir = SRC / "environmentvariabledefinitions" / f"{PREFIX}_SiteUrl"
    env_dir.mkdir(parents=True)

    flows = {"SP-00 Create lists": sp00(), "ER-01 Approvals": er01(), "ER-02 Execute": er02(), "ER-03 Catalog sync": er03(),
             "ER-04 Onboard group": er04(), "ER-05 Find app": er05(), "ER-06 Tag owning group": er06(),
             "ER-07 Requeue approved": er07()}
    for name, definition in flows.items():
        wid = FLOW_IDS[name]
        file = f"{name.replace(' ', '').replace('-', '')}-{wid.upper()}.json"
        (SRC / "Workflows" / file).write_text(json.dumps(definition, indent=2, ensure_ascii=False))
        (SRC / "Workflows" / f"{file}.data.xml").write_text(workflow_data_xml(name, wid, file))
        print(f"  {name}: {count_actions(definition['properties']['definition']['actions'])} actions")
    (SRC / "Other" / "Solution.xml").write_text(solution_xml(list(FLOW_IDS.values())))
    (SRC / "Other" / "Customizations.xml").write_text(customizations_xml())
    (env_dir / "environmentvariabledefinition.xml").write_text(ENV_VAR_XML)
    print(f"wrote {SRC}")

    pac = os.environ.get("PAC") or shutil.which("pac")
    if not pac:
        print("pac not found: set PAC=/path/to/pac to also pack the zip")
        return
    DIST.mkdir(exist_ok=True)
    zipfile = DIST / f"{SOLUTION}_{VERSION.replace('.', '_')}.zip"
    subprocess.run([pac, "solution", "pack", "--zipfile", str(zipfile), "--folder", str(SRC),
                    "--packagetype", "Unmanaged"], check=True)
    print(f"packed {zipfile}")


def count_actions(actions: dict) -> int:
    n = 0
    for a in actions.values():
        n += 1
        n += count_actions(a.get("actions", {}))
        n += count_actions(a.get("else", {}).get("actions", {}))
        for c in a.get("cases", {}).values():
            n += count_actions(c.get("actions", {}))
    return n


if __name__ == "__main__":
    build()
