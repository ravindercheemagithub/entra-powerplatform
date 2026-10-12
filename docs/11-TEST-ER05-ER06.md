# 11. Testing ER-05 Find app and ER-06 Tag owning group

Both flows run without approval, the moment the app writes a request item:
- **ER-05** handles the **Search** button on the change screen. It is read-only in Entra.
- **ER-06** handles the **Owning group** card. It changes only an app's `team:` and `teamName:` tags.

How to read a run (which steps ran, inputs and outputs): see [6.6 Checking a run](06-TEST-ER01.md#66-checking-a-run).

## 11.1 Who owns an app

| Team tag on the app registration | Who may Search for it, change it, or hand it to a group |
|---|---|
| `team:user\<user object id>` | that user only (an app created without an owning group) |
| `team:group\<group object id>` | members of that group, including nested members |
| `team:<group object id>` | apps created by 1.2; treated as `team:group\…` |
| no team tag | nobody: the Entra ID team adds a tag by hand first (Entra → App registrations → the app → Manifest → `tags`) |

Owners of the app registration object are not used.

## 11.2 Before you start

| Check | How |
|---|---|
| RequestType has `lookupApp` and `tagOwnerGroup` | EntraRequests → List settings → RequestType |
| ER-05 and ER-06 are **On** | Solutions → Entra Self-Service → Cloud flows |
| Two test apps | **A**: created through the app **without** an owning group (tag `team:user\<you>`). **B**: created **with** an owning group you are in. |
| A second test user who is in none of your groups | for the negative tests |
| Your object ID | Entra → Users → you → Object ID |

To find an app's IDs: Entra → App registrations → the app → *Application (client) ID* and *Object ID*.

## 11.3 ER-05: Search

| # | Do this | Expected |
|---|---|---|
| 1 | Home → **Expose an API** → paste app A's **Application (client) ID** → **Search** | Within about a minute the right side shows app A; *Owner tag* is `team:user\<your object id>`. ER-05 run **Succeeded**; the `lookupApp` item is **Completed** and its ResultJson holds the app's IDs, roles and scopes. |
| 2 | Same with app A's **Object ID** | Same result (looked up by object id after the appId search finds nothing). |
| 3 | App B's client ID | Found; the owner tag is `team:group\<group id>` (teamName = the group). |
| 4 | Text that isn't a GUID, e.g. `orders-api` | The app refuses before searching: *Enter the app registration's Application (client) ID or Object ID (a GUID).* |
| 5 | A GUID no app has, e.g. `00000000-0000-0000-0000-000000000001` | Red message *No app registration has the Application (client) ID or Object ID …* |
| 6 | Signed in as the **second user**: search app A | *Not authorized owner: <app> is tagged team:user\<…>. Only that user, or a member of that group, can use it here.* |
| 7 | Any app registration created outside the platform | *Not authorized owner: … is tagged with no team.* |
| 8 | After step 1: add a scope and **Submit request**, approve twice | ER-02 runs its own ownership check (`Requester may change`) and completes. |

`lookupApp` items don't appear in *Home → recent requests* or *My requests*.

## 11.4 ER-06: Owning group

| # | Do this | Expected |
|---|---|---|
| 1 | Home → **Owning group** → app A's client ID → pick one of your groups → **Change owning group** | Banner *Done: <app> is now owned by group <group>.* ER-06 **Succeeded**. In Entra, app A's tags have `team:group\<group id>` and `teamName:<group>` instead of the `team:user\…` pair, plus new `lastUpdatedBy`, `lastUpdatedTimestamp` and `requestId` tags. Its enterprise app (if any) has the same team tags. |
| 2 | Search app A again as a **member** of that group who is not you | Found: group members can now change it. |
| 3 | Second user (not in the group): Owning group with app A | *Not authorized owner: …* |
| 4 | You, with a group you are **not** in | *You are neither a member nor an owner of <group>. You can only hand an app registration to a group you belong to.* |
| 5 | A Microsoft 365 group that isn't security-enabled | *<group> is not a security group…* |
| 6 | A group Object ID that doesn't exist | *No group has the Object ID …* |

*My requests* shows each `tagOwnerGroup` request with *Not needed* for both approval stages, the previous owner tag and the new group.

## 11.5 Troubleshooting

| Symptom | Likely cause |
|---|---|
| Search keeps saying *Searching Entra…* and then *No answer yet* | ER-05 is off, the `lookupApp` choice is missing (the Patch fails earlier with a banner), or the SharePoint trigger is slow: check ER-05's run history |
| `HTTP App by object id` fails with 400 | the tenant rejects `$filter=id eq …` on applications; search by the Application (client) ID instead, and report it |
| ER-06 `HTTP Patch app tags` 403 | the platform app lacks `Application.ReadWrite.All` (doc 01) |
| You own the app but get *Not authorized owner* | its tag holds a different object ID (e.g. created by another account), or your membership of the tagged group is very recent: Entra can take a few minutes |
