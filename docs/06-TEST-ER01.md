# 6. Testing ER-01 Approvals on its own (no Power App needed)

ER-01 runs when a **new item** is added to `EntraRequests` with **Status = Submitted**. You can create that item by hand in the SharePoint list, so the Power App doesn't need to exist yet. ER-01 changes nothing in Entra ID; it only locks the item, collects two approvals and updates the item.

## 6.1 Before you start

- **Turn ER-02 off** if you have built it (flow page → **Turn off**). Otherwise a fully approved test request creates real objects in Entra.
- Create the test items as a **test requester**: a user who has a **Manager** set in Entra, and who is not the flow account and not in `EntraApproverEmails`. Whoever creates the item is the requester (*Created By*).
- `EntraSettings` item 1 must have these filled in:

| Column | Value for testing |
|---|---|
| `FallbackApproverEmail` | an approver used when the requester has no manager |
| `EntraApproverEmails` | one or more Entra team approvers, `;`-separated on one line, e.g. `alice@contoso.com;bob@contoso.com` |
| `PowerAppUrl` | until the app exists, the list URL: `https://<tenant>.sharepoint.com/teams/m365automationqa/Lists/EntraRequests`. The approval cards link to it. |

## 6.2 Create a test request

1. Optional: open ER-01 → **Test** → **Manually** → **Test**, to watch the run live.
2. Signed in as the test requester, open the site → **EntraRequests** → **+ New**.
3. Fill in the columns below, paste one of the payloads from 6.3 into **PayloadJson**, and **Save**. Leave every other column empty.

| Column | Value |
|---|---|
| Title | `REQ-TEST-0001` (use a new number for each test) |
| RequestType | the type of the payload you paste (e.g. `createAppRegistration`) |
| Status | `Submitted` (the default; leave it) |
| AppCatId | `APP-1234` |
| TargetDisplayName | the payload's `displayName` (e.g. `pp-test-app`) |
| Justification | `Testing ER-01` |
| PayloadJson | a payload from 6.3, pasted as a single line |

The flow starts within about a minute (sooner in test mode). PayloadJson must be valid JSON; if it is empty or broken, the `Payload` step fails.

## 6.3 Test payloads

Copy the whole line. Each one is valid JSON.

**A. createAppRegistration, minimal** (RequestType `createAppRegistration`, TargetDisplayName `pp-test-app`)

```json
{"displayName":"pp-test-app","description":"ER-01 test","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"new","id":"","displayName":"grp-pp-test-team","description":"","ownerIds":""},"redirectUrisWeb":"","redirectUrisSpa":"","exposeApi":{"enabled":false,"identifierUriTemplate":"api://{appId}","scopes":[]},"optionalClaimsIdToken":"","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"additionalOwnerIds":"","tags":""}
```

**B. createAppRegistration with an API scope and two roles with groups** (RequestType `createAppRegistration`, TargetDisplayName `pp-orders-api`). The approval summary then shows the API and both roles.

```json
{"displayName":"pp-orders-api","description":"Orders API (ER-01 test)","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"new","id":"","displayName":"grp-pp-orders-team","description":"","ownerIds":""},"redirectUrisWeb":"","redirectUrisSpa":"https://localhost:3000","exposeApi":{"enabled":true,"identifierUriTemplate":"api://{appId}","scopes":[{"value":"access_as_user","type":"User","adminConsentDisplayName":"Access pp-orders-api","adminConsentDescription":"Allows the app to call pp-orders-api as the signed-in user."}]},"optionalClaimsIdToken":"email","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[{"value":"OrdersApi.User","displayName":"pp-orders-api User","description":"Can use pp-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"new","id":"","displayName":"grp-pp-orders-users","description":"","ownerIds":""}]},{"value":"OrdersApi.Admin","displayName":"pp-orders-api Admin","description":"Can administer pp-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"new","id":"","displayName":"grp-pp-orders-admins","description":"","ownerIds":""}]}],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"additionalOwnerIds":"","tags":"costCentre=CC-0000"}
```

**C. createGroup** (RequestType `createGroup`, TargetDisplayName `grp-pp-test-group`)

```json
{"displayName":"grp-pp-test-group","description":"ER-01 test group","ownerIds":"","memberIds":""}
```

## 6.4 What should happen

| After | Where to check | Expected |
|---|---|---|
| Steps 2–6 (lock) | The item → **… → Manage access** | The item has its own permissions: Owners have Full Control, the requester has **Read** only. As the requester, editing the item is no longer possible. |
| Step 14 | The item | Status **PendingManagerApproval**; ManagerEmail and ManagerName filled in; ApprovedPayloadJson equals PayloadJson; RequestSummary has text |
| Step 15 | The manager's Outlook, Teams Approvals app, or Power Automate → **Approvals** | Card *Entra request REQ-TEST-0001: createAppRegistration – pp-test-app* with the summary |
| Manager approves | The item | ManagerDecision **Approved**, ManagerDecisionBy/At/Comment filled; Status **PendingEntraApproval** |
| Step 20 | The Entra approvers' inbox / Approvals | Card *Entra team approval – REQ-TEST-0001: pp-test-app* |
| Entra team approves | The item, and the requester's inbox | EntraDecision **Approved**; **Status Approved**; *Modified By* = the flow account; the requester gets *… is approved and being applied* |

Follow the run as described in [6.6](#66-checking-a-run). While it waits for an approval the run shows **Running**, which is normal. The first approval in a new environment can take a few minutes while Power Automate sets up Approvals (Dataverse).

*Modified By* on the final update must be the account in `EntraSettings.ServiceAccountUpn`, or ER-02 will refuse to run later.

## 6.5 Other paths

Use a new Title for each test.

| Test | How | Expected |
|---|---|---|
| Manager rejects | Reject with a comment | Status **Rejected**; requester gets *rejected by your manager* with the comment |
| Entra team rejects | Manager approves, Entra team rejects | Status **Rejected**; requester gets *rejected by the Entra ID team* |
| Self-approval | Put the test requester in `FallbackApproverEmail` (and use a requester without a manager) or in `EntraApproverEmails`, then approve their own request | Treated as **Reject**; the manager rejection email adds *a request cannot be approved by the person who raised it* |
| No manager | Submit as a user with no Manager in Entra | `Get manager` fails (red) but the run continues; the approval goes to `FallbackApproverEmail` |

## 6.6 Checking a run

The same applies to ER-02 and ER-03.

1. Go to make.powerautomate.com → **My flows** (or **Solutions** → your solution → the flow) → click the flow's name.
2. The flow's details page lists **28-day run history**: start time, duration and status for each run.

| Status | Meaning |
|---|---|
| **Running** | Still going; for ER-01 usually waiting for an approval |
| **Succeeded** | Every step that ran finished without error |
| **Failed** | A step failed and nothing handled it |
| **Cancelled** | Stopped by a Terminate (Cancelled) action, e.g. ER-02's guard, or cancelled by hand |

3. Click a run's **start time** to open it. Every action shows its result:
   - green tick: succeeded
   - red exclamation: **failed**; the error is shown when you expand it, and the run summary at the top names the failing action
   - grey: skipped (a branch that didn't run, or a step after a failure)
4. Click any action to expand it and see its **Inputs** and **Outputs** (**Show raw inputs / outputs** for the full JSON). For example:
   - `Manager email` → Outputs: the address the approval went to
   - `Payload` → Outputs: the parsed request
   - a SharePoint HTTP step → Outputs: status code and SharePoint's error message
   - a **Condition** shows which branch ran (*true* / *false*) and the values it compared
   - an **Apply to each** has **< Previous / Next >** to step through iterations; failed iterations are marked
   - actions with **Secure inputs/outputs** on show *Content not shown due to security configuration*
5. Buttons at the top of a run: **Resubmit** reruns the flow with the same trigger data (after you fix the flow); **Cancel run** stops a running one.

Elsewhere:
- **All runs**, at the bottom right of the run history, shows more than the latest runs, with a status filter.
- **Monitor → Cloud flow activity**, in the left menu, lists failed runs across all your flows.
- **Approvals → Sent / Received / History** shows each approval, who it was assigned to and the response.
- Before saving, the **Flow checker** (stethoscope icon in the designer) lists errors and warnings in expressions.

## 6.7 Troubleshooting

| Symptom | Likely cause |
|---|---|
| Flow never starts | Flow is off; wrong site/list on the trigger; trigger condition not exactly `@equals(triggerOutputs()?['body/Status/Value'], 'Submitted')`; Status was not `Submitted` |
| `Ensure requester` 400 | Body is not exactly `{"logonName": "@{triggerOutputs()?['body/Author/Claims']}"}`, or the Content-Type header is missing |
| `Break inheritance` / `Grant …` 403 | The flow account is not a **site owner** |
| `Payload` fails | PayloadJson empty or not valid JSON |
| `Get locked item` / `Update …` "Enter a valid integer" | Id typed as text; use fx `int(triggerOutputs()?['body/ID'])` |
| `Update …` fails with an invalid choice | A choice value is misspelt; compare with the column's choices in list settings |
| Approval fails on Item link | PowerAppUrl empty; set the temporary list URL from 6.1 |
| No approval email | Power Automate → **Approvals → Sent**; open `Manager email` → Outputs in the run to see the address used |
| Run stuck **Running** | It is waiting for an approval; answer it |

## 6.8 Clean up

Delete the test items from `EntraRequests` (as a site owner). Nothing was created in Entra ID.
