# 4. Power Automate: three flows

| Flow | Trigger | Connectors | Licence |
|---|---|---|---|
| **ER-01 Approvals** | SharePoint: item created in EntraRequests | SharePoint, Office 365 Users, Approvals, Office 365 Outlook, Teams | Standard |
| **ER-02 Execute** | SharePoint: item created or modified, `Status = Approved` | SharePoint, **HTTP**, **Azure Key Vault**, Outlook | Premium (owner's licence) |
| **ER-03 Catalog sync** | Recurrence, hourly (+ run manually) | SharePoint, **HTTP**, **Azure Key Vault** | Premium (owner's licence) |

Build all three **signed in as `svc-entra-flows`**, in the Entra Self-Service environment, ideally inside a **solution** (Solutions → New solution → New → Automation → Cloud flow) so you can export and move them later. Add the Entra ID team as co-owners.

## Conventions used below

- **Action names matter.** Rename every action exactly as written (*… → Rename*). Expressions refer to actions by name, with spaces replaced by underscores: an action named `HTTP Create application` is `body('HTTP_Create_application')`.
- `Expr:` means type it in the **expression** editor (fx), not as text.
- Body files: [`powerautomate/actions/*.json`](../powerautomate/actions). Open the file and paste its content into the HTTP action's **Body**. The `@{...}` parts become expression tokens. If your designer leaves them as plain text, switch off **New designer** (top right), paste, and switch back.
- `ID` means `triggerOutputs()?['body/ID']`, and `Title` means `triggerOutputs()?['body/Title']`.
- **SharePoint – Update item** always needs **Id** and **Title** (Title is a required column). Pass `ID` and `Title` every time, plus the columns listed.
- In ER-02, set **Settings → Concurrency control → On, degree 1** on **every** *Apply to each*. They set and append variables, which parallel iterations would corrupt.

### The Graph HTTP action (ER-02, ER-03)

Every **HTTP** action that calls Graph uses the same settings. Build the first one completely, then copy it (*… → Copy to my clipboard*, or *Copy action* in the new designer) and paste it for the others.

| Field | Value |
|---|---|
| Method / URI / Headers / Body | per action |
| **Authentication** | **Active Directory OAuth** (called *Microsoft Entra ID OAuth* in some versions) |
| Authority | `https://login.microsoftonline.com` |
| Tenant | Expr: `body('Get_settings')?['TenantId']` |
| Audience | `https://graph.microsoft.com` |
| Client ID | Expr: `body('Get_settings')?['GraphClientId']` |
| Credential Type | **Certificate** |
| Pfx | Expr: `body('Get_PFX')?['value']` |
| Password | Expr: `body('Get_PFX_password')?['value']` |
| Settings → **Secure inputs** / **Secure outputs** | On (keeps the certificate and payloads out of run history) |

Common header for every POST/PATCH: `Content-Type: application/json`.

---

## ER-01 Approvals (standard connectors only)

**+ Create → Automated cloud flow** → name `ER-01 Approvals` → trigger **SharePoint – When an item is created** → Site Address = your site, List Name = `EntraRequests`.
Trigger **Settings → Trigger conditions**: `@equals(triggerOutputs()?['body/Status/Value'], 'Submitted')`

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List `EntraSettings`, Id `1` |
| 2 | `Ensure requester` | SharePoint – Send an HTTP request to SharePoint | Method `POST`, Uri `_api/web/ensureuser`, Headers `Accept: application/json;odata=nometadata` and `Content-Type: application/json;odata=nometadata`, Body `{"logonName": "@{triggerOutputs()?['body/Author/Claims']}"}` |
| 3 | `Get owner group` | Send an HTTP request to SharePoint | `GET` `_api/web/associatedownergroup?$select=Id`, header `Accept: application/json;odata=nometadata` |
| 4 | `Break inheritance` | Send an HTTP request to SharePoint | `POST` `_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})/breakroleinheritance(copyRoleAssignments=false,clearSubscopes=true)` |
| 5 | `Grant owners` | Send an HTTP request to SharePoint | `POST` `_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})/roleassignments/addroleassignment(principalid=@{body('Get_owner_group')?['Id']},roledefid=1073741829)` (Full Control) |
| 6 | `Grant requester read` | Send an HTTP request to SharePoint | `POST` `…/items(@{triggerOutputs()?['body/ID']})/roleassignments/addroleassignment(principalid=@{body('Ensure_requester')?['Id']},roledefid=1073741826)` (Read) |
| 7 | `Get locked item` | SharePoint – Get item | List `EntraRequests`, Id = `ID`. Re-reads the item **after** locking; this is the version that gets approved. |
| 8 | `Payload` | Compose | Expr: `json(body('Get_locked_item')?['PayloadJson'])` |
| 9 | `Get manager` | Office 365 Users – Get manager (V2) | User (UPN) = `triggerOutputs()?['body/Author/Email']` |
| 10 | `Manager email` | Compose | **Configure run after**: *is successful* + *has failed*. Expr: `if(equals(actions('Get_manager')?['status'], 'Succeeded'), coalesce(body('Get_manager')?['mail'], body('Get_manager')?['userPrincipalName']), body('Get_settings')?['FallbackApproverEmail'])` |
| 11 | `Manager name` | Compose | Expr: `if(equals(actions('Get_manager')?['status'], 'Succeeded'), body('Get_manager')?['displayName'], 'Fallback approver')` |
| 12 | `Select roles text` | Data Operation – Select | From Expr: `coalesce(outputs('Payload')?['appRoles'], createArray())`. Switch Map to **text** mode, Expr: `concat('- App role ', item()?['value'], ' (', string(length(coalesce(item()?['assignGroups'], createArray()))), ' group(s))')` |
| 13 | `Summary` | Compose | Expr: see [below](#er-01-summary-expression) |
| 14 | `Update pending manager` | SharePoint – Update item | Id = `ID`, Title = `Title`, **Status Value** = `PendingManagerApproval`, ManagerEmail = `outputs('Manager_email')`, ManagerName = `outputs('Manager_name')`, ApprovedPayloadJson = `body('Get_locked_item')?['PayloadJson']`, RequestSummary = `outputs('Summary')` |
| 15 | `Manager approval` | Approvals – Start and wait for an approval | Type **Approve/Reject – First to respond**. Title: `Entra request @{Title}: @{triggerOutputs()?['body/RequestType/Value']} – @{triggerOutputs()?['body/TargetDisplayName']}`. Assigned to: `outputs('Manager_email')`. Details: `outputs('Summary')`. Item link: `body('Get_settings')?['PowerAppUrl']`, description *Open Entra Self-Service* |
| 16 | `Manager outcome` | Compose | Expr (a requester answering their own approval counts as a rejection): `if(equals(toLower(coalesce(first(body('Manager_approval')?['responses'])?['responder']?['email'], '')), toLower(triggerOutputs()?['body/Author/Email'])), 'Reject', body('Manager_approval')?['outcome'])` |
| 17 | `Update manager decision` | SharePoint – Update item | Id, Title; **ManagerDecision Value** = `if(equals(outputs('Manager_outcome'), 'Approve'), 'Approved', 'Rejected')`; ManagerDecisionBy = `first(body('Manager_approval')?['responses'])?['responder']?['email']`; ManagerDecisionAt = `utcNow()`; ManagerComment = `first(body('Manager_approval')?['responses'])?['comments']`; **Status Value** = `if(equals(outputs('Manager_outcome'), 'Approve'), 'PendingEntraApproval', 'Rejected')` |
| 18 | `Manager approved?` | Condition | `outputs('Manager_outcome')` *is equal to* `Approve` |

**18 → If no:**
- `Mail manager rejected`: Office 365 Outlook – Send an email (V2). To `triggerOutputs()?['body/Author/Email']`, Subject `Your Entra request @{Title} was rejected by your manager`, Body with the comment and the PowerAppUrl.

**18 → If yes:**

| # | Action | Type | Configuration |
|---|---|---|---|
| 19 | `Notify Entra team` | Microsoft Teams – Post message in a chat or channel *(optional)* | Post as Flow bot → your Entra team channel: `Request @{Title} (@{triggerOutputs()?['body/RequestType/Value']} – @{triggerOutputs()?['body/TargetDisplayName']}) was approved by @{outputs('Manager_name')} and waits for the Entra ID team.` |
| 20 | `Entra approval` | Start and wait for an approval | First to respond. Title `Entra team approval – @{Title}: @{triggerOutputs()?['body/TargetDisplayName']}`. Assigned to `body('Get_settings')?['EntraApproverEmails']`. Details: `concat(outputs('Summary'), decodeUriComponent('%0A%0A'), 'Manager approval: ', first(body('Manager_approval')?['responses'])?['responder']?['displayName'])`. Item link as above |
| 21 | `Entra outcome` | Compose | Same self-approval rule: `if(equals(toLower(coalesce(first(body('Entra_approval')?['responses'])?['responder']?['email'], '')), toLower(triggerOutputs()?['body/Author/Email'])), 'Reject', body('Entra_approval')?['outcome'])` |
| 22 | `Update entra decision` | SharePoint – Update item | **EntraDecision Value** = `if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')`; EntraDecisionBy / EntraDecisionAt / EntraComment from `body('Entra_approval')` (as in 17); **Status Value** = `if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')` ← **`Approved` starts ER-02** |
| 23 | `Mail requester` | Send an email (V2) | Subject `if(equals(outputs('Entra_outcome'), 'Approve'), concat('Your Entra request ', Title, ' is approved and being applied'), concat('Your Entra request ', Title, ' was rejected by the Entra ID team'))` |

### ER-01 summary expression

```
concat(
  '**', triggerOutputs()?['body/RequestType/Value'], '** – ', triggerOutputs()?['body/TargetDisplayName'], decodeUriComponent('%0A%0A'),
  'Request: ', triggerOutputs()?['body/Title'], ' · appCatID: ', triggerOutputs()?['body/AppCatId'], decodeUriComponent('%0A%0A'),
  'Requested by: ', triggerOutputs()?['body/Author/DisplayName'], ' (', triggerOutputs()?['body/Author/Email'], ')', decodeUriComponent('%0A%0A'),
  if(empty(outputs('Payload')?['owningGroup']), '', concat('Owning team: ', outputs('Payload')?['owningGroup']?['displayName'], if(equals(outputs('Payload')?['owningGroup']?['mode'], 'new'), ' (new group)', ''), decodeUriComponent('%0A%0A'))),
  if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), concat('Expose API: ', outputs('Payload')?['exposeApi']?['identifierUriTemplate'], ', ', string(length(coalesce(outputs('Payload')?['exposeApi']?['scopes'], createArray()))), ' scope(s)', decodeUriComponent('%0A%0A')), ''),
  if(empty(body('Select_roles_text')), '', concat(join(body('Select_roles_text'), decodeUriComponent('%0A')), decodeUriComponent('%0A%0A'))),
  'Justification: ', triggerOutputs()?['body/Justification']
)
```

---

## ER-02 Execute (Premium: HTTP)

**Automated cloud flow** `ER-02 Execute` → trigger **SharePoint – When an item is created or modified** (EntraRequests).
Trigger **Settings**:
- Trigger condition `@equals(triggerOutputs()?['body/Status/Value'], 'Approved')`
- **Concurrency control: On, Degree of parallelism 1** (one execution at a time)

### Top level (before the Try scope)

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | `EntraSettings`, Id `1` |
| 2 | `Approved by the flow?` | Condition | **all** of: `toLower(triggerOutputs()?['body/Editor/Email'])` = `toLower(body('Get_settings')?['ServiceAccountUpn'])`; `triggerOutputs()?['body/ManagerDecision/Value']` = `Approved`; `triggerOutputs()?['body/EntraDecision/Value']` = `Approved`. **If no** → `Terminate` (Status *Cancelled*, message *Status was not set to Approved by ER-01*). Someone editing the list by hand therefore never executes anything. |
| 3 | `Get PFX` | Azure Key Vault – Get secret | Name = `body('Get_settings')?['PfxSecretName']`. Settings → **Secure outputs On** |
| 4 | `Get PFX password` | Azure Key Vault – Get secret | Name = `body('Get_settings')?['PfxPasswordSecretName']`, Secure outputs On |
| 5 | `Mark in progress` | SharePoint – Update item | Id, Title, Status `InProgress` |
| 6 | `Requester` | Compose | Expr: `toLower(triggerOutputs()?['body/Author/Email'])` |
| 7 | `Payload` | Compose | Expr: `json(triggerOutputs()?['body/ApprovedPayloadJson'])` |
| 8 | `Now` | Compose | Expr: `utcNow()` |
| 9 | Initialize variables | Initialize variable ×8 | `varTeamGroupId` String, `varTeamGroupName` String, `varSpId` String, `varGroupId` String, `varRoleId` String, `varAssignTodo` Array `[]`, `varAssignments` Array `[]`, `varResult` Object `{}` |

### `Try` (Scope) – contents in order

**Shared preparation**

| Action | Type | Configuration |
|---|---|---|
| `HTTP Get requester` | HTTP (Graph) | `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Requester')}?$select=id,displayName,userPrincipalName` |
| `Base tags` | Compose | Expr: `createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId']), concat('createdBy:', outputs('Requester')), concat('createdById:', body('HTTP_Get_requester')?['id']), concat('createdTimestamp:', outputs('Now')), concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('managedBy:', body('Get_settings')?['ManagedByTag']), concat('requestId:', triggerOutputs()?['body/Title']))` |
| `Group meta` | Compose | Expr: `concat(' [appCatID=', triggerOutputs()?['body/AppCatId'], '; requestId=', triggerOutputs()?['body/Title'], '; createdBy=', outputs('Requester'), '; managedBy=', body('Get_settings')?['ManagedByTag'], ']')` |

**Existing-app checks** – Condition `Has target app?`: `triggerOutputs()?['body/TargetObjectId']` *is not equal to* (empty). **If yes:**

| Action | Type | Configuration |
|---|---|---|
| `HTTP Get target app` | HTTP | `GET` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}?$select=id,appId,displayName,tags,identifierUris,api,appRoles` |
| `Filter team tag` | Filter array | From `body('HTTP_Get_target_app')?['tags']`; advanced: `@startsWith(item(), 'team:')` |
| `Filter appcat tag` | Filter array | From same; `@startsWith(item(), 'appCatID:')` |
| `Filter kept tags` | Filter array | From same; `@not(or(startsWith(item(), 'lastUpdatedBy:'), startsWith(item(), 'lastUpdatedTimestamp:'), startsWith(item(), 'requestId:')))` |
| `HTTP Check target team` | HTTP | `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`, Body = [`HTTP_Check_target_team.json`](../powerautomate/actions/HTTP_Check_target_team.json) |
| `HTTP Target owners` | HTTP | `GET` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}/owners?$select=id` |
| `Requester may change?` | Condition | Advanced: `@and(or(not(empty(body('HTTP_Check_target_team')?['value'])), contains(string(body('HTTP_Target_owners')?['value']), body('HTTP_Get_requester')?['id'])), or(empty(body('Filter_appcat_tag')), equals(first(body('Filter_appcat_tag')), concat('appCatID:', triggerOutputs()?['body/AppCatId']))))`. **If no:** `Fail not owner` (Update item: Status `Failed`, ErrorMessage *The app is not owned by any of your groups, or its appCatID differs.*) then `Terminate` (Failed). |
| `Updated tags` | Compose | Expr: `union(body('Filter_kept_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])), if(empty(body('Filter_appcat_tag')), createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId']), concat('managedBy:', body('Get_settings')?['ManagedByTag'])), createArray()))` |
| `HTTP Find target SP` | HTTP | `GET` `https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '@{body('HTTP_Get_target_app')?['appId']}'&$select=id` |
| `Set target SP` | Set variable | `varSpId` = `coalesce(first(body('HTTP_Find_target_SP')?['value'])?['id'], '')` |

**Switch** `Request type` on `triggerOutputs()?['body/RequestType/Value']`. Inside each case add **one Scope** named `Do <type>`; the Catch needs those exact names.

#### Case `createAppRegistration` → Scope `Do createAppRegistration`

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Team is new?` | Condition | `outputs('Payload')?['owningGroup']?['mode']` = `new` |
| 1y | `Select team owner binds` | Select (text) | From: `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['owningGroup']?['ownerIds']), createArray(), split(outputs('Payload')?['owningGroup']?['ownerIds'], ';')))` · Map: `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| | `HTTP Create team group` | HTTP | `POST` `https://graph.microsoft.com/v1.0/groups`, Body [`HTTP_Create_team_group.json`](../powerautomate/actions/HTTP_Create_team_group.json) |
| | `Set team id (new)` / `Set team name (new)` | Set variable | `body('HTTP_Create_team_group')?['id']` / `?['displayName']` |
| | `Catalog new team` | SharePoint – Create item | `EntraCatalogGroups`: Title = team name, GroupId = team id, AppCatId, Description = `body('HTTP_Create_team_group')?['description']`, OwnerUpns = `concat(';', outputs('Requester'), ';')`, MemberUpns = same, LastSynced = `utcNow()` |
| 1n | `HTTP Check team membership` | HTTP | `POST` `…/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups` Body `{"groupIds": ["@{outputs('Payload')?['owningGroup']?['id']}"]}` |
| | `Is team member?` | Condition | `length(body('HTTP_Check_team_membership')?['value'])` greater than `0`. **No:** `Fail not team member` (Update item Failed, *You are not a member of the owning team*) → `Terminate` Failed |
| | `HTTP Get team group` | HTTP | `GET` `…/groups/@{outputs('Payload')?['owningGroup']?['id']}?$select=id,displayName` |
| | `Set team id` / `Set team name` | Set variable | from `body('HTTP_Get_team_group')` |
| 2 | `Select app roles` | Select (key/value) | From `coalesce(outputs('Payload')?['appRoles'], createArray())` · `id` = Expr `guid()` · `value` = `item()?['value']` · `displayName` = `item()?['displayName']` · `description` = `item()?['description']` · `allowedMemberTypes` = Expr `split(item()?['allowedMemberTypes'], ',')` · `isEnabled` = Expr `true` |
| 3 | `Select scopes` | Select | From `if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), coalesce(outputs('Payload')?['exposeApi']?['scopes'], createArray()), createArray())` · `id` = `guid()` · `value`, `type`, `adminConsentDisplayName`, `adminConsentDescription` = `item()?['…']` · `userConsentDisplayName` = `item()?['adminConsentDisplayName']` · `userConsentDescription` = `item()?['adminConsentDescription']` · `isEnabled` = `true` |
| 4 | `Select id token claims` | Select | From `if(empty(outputs('Payload')?['optionalClaimsIdToken']), createArray(), split(outputs('Payload')?['optionalClaimsIdToken'], ','))` · `name` = `item()` · `essential` = Expr `false` |
| 5 | `Select access token claims` | Select | Same with `optionalClaimsAccessToken` |
| 6 | `Filter optional tags` | Filter array | From `split(coalesce(outputs('Payload')?['tags'], ''), ';')` · `@and(contains(item(), '='), greater(length(trim(item())), 2))` |
| 7 | `Select optional tags` | Select (text) | From `body('Filter_optional_tags')` · `concat(trim(first(split(item(), '='))), ':', trim(last(split(item(), '='))))` |
| 8 | `App tags` | Compose | `union(outputs('Base_tags'), createArray(concat('team:', variables('varTeamGroupId')), concat('teamName:', variables('varTeamGroupName'))), body('Select_optional_tags'))` |
| 9 | `HTTP Create application` | HTTP | `POST` `https://graph.microsoft.com/v1.0/applications`, Body [`HTTP_Create_application.json`](../powerautomate/actions/HTTP_Create_application.json) |
| 10 | `Expose API?` | Condition | `outputs('Payload')?['exposeApi']?['enabled']` is equal to Expr `true` → **Yes:** `HTTP Expose API`: `PATCH` `…/applications/@{body('HTTP_Create_application')?['id']}`, Body [`HTTP_Expose_API.json`](../powerautomate/actions/HTTP_Expose_API.json) |
| 11 | `Apply to each owner` | Apply to each | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['additionalOwnerIds']), createArray(), split(outputs('Payload')?['additionalOwnerIds'], ';')))` → `HTTP Add owner`: `POST` `…/applications/@{body('HTTP_Create_application')?['id']}/owners/$ref`, Body [`HTTP_Add_owner.json`](../powerautomate/actions/HTTP_Add_owner.json) |
| 12 | `Create SP?` | Condition | `outputs('Payload')?['createServicePrincipal']` is equal to `true` → **Yes:** |
| | `Wait for replication` | Delay | 10 seconds |
| | `Do until SP` | Do until | Until `variables('varSpId')` is not equal to (empty); Limits: Count 6, Timeout `PT10M`. Inside: `HTTP Create SP` (`POST` `…/servicePrincipals`, Body [`HTTP_Create_SP.json`](../powerautomate/actions/HTTP_Create_SP.json), Settings → Retry policy **None**) → `SP created?` (Condition, **run after: is successful + has failed**): `outputs('HTTP_Create_SP')?['statusCode']` = `201` → Yes: `Set SP id` = `body('HTTP_Create_SP')?['id']`; No: `Retry delay` 10 seconds |
| 13 | `For each new role` | Apply to each (concurrency 1) | From `coalesce(outputs('Payload')?['appRoles'], createArray())` → `Filter created role` (Filter array: from `body('HTTP_Create_application')?['appRoles']`, `@equals(item()?['value'], items('For_each_new_role')?['value'])`) → `For each new role group` (Apply to each, from `coalesce(items('For_each_new_role')?['assignGroups'], createArray())`) → `Queue new role assignment` (**Append to array variable** `varAssignTodo`): `{"roleId": "@{first(body('Filter_created_role'))?['id']}", "roleValue": "@{items('For_each_new_role')?['value']}", "mode": "@{items('For_each_new_role_group')?['mode']}", "id": "@{items('For_each_new_role_group')?['id']}", "displayName": "@{items('For_each_new_role_group')?['displayName']}", "description": "@{items('For_each_new_role_group')?['description']}", "ownerIds": "@{items('For_each_new_role_group')?['ownerIds']}"}` |
| 14 | `Result create app` | Set variable | `varResult` = `{"applicationObjectId": "@{body('HTTP_Create_application')?['id']}", "appId": "@{body('HTTP_Create_application')?['appId']}", "identifierUri": "@{if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), '')}", "servicePrincipalId": "@{variables('varSpId')}", "teamGroupId": "@{variables('varTeamGroupId')}"}` |
| 15 | `Catalog new app` | SharePoint – Create item | `EntraCatalogApps`: Title = displayName, ObjectId, AppId, AppCatId, TeamGroupId, TeamGroupName, ServicePrincipalId = `variables('varSpId')`, IdentifierUri (as in 14), AppRolesJson = `string(body('HTTP_Create_application')?['appRoles'])`, ScopesJson = `string(body('Select_scopes'))`, TeamMemberUpns = `concat(';', outputs('Requester'), ';')`, OwnerUpns = same, LastSynced `utcNow()` (ER-03 fills in the full team membership within the hour) |

#### Case `createGroup` → Scope `Do createGroup`

| Action | Type | Configuration |
|---|---|---|
| `Select group owner binds` | Select (text) | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['ownerIds']), createArray(), split(outputs('Payload')?['ownerIds'], ';')))` · `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| `Select group member binds` | Select (text) | Same with `memberIds` |
| `HTTP Create group` | HTTP | `POST` `…/groups`, Body [`HTTP_Create_group.json`](../powerautomate/actions/HTTP_Create_group.json) |
| `Catalog group` | SharePoint – Create item | `EntraCatalogGroups`: Title, GroupId = `body('HTTP_Create_group')?['id']`, AppCatId, Description, OwnerUpns `concat(';', outputs('Requester'), ';')`, MemberUpns same |
| `Result create group` | Set variable | `varResult` = `{"groupId": "@{body('HTTP_Create_group')?['id']}", "groupDisplayName": "@{body('HTTP_Create_group')?['displayName']}"}` |

#### Case `exposeApi` → Scope `Do exposeApi`

| Action | Type | Configuration |
|---|---|---|
| `Select new scopes` | Select | as `Select scopes` above, From `coalesce(outputs('Payload')?['scopes'], createArray())` |
| `HTTP Patch expose` | HTTP | `PATCH` `…/applications/@{triggerOutputs()?['body/TargetObjectId']}`, Body [`HTTP_Patch_expose.json`](../powerautomate/actions/HTTP_Patch_expose.json) |
| `Result expose` | Set variable | `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "appId": "@{body('HTTP_Get_target_app')?['appId']}", "identifierUri": "@{replace(outputs('Payload')?['identifierUriTemplate'], '{appId}', body('HTTP_Get_target_app')?['appId'])}"}` |

#### Case `addAppRoles` → Scope `Do addAppRoles`

| Action | Type | Configuration |
|---|---|---|
| `Select new roles` | Select | as `Select app roles`, From `coalesce(outputs('Payload')?['appRoles'], createArray())` |
| `HTTP Patch roles` | HTTP | `PATCH` `…/applications/@{triggerOutputs()?['body/TargetObjectId']}`, Body [`HTTP_Patch_roles.json`](../powerautomate/actions/HTTP_Patch_roles.json) |
| `For each added role` → `Filter added role` → `For each added role group` → `Queue added role assignment` | | same pattern as step 13 of createAppRegistration, using `body('Select_new_roles')` and these loop names |
| `Needs SP for roles?` | Condition | `@and(greater(length(variables('varAssignTodo')), 0), empty(variables('varSpId')))` → `HTTP Create SP for roles` (`POST` `…/servicePrincipals`, Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json)) → `Set SP id roles` |
| `Result roles` | Set variable | `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "appId": "@{body('HTTP_Get_target_app')?['appId']}", "servicePrincipalId": "@{variables('varSpId')}"}` |

#### Case `assignGroupsToAppRoles` → Scope `Do assignGroupsToAppRoles`

| Action | Type | Configuration |
|---|---|---|
| `Select assignment todo` | Select | From `coalesce(outputs('Payload')?['assignments'], createArray())` · `roleId` = `item()?['appRoleId']` · `roleValue` = `item()?['appRoleValue']` · `mode`, `id`, `displayName`, `description`, `ownerIds` = `item()?['…']` |
| `Set assignment todo` | Set variable | `varAssignTodo` = `body('Select_assignment_todo')` |
| `Needs SP for assign?` | Condition | `empty(variables('varSpId'))` → `HTTP Create SP for assign` (Body `HTTP_Create_SP_existing.json`) → `Set SP id assign` |
| `HTTP Patch tags assign` | HTTP | `PATCH` `…/applications/@{triggerOutputs()?['body/TargetObjectId']}`, Body [`HTTP_Patch_tags.json`](../powerautomate/actions/HTTP_Patch_tags.json) |
| `Result assign` | Set variable | `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "servicePrincipalId": "@{variables('varSpId')}"}` |

#### Case `createServicePrincipal` → Scope `Do createServicePrincipal`

| Action | Type | Configuration |
|---|---|---|
| `SP already exists?` | Condition | `variables('varSpId')` is not empty → Yes: `Fail SP exists` (Update item Failed, *already has an enterprise application*) → `Terminate` |
| `HTTP Create SP existing` | HTTP | `POST` `…/servicePrincipals`, Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json) |
| `HTTP Patch tags sp` | HTTP | `PATCH` the app with [`HTTP_Patch_tags.json`](../powerautomate/actions/HTTP_Patch_tags.json) |
| `Result sp` | Set variable | `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "servicePrincipalId": "@{body('HTTP_Create_SP_existing')?['id']}"}` |

#### After the Switch (still inside `Try`): role assignments, shared by three cases

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Apply to each assignment` | Apply to each, **Settings → Concurrency 1** | From `variables('varAssignTodo')` |
| 1.1 | `Group is new?` | Condition | `items('Apply_to_each_assignment')?['mode']` = `new` |
| | Yes: `Select role group owner binds` | Select (text) | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(items('Apply_to_each_assignment')?['ownerIds']), createArray(), split(items('Apply_to_each_assignment')?['ownerIds'], ';')))` · `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| | Yes: `HTTP Create role group` | HTTP | `POST` `…/groups`, Body [`HTTP_Create_role_group.json`](../powerautomate/actions/HTTP_Create_role_group.json) |
| | Yes: `Set group id (new)` | Set variable | `varGroupId` = `body('HTTP_Create_role_group')?['id']` |
| | Yes: `Catalog role group` | SharePoint – Create item | EntraCatalogGroups row (Title, GroupId, AppCatId, OwnerUpns `concat(';', outputs('Requester'), ';')`) |
| | Yes: `Wait for group replication` | Delay | 15 seconds |
| | No: `Set group id` | Set variable | `varGroupId` = `items('Apply_to_each_assignment')?['id']` |
| 1.2 | `HTTP Assign role` | HTTP | `POST` `https://graph.microsoft.com/v1.0/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`, Body [`HTTP_Assign_role.json`](../powerautomate/actions/HTTP_Assign_role.json). Settings → Retry policy: **Exponential**, count 4, interval `PT10S` |
| 1.3 | `Record assignment` | Append to array variable | `varAssignments`: `concat(items('Apply_to_each_assignment')?['displayName'], ' -> ', items('Apply_to_each_assignment')?['roleValue'])` |
| 2 | `Default access?` | Condition | `@and(equals(triggerOutputs()?['body/RequestType/Value'], 'createAppRegistration'), empty(variables('varAssignments')), not(equals(outputs('Payload')?['appRoleAssignmentRequired'], false)), not(empty(variables('varSpId'))))` → `HTTP Assign default access`: `POST` `…/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`, Body [`HTTP_Assign_default_access.json`](../powerautomate/actions/HTTP_Assign_default_access.json). With assignment required and no roles, the owning team gets Default Access so someone can sign in. |
| 3 | `Mark completed` | SharePoint – Update item | Status `Completed`, CompletedAt `utcNow()`, ErrorMessage (empty), ResultJson = Expr `string(setProperty(variables('varResult'), 'assignmentsText', join(variables('varAssignments'), '; ')))` |
| 4 | `Mail completed` | Send an email (V2) | To requester: `Your Entra request @{Title} is complete`, with the ResultJson values and the PowerAppUrl |

### `Catch` (Scope), **Configure run after → `Try`: has failed, has timed out**

| Action | Type | Configuration |
|---|---|---|
| `Failed actions` | Filter array | From Expr `union(result('Do_createAppRegistration'), result('Do_createGroup'), result('Do_exposeApi'), result('Do_addAppRoles'), result('Do_assignGroupsToAppRoles'), result('Do_createServicePrincipal'), result('Try'))` · `@equals(item()?['status'], 'Failed')` |
| `Error text` | Compose | `concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-02 run history'))` |
| `Mark failed` | SharePoint – Update item | Status `Failed`, ErrorMessage `outputs('Error_text')`, ResultJson `string(variables('varResult'))` (what was created before the failure, for a manual fix) |
| `Mail failed` | Send an email (V2) | To requester and `body('Get_settings')?['EntraApproverEmails']`: `Entra request @{Title} failed`, body `outputs('Error_text')` |

**Retry a failed request:** fix the cause, then on the item set ManagerDecision/EntraDecision as they were and Status = `Approved` **as the service account** (or re-run ER-02 from its run history with *Resubmit*). Note that createAppRegistration is not idempotent in Power Automate: a retry creates a second app unless you delete the first. ResultJson lists what the failed run created.

---

## ER-03 Catalog sync (Premium: HTTP)

**Scheduled cloud flow** `ER-03 Catalog sync`, **Recurrence every 1 hour**. Run it manually after setup and whenever you onboard groups.

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings`, `Get PFX`, `Get PFX password` | as in ER-02 | |
| 2 | `Initialize varMembers` | Initialize variable | String, empty |
| 3 | `HTTP List managed apps` | HTTP | `GET` `https://graph.microsoft.com/v1.0/applications?$filter=tags/any(t:t eq 'managedBy:@{body('Get_settings')?['ManagedByTag']}')&$select=id,appId,displayName,tags,identifierUris,appRoles,api&$count=true&$top=999`, header `ConsistencyLevel: eventual` (up to 999 apps per page; add a Do-until over `@odata.nextLink` if you expect more) |
| 4 | `Apply to each app` | Apply to each, **concurrency 1** | From `body('HTTP_List_managed_apps')?['value']` |
| 4.1 | `Filter app team` / `Filter app team name` / `Filter app appcat` | Filter array | From `items('Apply_to_each_app')?['tags']`; `@startsWith(item(), 'team:')` / `'teamName:'` / `'appCatID:'` |
| 4.2 | `Team id` | Compose | `if(empty(body('Filter_app_team')), '', substring(first(body('Filter_app_team')), 5))` |
| 4.3 | `Reset members` | Set variable | `varMembers` = (empty) |
| 4.4 | `Has team?` | Condition | `outputs('Team_id')` is not empty → `HTTP Team members` (`GET` `…/groups/@{outputs('Team_id')}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999`) → `Select member upns` (text: `toLower(item()?['userPrincipalName'])`) → `Set members` = `concat(';', join(body('Select_member_upns'), ';'), ';')` → `Get team row` (SharePoint Get items, EntraCatalogGroups, Filter Query `GroupId eq '@{outputs('Team_id')}'`, Top 1) → `Team row missing?` (`empty(body('Get_team_row')?['value'])`) → `Create team row` (Title = `substring(first(body('Filter_app_team_name')), 9)`, GroupId = team id) |
| 4.5 | `HTTP App owners` | HTTP | `GET` `…/applications/@{items('Apply_to_each_app')?['id']}/owners/microsoft.graph.user?$select=userPrincipalName` |
| 4.6 | `Select owner upns` | Select (text) | `toLower(item()?['userPrincipalName'])` from `body('HTTP_App_owners')?['value']` |
| 4.7 | `HTTP App SP` | HTTP | `GET` `…/servicePrincipals?$filter=appId eq '@{items('Apply_to_each_app')?['appId']}'&$select=id` |
| 4.8 | `Get app row` | SharePoint – Get items | `EntraCatalogApps`, Filter Query `ObjectId eq '@{items('Apply_to_each_app')?['id']}'`, Top 1 |
| 4.9 | `App row missing?` | Condition | `empty(body('Get_app_row')?['value'])` → Yes: `Create app row` / No: `Update app row` (Id `first(body('Get_app_row')?['value'])?['ID']`) with the fields below |

App row fields:

| Column | Value |
|---|---|
| Title | `items('Apply_to_each_app')?['displayName']` |
| ObjectId / AppId | `items('Apply_to_each_app')?['id']` / `?['appId']` |
| AppCatId | `if(empty(body('Filter_app_appcat')), '', substring(first(body('Filter_app_appcat')), 9))` |
| TeamGroupId | `outputs('Team_id')` |
| TeamGroupName | `if(empty(body('Filter_app_team_name')), '', substring(first(body('Filter_app_team_name')), 9))` |
| ServicePrincipalId | `coalesce(first(body('HTTP_App_SP')?['value'])?['id'], '')` |
| IdentifierUri | `coalesce(first(items('Apply_to_each_app')?['identifierUris']), '')` |
| AppRolesJson | `string(coalesce(items('Apply_to_each_app')?['appRoles'], createArray()))` |
| ScopesJson | `string(coalesce(items('Apply_to_each_app')?['api']?['oauth2PermissionScopes'], createArray()))` |
| TeamMemberUpns | `variables('varMembers')` |
| OwnerUpns | `concat(';', join(body('Select_owner_upns'), ';'), ';')` |
| LastSynced | `utcNow()` |

**Then refresh every catalog group** (this also completes rows added by hand or by ER-02):

| # | Action | Type | Configuration |
|---|---|---|---|
| 5 | `Get catalog groups` | SharePoint – Get items | `EntraCatalogGroups`, Top Count 5000 |
| 6 | `Apply to each catalog group` | Apply to each (concurrency 5 is fine; no variables) | From `body('Get_catalog_groups')?['value']` |
| 6.1 | `HTTP Group` | HTTP | `GET` `…/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}?$select=id,displayName,description` |
| 6.2 | `HTTP Group members` | HTTP | `GET` `…/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999` |
| 6.3 | `HTTP Group owners` | HTTP | `GET` `…/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}/owners/microsoft.graph.user?$select=userPrincipalName` |
| 6.4 | `Select group member upns` / `Select group owner upns` | Select (text) | `toLower(item()?['userPrincipalName'])` |
| 6.5 | `Update group row` | SharePoint – Update item | Id `items('Apply_to_each_catalog_group')?['ID']`; Title `body('HTTP_Group')?['displayName']`; Description `body('HTTP_Group')?['description']`; AppCatId `if(contains(coalesce(body('HTTP_Group')?['description'], ''), '[appCatID='), first(split(last(split(body('HTTP_Group')?['description'], '[appCatID=')), ';')), '')`; MemberUpns `concat(';', join(body('Select_group_member_upns'), ';'), ';')`; OwnerUpns `concat(';', join(body('Select_group_owner_upns'), ';'), ';')`; LastSynced `utcNow()` |

A deleted group makes `HTTP Group` fail with 404, which fails that iteration. To flag or remove such rows, add a parallel branch with run-after *has failed*.

---

## Graph calls at a glance

| Step | Request |
|---|---|
| requester id | `GET /users/{upn}?$select=id` |
| team membership | `POST /users/{id}/checkMemberGroups {"groupIds":[…]}` |
| new group | `POST /groups` (owners@odata.bind / members@odata.bind) |
| new app | `POST /applications` (tags, notes, appRoles, web/spa, optionalClaims, groupMembershipClaims, api.requestedAccessTokenVersion=2) |
| App ID URI + scopes | `PATCH /applications/{id}` (identifierUris, api.oauth2PermissionScopes) |
| owners | `POST /applications/{id}/owners/$ref` |
| enterprise app | `POST /servicePrincipals` (retried for ~60 s while the new app replicates) |
| role assignment | `POST /servicePrincipals/{spId}/appRoleAssignedTo {principalId, resourceId, appRoleId}` |
| catalog | `GET /applications?$filter=tags/any(...)`, `GET /groups/{id}/transitiveMembers`, `GET …/owners` |
