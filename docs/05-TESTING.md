# 5. Testing against your tenant

Work through the steps in order. Each one proves one link before the next depends on it.

## 5.1 Graph identity (5 minutes, before any flow)

```bash
# Token as entra-pp-graph, using its certificate (PEM = key + cert)
cat entra/certs/entra-pp-graph.key entra/certs/entra-pp-graph.crt > /tmp/pp.pem
az login --service-principal -u <GraphClientId> --certificate /tmp/pp.pem --tenant <TenantId> --allow-no-subscriptions
az rest --method GET --url "https://graph.microsoft.com/v1.0/applications?\$top=1&\$select=id,displayName"
az account get-access-token --resource https://graph.microsoft.com --query accessToken -o tsv | cut -d. -f2 | base64 -d 2>/dev/null | grep -o '"roles":\[[^]]*\]'
az logout ; rm /tmp/pp.pem
```

The `roles` claim must list the five permissions from doc 01.

## 5.2 SharePoint

- As a normal user (not an owner), open the `EntraRequests` list: you see only your own items, after you create one.
- `EntraSettings` has exactly one item, ID 1, with TenantId, GraphClientId, ServiceAccountUpn (lower-case), approvers and Key Vault names.

## 5.3 ER-03 first (it has no side effects)

Run **ER-03 Catalog sync** manually. Expected:
- Run succeeds. With no managed apps yet, `Apply to each app` has 0 iterations.
- Add a row to `EntraCatalogGroups` with Title + GroupId of a group **you** are a member of, run ER-03 again: MemberUpns contains `;you@contoso.com;`.
- In the app, the wizard's **Owning team** box now lists that group.

## 5.4 A security group, end to end (the smallest request)

1. App → **Security group** → name `grp-pp-test-01`, appCatID, justification → **Submit request**.
2. Within a minute, the SharePoint item:
   - is read-only for you (its permissions stopped inheriting; you have Read)
   - shows `Status = PendingManagerApproval`, with ManagerEmail / ManagerName filled and ApprovedPayloadJson = PayloadJson
3. The manager gets an approval in Outlook / Teams with the summary → **Approve**. Status becomes `PendingEntraApproval`, and the Entra approvers get theirs → **Approve**.
4. Status becomes `Approved` → **ER-02** runs → `InProgress` → `Completed`, with ResultJson `{"groupId": "…"}`.
5. In Entra: the group exists, its description ends with `[appCatID=…; requestId=REQ-…; createdBy=you; managedBy=entra-pp]`, and you are owner and member.
6. **My requests** shows four green stages and the group ID.

## 5.5 The full app registration

Wizard: name `pp-orders-api`, your appCatID, owning team = the group from 5.4. Then:
- **Section 2:** tick Expose an API, add `access_as_user`, tick `email` (ID token), groups claim `ApplicationGroup`.
- **Section 3:** *User + Admin roles with groups*.
- **Section 4:** defaults.

Submit, approve twice. Check in the Entra admin center:

| Where | Expect |
|---|---|
| App registrations → pp-orders-api → Overview | Application ID URI `api://<appId>` |
| → Expose an API | scope `access_as_user` |
| → App roles | `PpOrdersApi.User`, `PpOrdersApi.Admin` |
| → Token configuration | optional claim `email` (ID), groups claim *Groups assigned to the application* |
| → Owners | you |
| → Manifest | `tags` with appCatID, team, teamName, createdBy, requestId, managedBy; `notes` |
| Enterprise applications → pp-orders-api → Properties | *Assignment required = Yes* |
| → Users and groups | `grp-pp-orders-api-users` → User role, `grp-pp-orders-api-admins` → Admin role |
| Groups | both groups exist, owned by you, with the appCatID line in their description |

After the next ER-03 run (or right away, through ER-02's catalog insert), the app appears under **Expose an API / App roles / Role assignments** in the app.

## 5.6 Negative tests

| Test | Expected |
|---|---|
| A user opens a colleague's request URL in SharePoint | not visible (item-level security) |
| Requester edits their item after submitting | denied (read-only after ER-01's lock) |
| Site owner sets Status = Approved by hand on a request | ER-02 runs and stops at `Approved by the flow?` (Terminate: Cancelled). Nothing executes. |
| Requester is their own approver (e.g. a manager requesting) and approves | recorded as Rejected |
| Change request for an app your groups don't own (forge the item as an owner) | ER-02: `Failed – The app is not owned by any of your groups` |
| Remove `AppRoleAssignment.ReadWrite.All` from entra-pp-graph, request role assignments | `Failed` with a Graph *Authorization_RequestDenied* message in ErrorMessage. Restore the permission. |

## 5.7 Troubleshooting

| Symptom | Cause / fix |
|---|---|
| HTTP action: `AADSTS700027` / *client assertion* | PFX doesn't match the certificate uploaded to entra-pp-graph, or wrong password. Re-export with `-legacy`. |
| HTTP action 403 `Authorization_RequestDenied` | the Graph application permission isn't granted / consented (doc 01) |
| `POST /servicePrincipals` 400 *does not reference a valid application* | replication lag; the Do-until retries. Raise the count if your tenant is slow. |
| `appRoleAssignedTo` 400/404 right after creating a group | replication lag; increase *Wait for group replication* to 30 s |
| ER-01 `Break inheritance` 403 | svc-entra-flows is not a site owner |
| App: Owning team box empty | no catalog group contains you: run ER-03 / add your group to EntraCatalogGroups |
| App paste error on a control | see doc 03 §3.3 |
| Flow designer leaves `@{…}` as text | switch off *New designer*, paste, switch back (doc 04) |
