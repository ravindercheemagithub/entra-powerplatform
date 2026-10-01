# 3. Power Apps: the canvas app

Five screens, built by pasting YAML into Power Apps Studio. Every control is a classic control, every formula uses English-locale separators (`,` and `;`), and nothing pins a control version. Studio uses the current version of each control.

| Screen | Purpose |
|---|---|
| `scrHome` | operation cards + your recent requests |
| `scrNewApp` | **Register an application**: 5 sections, Submit / Next / Cancel at the bottom |
| `scrNewGroup` | new security group, as a request on its own or inline for the wizard ("Create new group") |
| `scrAppChange` | changes to an existing app your groups own: Expose an API, App roles, Role assignments, Enterprise app |
| `scrMyRequests` | history with approval stages, created IDs and errors |

## 3.1 Create the app

1. make.powerapps.com → switch to the **Entra Self-Service** environment → **Create → Start with a blank canvas → Tablet size** → name it *Entra Self-Service*.
2. **Settings → General**: *Data row limit* = **2000** (the catalog filters use `in`, which isn't delegable).
   **Settings → Display**: leave *Scale to fit* on (the layout is designed for 1366 × 768 and scales).
   **Settings → Updates**: if *Named formulas* is listed, turn it on (it's on by default in current versions).
3. **Data → Add data**:
   - SharePoint → your site → tick **EntraRequests**, **EntraCatalogApps**, **EntraCatalogGroups** (not EntraSettings)
   - **Office 365 Users**

   Add the data sources **before** pasting anything; the pasted formulas reference them.

## 3.2 App-level formulas

In the Tree view select **App**:
- Property **Formulas** → paste all of [`powerapps/App.Formulas.fx`](../powerapps/App.Formulas.fx)
- Property **OnStart** → paste all of [`powerapps/App.OnStart.fx`](../powerapps/App.OnStart.fx) → then *… → Run OnStart*

## 3.3 Screens

For each screen, in this order: **scrHome, scrMyRequests, scrNewGroup, scrNewApp, scrAppChange**. The order avoids "screen not found" errors while you paste, since formulas navigate between screens; any order works once all exist.

1. **New screen → Blank**, rename it exactly (e.g. `scrHome`). Delete `Screen1` at the end; `scrHome` must be first in the Tree view, which makes it the start screen.
2. Select the screen. Set **Fill** = `gTheme.Bg`, and **OnVisible** = its formula from [`powerapps/Screens.OnVisible.fx`](../powerapps/Screens.OnVisible.fx).
3. Open the screen's YAML file in VS Code (`powerapps/screens/scrHome.pa.yaml`) → select all → copy.
4. In Studio select the **screen** in the Tree view → **Ctrl+V** (or right-click → *Paste*). Allow clipboard access if the browser asks. The root container `cntRoot_<screen>` appears with all controls.

Studio validates the code before creating controls. If a paste is refused:
- **"Unknown control" / version error:** your Studio version names a control differently. Insert that control manually once (e.g. a classic *Combo box*), right-click → **View code**, and compare its `Control:` line with the file. Send me the line and I'll regenerate the YAML.
- **Formula errors after the paste** (red underlines): usually a missing data source or connection (3.1 step 3), or a non-English locale (`;` instead of `,` in formulas).
- **Pasting twice** auto-renames controls (`_1`), which breaks references. Delete the root container and paste again.

## 3.4 What each screen does

### scrHome
- **galOps_Home**: cards from `gOperations` (3 per row). Clicking a card navigates: *App registration* → `scrNewApp`; *Security group* → `scrNewGroup` (standalone); *My requests* → `scrMyRequests`; the other four → `scrAppChange`, with `varOp` = the operation.
- **galRecent_Home**: your last 7 requests (item-level security means the list only returns your items). Click one to open it.

### scrNewApp: Register an application
Left: a step list (`galSteps_NewApp`). You can click back to any step you've visited. Right: one container per section; the bottom bar has **Submit request**, **Next ›**, **‹ Previous**, **Cancel**.

| Section | Fields (control name) | Required |
|---|---|---|
| 1 Basics | Display name `txtAppName_NewApp`, appCatID `txtAppCatId_NewApp` (defaults to your groups' appCatID), Account types `radAudience_NewApp`, Owning team `cmbTeam_NewApp` or **＋ Create new team group**, Justification `txtJustification_NewApp`, Description, Redirect URI platform + URIs, Change ticket | name, appCatID, team, justification |
| 2 Expose an API & claims | Expose an API `chkExpose_NewApp`; App ID URI (`api://{appId}` or custom); scopes editor (**＋ access_as_user**, **＋ Custom scope**); optional claims in ID / access token; groups claim | – |
| 3 App roles & groups | **＋ User + Admin roles with groups** (adds `<Name>.User` / `<Name>.Admin` with new groups `grp-<name>-users/-admins`); **＋ Custom role**; per role: value, display name, members, description, groups (pick existing, or **＋ Create new group**) | – |
| 4 Enterprise app & owners | Create the enterprise app (forced on when any role has groups), Assignment required, Additional owners, Optional tags | – |
| 5 Review + submit | HTML summary of everything + what happens next | – |

- **Next** validates the current section (hidden labels `lblErr1/2/3_NewApp` hold the rules).
- **Submit** validates everything, builds `PayloadJson` with `JSON()`, and **Patches** `EntraRequests` with `Status = Submitted`. Then it opens My requests.
- "＋ Create new group" opens `scrNewGroup` in *inline* mode. **Add to request** returns to the wizard with the group added, marked *(new)*; it is created when the request is approved. Everything typed so far is kept: `scrNewApp.OnVisible` resets only when `varResetNewApp` is true.

### scrNewGroup
- **Standalone** (from Home): name, appCatID, description, additional owners, initial members, justification → **Submit request** (`createGroup`).
- **Inline** (`varGroupMode` = `inline-team` / `inline-role` / `inline-assign`): name, description, owners → **Add to request** → back.

### scrAppChange
- Left: **your applications** (`gMyApps`: catalog rows where you're in the team group or an owner), with search.
- Right: app details, plus the section for `varOp`:
  - **Expose an API**: URI (added; existing ones are kept) + new scopes
  - **App roles**: new roles, each with groups (existing or new)
  - **Role assignments**: pick an app role (from `AppRolesJson`) and a group, **Add**; or "＋ Create new group" for that role
  - **Enterprise application**: assignment required toggle (disabled if one exists)
- Justification + **Submit request** → `exposeApi` / `addAppRoles` / `assignGroupsToAppRoles` / `createServicePrincipal`.

### scrMyRequests
- Filter (All / Open / Completed / Rejected-failed), Refresh, list.
- Detail: status badge, 4 stage tiles (Submitted → Manager → Entra team → Applied), justification, comments, created IDs (from `ResultJson`), error, the summary sent to approvers, and **Open in Entra admin center**.

## 3.5 Payloads the app writes (`PayloadJson`)

Same shapes as `entra-portal-next`, with string lists as `;`-separated strings so the flow can `split()` them.

```json
{
  "displayName": "orders-api", "description": "Orders REST API", "signInAudience": "AzureADMyOrg",
  "owningGroup": { "mode": "existing", "id": "<group id>", "displayName": "team-orders", "description": "", "ownerIds": "" },
  "redirectUrisWeb": "", "redirectUrisSpa": "https://orders.contoso.com",
  "exposeApi": { "enabled": true, "identifierUriTemplate": "api://{appId}",
                 "scopes": [ { "value": "access_as_user", "type": "User", "adminConsentDisplayName": "Access orders-api", "adminConsentDescription": "…" } ] },
  "optionalClaimsIdToken": "email,upn", "optionalClaimsAccessToken": "idtyp", "groupMembershipClaims": "None",
  "appRoles": [ { "value": "OrdersApi.User", "displayName": "orders-api User", "description": "…", "allowedMemberTypes": "User",
                  "assignGroups": [ { "mode": "new", "id": "", "displayName": "grp-orders-api-users", "description": "…", "ownerIds": "" } ] } ],
  "createServicePrincipal": true, "appRoleAssignmentRequired": true, "additionalOwnerIds": "<oid>;<oid>", "tags": "costCentre=CC-4410"
}
```

| Request type | Payload |
|---|---|
| `createGroup` | `{ displayName, description, ownerIds: "a;b", memberIds: "a;b" }` |
| `exposeApi` | `{ applicationObjectId, applicationDisplayName, identifierUriTemplate, scopes: [...] }` |
| `addAppRoles` | `{ applicationObjectId, applicationDisplayName, appRoles: [...] }` (same role shape as above) |
| `assignGroupsToAppRoles` | `{ applicationObjectId, applicationDisplayName, assignments: [ { appRoleId, appRoleValue, mode, id, displayName, description, ownerIds } ] }` |
| `createServicePrincipal` | `{ applicationObjectId, applicationDisplayName, appRoleAssignmentRequired }` |

Free text that the flow later embeds in Graph JSON (descriptions) has line breaks, double quotes and backslashes removed in the app. Display names may not contain `"` or `\`.

## 3.6 Publish and share

**File → Save → Publish**. **Share**: add *Everyone* (or your requester group) as **User**. They also need **Member** access on the SharePoint site (doc 02). Copy the app's **Web link** into `EntraSettings.PowerAppUrl`, so approval emails link to it.

## 3.7 Layout preview and regenerating the YAML

`powerapps/preview/index.html` draws every screen (each wizard step, each change operation) at 1366 × 768 from the generated YAML. It shows positions and texts only, not Power Fx behaviour. Open it in a browser to see the layout before pasting. Regenerate it with `python3 preview.py`.

The YAML is generated by `powerapps/tools/build.py` (helpers in `pa.py`). To change layout, colours or text, edit the generator and run:

```bash
cd powerapps/tools && python3 build.py
```

Then delete the screen's root container in Studio and paste the new file.
