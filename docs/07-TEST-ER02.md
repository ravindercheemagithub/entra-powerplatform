# 7. Testing ER-02 Execute

ER-02 runs when a request's **Status becomes Approved**, and only if the item was last changed by the flow account and both decisions are Approved. It is the only flow that **changes Entra ID**: every successful test creates real objects. Work from the smallest request to the largest, and clean up at the end (7.8).

How to read a run (which steps ran, which failed, inputs and outputs): see [6.6 Checking a run](06-TEST-ER01.md#66-checking-a-run).

## 7.1 Before you start

| Check | How |
|---|---|
| ER-01 works | [doc 06](06-TEST-ER01.md) passes: an approved request ends with Status **Approved** and *Modified By* = the flow account |
| Graph connection works | In a scratch flow, **Invoke an HTTP request** `GET` `/v1.0/organization` succeeds, and a Compose with `body('Test')?['value']` shows your tenant (see doc 04, *The Graph connection*). A 403 means admin consent is missing; AADSTS700027 means the certificate doesn't match. |
| `EntraSettings.ServiceAccountUpn` | equals the UPN of the account that owns **ER-01's SharePoint connection** (lower case). Otherwise every ER-02 run is Cancelled. |
| `EntraSettings.ManagedByTag` | set, e.g. `entra-pp` (doc: [why](02-SHAREPOINT.md#entrasettings-exactly-one-item-id-1)) |
| Licence for group assignment | Assigning groups to app roles needs **Microsoft Entra ID P1 or P2** in the tenant |
| ER-02 is **on** | flow page → **Turn on** |
| Existing test groups | Groups are not created by this platform. Have **three security groups** you (the requester) are a **member** of, e.g. `grp-pp-team`, `grp-pp-users`, `grp-pp-admins`, and note their **Object IDs** (Entra → Groups → the group → Object ID). The payloads below use them as `<TEAM_ID>`, `<USERS_ID>` and `<ADMINS_ID>`. |

## 7.2 Two ways to start ER-02

**A. Full path (end to end).** Create a request as in [doc 06](06-TEST-ER01.md) and approve it twice. ER-01 sets Status = Approved and ER-02 starts within about a minute.

**B. Shortcut (ER-02 only, no approvals).** Sign in to SharePoint **as the flow account** and create the item directly as already approved. ER-01 ignores it (its trigger only fires for `Submitted`); ER-02's guard accepts it because the flow account made the change.

| Column | Value |
|---|---|
| Title | `REQ-T2-0001` (new number each test) |
| RequestType | as stated for the payload |
| Status | **Approved** |
| ManagerDecision | **Approved** |
| EntraDecision | **Approved** |
| AppCatId | `APP-1234` |
| TargetDisplayName | as stated for the payload |
| TargetObjectId | only for change requests (7.5) |
| Justification | `Testing ER-02` |
| PayloadJson | the payload |
| **ApprovedPayloadJson** | **the same payload**: ER-02 executes only this column |

With the shortcut the requester (*Created By*) is the flow account, so the **flow account** must be a member of `<TEAM_ID>`. Use path A at least once to test with a real requester.

Replace every `<…_ID>` in a payload with the real Object ID before pasting, in **both** payload columns.

## 7.3 Test 1: a minimal app registration

RequestType `createAppRegistration`, TargetDisplayName `APP-1234-D-PPTEST-pp-t2-app`. The display name follows the naming convention `<appCatID>-<env>-<BoR short name>-<free text>`.

```json
{"displayName":"APP-1234-D-PPTEST-pp-t2-app","appEnv":"D","borShortName":"PPTEST","nameText":"pp-t2-app","description":"ER-02 test","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"existing","id":"<TEAM_ID>","displayName":"grp-pp-team"},"redirectUrisWeb":"","redirectUrisSpa":"","exposeApi":{"enabled":false,"identifierUriTemplate":"api://{appId}","scopes":[]},"optionalClaimsIdToken":"","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"tags":""}
```

| Where | Expected |
|---|---|
| The item | Status **InProgress**, then **Completed**; ResultJson has applicationObjectId, appId, servicePrincipalId, teamGroupId |
| Requester's inbox | *Your Entra request REQ-T2-0001 is complete*, with the IDs |
| Entra → **App registrations** → the app | Created with the full display name; **Owners: none** (the platform adds no owners) |
| → **Manifest** (or Graph Explorer) | `tags` include `appCatID:APP-1234`, `appEnv:D`, `borShortName:PPTEST`, `team:<TEAM_ID>`, `teamName:grp-pp-team`, `createdBy:…`, `managedBy:entra-pp`, `requestId:REQ-T2-…`; `notes` = `appCatID=…; requestId=…; createdBy=…; managedBy=…` |
| Entra → **Enterprise applications** → the app | Created for the same **Application (client) ID**; **Properties → Assignment required: Yes** (from the payload's `appRoleAssignmentRequired`); **Users and groups**: grp-pp-team with **Default Access** |
| Entra → **Groups** | **No new groups** |
| `EntraCatalogApps` | New row with ObjectId, AppId, AppCatId, TeamGroupId/Name, ServicePrincipalId |

## 7.4 Test 2: API scope and two roles held by existing groups

RequestType `createAppRegistration`, TargetDisplayName `APP-1234-D-PPTEST-pp-t2-orders-api`:

```json
{"displayName":"APP-1234-D-PPTEST-pp-t2-orders-api","appEnv":"D","borShortName":"PPTEST","nameText":"pp-t2-orders-api","description":"Orders API (ER-02 test)","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"existing","id":"<TEAM_ID>","displayName":"grp-pp-team"},"redirectUrisWeb":"","redirectUrisSpa":"https://localhost:3000","exposeApi":{"enabled":true,"identifierUriTemplate":"api://{appId}","scopes":[{"value":"access_as_user","type":"User","adminConsentDisplayName":"Access pp-t2-orders-api","adminConsentDescription":"Allows the app to call pp-t2-orders-api as the signed-in user."}]},"optionalClaimsIdToken":"email","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[{"value":"OrdersApi.User","displayName":"pp-t2-orders-api User","description":"Can use pp-t2-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"existing","id":"<USERS_ID>","displayName":"grp-pp-users"}]},{"value":"OrdersApi.Admin","displayName":"pp-t2-orders-api Admin","description":"Can administer pp-t2-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"existing","id":"<ADMINS_ID>","displayName":"grp-pp-admins"}]}],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"tags":"costCentre=CC-0000"}
```

Expected, in addition to test 1:

| Where | Expected |
|---|---|
| The item | ResultJson includes identifierUri and `assignmentsText` = `grp-pp-users -> OrdersApi.User; grp-pp-admins -> OrdersApi.Admin` |
| The run | `Wait for app replication` (15 s) after `HTTP Create application`; `Until HTTP Expose API` succeeds on the first or a later attempt |
| App registration → **Expose an API** | Application ID URI `api://<appId>`; scope `access_as_user` |
| → **App roles** | OrdersApi.User and OrdersApi.Admin |
| → **Authentication** | SPA redirect URI `https://localhost:3000` |
| Enterprise app → **Users and groups** | grp-pp-users → OrdersApi.User, grp-pp-admins → OrdersApi.Admin |

## 7.5 Tests 3 to 6: changes to an existing app

These need **TargetObjectId** = the **Object ID** of the app from test 1 (Entra → App registrations → the app → Overview → *Object ID*), and **AppCatId** = `APP-1234`. The requester must be a member of the app's team group (`grp-pp-team`). Replace `<OBJECT_ID>` in the payload with that Object ID.

**Test 3, expose an API** (RequestType `exposeApi`):

```json
{"applicationObjectId":"<OBJECT_ID>","applicationDisplayName":"APP-1234-D-PPTEST-pp-t2-app","identifierUriTemplate":"api://{appId}","scopes":[{"value":"access_as_user","type":"User","adminConsentDisplayName":"Access pp-t2-app","adminConsentDescription":"Allows the app to call pp-t2-app as the signed-in user."}]}
```

Expected: Expose an API shows `api://<appId>` and `access_as_user`.

**Test 4, add an app role held by an existing group** (RequestType `addAppRoles`):

```json
{"applicationObjectId":"<OBJECT_ID>","applicationDisplayName":"APP-1234-D-PPTEST-pp-t2-app","appRoles":[{"value":"PpT2.Reader","displayName":"pp-t2-app Reader","description":"Read access","allowedMemberTypes":"User","assignGroups":[{"mode":"existing","id":"<USERS_ID>","displayName":"grp-pp-users"}]}]}
```

Expected: App roles shows PpT2.Reader; enterprise app → Users and groups shows grp-pp-users → PpT2.Reader.

**Test 5, assign another existing group to that role** (RequestType `assignGroupsToAppRoles`). `<ROLE_ID>` is the role's `id` (App registration → **Manifest** → `appRoles`, or the `AppRolesJson` column in EntraCatalogApps):

```json
{"applicationObjectId":"<OBJECT_ID>","applicationDisplayName":"APP-1234-D-PPTEST-pp-t2-app","assignments":[{"appRoleId":"<ROLE_ID>","appRoleValue":"PpT2.Reader","mode":"existing","id":"<ADMINS_ID>","displayName":"grp-pp-admins"}]}
```

Expected: enterprise app → Users and groups shows grp-pp-admins → PpT2.Reader.

**Test 6, create an enterprise app** for an app that has none. First run test 1 again with `"createServicePrincipal":false` and the free text `pp-t2-nosp`, then use its Object ID (RequestType `createServicePrincipal`):

```json
{"applicationObjectId":"<OBJECT_ID>","applicationDisplayName":"APP-1234-D-PPTEST-pp-t2-nosp","appRoleAssignmentRequired":true}
```

Expected: Enterprise applications lists the app, created for its appId, with Assignment required = Yes. Running the same request again fails with *This app already has an enterprise application.*

## 7.6 Negative tests (nothing must be created)

| Test | How | Expected |
|---|---|---|
| Hand-edited status | As a site owner who is **not** the flow account, set an item's Status to Approved (with both decisions Approved) | ER-02 run status **Cancelled** at `Approved by the flow`; nothing in Entra |
| Not your app | Path A: a requester who is not in the app's team group submits test 3 | Status **Failed**, *The app is not owned by any of your groups, or its appCatID differs.* |
| Wrong appCatID | Test 3 with AppCatId `APP-9999` | Status **Failed** with the same message |
| Not in owning team | Test 1 with `<TEAM_ID>` = a group the requester is not a member of | Status **Failed**, *You are not a member of the owning team.* |
| No owning team | Test 1 with `"owningGroup":{"mode":"existing","id":"","displayName":""}` | Status **Failed**, *The request has no owning team…* |
| Old-style new group | Test 2 with a role group `{"mode":"new","id":"","displayName":"grp-x"}` | Status **Failed**, *Group grp-x has no Object ID. Requests can only use existing groups…* (the app registration was created first; delete it) |
| Graph rejects the request | Test 1 with `"signInAudience":"NotAValue"` | Status **Failed**; ErrorMessage starts with `HTTP_Create_application:` and Graph's message; nothing created |

## 7.7 Troubleshooting

| Symptom | Likely cause |
|---|---|
| ER-02 never starts | Flow off; trigger condition not exactly `@equals(triggerOutputs()?['body/Status/Value'], 'Approved')`; Status not Approved |
| Every run **Cancelled** | `ServiceAccountUpn` is not the account in the item's *Modified By*; open the run → trigger outputs → `Editor` → `Claims` and compare the part after the last `\|` |
| `HTTP …` 401 / 403 | Connection uses the wrong auth type (must be *Client Certificate Auth*), certificate mismatch, or admin consent missing for a permission |
| `body('HTTP_…')?['id']` empty, later steps fail | The connector returned the body as text; see doc 04, *Check how responses come back* |
| `HTTP Create SP` fails 6 times | The new app had not replicated after ~70 s; rare, re-run |
| `HTTP Assign role` 400 *Permission being assigned was not found* | Role ID wrong (test 5) or the role does not allow `User` members |
| `HTTP Assign role` 403 / licence error | Tenant has no Entra ID P1/P2 for group assignment |
| Flow checker warns *"Your flow may have a circular loop"* on Mark in progress, Mark completed, Mark failed and the Fail … actions | Expected. ER-02 updates the list it is triggered by, but it only starts when Status = Approved and it only ever writes InProgress, Completed or Failed, so its own updates never start another run. The warnings don't stop the flow from saving or running. |
| Status stuck **InProgress** | The run is still going (open it), or it was cancelled manually; check run history |

## 7.8 Clean up

Done by you in Entra (the flows never delete anything):
1. **App registrations** → each `pp-t2-…` app → **Delete**. This also removes its enterprise app. Optionally **Deleted applications** → **Delete permanently**.
2. Groups: nothing to delete; the platform never creates groups. Keep `grp-pp-team`, `grp-pp-users` and `grp-pp-admins` for the next test.
3. SharePoint: delete the test items in `EntraRequests` and the test rows in `EntraCatalogApps` / `EntraCatalogGroups`.
