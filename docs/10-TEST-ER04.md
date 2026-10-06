# 10. Testing ER-04 Onboard group

ER-04 makes an **existing** Entra group selectable in the app (Owning team and group pickers). It runs when a request with **RequestType = onboardGroup** is created, checks that the requester is a **member or owner** of the group and that it is **security-enabled**, then creates or updates the group's row in `EntraCatalogGroups`. It needs no approval and **changes nothing in Entra**.

How to read a run: [6.6 Checking a run](06-TEST-ER01.md#66-checking-a-run).

## 10.1 Before you start

| Check | How |
|---|---|
| RequestType has the choice `onboardGroup` | EntraRequests → List settings → RequestType. Add it if missing (lists created before ER-04). |
| ER-01 skips onboardGroup | ER-01 trigger condition is `@and(equals(...Status..., 'Submitted'), not(equals(...RequestType..., 'onboardGroup')))` (solution 1.1, or doc 04). Otherwise ER-01 would send onboard requests for approval. |
| Graph connection works | as in [7.1](07-TEST-ER02.md#71-before-you-start) |
| ER-04 is **on** | flow page → Turn on |

## 10.2 Test 1: a group you belong to

1. Pick a **security group you are a member of** that is *not* in the app's Owning team list. Entra → Groups → the group → copy the **Object ID**.
2. In the app: Home → **Add existing group** (or on the New app screen: **Group not listed? Add an existing group**).
3. Paste the Object ID → **Add group**.

Expected:

| Where | Expected |
|---|---|
| App, *Your recent additions* | The request appears as **Submitted**, then (↻ Refresh after a minute) **Completed** with the group's name |
| `EntraRequests` item | RequestType `onboardGroup`; Status **Completed**; TargetDisplayName = group name; ResultJson `{"groupId":"…","groupDisplayName":"…"}`; ManagerDecision/EntraDecision stay **Pending** (no approval) |
| `EntraCatalogGroups` | A row with Title, GroupId, MemberUpns containing `;you@…;`, OwnerUpns, LastSynced |
| App → Register an application → Owning team | The group is listed (the screen refreshes the list when you open it) |
| ER-01 run history | **No** run for this request |
| Entra | Nothing changed |

Without the app, create the item by hand in EntraRequests: Title `REQ-T4-0001`, RequestType `onboardGroup`, Status `Submitted`, TargetObjectId = the Object ID.

## 10.3 Test 2: a group you own but aren't a member of

Same steps with a group where you are **owner only**. Expected: **Completed**; the row's OwnerUpns contains you. It appears in the role-group pickers (owners or members), but **not** in Owning team, which lists only groups you are a member of (ER-02 requires membership of the owning team).

## 10.4 Negative tests

| Test | How | Expected (Status **Failed**, ErrorMessage) |
|---|---|---|
| Not your group | Object ID of a group you are neither member nor owner of | *You are neither a member nor an owner of this group.* No catalog row. |
| Wrong ID | A GUID that is no group, e.g. `00000000-0000-0000-0000-000000000001` | *Group not found: check the Object ID …* |
| Not a security group | A Microsoft 365 group that is not security-enabled | *Only security-enabled groups can be used for owning teams and app roles.* |
| Already available | Object ID of a group already in your pickers | The app says *This group is already available to you* and creates no request |
| Not a GUID | `abc` | The app asks for an Object ID in GUID form and creates no request |

## 10.5 Re-adding and updates

Adding a group that already has a catalog row (e.g. added by someone else) **updates** that row instead of duplicating it. ER-03 keeps every row current each hour, so later membership changes in Entra show up without another request.

## 10.6 Troubleshooting

| Symptom | Likely cause |
|---|---|
| Stays **Submitted** | ER-04 is off, or its trigger condition doesn't match (RequestType value must be exactly `onboardGroup`) |
| Request went to the manager for approval | ER-01's trigger condition wasn't updated (10.1) |
| **Failed** with `HTTP_…: Insufficient privileges` | Graph connection or admin consent (`Directory.Read.All`, `User.Read.All`, `Group.ReadWrite.All` cover these reads) |
| Completed, but the group isn't in Owning team | You are owner only (10.3), or the app hasn't refreshed: reopen the New app screen |

## 10.7 Clean up

Delete the test items from `EntraRequests` and, if you want, the added rows from `EntraCatalogGroups`. Nothing was changed in Entra.
