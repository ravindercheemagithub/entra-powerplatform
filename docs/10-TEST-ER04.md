# 10. Testing ER-04 Onboard group

Groups are created outside this platform. ER-04 makes an **existing** Entra group selectable in the app (Owning team and group pickers). It runs when a request with **RequestType = onboardGroup** is created, finds the group by **display name or Object ID**, checks that the requester is a **member or owner** of the group and that it is **security-enabled**, then creates or updates the group's row in `EntraCatalogGroups`. It needs no approval and **changes nothing in Entra**.

How to read a run: [6.6 Checking a run](06-TEST-ER01.md#66-checking-a-run).

## 10.1 Before you start

| Check | How |
|---|---|
| RequestType has the choice `onboardGroup` | EntraRequests → List settings → RequestType. Add it if missing (lists created before ER-04). |
| ER-01 skips onboardGroup | ER-01 trigger condition is `@and(equals(...Status..., 'Submitted'), not(equals(...RequestType..., 'onboardGroup')))` (solution 1.1, or doc 04). Otherwise ER-01 would send onboard requests for approval. |
| Graph connection works | as in [7.1](07-TEST-ER02.md#71-before-you-start) |
| ER-04 is **on** | flow page → Turn on |

## 10.2 Test 1: a group you belong to

1. Pick a **security group you are a member of** that is *not* in the app's Owning team list. Note its exact **display name** and its **Object ID** (Entra → Groups → the group).
2. In the app: Home → **Add existing group** (or on the New app screen: **Group not listed? Add an existing group**).
3. Type the group's **exact name** (test 1a) or paste its **Object ID** (test 1b) → **Add group**. The app shows *Checking the group in Entra…* and then the result in a banner, within a few seconds.

Expected:

| Where | Expected |
|---|---|
| App | Banner *Added: <group>. It is now available in the Owning team and role-group pickers.*; *Your recent additions* shows **Completed** |
| `EntraRequests` item | RequestType `onboardGroup`; Status **Completed**; TargetDisplayName = group name; ResultJson `{"groupId":"…","groupDisplayName":"…"}`; ManagerDecision/EntraDecision stay **Pending** (no approval) |
| `EntraCatalogGroups` | A row with Title, GroupId, MemberUpns containing `;you@…;`, OwnerUpns, LastSynced |
| App → Register an application → Owning team | The group is listed (the screen refreshes the list when you open it) |
| ER-01 run history | **No** run for this request |
| Entra | Nothing changed |

Without the app, create the item by hand in EntraRequests: Title `REQ-T4-0001`, RequestType `onboardGroup`, Status `Submitted`, **TargetDisplayName** = the group name or Object ID.

## 10.3 Test 2: a group you own but aren't a member of

Same steps with a group where you are **owner only**. Expected: **Completed**; the row's OwnerUpns contains you. It appears in the role-group pickers (owners or members), but **not** in Owning team, which lists only groups you are a member of (ER-02 requires membership of the owning team).

## 10.4 Negative tests

| Test | How | Expected (Status **Failed**, ErrorMessage) |
|---|---|---|
| Not your group | Name or Object ID of a group you are neither member nor owner of | *You are neither a member nor an owner of <group>. Ask one of its owners to add you, or pick another group.* No catalog row. |
| Wrong ID | A GUID that is no group, e.g. `00000000-0000-0000-0000-000000000001` | *No group with Object ID … was found …* |
| Wrong name | A name that no group has, e.g. `grp-does-not-exist` | *No group named grp-does-not-exist was found …* |
| Ambiguous name | A name two groups share | *2 groups are named …. Enter the Object ID of the one you mean.* |
| Not a security group | A Microsoft 365 group that is not security-enabled | *<group> is not a security group. Only security-enabled groups can be used …* |
| Already available | Object ID of a group already in your pickers | The app says *This group is already available to you* and creates no request |
| Empty | nothing typed | The app asks for the group's name or Object ID and creates no request |

## 10.5 Re-adding and updates

Adding a group that already has a catalog row (e.g. added by someone else) **updates** that row instead of duplicating it. ER-03 keeps every row current each hour, so later membership changes in Entra show up without another request.

## 10.6 Troubleshooting

| Symptom | Likely cause |
|---|---|
| Stays **Submitted** | ER-04 is off, or its trigger condition doesn't match (RequestType value must be exactly `onboardGroup`) |
| Request went to the manager for approval | ER-01's trigger condition wasn't updated (10.1) |
| **Failed** with `HTTP_…: Insufficient privileges` | Graph connection or admin consent (`Directory.Read.All` and `User.Read.All` cover these reads) |
| Completed, but the group isn't in Owning team | You are owner only (10.3), or the app hasn't refreshed: reopen the New app screen |

## 10.7 Clean up

Delete the test items from `EntraRequests` and, if you want, the added rows from `EntraCatalogGroups`. Nothing was changed in Entra.
