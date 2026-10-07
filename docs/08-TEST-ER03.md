# 8. Testing ER-03 Catalog sync

ER-03 runs every hour. It **only reads** Entra ID and writes the two catalog lists the Power App uses for its pickers: `EntraCatalogApps` (apps your groups own) and `EntraCatalogGroups` (groups you can pick). It never changes anything in Entra, so it is safe to run at any time.

How to read a run (which steps ran, which failed, inputs and outputs): see [6.6 Checking a run](06-TEST-ER01.md#66-checking-a-run).

## 8.1 Before you start

| Check | How |
|---|---|
| Graph connection works | Same test as [7.1](07-TEST-ER02.md#71-before-you-start): `GET /v1.0/organization` succeeds |
| `EntraSettings.ManagedByTag` | set (e.g. `entra-pp`) and identical to what ER-02 stamps. ER-03 lists only apps tagged `managedBy:<this value>`. |
| How to run it | Flow page → **Run** → **Run flow**. It also runs on its own every hour. |

## 8.2 Test 1: empty run

Run ER-03 before any app has been created through the platform.

Expected:
- Run **Succeeded**.
- `HTTP List managed apps` returns `"value": []`, and `Apply to each app` has 0 iterations.
- `Apply to each catalog group` has one iteration per row in `EntraCatalogGroups` (0 if the list is empty).

If `HTTP List managed apps` fails with 400 *Request_UnsupportedQuery*, the `ConsistencyLevel: eventual` header is missing.

## 8.3 Test 2: onboard an existing group

This is how existing team groups become pickable in the app before any app exists.

1. Pick a security group **you are a member of** (Entra → Groups → the group → copy its **Object ID**).
2. In `EntraCatalogGroups` → **+ New**: Title = the group's name, GroupId = the Object ID. Leave the rest empty.
3. Run ER-03.

Expected on that row:

| Column | Expected |
|---|---|
| Title / Description | the group's name and description from Entra |
| MemberUpns | `;you@contoso.com;…;` (lower case, `;` at both ends, includes members of nested groups) |
| OwnerUpns | the group's owners in the same format |
| AppCatId | the value from `[appCatID=…]` in the description, or empty for a group not created by the platform |
| LastSynced | the time of the run |

## 8.4 Test 3: an app created by ER-02

After [ER-02 test 2 or 3](07-TEST-ER02.md#74-test-2-and-3-app-registrations):

1. In Entra, add a second user to the app's **team group** (Groups → grp-pp-t2-team → Members → Add members). You can, because ER-02 made the requester an owner of the group.
2. Run ER-03.

Expected:
- `HTTP List managed apps` returns the app.
- Its `EntraCatalogApps` row (created by ER-02) is **updated**, not duplicated: TeamMemberUpns now lists both users, OwnerUpns lists the app owners, ServicePrincipalId and AppRolesJson are filled, and LastSynced is now.
- `EntraCatalogGroups` has a row for the team group (ER-03 creates it if missing).
- In the Power App, the second user now sees the app under *Change an existing app*.

## 8.5 Test 4: a row that has gone missing

1. Delete the app's row from `EntraCatalogApps`.
2. Run ER-03.

Expected: the row is created again with all columns (`App row missing` → If yes → `Create app row`).

## 8.6 Test 5: a deleted group

1. Add a row to `EntraCatalogGroups` with Title `deleted-test` and GroupId `00000000-0000-0000-0000-000000000001` (an ID that doesn't exist).
2. Run ER-03.

Expected: `HTTP Group` fails with **404** in that iteration, and the run ends as **Failed**, while the other rows are still updated. This is the documented behaviour (doc 04, end of ER-03); add a *has failed* branch if you want such rows flagged or removed. Delete the test row afterwards.

## 8.7 Things to watch

- **Throttling (option A):** the HTTP with Microsoft Entra ID connection allows 100 calls per minute. ER-03 makes about 4 calls per app and 3 per catalog group, so beyond roughly 25 items per minute some calls get **429** and are retried automatically. A run then takes longer but still succeeds. Lower *Apply to each catalog group* concurrency if you see many retries.
- **Apps created outside the platform** never appear: they don't carry the `managedBy` tag. They are picked up only after a change request through ER-02 (which adds `appCatID` and `managedBy` when the app has none).
- **More than 999 managed apps:** `HTTP List managed apps` returns one page. Add a Do until over `@odata.nextLink` (doc 04).

## 8.8 Troubleshooting

| Symptom | Likely cause |
|---|---|
| `HTTP List managed apps` returns nothing although ER-02 created apps | `ManagedByTag` differs from the value stamped on the apps (check the app's tags in its Manifest) |
| `HTTP …` 401 / 403 | Graph connection auth type or certificate wrong, or admin consent missing (`Application.ReadWrite.All` / `Directory.Read.All`) |
| `Get app row` / `Get team row` fails | Filter Query typo; it must be `ObjectId eq '@{items('Apply_to_each_app')?['id']}'` / `GroupId eq '@{outputs('Team_id')}'` |
| Duplicate rows in `EntraCatalogApps` | `Get app row` filter not matching (wrong column name), so `App row missing` is always true |
| Some members missing from MemberUpns | Only user accounts are listed; devices, service principals and contacts in a group are left out on purpose (`microsoft.graph.user`) |

## 8.9 Clean up

Delete the test rows you added to `EntraCatalogGroups`. ER-03 changes nothing in Entra.
