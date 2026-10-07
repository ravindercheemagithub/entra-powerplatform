# 4. Power Automate: three flows

| Flow | Trigger | Connectors | Licence |
|---|---|---|---|
| **ER-01 Approvals** | SharePoint: item created in EntraRequests | SharePoint, Office 365 Users, Approvals, Office 365 Outlook, Teams (optional) | Standard |
| **ER-02 Execute** | SharePoint: item created or modified, `Status = Approved` | SharePoint, Outlook, plus a Graph connection: **HTTP with Microsoft Entra ID (preauthorized)** (option A) or **HTTP** + **Azure Key Vault** (option B) | Premium (owner's licence) |
| **ER-03 Catalog sync** | Recurrence, hourly (+ run manually) | SharePoint, plus the same Graph connection | Premium (owner's licence) |
| **ER-04 Onboard group** | SharePoint: item created, `RequestType = onboardGroup` | SharePoint, plus the same Graph connection | Premium (owner's licence) |

**Shortcut:** instead of building the flows by hand, import them as a solution: [doc 09](09-SOLUTION-IMPORT.md). This page remains the reference for what each action does.

Build all three **signed in as the flow account** (the account in `EntraSettings.ServiceAccountUpn`), in the Entra Self-Service environment, ideally inside a **solution** (Solutions → New solution → New → Automation → Cloud flow) so you can export and move them later. Add the Entra ID team as co-owners.

## Conventions used below

**Names**
- **Action names can't contain `?`** (or `< > % & \ / : * # "`). Power Automate refuses to save them. The condition names in this guide are written without question marks for that reason.
- **Action names matter.** Rename every action exactly as written (classic designer: *… → Rename*; new designer: click the title). Expressions refer to actions by name with spaces replaced by underscores: an action named `HTTP Create application` is `body('HTTP_Create_application')`. Renaming an action after an expression refers to it does not update the expression.

**How to enter a value**
- A value in `code` that contains a function call, such as `int(...)`, `body(...)`, `outputs(...)`, `concat(...)` or `utcNow()`, is an **expression**. Click into the field, click **fx** (new designer: type `/` → *Insert expression*), paste it, and click **Add**. It must show as a purple **fx** chip. If you can read the expression as plain text in the field, it went in as text and the flow will fail ("Enter a valid integer", "Enter a valid datetime").
- A value in `code` that contains `@{...}`, such as a URL or a JSON body, is **text with embedded expressions**. Paste it as is. The classic designer turns each `@{...}` into a token. If the new designer leaves them as plain text, switch off **New designer** (top right), paste, and switch back.
- *Plain text* values are typed exactly as shown.
- **Choice columns** (Status, ManagerDecision, EntraDecision, RequestType) appear as *Status Value* etc. For a fixed value, **pick it from the dropdown**. For an expression, open the dropdown, choose **Enter custom value**, then use fx.
- **Dynamic content entries named like a column** (e.g. *ManagerEmail* under *When an item is created*) are the list item's current column values, not the result of a Compose action. A Compose result is always called **Outputs** under the Compose action's name. Prefer the expressions given here.

**SharePoint actions**
- Every SharePoint action: **Site Address** = your site (e.g. `https://contoso.sharepoint.com/teams/m365automationqa`, no trailing `/`), **List Name** as stated.
- **SharePoint – Update item** always needs **Id** and **Title** (Title is required). Every Update item below lists them. Columns you leave empty keep their current value. Columns are under **Advanced parameters → Show all** (new designer) or **Show advanced options** (classic).
- **Id** fields need a number: always `int(triggerOutputs()?['body/ID'])` (or the expression given).

**Loops and conditions**
- In ER-02, set **Settings → Concurrency control → On, Degree of parallelism 1** on **every** *Apply to each*. They set and append variables, which parallel iterations would corrupt.
- Conditions written as *`expression` is equal to `true`* are built like this: left box **fx** → the expression; operator **is equal to**; right box **fx** → `true`.

**Who the requester is**
- The requester is the item's built-in **Created By** (`Author`). Its email (`Author/Email`) can differ from the UPN in some tenants, so where a UPN is needed (Get manager, Graph `/users/{upn}`) the flows use `last(split(triggerOutputs()?['body/Author/Claims'], '|'))`, which turns `i:0#.f|membership|alex@contoso.com` into `alex@contoso.com`.

### The Graph connection (ER-02, ER-03)

Every Graph call below is written as an action named `HTTP …` with a **Method**, a full **URI** starting `https://graph.microsoft.com/v1.0/`, optional **Headers** and **Body**. Build them with one of the two options. **Give the action the same name either way** (e.g. `HTTP Create application`), so every expression and body file works unchanged.

**Option A (recommended): HTTP with Microsoft Entra ID (preauthorized)**

Create the connection once (Connections → New, or the first time you add the action):

| Connection field | Value |
|---|---|
| Authentication type | **Log in using a Client Certificate Auth** (not *Log in with Microsoft Entra ID*: that calls Graph as you) |
| Microsoft Entra ID Resource URI (Application ID URI) | `https://graph.microsoft.com` |
| Base Resource URL | `https://graph.microsoft.com` |
| Tenant | Directory (tenant) ID |
| Client ID | Application (client) ID of the platform app registration |
| Client certificate secret | upload the `.pfx`, enter its password |

Each Graph call is the action **Invoke an HTTP request**:

| Action field | Value |
|---|---|
| Method | as listed (GET, POST, PATCH) |
| Url of the request | the URI from this guide **from `/v1.0/` on**, e.g. `/v1.0/applications` (the base URL is added by the connection) |
| Headers | `Content-Type`: `application/json` on every POST and PATCH; plus any header listed |
| Body of the request | as listed |
| Settings → Secure inputs / Secure outputs | On |
| Settings → Retry policy | as listed (default otherwise) |

No *Get PFX* actions are needed: skip ER-02 steps 3–4 and ER-03 step 2.

**Check how responses come back before you build everything.** Microsoft documents the response body as a string. Add a test **Invoke an HTTP request** named `Test` with `GET` `/v1.0/organization`, then a Compose with `body('Test')?['value']`. If the Compose shows your tenant's details, use the expressions in this guide as written. If it is empty, the body arrives as text: either use option B, or wrap each `body('HTTP_…')` in `json(...)` (e.g. `json(body('HTTP_Create_application'))?['id']`).

**Option B: HTTP action + Azure Key Vault**

| Field | Value |
|---|---|
| Method / URI / Headers / Body | as listed |
| **Authentication** | **Active Directory OAuth** (called *Microsoft Entra ID OAuth* in some versions) |
| Authority | `https://login.microsoftonline.com` |
| Tenant | `body('Get_settings')?['TenantId']` |
| Audience | `https://graph.microsoft.com` |
| Client ID | `body('Get_settings')?['GraphClientId']` |
| Credential Type | **Certificate** |
| Pfx | `body('Get_PFX')?['value']` |
| Password | `body('Get_PFX_password')?['value']` |
| Settings → **Secure inputs** / **Secure outputs** | On (keeps the certificate and payloads out of run history) |

Header for every POST/PATCH: `Content-Type: application/json`.

Either way, build the first Graph action completely, then copy it (classic: *… → Copy to my clipboard*; new designer: *Copy action*) and paste it for the others.

**Body files:** [`powerautomate/actions/*.json`](../powerautomate/actions). Open the file and paste its whole content into the action's Body.

---

## ER-01 Approvals (standard connectors only)

**+ Create → Automated cloud flow** → name `ER-01 Approvals` → trigger **SharePoint – When an item is created** → Site Address = your site, List Name = `EntraRequests`.
Trigger **Settings → Trigger conditions** → **+ Add**: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), not(equals(triggerOutputs()?['body/RequestType/Value'], 'onboardGroup')))` (onboardGroup requests need no approval; ER-04 handles them)

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List Name `EntraSettings`; Id: *plain text* `1` |
| 2 | `Ensure requester` | SharePoint – Send an HTTP request to SharePoint | Method `POST`; Uri `_api/web/ensureuser`; Headers `Accept`: `application/json;odata=nometadata` and `Content-Type`: `application/json;odata=nometadata`; Body `{"logonName": "@{triggerOutputs()?['body/Author/Claims']}"}` |
| 3 | `Get owner group` | Send an HTTP request to SharePoint | Method `GET`; Uri `_api/web/associatedownergroup?$select=Id`; Headers `Accept`: `application/json;odata=nometadata`; Body empty |
| 4 | `Break inheritance` | Send an HTTP request to SharePoint | Method `POST`; Uri `_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})/breakroleinheritance(copyRoleAssignments=false,clearSubscopes=true)`; Headers `Accept`: `application/json;odata=nometadata`; Body empty |
| 5 | `Grant owners` | Send an HTTP request to SharePoint | Method `POST`; Uri `_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})/roleassignments/addroleassignment(principalid=@{body('Get_owner_group')?['Id']},roledefid=1073741829)` (1073741829 = Full Control); Headers `Accept`: `application/json;odata=nometadata`; Body empty |
| 6 | `Grant requester read` | Send an HTTP request to SharePoint | Method `POST`; Uri `_api/web/lists/getbytitle('EntraRequests')/items(@{triggerOutputs()?['body/ID']})/roleassignments/addroleassignment(principalid=@{body('Ensure_requester')?['Id']},roledefid=1073741826)` (1073741826 = Read); Headers `Accept`: `application/json;odata=nometadata`; Body empty |
| 7 | `Get locked item` | SharePoint – Get item | List Name `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`. Re-reads the item **after** locking; this is the version that gets approved. |
| 8 | `Payload` | Data Operation – Compose | Inputs `json(body('Get_locked_item')?['PayloadJson'])` |
| 9 | `Get manager` | Office 365 Users – Get manager (V2) | User (UPN) `last(split(triggerOutputs()?['body/Author/Claims'], '\|'))` |
| 10 | `Manager email` | Compose | Inputs `if(equals(actions('Get_manager')?['status'], 'Succeeded'), coalesce(body('Get_manager')?['mail'], body('Get_manager')?['userPrincipalName']), body('Get_settings')?['FallbackApproverEmail'])`. **Run after** (new designer: Settings → Run after; classic: *… → Configure run after*): `Get manager` **is successful** + **has failed**. Without this, a requester with no manager stops the flow. |
| 11 | `Manager name` | Compose | Inputs `if(equals(actions('Get_manager')?['status'], 'Succeeded'), body('Get_manager')?['displayName'], 'Fallback approver')` |
| 12 | `Select roles text` | Data Operation – Select | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`. Click the **T** icon next to Map (text mode), Map `concat('- App role ', item()?['value'], ' (', string(length(coalesce(item()?['assignGroups'], json('[]')))), ' group(s))')` |
| 13 | `Summary` | Compose | Inputs: the expression in [ER-01 summary expression](#er-01-summary-expression) |
| 14 | `Update pending manager` | SharePoint – Update item | List Name `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `PendingManagerApproval`; ManagerEmail `outputs('Manager_email')`; ManagerName `outputs('Manager_name')`; ApprovedPayloadJson `body('Get_locked_item')?['PayloadJson']`; RequestSummary `outputs('Summary')` |
| 15 | `Manager approval` | Approvals – Start and wait for an approval | Approval type **Approve/Reject – First to respond**; Title `concat('Entra request ', triggerOutputs()?['body/Title'], ': ', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'])`; Assigned to `outputs('Manager_email')`; Details `outputs('Summary')`; Item link `body('Get_settings')?['PowerAppUrl']`; Item link description *plain text* `Open Entra Self-Service`; Requestor (advanced) `triggerOutputs()?['body/Author/Email']`. Optional: Settings → Timeout `P7D` |
| 16 | `Manager outcome` | Compose | Inputs `if(equals(toLower(coalesce(first(body('Manager_approval')?['responses'])?['responder']?['email'], '')), toLower(triggerOutputs()?['body/Author/Email'])), 'Reject', body('Manager_approval')?['outcome'])` (the requester answering their own approval counts as a rejection) |
| 17 | `Update manager decision` | SharePoint – Update item | List Name `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **ManagerDecision Value** (Enter custom value) `if(equals(outputs('Manager_outcome'), 'Approve'), 'Approved', 'Rejected')`; ManagerDecisionBy `first(body('Manager_approval')?['responses'])?['responder']?['email']`; ManagerDecisionAt `utcNow()`; ManagerComment `first(body('Manager_approval')?['responses'])?['comments']`; **Status Value** (Enter custom value) `if(equals(outputs('Manager_outcome'), 'Approve'), 'PendingEntraApproval', 'Rejected')` |
| 18 | `Manager approved` | Control – Condition | Left `outputs('Manager_outcome')`; operator **is equal to**; right *plain text* `Approve` (capital A, not "Approved") |

**18 → If no (False):**

| # | Action | Type | Configuration |
|---|---|---|---|
| 18n | `Mail manager rejected` | Office 365 Outlook – Send an email (V2) | To `triggerOutputs()?['body/Author/Email']`; Subject `concat('Your Entra request ', triggerOutputs()?['body/Title'], ' was rejected by your manager')`; Body: [manager rejection body](#er-01-manager-rejection-email-body) |

**18 → If yes (True):**

| # | Action | Type | Configuration |
|---|---|---|---|
| 19 | `Notify Entra team` *(optional)* | Microsoft Teams – Post message in a chat or channel | Post as **Flow bot**; Post in **Channel**; Team / Channel: pick yours; Message `concat('Request ', triggerOutputs()?['body/Title'], ' (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') was approved by ', coalesce(first(body('Manager_approval')?['responses'])?['responder']?['displayName'], outputs('Manager_name')), ' and is waiting for the Entra ID team.')` |
| 20 | `Entra approval` | Approvals – Start and wait for an approval | Approval type **Approve/Reject – First to respond**; Title `concat('Entra team approval – ', triggerOutputs()?['body/Title'], ': ', triggerOutputs()?['body/TargetDisplayName'])`; Assigned to `replace(replace(body('Get_settings')?['EntraApproverEmails'], decodeUriComponent('%0D'), ''), decodeUriComponent('%0A'), ';')` (turns line breaks in the settings value into `;`); Details `concat(outputs('Summary'), decodeUriComponent('%0A%0A'), 'Manager approval: ', coalesce(first(body('Manager_approval')?['responses'])?['responder']?['displayName'], ''))`; Item link `body('Get_settings')?['PowerAppUrl']`; Item link description *plain text* `Open Entra Self-Service`; Requestor `triggerOutputs()?['body/Author/Email']` |
| 21 | `Entra outcome` | Compose | Inputs `if(equals(toLower(coalesce(first(body('Entra_approval')?['responses'])?['responder']?['email'], '')), toLower(triggerOutputs()?['body/Author/Email'])), 'Reject', body('Entra_approval')?['outcome'])` |
| 22 | `Update entra decision` | SharePoint – Update item | List Name `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **EntraDecision Value** (Enter custom value) `if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')`; EntraDecisionBy `first(body('Entra_approval')?['responses'])?['responder']?['email']`; EntraDecisionAt `utcNow()`; EntraComment `first(body('Entra_approval')?['responses'])?['comments']`; **Status Value** (Enter custom value) `if(equals(outputs('Entra_outcome'), 'Approve'), 'Approved', 'Rejected')`. Leave the Manager columns empty. **`Approved` starts ER-02**, which checks this update was made by the flow account. |
| 23 | `Mail requester` | Send an email (V2) | To `triggerOutputs()?['body/Author/Email']`; Subject `if(equals(outputs('Entra_outcome'), 'Approve'), concat('Your Entra request ', triggerOutputs()?['body/Title'], ' is approved and being applied'), concat('Your Entra request ', triggerOutputs()?['body/Title'], ' was rejected by the Entra ID team'))`; Body: [requester email body](#er-01-requester-email-body) |

### ER-01 manager rejection email body

Step 18n **Body**, entered with fx. Email bodies are HTML, so line breaks are `<br>`:

```
concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was rejected by your manager.<br>Rejected by: ', coalesce(first(body('Manager_approval')?['responses'])?['responder']?['displayName'], ''), '<br>Comment: ', coalesce(first(body('Manager_approval')?['responses'])?['comments'], '(none)'), if(equals(body('Manager_approval')?['outcome'], 'Approve'), '<br><br>Note: a request cannot be approved by the person who raised it.', ''), '<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>')
```

### ER-01 requester email body

Step 23 **Body**, entered with fx:

```
if(equals(outputs('Entra_outcome'), 'Approve'),
  concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was approved by your manager and the Entra ID team. It is being applied now; you will get another email when it is complete.<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>'),
  concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/TargetDisplayName'], ') was rejected by the Entra ID team.<br>Rejected by: ', coalesce(first(body('Entra_approval')?['responses'])?['responder']?['displayName'], ''), '<br>Comment: ', coalesce(first(body('Entra_approval')?['responses'])?['comments'], '(none)'), '<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>'))
```

### ER-01 summary expression

Step 13 **Inputs**, entered with fx. Approval details support Markdown, so `**` is bold:

```
concat(
  '**', triggerOutputs()?['body/RequestType/Value'], '** – ', triggerOutputs()?['body/TargetDisplayName'], decodeUriComponent('%0A%0A'),
  'Request: ', triggerOutputs()?['body/Title'], ' · appCatID: ', triggerOutputs()?['body/AppCatId'], decodeUriComponent('%0A%0A'),
  'Requested by: ', triggerOutputs()?['body/Author/DisplayName'], ' (', triggerOutputs()?['body/Author/Email'], ')', decodeUriComponent('%0A%0A'),
  if(empty(outputs('Payload')?['owningGroup']), '', concat('Owning team: ', outputs('Payload')?['owningGroup']?['displayName'], if(equals(outputs('Payload')?['owningGroup']?['mode'], 'new'), ' (new group)', ''), decodeUriComponent('%0A%0A'))),
  if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), concat('Expose API: ', outputs('Payload')?['exposeApi']?['identifierUriTemplate'], ', ', string(length(coalesce(outputs('Payload')?['exposeApi']?['scopes'], json('[]')))), ' scope(s)', decodeUriComponent('%0A%0A')), ''),
  if(empty(body('Select_roles_text')), '', concat(join(body('Select_roles_text'), decodeUriComponent('%0A')), decodeUriComponent('%0A%0A'))),
  'Justification: ', triggerOutputs()?['body/Justification']
)
```

---

## ER-02 Execute (Premium)

**+ Create → Automated cloud flow** → name `ER-02 Execute` → trigger **SharePoint – When an item is created or modified** → Site Address = your site, List Name = `EntraRequests`.
Trigger **Settings**:
- Trigger conditions → **+ Add**: `@equals(triggerOutputs()?['body/Status/Value'], 'Approved')`. ER-02's own updates (InProgress, Completed, Failed) fire the trigger again, but this condition ignores them.
- **Concurrency control: On, Degree of parallelism 1**, so one request is executed at a time.

### Top level (before the Try scope)

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List Name `EntraSettings`; Id *plain text* `1` |
| 2 | `Approved by the flow` | Control – Condition | Three rows joined with **And**: ① `toLower(last(split(triggerOutputs()?['body/Editor/Claims'], '\|')))` is equal to `toLower(body('Get_settings')?['ServiceAccountUpn'])`; ② `triggerOutputs()?['body/ManagerDecision/Value']` is equal to *plain text* `Approved`; ③ `triggerOutputs()?['body/EntraDecision/Value']` is equal to *plain text* `Approved`. **If no:** `Stop not approved` (Control – Terminate: Status **Cancelled**). Someone editing the list by hand is not the flow account, so nothing executes. **If yes:** leave empty; everything below goes **after** the condition, not inside it. |
| 3 | `Get PFX` *(option B only)* | Azure Key Vault – Get secret | Name of the secret `body('Get_settings')?['PfxSecretName']`; Settings → **Secure outputs On** |
| 4 | `Get PFX password` *(option B only)* | Azure Key Vault – Get secret | Name of the secret `body('Get_settings')?['PfxPasswordSecretName']`; Settings → **Secure outputs On** |
| 5 | `Mark in progress` | SharePoint – Update item | List Name `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `InProgress` |
| 6 | `Requester` | Compose | Inputs `toLower(last(split(triggerOutputs()?['body/Author/Claims'], '\|')))` (the requester's UPN) |
| 7 | `Payload` | Compose | Inputs `json(triggerOutputs()?['body/ApprovedPayloadJson'])` |
| 8 | `Now` | Compose | Inputs `utcNow()` |
| 9 | Eight variables | Variables – Initialize variable ×8 | One action per row, named `Init <name>`: `varTeamGroupId` String (empty); `varTeamGroupName` String (empty); `varSpId` String (empty); `varGroupId` String (empty); `varRoleId` String (empty); `varAssignTodo` Array, Value *plain text* `[]`; `varAssignments` Array, Value `[]`; `varResult` Object, Value `{}` |
| 10 | `Try` | Control – Scope | Everything in the next sections goes **inside** this scope |
| 11 | `Catch` | Control – Scope | After `Try` (not inside it). See [Catch](#catch-scope). |

### Inside `Try`: shared preparation

| Action | Type | Configuration |
|---|---|---|
| `HTTP Get requester` | Graph | `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Requester')}?$select=id,displayName,userPrincipalName` |
| `Base tags` | Compose | Inputs `createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId']), concat('createdBy:', outputs('Requester')), concat('createdById:', body('HTTP_Get_requester')?['id']), concat('createdTimestamp:', outputs('Now')), concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('managedBy:', body('Get_settings')?['ManagedByTag']), concat('requestId:', triggerOutputs()?['body/Title']))` |
| `Group meta` | Compose | Inputs `concat(' [appCatID=', triggerOutputs()?['body/AppCatId'], '; requestId=', triggerOutputs()?['body/Title'], '; createdBy=', outputs('Requester'), '; managedBy=', body('Get_settings')?['ManagedByTag'], ']')` |
| `Has target app` | Condition | `empty(triggerOutputs()?['body/TargetObjectId'])` is equal to `false`. **If yes:** the actions in the next table. **If no:** leave empty. |

### Inside `Has target app` → If yes: existing-app checks

| Action | Type | Configuration |
|---|---|---|
| `HTTP Get target app` | Graph | `GET` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}?$select=id,appId,displayName,tags,identifierUris,api,appRoles` |
| `Filter team tag` | Data Operation – Filter array | From `body('HTTP_Get_target_app')?['tags']`; condition `startsWith(item(), 'team:')` is equal to `true` |
| `Filter appcat tag` | Filter array | From `body('HTTP_Get_target_app')?['tags']`; condition `startsWith(item(), 'appCatID:')` is equal to `true` |
| `Filter kept tags` | Filter array | From `body('HTTP_Get_target_app')?['tags']`; condition `not(or(startsWith(item(), 'lastUpdatedBy:'), startsWith(item(), 'lastUpdatedTimestamp:'), startsWith(item(), 'requestId:')))` is equal to `true` |
| `HTTP Check target team` | Graph | `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`; Body [`HTTP_Check_target_team.json`](../powerautomate/actions/HTTP_Check_target_team.json) |
| `HTTP Target owners` | Graph | `GET` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}/owners?$select=id` |
| `Requester may change` | Condition | `and(or(not(empty(body('HTTP_Check_target_team')?['value'])), contains(string(body('HTTP_Target_owners')?['value']), body('HTTP_Get_requester')?['id'])), or(empty(body('Filter_appcat_tag')), equals(first(body('Filter_appcat_tag')), concat('appCatID:', triggerOutputs()?['body/AppCatId']))))` is equal to `true`. **If no:** `Fail not owner` (SharePoint – Update item: List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage *plain text* `The app is not owned by any of your groups, or its appCatID differs.`) → `Stop not owner` (Terminate: Status **Failed**, Code `NotOwner`, Message *plain text* `Requester may not change this app`). **If yes:** leave empty. |
| `Updated tags` | Compose | Inputs `union(body('Filter_kept_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])), if(empty(body('Filter_appcat_tag')), createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId']), concat('managedBy:', body('Get_settings')?['ManagedByTag'])), json('[]')))` |
| `HTTP Find target SP` | Graph | `GET` `https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '@{body('HTTP_Get_target_app')?['appId']}'&$select=id` |
| `Set target SP` | Variables – Set variable | Name `varSpId`; Value `coalesce(first(body('HTTP_Find_target_SP')?['value'])?['id'], '')` |

### Inside `Try`, after `Has target app`: Switch

**Control – Switch** named `Request type`; On `triggerOutputs()?['body/RequestType/Value']`. Add six cases; in each case's **Equals** box type the request type as *plain text* (e.g. `createAppRegistration`). Inside each case add **one Scope** named `Do <type>` (e.g. `Do createAppRegistration`) and put that case's actions inside it. The Catch refers to those exact scope names. Leave **Default** empty.

#### Case `createAppRegistration` → Scope `Do createAppRegistration`

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Team is new` | Condition | Left `outputs('Payload')?['owningGroup']?['mode']`; is equal to; right *plain text* `new` |
| 1y.1 | *If yes:* `Select team owner binds` | Select | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['owningGroup']?['ownerIds']), json('[]'), split(outputs('Payload')?['owningGroup']?['ownerIds'], ';')))`; Map in text mode `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| 1y.2 | *If yes:* `HTTP Create team group` | Graph | `POST` `https://graph.microsoft.com/v1.0/groups`; Body [`HTTP_Create_team_group.json`](../powerautomate/actions/HTTP_Create_team_group.json) |
| 1y.3 | *If yes:* `Set team id (new)` | Set variable | Name `varTeamGroupId`; Value `body('HTTP_Create_team_group')?['id']` |
| 1y.4 | *If yes:* `Set team name (new)` | Set variable | Name `varTeamGroupName`; Value `body('HTTP_Create_team_group')?['displayName']` |
| 1y.5 | *If yes:* `Catalog new team` | SharePoint – Create item | List `EntraCatalogGroups`; Title `body('HTTP_Create_team_group')?['displayName']`; GroupId `body('HTTP_Create_team_group')?['id']`; AppCatId `triggerOutputs()?['body/AppCatId']`; Description `body('HTTP_Create_team_group')?['description']`; OwnerUpns `concat(';', outputs('Requester'), ';')`; MemberUpns `concat(';', outputs('Requester'), ';')`; LastSynced `utcNow()` |
| 1n.1 | *If no:* `HTTP Check team membership` | Graph | `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`; Body `{"groupIds": ["@{outputs('Payload')?['owningGroup']?['id']}"]}` |
| 1n.2 | *If no:* `Is team member` | Condition | Left `length(body('HTTP_Check_team_membership')?['value'])`; **is greater than**; right *plain text* `0`. **If no:** `Fail not team member` (Update item: List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage *plain text* `You are not a member of the owning team.`) → `Stop not team member` (Terminate: Status **Failed**, Code `NotTeamMember`, Message *plain text* `Requester is not in the owning team`). **If yes:** leave empty. |
| 1n.3 | *If no (after 1n.2):* `HTTP Get team group` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Payload')?['owningGroup']?['id']}?$select=id,displayName` |
| 1n.4 | *If no:* `Set team id` | Set variable | Name `varTeamGroupId`; Value `body('HTTP_Get_team_group')?['id']` |
| 1n.5 | *If no:* `Set team name` | Set variable | Name `varTeamGroupName`; Value `body('HTTP_Get_team_group')?['displayName']` |
| 2 | `Select app roles` | Select | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`; Map (key/value rows): `id` → `guid()`; `value` → `item()?['value']`; `displayName` → `item()?['displayName']`; `description` → `item()?['description']`; `allowedMemberTypes` → `split(item()?['allowedMemberTypes'], ',')`; `isEnabled` → `true` |
| 3 | `Select scopes` | Select | From `if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), coalesce(outputs('Payload')?['exposeApi']?['scopes'], json('[]')), json('[]'))`; Map: `id` → `guid()`; `value` → `item()?['value']`; `type` → `item()?['type']`; `adminConsentDisplayName` → `item()?['adminConsentDisplayName']`; `adminConsentDescription` → `item()?['adminConsentDescription']`; `userConsentDisplayName` → `item()?['adminConsentDisplayName']`; `userConsentDescription` → `item()?['adminConsentDescription']`; `isEnabled` → `true` |
| 4 | `Select id token claims` | Select | From `if(empty(outputs('Payload')?['optionalClaimsIdToken']), json('[]'), split(outputs('Payload')?['optionalClaimsIdToken'], ','))`; Map: `name` → `item()`; `essential` → `false` |
| 5 | `Select access token claims` | Select | From `if(empty(outputs('Payload')?['optionalClaimsAccessToken']), json('[]'), split(outputs('Payload')?['optionalClaimsAccessToken'], ','))`; Map: `name` → `item()`; `essential` → `false` |
| 6 | `Filter optional tags` | Filter array | From `split(coalesce(outputs('Payload')?['tags'], ''), ';')`; condition `and(contains(item(), '='), greater(length(trim(item())), 2))` is equal to `true` |
| 7 | `Select optional tags` | Select | From `body('Filter_optional_tags')`; Map in text mode `concat(trim(first(split(item(), '='))), ':', trim(last(split(item(), '='))))` |
| 8 | `App tags` | Compose | Inputs `union(outputs('Base_tags'), createArray(concat('team:', variables('varTeamGroupId')), concat('teamName:', variables('varTeamGroupName'))), body('Select_optional_tags'))` |
| 9 | `HTTP Create application` | Graph | `POST` `https://graph.microsoft.com/v1.0/applications`; Body [`HTTP_Create_application.json`](../powerautomate/actions/HTTP_Create_application.json) |
| 10 | `Expose API` | Condition | `equals(outputs('Payload')?['exposeApi']?['enabled'], true)` is equal to `true`. **If yes:** `HTTP Expose API` (Graph: `PATCH` `https://graph.microsoft.com/v1.0/applications/@{body('HTTP_Create_application')?['id']}`; Body [`HTTP_Expose_API.json`](../powerautomate/actions/HTTP_Expose_API.json)). **If no:** leave empty. |
| 11 | `Apply to each owner` | Control – Apply to each (concurrency 1) | Select an output from previous steps `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['additionalOwnerIds']), json('[]'), split(outputs('Payload')?['additionalOwnerIds'], ';')))`. Inside: `HTTP Add owner` (Graph: `POST` `https://graph.microsoft.com/v1.0/applications/@{body('HTTP_Create_application')?['id']}/owners/$ref`; Body [`HTTP_Add_owner.json`](../powerautomate/actions/HTTP_Add_owner.json)) |
| 12 | `Create SP` | Condition | `equals(outputs('Payload')?['createServicePrincipal'], true)` is equal to `true`. **If yes:** 12.1–12.2. **If no:** leave empty. |
| 12.1 | *If yes:* `Wait for replication` | Schedule – Delay | Count `10`, Unit **Second** |
| 12.2 | *If yes:* `Do until SP` | Control – Do until | Loop until: `empty(variables('varSpId'))` is equal to `false`. Change limits: Count `6`, Timeout `PT10M`. Inside, in order: **(a)** `HTTP Create SP` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP.json`](../powerautomate/actions/HTTP_Create_SP.json); Settings → Retry policy **None**). **(b)** `SP created` (Condition: `outputs('HTTP_Create_SP')?['statusCode']` is equal to *plain text* `201`; **Run after** `HTTP Create SP`: **is successful** + **has failed**). *If yes:* `Set SP id` (Set variable `varSpId` = `body('HTTP_Create_SP')?['id']`). *If no:* `Retry delay` (Delay 10 seconds). |
| 13 | `For each new role` | Apply to each (concurrency 1) | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`. Inside, in order: **(a)** `Filter created role` (Filter array: From `body('HTTP_Create_application')?['appRoles']`; condition `item()?['value']` is equal to `items('For_each_new_role')?['value']`). **(b)** `For each new role group` (Apply to each, concurrency 1, From `coalesce(items('For_each_new_role')?['assignGroups'], json('[]'))`). Inside it: `Queue new role assignment` (Variables – **Append to array variable**, Name `varAssignTodo`, Value: the JSON below). |
| 14 | `Result create app` | Set variable | Name `varResult`; Value (text with tokens) `{"applicationObjectId": "@{body('HTTP_Create_application')?['id']}", "appId": "@{body('HTTP_Create_application')?['appId']}", "identifierUri": "@{if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), '')}", "servicePrincipalId": "@{variables('varSpId')}", "teamGroupId": "@{variables('varTeamGroupId')}"}` |
| 15 | `Catalog new app` | SharePoint – Create item | List `EntraCatalogApps`; Title `outputs('Payload')?['displayName']`; ObjectId `body('HTTP_Create_application')?['id']`; AppId `body('HTTP_Create_application')?['appId']`; AppCatId `triggerOutputs()?['body/AppCatId']`; TeamGroupId `variables('varTeamGroupId')`; TeamGroupName `variables('varTeamGroupName')`; ServicePrincipalId `variables('varSpId')`; IdentifierUri `variables('varResult')?['identifierUri']`; AppRolesJson `string(body('HTTP_Create_application')?['appRoles'])`; ScopesJson `string(body('Select_scopes'))`; TeamMemberUpns `concat(';', outputs('Requester'), ';')`; OwnerUpns `concat(';', outputs('Requester'), ';')`; LastSynced `utcNow()`. ER-03 fills in the full team membership within the hour. |

Step 13 `Queue new role assignment` Value (text with tokens):

```
{"roleId": "@{first(body('Filter_created_role'))?['id']}", "roleValue": "@{items('For_each_new_role')?['value']}", "mode": "@{items('For_each_new_role_group')?['mode']}", "id": "@{items('For_each_new_role_group')?['id']}", "displayName": "@{items('For_each_new_role_group')?['displayName']}", "description": "@{items('For_each_new_role_group')?['description']}", "ownerIds": "@{items('For_each_new_role_group')?['ownerIds']}"}
```

#### Case `createGroup` → Scope `Do createGroup`

| Action | Type | Configuration |
|---|---|---|
| `Select group owner binds` | Select | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(outputs('Payload')?['ownerIds']), json('[]'), split(outputs('Payload')?['ownerIds'], ';')))`; Map in text mode `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| `Select group member binds` | Select | From `if(empty(outputs('Payload')?['memberIds']), json('[]'), split(outputs('Payload')?['memberIds'], ';'))`; Map in text mode `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| `HTTP Create group` | Graph | `POST` `https://graph.microsoft.com/v1.0/groups`; Body [`HTTP_Create_group.json`](../powerautomate/actions/HTTP_Create_group.json) |
| `Catalog group` | SharePoint – Create item | List `EntraCatalogGroups`; Title `body('HTTP_Create_group')?['displayName']`; GroupId `body('HTTP_Create_group')?['id']`; AppCatId `triggerOutputs()?['body/AppCatId']`; Description `body('HTTP_Create_group')?['description']`; OwnerUpns `concat(';', outputs('Requester'), ';')`; MemberUpns: leave empty (ER-03 fills it); LastSynced `utcNow()` |
| `Result create group` | Set variable | Name `varResult`; Value `{"groupId": "@{body('HTTP_Create_group')?['id']}", "groupDisplayName": "@{body('HTTP_Create_group')?['displayName']}"}` |

#### Case `exposeApi` → Scope `Do exposeApi`

| Action | Type | Configuration |
|---|---|---|
| `Select new scopes` | Select | From `coalesce(outputs('Payload')?['scopes'], json('[]'))`; Map: `id` → `guid()`; `value` → `item()?['value']`; `type` → `item()?['type']`; `adminConsentDisplayName` → `item()?['adminConsentDisplayName']`; `adminConsentDescription` → `item()?['adminConsentDescription']`; `userConsentDisplayName` → `item()?['adminConsentDisplayName']`; `userConsentDescription` → `item()?['adminConsentDescription']`; `isEnabled` → `true` |
| `HTTP Patch expose` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}`; Body [`HTTP_Patch_expose.json`](../powerautomate/actions/HTTP_Patch_expose.json) |
| `Result expose` | Set variable | Name `varResult`; Value `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "appId": "@{body('HTTP_Get_target_app')?['appId']}", "identifierUri": "@{replace(outputs('Payload')?['identifierUriTemplate'], '{appId}', body('HTTP_Get_target_app')?['appId'])}"}` |

#### Case `addAppRoles` → Scope `Do addAppRoles`

| Action | Type | Configuration |
|---|---|---|
| `Select new roles` | Select | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`; Map: `id` → `guid()`; `value` → `item()?['value']`; `displayName` → `item()?['displayName']`; `description` → `item()?['description']`; `allowedMemberTypes` → `split(item()?['allowedMemberTypes'], ',')`; `isEnabled` → `true` |
| `HTTP Patch roles` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}`; Body [`HTTP_Patch_roles.json`](../powerautomate/actions/HTTP_Patch_roles.json) |
| `For each added role` | Apply to each (concurrency 1) | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`. Inside, in order: **(a)** `Filter added role` (Filter array: From `body('Select_new_roles')`; condition `item()?['value']` is equal to `items('For_each_added_role')?['value']`). This picks up the id generated in `Select new roles`; the PATCH response is empty. **(b)** `For each added role group` (Apply to each, concurrency 1, From `coalesce(items('For_each_added_role')?['assignGroups'], json('[]'))`). Inside it: `Queue added role assignment` (Append to array variable `varAssignTodo`, Value below). |
| `Needs SP for roles` | Condition | `and(greater(length(variables('varAssignTodo')), 0), empty(variables('varSpId')))` is equal to `true`. **If yes:** `HTTP Create SP for roles` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json)) → `Set SP id roles` (Set variable `varSpId` = `body('HTTP_Create_SP_for_roles')?['id']`) |
| `Result roles` | Set variable | Name `varResult`; Value `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "appId": "@{body('HTTP_Get_target_app')?['appId']}", "servicePrincipalId": "@{variables('varSpId')}"}` |

`Queue added role assignment` Value (text with tokens):

```
{"roleId": "@{first(body('Filter_added_role'))?['id']}", "roleValue": "@{items('For_each_added_role')?['value']}", "mode": "@{items('For_each_added_role_group')?['mode']}", "id": "@{items('For_each_added_role_group')?['id']}", "displayName": "@{items('For_each_added_role_group')?['displayName']}", "description": "@{items('For_each_added_role_group')?['description']}", "ownerIds": "@{items('For_each_added_role_group')?['ownerIds']}"}
```

#### Case `assignGroupsToAppRoles` → Scope `Do assignGroupsToAppRoles`

| Action | Type | Configuration |
|---|---|---|
| `Select assignment todo` | Select | From `coalesce(outputs('Payload')?['assignments'], json('[]'))`; Map: `roleId` → `item()?['appRoleId']`; `roleValue` → `item()?['appRoleValue']`; `mode` → `item()?['mode']`; `id` → `item()?['id']`; `displayName` → `item()?['displayName']`; `description` → `item()?['description']`; `ownerIds` → `item()?['ownerIds']` |
| `Set assignment todo` | Set variable | Name `varAssignTodo`; Value `body('Select_assignment_todo')` |
| `Needs SP for assign` | Condition | `empty(variables('varSpId'))` is equal to `true`. **If yes:** `HTTP Create SP for assign` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json)) → `Set SP id assign` (Set variable `varSpId` = `body('HTTP_Create_SP_for_assign')?['id']`) |
| `HTTP Patch tags assign` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}`; Body [`HTTP_Patch_tags.json`](../powerautomate/actions/HTTP_Patch_tags.json) |
| `Result assign` | Set variable | Name `varResult`; Value `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "servicePrincipalId": "@{variables('varSpId')}"}` |

#### Case `createServicePrincipal` → Scope `Do createServicePrincipal`

| Action | Type | Configuration |
|---|---|---|
| `SP already exists` | Condition | `empty(variables('varSpId'))` is equal to `false`. **If yes:** `Fail SP exists` (Update item: List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage *plain text* `This app already has an enterprise application.`) → `Stop SP exists` (Terminate: Status **Failed**, Code `SpExists`, Message *plain text* `Enterprise application already exists`). **If no:** leave empty. |
| `HTTP Create SP existing` | Graph | `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json) |
| `Set SP id sp` | Set variable | Name `varSpId`; Value `body('HTTP_Create_SP_existing')?['id']` |
| `HTTP Patch tags sp` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}`; Body [`HTTP_Patch_tags.json`](../powerautomate/actions/HTTP_Patch_tags.json) |
| `Result sp` | Set variable | Name `varResult`; Value `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "servicePrincipalId": "@{body('HTTP_Create_SP_existing')?['id']}"}` |

#### Inside `Try`, after the Switch: role assignments (shared by three cases)

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Apply to each assignment` | Apply to each, **Settings → Concurrency 1** | From `variables('varAssignTodo')`. Inside: 1.1 to 1.3. |
| 1.1 | `Group is new` | Condition | Left `items('Apply_to_each_assignment')?['mode']`; is equal to; right *plain text* `new` |
| | *If yes:* `Select role group owner binds` | Select | From `union(createArray(body('HTTP_Get_requester')?['id']), if(empty(items('Apply_to_each_assignment')?['ownerIds']), json('[]'), split(items('Apply_to_each_assignment')?['ownerIds'], ';')))`; Map in text mode `concat('https://graph.microsoft.com/v1.0/directoryObjects/', item())` |
| | *If yes:* `HTTP Create role group` | Graph | `POST` `https://graph.microsoft.com/v1.0/groups`; Body [`HTTP_Create_role_group.json`](../powerautomate/actions/HTTP_Create_role_group.json) |
| | *If yes:* `Set group id (new)` | Set variable | Name `varGroupId`; Value `body('HTTP_Create_role_group')?['id']` |
| | *If yes:* `Catalog role group` | SharePoint – Create item | List `EntraCatalogGroups`; Title `body('HTTP_Create_role_group')?['displayName']`; GroupId `body('HTTP_Create_role_group')?['id']`; AppCatId `triggerOutputs()?['body/AppCatId']`; Description `body('HTTP_Create_role_group')?['description']`; OwnerUpns `concat(';', outputs('Requester'), ';')`; LastSynced `utcNow()` |
| | *If yes:* `Wait for group replication` | Delay | Count `15`, Unit **Second** |
| | *If no:* `Set group id` | Set variable | Name `varGroupId`; Value `items('Apply_to_each_assignment')?['id']` |
| 1.2 | `HTTP Assign role` | Graph | `POST` `https://graph.microsoft.com/v1.0/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`; Body [`HTTP_Assign_role.json`](../powerautomate/actions/HTTP_Assign_role.json); Settings → Retry policy **Exponential interval**, Count `4`, Interval `PT10S` |
| 1.3 | `Record assignment` | Append to array variable | Name `varAssignments`; Value `concat(items('Apply_to_each_assignment')?['displayName'], ' -> ', items('Apply_to_each_assignment')?['roleValue'])` |
| 2 | `Default access` | Condition | `and(equals(triggerOutputs()?['body/RequestType/Value'], 'createAppRegistration'), empty(variables('varAssignments')), not(equals(outputs('Payload')?['appRoleAssignmentRequired'], false)), not(empty(variables('varSpId'))))` is equal to `true`. **If yes:** `HTTP Assign default access` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`; Body [`HTTP_Assign_default_access.json`](../powerautomate/actions/HTTP_Assign_default_access.json)). With assignment required and no roles, the owning team gets Default Access so someone can sign in. |
| 3 | `Mark completed` | SharePoint – Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Completed`; CompletedAt `utcNow()`; ResultJson `string(setProperty(variables('varResult'), 'assignmentsText', join(variables('varAssignments'), '; ')))` |
| 4 | `Mail completed` | Send an email (V2) | To `triggerOutputs()?['body/Author/Email']`; Subject `concat('Your Entra request ', triggerOutputs()?['body/Title'], ' is complete')`; Body: [completed email body](#er-02-completed-email-body) |

### Catch scope

**Control – Scope** named `Catch`, placed after `Try`. **Run after** (new designer: Settings → Run after; classic: *… → Configure run after*): `Try` **has failed** + **has timed out**, with *is successful* unticked.

| Action | Type | Configuration |
|---|---|---|
| `Failed actions` | Filter array | From `union(result('Do_createAppRegistration'), result('Do_createGroup'), result('Do_exposeApi'), result('Do_addAppRoles'), result('Do_assignGroupsToAppRoles'), result('Do_createServicePrincipal'), result('Try'))`; condition `item()?['status']` is equal to *plain text* `Failed` |
| `Error text` | Compose | Inputs `concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-02 run history'))` |
| `Mark failed` | SharePoint – Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage `outputs('Error_text')`; ResultJson `string(variables('varResult'))` (what was created before the failure, for a manual fix) |
| `Mail failed` | Send an email (V2) | To `concat(triggerOutputs()?['body/Author/Email'], ';', replace(replace(body('Get_settings')?['EntraApproverEmails'], decodeUriComponent('%0D'), ''), decodeUriComponent('%0A'), ';'))`; Subject `concat('Entra request ', triggerOutputs()?['body/Title'], ' failed')`; Body: [failed email body](#er-02-failed-email-body) |

**Retry a failed request:** fix the cause. Then either re-run ER-02 from its run history with **Resubmit**, or, as the flow account, set Status = `Approved` on the item (ManagerDecision and EntraDecision must still be `Approved`). createAppRegistration is not idempotent: a retry creates a second app unless you delete the first. ResultJson lists what the failed run created.

### ER-02 completed email body

`Mail completed` **Body**, entered with fx:

```
concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') is complete.<br><br>',
  if(empty(variables('varResult')?['applicationObjectId']), '', concat('Application (object) ID: ', variables('varResult')?['applicationObjectId'], '<br>')),
  if(empty(variables('varResult')?['appId']), '', concat('Application (client) ID: ', variables('varResult')?['appId'], '<br>')),
  if(empty(variables('varResult')?['identifierUri']), '', concat('Application ID URI: ', variables('varResult')?['identifierUri'], '<br>')),
  if(empty(variables('varResult')?['servicePrincipalId']), '', concat('Enterprise application (object) ID: ', variables('varResult')?['servicePrincipalId'], '<br>')),
  if(empty(variables('varResult')?['teamGroupId']), '', concat('Owning team group ID: ', variables('varResult')?['teamGroupId'], '<br>')),
  if(empty(variables('varResult')?['groupId']), '', concat('Group: ', variables('varResult')?['groupDisplayName'], ' (', variables('varResult')?['groupId'], ')<br>')),
  if(empty(variables('varAssignments')), '', concat('Role assignments: ', join(variables('varAssignments'), '; '), '<br>')),
  '<br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>')
```

### ER-02 failed email body

`Mail failed` **Body**, entered with fx:

```
concat('Request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') failed while being applied.<br><br>Error: ', outputs('Error_text'), '<br><br>Already created (clean up before retrying): ', string(variables('varResult')), '<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>')
```

---

## ER-03 Catalog sync (Premium)

**+ Create → Scheduled cloud flow** → name `ER-03 Catalog sync` → Repeat every **1 Hour**. Run it manually (**Run**) after setup and whenever you onboard groups.

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List Name `EntraSettings`; Id *plain text* `1` |
| 2 | `Get PFX`, `Get PFX password` *(option B only)* | Azure Key Vault – Get secret | Exactly as ER-02 steps 3–4: Name `body('Get_settings')?['PfxSecretName']` / `body('Get_settings')?['PfxPasswordSecretName']`; Secure outputs On |
| 3 | `Init varMembers` | Initialize variable | Name `varMembers`; Type String; Value empty |
| 4 | `HTTP List managed apps` | Graph | `GET` `https://graph.microsoft.com/v1.0/applications?$filter=tags/any(t:t eq 'managedBy:@{body('Get_settings')?['ManagedByTag']}')&$select=id,appId,displayName,tags,identifierUris,appRoles,api&$count=true&$top=999`; Headers `ConsistencyLevel`: `eventual`. Returns up to 999 apps per page; add a Do until over `@odata.nextLink` if you expect more. |
| 5 | `Apply to each app` | Apply to each, **concurrency 1** | From `body('HTTP_List_managed_apps')?['value']`. Inside: 5.1 to 5.10. |
| 5.1 | `Filter app team` | Filter array | From `items('Apply_to_each_app')?['tags']`; condition `startsWith(item(), 'team:')` is equal to `true` |
| 5.2 | `Filter app team name` | Filter array | From `items('Apply_to_each_app')?['tags']`; condition `startsWith(item(), 'teamName:')` is equal to `true` |
| 5.3 | `Filter app appcat` | Filter array | From `items('Apply_to_each_app')?['tags']`; condition `startsWith(item(), 'appCatID:')` is equal to `true` |
| 5.4 | `Team id` | Compose | Inputs `if(empty(body('Filter_app_team')), '', substring(first(body('Filter_app_team')), 5))` |
| 5.5 | `Reset members` | Set variable | Name `varMembers`; Value: leave empty |
| 5.6 | `Has team` | Condition | `empty(outputs('Team_id'))` is equal to `false`. **If yes:** the actions in [Has team? → If yes](#er-03-has-team--if-yes). **If no:** leave empty. |
| 5.7 | `HTTP App owners` | Graph | `GET` `https://graph.microsoft.com/v1.0/applications/@{items('Apply_to_each_app')?['id']}/owners/microsoft.graph.user?$select=userPrincipalName` |
| 5.8 | `Select owner upns` | Select | From `body('HTTP_App_owners')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 5.9 | `HTTP App SP` | Graph | `GET` `https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '@{items('Apply_to_each_app')?['appId']}'&$select=id` |
| 5.10a | `Get app row` | SharePoint – Get items | List `EntraCatalogApps`; Filter Query `ObjectId eq '@{items('Apply_to_each_app')?['id']}'`; Top Count `1` |
| 5.10b | `App row missing` | Condition | `empty(body('Get_app_row')?['value'])` is equal to `true`. **If yes:** `Create app row` (SharePoint – Create item, List `EntraCatalogApps`, the [app row fields](#er-03-app-row-fields)). **If no:** `Update app row` (SharePoint – Update item, List `EntraCatalogApps`, Id `first(body('Get_app_row')?['value'])?['ID']`, plus the same app row fields; Title is one of them). |

### ER-03 Has team? → If yes

| Action | Type | Configuration |
|---|---|---|
| `HTTP Team members` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Team_id')}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999` |
| `Select member upns` | Select | From `body('HTTP_Team_members')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| `Set members` | Set variable | Name `varMembers`; Value `concat(';', join(body('Select_member_upns'), ';'), ';')` |
| `Get team row` | SharePoint – Get items | List `EntraCatalogGroups`; Filter Query `GroupId eq '@{outputs('Team_id')}'`; Top Count `1` |
| `Team row missing` | Condition | `empty(body('Get_team_row')?['value'])` is equal to `true`. **If yes:** `Create team row` (SharePoint – Create item: List `EntraCatalogGroups`; Title `if(empty(body('Filter_app_team_name')), outputs('Team_id'), substring(first(body('Filter_app_team_name')), 9))`; GroupId `outputs('Team_id')`; AppCatId `if(empty(body('Filter_app_appcat')), '', substring(first(body('Filter_app_appcat')), 9))`; LastSynced `utcNow()`). Step 7 fills in members and owners. **If no:** leave empty. |

### ER-03 app row fields

| Column | Value (fx) |
|---|---|
| Title | `items('Apply_to_each_app')?['displayName']` |
| ObjectId | `items('Apply_to_each_app')?['id']` |
| AppId | `items('Apply_to_each_app')?['appId']` |
| AppCatId | `if(empty(body('Filter_app_appcat')), '', substring(first(body('Filter_app_appcat')), 9))` |
| TeamGroupId | `outputs('Team_id')` |
| TeamGroupName | `if(empty(body('Filter_app_team_name')), '', substring(first(body('Filter_app_team_name')), 9))` |
| ServicePrincipalId | `coalesce(first(body('HTTP_App_SP')?['value'])?['id'], '')` |
| IdentifierUri | `coalesce(first(items('Apply_to_each_app')?['identifierUris']), '')` |
| AppRolesJson | `string(coalesce(items('Apply_to_each_app')?['appRoles'], json('[]')))` |
| ScopesJson | `string(coalesce(items('Apply_to_each_app')?['api']?['oauth2PermissionScopes'], json('[]')))` |
| TeamMemberUpns | `variables('varMembers')` |
| OwnerUpns | `concat(';', join(body('Select_owner_upns'), ';'), ';')` |
| LastSynced | `utcNow()` |

### Then refresh every catalog group

After `Apply to each app` (not inside it). This also completes rows added by hand or by ER-02.

| # | Action | Type | Configuration |
|---|---|---|---|
| 6 | `Get catalog groups` | SharePoint – Get items | List `EntraCatalogGroups`; Top Count `5000` |
| 7 | `Apply to each catalog group` | Apply to each (concurrency 5 is fine; no variables) | From `body('Get_catalog_groups')?['value']`. Inside: 7.1 to 7.6. |
| 7.1 | `HTTP Group` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}?$select=id,displayName,description` |
| 7.2 | `HTTP Group members` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999` |
| 7.3 | `HTTP Group owners` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{items('Apply_to_each_catalog_group')?['GroupId']}/owners/microsoft.graph.user?$select=userPrincipalName` |
| 7.4 | `Select group member upns` | Select | From `body('HTTP_Group_members')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 7.5 | `Select group owner upns` | Select | From `body('HTTP_Group_owners')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 7.6 | `Update group row` | SharePoint – Update item | List `EntraCatalogGroups`; Id `items('Apply_to_each_catalog_group')?['ID']`; Title `body('HTTP_Group')?['displayName']`; Description `body('HTTP_Group')?['description']`; AppCatId `if(contains(coalesce(body('HTTP_Group')?['description'], ''), '[appCatID='), first(split(last(split(body('HTTP_Group')?['description'], '[appCatID=')), ';')), '')`; MemberUpns `concat(';', join(body('Select_group_member_upns'), ';'), ';')`; OwnerUpns `concat(';', join(body('Select_group_owner_upns'), ';'), ';')`; LastSynced `utcNow()` |

A deleted group makes `HTTP Group` fail with 404, which fails that iteration and marks the run as failed. To flag or remove such rows, add an action after `HTTP Group` with **Run after → has failed** (for example an Update item that sets LastSynced and a note in Description, or a Delete item).

---

## ER-04 Onboard group (Premium)

Adds an **existing** group to `EntraCatalogGroups` so it appears in the app's pickers for its members and owners. The requester must be a **member or owner** of the group and the group must be **security-enabled**. No approval is needed and nothing changes in Entra.

**+ Create → Automated cloud flow** → name `ER-04 Onboard group` → trigger **SharePoint – When an item is created** → Site Address = your site, List Name = `EntraRequests`.
Trigger **Settings → Trigger conditions** → **+ Add**: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), equals(triggerOutputs()?['body/RequestType/Value'], 'onboardGroup'))`

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List Name `EntraSettings`; Id *plain text* `1` |
| 2 | `Mark in progress` | SharePoint – Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `InProgress` |
| 3 | `Requester` | Compose | Inputs `toLower(last(split(triggerOutputs()?['body/Author/Claims'], '\|')))` |
| 4 | `Group id` | Compose | Inputs `toLower(trim(coalesce(triggerOutputs()?['body/TargetObjectId'], '')))` |
| 5 | `Try` | Control – Scope | Contains 5.1–5.12 |
| 5.1 | `HTTP Get requester` | Graph | `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Requester')}?$select=id` |
| 5.2 | `HTTP Get group` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_id')}?$select=id,displayName,description,securityEnabled` |
| 5.3 | `HTTP Check membership` | Graph | `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`; Body `{"groupIds": ["@{outputs('Group_id')}"]}` (transitive: nested membership counts) |
| 5.4 | `HTTP Group owners` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_id')}/owners/microsoft.graph.user?$select=id,userPrincipalName` |
| 5.5 | `Member or owner` | Condition | `or(not(empty(body('HTTP_Check_membership')?['value'])), contains(string(body('HTTP_Group_owners')?['value']), body('HTTP_Get_requester')?['id']))` is equal to `true`. **If no:** `Fail not member` (Update item: List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage *plain text* `You are neither a member nor an owner of this group.`) → `Stop not member` (Terminate: **Failed**, Code `NotMemberOrOwner`) |
| 5.6 | `Security enabled` | Condition | Left `body('HTTP_Get_group')?['securityEnabled']`; is equal to; right **fx** `true`. **If no:** `Fail not security` (Update item as above with ErrorMessage *plain text* `Only security-enabled groups can be used for owning teams and app roles.`) → `Stop not security` (Terminate: **Failed**, Code `NotSecurityGroup`) |
| 5.7 | `HTTP Group members` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_id')}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999` |
| 5.8 | `Select member upns` | Select | From `body('HTTP_Group_members')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 5.9 | `Select owner upns` | Select | From `body('HTTP_Group_owners')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 5.10 | `Get catalog row` | SharePoint – Get items | List `EntraCatalogGroups`; Filter Query `GroupId eq '@{outputs('Group_id')}'`; Top Count `1` |
| 5.11 | `Row missing` | Condition | `empty(body('Get_catalog_row')?['value'])` is equal to `true`. **If yes:** `Create catalog row` (Create item, List `EntraCatalogGroups`, fields below). **If no:** `Update catalog row` (Update item, List `EntraCatalogGroups`, Id `first(body('Get_catalog_row')?['value'])?['ID']`, fields below) |
| 5.12 | `Mark completed` | Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Completed`; CompletedAt `utcNow()`; TargetDisplayName `body('HTTP_Get_group')?['displayName']`; ResultJson `string(setProperty(setProperty(json('{}'), 'groupId', body('HTTP_Get_group')?['id']), 'groupDisplayName', body('HTTP_Get_group')?['displayName']))` |
| 6 | `Catch` | Scope, **Run after** `Try`: has failed + has timed out | `Failed actions` (Filter array: From `result('Try')`; `item()?['status']` is equal to `Failed`) → `Error text` (Compose: `if(equals(outputs('HTTP_Get_group')?['statusCode'], 404), 'Group not found: check the Object ID (Entra admin center > Groups > the group > Object ID).', concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-04 run history')))`) → `Mark failed` (Update item: Id, Title, **Status Value** `Failed`, ErrorMessage `outputs('Error_text')`) |

Catalog row fields (5.11):

| Column | Value (fx) |
|---|---|
| Title | `body('HTTP_Get_group')?['displayName']` |
| GroupId | `body('HTTP_Get_group')?['id']` |
| Description | `body('HTTP_Get_group')?['description']` |
| AppCatId | `if(contains(coalesce(body('HTTP_Get_group')?['description'], ''), '[appCatID='), first(split(last(split(body('HTTP_Get_group')?['description'], '[appCatID=')), ';')), '')` |
| MemberUpns | `concat(';', join(body('Select_member_upns'), ';'), ';')` |
| OwnerUpns | `concat(';', join(body('Select_owner_upns'), ';'), ';')` |
| LastSynced | `utcNow()` |

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
