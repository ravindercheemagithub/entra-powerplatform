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

With the shortcut the requester (*Created By*) is the flow account, so the flow account becomes owner of what it creates. That is fine for testing. Use path A at least once to test with a real requester.

## 7.3 Test 1: a security group (smallest request)

RequestType `createGroup`, TargetDisplayName `grp-pp-t2-group`:

```json
{"displayName":"grp-pp-t2-group","description":"ER-02 test group","ownerIds":"","memberIds":""}
```

| Where | Expected |
|---|---|
| The item | Status **InProgress**, then **Completed**; CompletedAt set; ResultJson `{"groupId":"…","groupDisplayName":"grp-pp-t2-group",…}` |
| Requester's inbox | *Your Entra request REQ-T2-0001 is complete*, with the group ID |
| Entra → **Groups** → grp-pp-t2-group | Security group; **Owners**: the requester; description ends with `[appCatID=APP-1234; requestId=REQ-T2-0001; createdBy=…; managedBy=entra-pp]` |
| `EntraCatalogGroups` | New row with Title, GroupId, AppCatId, OwnerUpns `;requester;` |

## 7.4 Test 2 and 3: app registrations

**Test 2, minimal** (RequestType `createAppRegistration`, TargetDisplayName `pp-t2-app`):

```json
{"displayName":"pp-t2-app","description":"ER-02 test","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"new","id":"","displayName":"grp-pp-t2-team","description":"","ownerIds":""},"redirectUrisWeb":"","redirectUrisSpa":"","exposeApi":{"enabled":false,"identifierUriTemplate":"api://{appId}","scopes":[]},"optionalClaimsIdToken":"","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"additionalOwnerIds":"","tags":""}
```

**Test 3, with an API scope and two roles with new groups** (RequestType `createAppRegistration`, TargetDisplayName `pp-t2-orders-api`):

```json
{"displayName":"pp-t2-orders-api","description":"Orders API (ER-02 test)","signInAudience":"AzureADMyOrg","owningGroup":{"mode":"new","id":"","displayName":"grp-pp-t2-orders-team","description":"","ownerIds":""},"redirectUrisWeb":"","redirectUrisSpa":"https://localhost:3000","exposeApi":{"enabled":true,"identifierUriTemplate":"api://{appId}","scopes":[{"value":"access_as_user","type":"User","adminConsentDisplayName":"Access pp-t2-orders-api","adminConsentDescription":"Allows the app to call pp-t2-orders-api as the signed-in user."}]},"optionalClaimsIdToken":"email","optionalClaimsAccessToken":"","groupMembershipClaims":"None","appRoles":[{"value":"OrdersApi.User","displayName":"pp-t2-orders-api User","description":"Can use pp-t2-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"new","id":"","displayName":"grp-pp-t2-orders-users","description":"","ownerIds":""}]},{"value":"OrdersApi.Admin","displayName":"pp-t2-orders-api Admin","description":"Can administer pp-t2-orders-api","allowedMemberTypes":"User","assignGroups":[{"mode":"new","id":"","displayName":"grp-pp-t2-orders-admins","description":"","ownerIds":""}]}],"createServicePrincipal":true,"appRoleAssignmentRequired":true,"additionalOwnerIds":"","tags":"costCentre=CC-0000"}
```

| Where | Expected |
|---|---|
| The item | **Completed**; ResultJson has applicationObjectId, appId, identifierUri (test 3), servicePrincipalId, teamGroupId, assignmentsText (test 3: `grp-pp-t2-orders-users -> OrdersApi.User; grp-pp-t2-orders-admins -> OrdersApi.Admin`) |
| Entra → **App registrations** → the app → **Overview** | Created; **Owners** = the requester |
| → **Manifest** (or Graph Explorer) | `tags` include `appCatID:APP-1234`, `team:<group id>`, `teamName:grp-pp-t2-…-team`, `createdBy:…`, `managedBy:entra-pp`, `requestId:REQ-T2-…` (test 3 also `costCentre:CC-0000`); `notes` = `appCatID=…; requestId=…; createdBy=…; managedBy=…` |
| → **Expose an API** (test 3) | Application ID URI `api://<appId>`; scope `access_as_user` |
| → **App roles** (test 3) | OrdersApi.User and OrdersApi.Admin |
| → **Authentication** (test 3) | SPA redirect URI `https://localhost:3000` |
| Entra → **Enterprise applications** → the app → **Properties** | **Assignment required: Yes** |
| → **Users and groups** | Test 2: the team group with **Default Access**. Test 3: grp-pp-t2-orders-users → OrdersApi.User, grp-pp-t2-orders-admins → OrdersApi.Admin |
| Entra → **Groups** | The team group (requester is owner and member) and, for test 3, the two role groups (requester is owner); descriptions end with the `[appCatID=…]` stamp |
| `EntraCatalogApps` | New row with ObjectId, AppId, AppCatId, TeamGroupId/Name, ServicePrincipalId, AppRolesJson |
| `EntraCatalogGroups` | Rows for each new group |

## 7.5 Tests 4 to 7: changes to an existing app

These need **TargetObjectId** = the **Object ID** of an app created in test 2 or 3 (Entra → App registrations → the app → Overview → *Object ID*), and **AppCatId** = that app's appCatID (`APP-1234`). The requester must be in the app's team group or an owner of the app: with path B that is the flow account, which owns the apps it created.

Replace `<objectId>` in the payload with the same Object ID.

**Test 4, expose an API** on pp-t2-app (RequestType `exposeApi`, TargetDisplayName `pp-t2-app`):

```json
{"applicationObjectId":"<objectId>","applicationDisplayName":"pp-t2-app","identifierUriTemplate":"api://{appId}","scopes":[{"value":"access_as_user","type":"User","adminConsentDisplayName":"Access pp-t2-app","adminConsentDescription":"Allows the app to call pp-t2-app as the signed-in user."}]}
```

Expected: Expose an API shows `api://<appId>` and `access_as_user`; tags now include a new `lastUpdatedTimestamp` and `requestId`.

**Test 5, add app roles** with a new group (RequestType `addAppRoles`, TargetDisplayName `pp-t2-app`):

```json
{"applicationObjectId":"<objectId>","applicationDisplayName":"pp-t2-app","appRoles":[{"value":"PpT2.Reader","displayName":"pp-t2-app Reader","description":"Read access","allowedMemberTypes":"User","assignGroups":[{"mode":"new","id":"","displayName":"grp-pp-t2-readers","description":"","ownerIds":""}]}]}
```

Expected: App roles shows PpT2.Reader next to any existing roles; enterprise app → Users and groups shows grp-pp-t2-readers → PpT2.Reader.

**Test 6, assign an existing group to an existing role** (RequestType `assignGroupsToAppRoles`, TargetDisplayName `pp-t2-app`). You need:
- `<roleId>`: the role's ID. Entra → App registrations → pp-t2-app → **Manifest** → `appRoles` → the `id` of PpT2.Reader; or the `AppRolesJson` column in EntraCatalogApps.
- `<groupId>`: the Object ID of an existing security group, e.g. grp-pp-t2-group from test 1.

```json
{"applicationObjectId":"<objectId>","applicationDisplayName":"pp-t2-app","assignments":[{"appRoleId":"<roleId>","appRoleValue":"PpT2.Reader","mode":"existing","id":"<groupId>","displayName":"grp-pp-t2-group","description":"","ownerIds":""}]}
```

Expected: enterprise app → Users and groups shows grp-pp-t2-group → PpT2.Reader; ResultJson `assignmentsText` = `grp-pp-t2-group -> PpT2.Reader`.

**Test 7, create an enterprise app** for an app that has none. First run test 2 again with `"createServicePrincipal":false` and a new name (e.g. `pp-t2-nosp`), then use its Object ID (RequestType `createServicePrincipal`, TargetDisplayName `pp-t2-nosp`):

```json
{"applicationObjectId":"<objectId>","applicationDisplayName":"pp-t2-nosp","appRoleAssignmentRequired":true}
```

Expected: Enterprise applications now lists pp-t2-nosp with Assignment required = Yes. Running the same request again fails with *This app already has an enterprise application.*

## 7.6 Negative tests (nothing must be created)

| Test | How | Expected |
|---|---|---|
| Hand-edited status | As a site owner who is **not** the flow account, set an item's Status to Approved (with both decisions Approved) | ER-02 run status **Cancelled** at `Approved by the flow`; the item stays as it was; nothing in Entra |
| Not your app | Path A: a requester who is neither in the app's team group nor an owner submits test 4 for pp-t2-app | Status **Failed**, ErrorMessage *The app is not owned by any of your groups, or its appCatID differs.* |
| Wrong appCatID | Test 4 with AppCatId `APP-9999` | Status **Failed** with the same message |
| Not in owning team | Test 2 with `"owningGroup":{"mode":"existing","id":"<a group the requester is not in>",…}` | Status **Failed**, *You are not a member of the owning team.* |
| Graph rejects the request | Test 2 with `"signInAudience":"NotAValue"` | Status **Failed**; ErrorMessage starts with `HTTP_Create_application:` and Graph's message; requester and Entra team get *… failed*; ResultJson shows what was created before the failure (here the team group) |

## 7.7 Troubleshooting

| Symptom | Likely cause |
|---|---|
| ER-02 never starts | Flow off; trigger condition not exactly `@equals(triggerOutputs()?['body/Status/Value'], 'Approved')`; Status not Approved |
| Every run **Cancelled** | `ServiceAccountUpn` is not the account in the item's *Modified By*; open the run → trigger outputs → `Editor` → `Claims` and compare the part after the last `\|` |
| `HTTP …` 401 / 403 | Connection uses the wrong auth type (must be *Client Certificate Auth*), certificate mismatch, or admin consent missing for a permission |
| `body('HTTP_…')?['id']` empty, later steps fail | The connector returned the body as text; see doc 04, *Check how responses come back* |
| `HTTP Create SP` fails 6 times | The new app had not replicated after ~70 s; rare, re-run |
| `HTTP Assign role` 400 *Permission being assigned was not found* | Role ID wrong (test 6) or the role does not allow `User` members |
| `HTTP Assign role` 403 / licence error | Tenant has no Entra ID P1/P2 for group assignment |
| Flow checker warns *"Your flow may have a circular loop"* on Mark in progress, Mark completed, Mark failed and the Fail … actions | Expected. ER-02 updates the list it is triggered by, but it only starts when Status = Approved and it only ever writes InProgress, Completed or Failed, so its own updates never start another run. The warnings don't stop the flow from saving or running. |
| Status stuck **InProgress** | The run is still going (open it), or it was cancelled manually; check run history |

## 7.8 Clean up

Done by you in Entra (the flows never delete anything):
1. **App registrations** → each `pp-t2-…` app → **Delete**. This also removes its enterprise app. Optionally **Deleted applications** → **Delete permanently**.
2. **Groups** → each `grp-pp-t2-…` group → **Delete**.
3. SharePoint: delete the test items in `EntraRequests` and the test rows in `EntraCatalogApps` / `EntraCatalogGroups`.
