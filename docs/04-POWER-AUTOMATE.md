# 4. Power Automate: the flows

| Flow | Trigger | Connectors | Licence |
|---|---|---|---|
| **ER-01 Approvals** | SharePoint: item created in EntraRequests | SharePoint, Office 365 Users, Approvals, Office 365 Outlook, Teams (optional) | Standard |
| **ER-02 Execute** | SharePoint: item created or modified, `Status = Approved` | SharePoint, Outlook, plus a Graph connection: **HTTP with Microsoft Entra ID (preauthorized)** (option A) or **HTTP** + **Azure Key Vault** (option B) | Premium (owner's licence) |
| **ER-03 Catalog sync** | Recurrence, hourly (+ run manually) | SharePoint, plus the same Graph connection | Premium (owner's licence) |
| **ER-04 Onboard group** | SharePoint: item created, `RequestType = onboardGroup` (group looked up by name or Object ID) | SharePoint, plus the same Graph connection | Premium (owner's licence) |
| **ER-05 Find app** | SharePoint: item created, `RequestType = lookupApp` (the **Search** button on the change screen) | SharePoint, plus the same Graph connection | Premium (owner's licence) |
| **ER-06 Tag owning group** | SharePoint: item created, `RequestType = tagOwnerGroup` | SharePoint, plus the same Graph connection | Premium (owner's licence) |
| **ER-07 Requeue approved** | Manual (instant), Entra ID team only | SharePoint, Office 365 Outlook | Standard |

**Shortcut:** instead of building the flows by hand, import them as a solution: [doc 09](09-SOLUTION-IMPORT.md). This page remains the reference for what each action does.

Build them all **signed in as the flow account** (the account in `EntraSettings.ServiceAccountUpn`), in the Entra Self-Service environment, ideally inside a **solution** (Solutions → New solution → New → Automation → Cloud flow) so you can export and move them later. Add the Entra ID team as co-owners.

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
Trigger **Settings → Trigger conditions** → **+ Add**: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), not(contains(createArray('onboardGroup', 'lookupApp', 'tagOwnerGroup'), triggerOutputs()?['body/RequestType/Value'])))` (these need no approval; ER-04, ER-05 and ER-06 handle them)

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
| 9 | Fifteen variables | Variables – Initialize variable ×15 | One action per row, named `Init <name>`: `varTeamGroupId` String (empty); `varTeamGroupName` String (empty); `varSpId` String (empty); `varGroupId` String (empty); `varRoleId` String (empty); `varAssignTodo` Array, Value *plain text* `[]`; `varAssignments` Array, Value `[]`; `varResult` Object, Value `{}`; `varExposeOk` String, Value `no`; `varAssignOk` String, Value `no`; `varTeamTag` String (empty); `varGroupOwner` String, Value `no`; `varLog` Array, Value `[]` (the step log); `varHadErrors` String, Value `no`; `varFailMessage` String (empty) |
| 10 | `Try` | Control – Scope | Everything in the next sections goes **inside** this scope |
| 11 | `Catch` | Control – Scope | After `Try` (not inside it). See [Catch](#catch-scope). |

### Step log and failures (1.3.3)

ER-02 writes one line per step to the array variable `varLog`; at the end it becomes the request's **CompletionNotes** and goes into the email, so the requester sees what was done and what wasn't:

```
Done: app registration APP-1234-D-ORDERS-api created (client ID …, object ID …), owner tag team:group\…, 2 app role(s)
Done: Application ID URI api://… and 1 scope(s) set
Failed: enterprise application not created (…). Use Enterprise application on this app to create it.
Skipped: 2 role assignment(s), because there is no enterprise application to assign them on
```

Three kinds of action do this:

| Pattern | Actions | Used when |
|---|---|---|
| **Log** | `Log …` (Append to array variable `varLog`, a `concat('Done: …')` expression) | after each step that worked |
| **Log failed** | `Log …` with `concat('Failed: …')` or `concat('Skipped: …')`, then `Log … flag` (Set variable `varHadErrors` = `yes`) | a step failed, but the steps that don't depend on it carry on (Expose API, enterprise app, each role assignment) |
| **Stop** | `Set <x> message` (Set variable `varFailMessage` = the message) → `Log <x>` (append `concat('Failed: ', variables('varFailMessage'))`) → `Throw <x>` (Compose, Inputs `json(concat('Stopped: ', variables('varFailMessage')))`) | nothing more should happen (not the owner, not in the owning group, enterprise app already exists). The Compose fails on purpose (`json()` of plain text), so **Try fails and Catch runs**. Don't use Terminate inside Try: it ends the run immediately, Catch is skipped, and the request gets no notes and no email. |

At the end of Try, `Had errors` decides: **Completed** if every step worked; otherwise **Failed** with the notes (*partly failed*): the Done steps stay in place, and the email says which card to use for the rest.

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
| *Ownership check* | | The [ownership check](#ownership-check-shared-by-er-02-er-05-er-06) with prefix `Target`, tags `body('HTTP_Get_target_app')?['tags']`, user id `body('HTTP_Get_requester')?['id']`, flag `varGroupOwner` |
| `Requester may change` | Condition | `and(<owner expression>, or(empty(body('Filter_appcat_tag')), empty(triggerOutputs()?['body/AppCatId']), equals(first(body('Filter_appcat_tag')), concat('appCatID:', triggerOutputs()?['body/AppCatId']))))` is equal to `true`, where `<owner expression>` is the one from the ownership check. **If no:** **Stop** `not owner` with message *plain text* `Not an authorized owner: the app's team tag names neither you (team:user\<your id>) nor a group you are a member of (team:group\<group id>), or its appCatID differs. Nothing was changed.` (see [Step log and failures](#step-log-and-failures-133)). Owners of the app registration object are not used. |
| `Updated tags` | Compose | Inputs `union(body('Filter_kept_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])), if(empty(body('Filter_appcat_tag')), createArray(concat('managedBy:', body('Get_settings')?['ManagedByTag'])), json('[]')), if(and(empty(body('Filter_appcat_tag')), not(empty(triggerOutputs()?['body/AppCatId']))), createArray(concat('appCatID:', triggerOutputs()?['body/AppCatId'])), json('[]')))` |
| `HTTP Find target SP` | Graph | `GET` `https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '@{body('HTTP_Get_target_app')?['appId']}'&$select=id` |
| `Set target SP` | Variables – Set variable | Name `varSpId`; Value `coalesce(first(body('HTTP_Find_target_SP')?['value'])?['id'], '')` |

### Inside `Try`, after `Has target app`: Switch

**Control – Switch** named `Request type`; On `triggerOutputs()?['body/RequestType/Value']`. Add five cases (createAppRegistration, exposeApi, addAppRoles, assignGroupsToAppRoles, createServicePrincipal); in each case's **Equals** box type the request type as *plain text* (e.g. `createAppRegistration`). Inside each case add **one Scope** named `Do <type>` (e.g. `Do createAppRegistration`) and put that case's actions inside it. The Catch refers to those exact scope names. Leave **Default** empty.

#### Case `createAppRegistration` → Scope `Do createAppRegistration`

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Has owning group` | Condition | `not(empty(outputs('Payload')?['owningGroup']?['id']))` is equal to `true`. The owning group is **optional**. **If yes:** `HTTP Check team membership` (Graph: `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`; Body `{"groupIds": ["@{outputs('Payload')?['owningGroup']?['id']}"]}`) → `Is team member` (Condition: `length(body('HTTP_Check_team_membership')?['value'])` is greater than `0`; **If no:** **Stop** `not team member` with message `You are not a member of the owning group. Nothing was created.`) → `HTTP Get team group` (Graph: `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Payload')?['owningGroup']?['id']}?$select=id,displayName`) → `Set team id` (`varTeamGroupId` = `body('HTTP_Get_team_group')?['id']`) → `Set team name` (`varTeamGroupName` = `body('HTTP_Get_team_group')?['displayName']`) → `Set group team tag` (`varTeamTag` = `concat('team:group\', body('HTTP_Get_team_group')?['id'])`). **If no:** `Set user team name` (`varTeamGroupName` = `outputs('Requester')`) → `Set user team tag` (`varTeamTag` = `concat('team:user\', toLower(body('HTTP_Get_requester')?['id']))`). |
| 2 | `Select app roles` | Select | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`; Map (key/value rows): `id` → `guid()`; `value` → `item()?['value']`; `displayName` → `item()?['displayName']`; `description` → `item()?['description']`; `allowedMemberTypes` → `split(item()?['allowedMemberTypes'], ',')`; `isEnabled` → `true` |
| 3 | `Select scopes` | Select | From `if(equals(outputs('Payload')?['exposeApi']?['enabled'], true), coalesce(outputs('Payload')?['exposeApi']?['scopes'], json('[]')), json('[]'))`; Map: `id` → `guid()`; `value` → `item()?['value']`; `type` → `item()?['type']`; `adminConsentDisplayName` → `item()?['adminConsentDisplayName']`; `adminConsentDescription` → `item()?['adminConsentDescription']`; `userConsentDisplayName` → `item()?['adminConsentDisplayName']`; `userConsentDescription` → `item()?['adminConsentDescription']`; `isEnabled` → `true` |
| 4 | `Select id token claims` | Select | From `if(empty(outputs('Payload')?['optionalClaimsIdToken']), json('[]'), split(outputs('Payload')?['optionalClaimsIdToken'], ','))`; Map: `name` → `item()`; `essential` → `false` |
| 5 | `Select access token claims` | Select | From `if(empty(outputs('Payload')?['optionalClaimsAccessToken']), json('[]'), split(outputs('Payload')?['optionalClaimsAccessToken'], ','))`; Map: `name` → `item()`; `essential` → `false` |
| 6 | `Filter optional tags` | Filter array | From `split(coalesce(outputs('Payload')?['tags'], ''), ';')`; condition `and(contains(item(), '='), greater(length(trim(item())), 2))` is equal to `true` |
| 7 | `Select optional tags` | Select | From `body('Filter_optional_tags')`; Map in text mode `concat(trim(first(split(item(), '='))), ':', trim(last(split(item(), '='))))` |
| 8 | `App tags` | Compose | Inputs `union(outputs('Base_tags'), createArray(variables('varTeamTag'), concat('teamName:', variables('varTeamGroupName'))), if(empty(outputs('Payload')?['appEnv']), json('[]'), createArray(concat('appEnv:', outputs('Payload')?['appEnv']))), if(empty(outputs('Payload')?['borShortName']), json('[]'), createArray(concat('borShortName:', outputs('Payload')?['borShortName']))), body('Select_optional_tags'))`. The team tag is `team:group\<group id>` or `team:user\<requester object id>`. |
| 9 | `HTTP Create application` | Graph | `POST` `https://graph.microsoft.com/v1.0/applications`; Body [`HTTP_Create_application.json`](../powerautomate/actions/HTTP_Create_application.json) |
| 9a | `Result create app` → `Log app created` | Set variable, Append to array variable | `varResult` = `{"applicationObjectId": "@{body('HTTP_Create_application')?['id']}", "appId": "@{body('HTTP_Create_application')?['appId']}", "identifierUri": "", "servicePrincipalId": "", "teamGroupId": "@{variables('varTeamGroupId')}", "team": "@{variables('varTeamTag')}"}` (so Catch can report the IDs if a later step fails); log `concat('Done: app registration ', body('HTTP_Create_application')?['displayName'], ' created (client ID ', body('HTTP_Create_application')?['appId'], ', object ID ', body('HTTP_Create_application')?['id'], '), owner tag ', variables('varTeamTag'), …)` |
| 9b | `Wait for app replication` | Schedule – Delay | Count `15`, Unit **Second**. A new app takes a few seconds to replicate; calls against it before that return 404. Expose API (10) also retries. |
| 10 | `Expose API` | Condition | `equals(outputs('Payload')?['exposeApi']?['enabled'], true)` is equal to `true`. **If yes:** the **retry pattern** below with call `HTTP Expose API` (Graph: `PATCH` `https://graph.microsoft.com/v1.0/applications/@{body('HTTP_Create_application')?['id']}`; Body [`HTTP_Expose_API.json`](../powerautomate/actions/HTTP_Expose_API.json)), success status `204`, flag `varExposeOk`; in `HTTP Expose API gave up` → If yes: **Log failed** `concat('Failed: Application ID URI and scopes were not set (', coalesce(body('HTTP_Expose_API')?['error']?['message'], 'no answer after 6 attempts'), '). Use Expose an API on this app to add them.')`. Then `Expose done` (Condition `variables('varExposeOk')` = `yes`; If yes: **Log** `concat('Done: Application ID URI ', replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), ' and ', string(length(body('Select_scopes'))), ' scope(s) set')`). **If no:** leave empty. |
| 12 | `Create SP` | Condition | `equals(outputs('Payload')?['createServicePrincipal'], true)` is equal to `true`. **If yes:** 12.1–12.2. **If no:** leave empty. |
| 12.1 | *If yes:* `Wait for replication` | Schedule – Delay | Count `10`, Unit **Second** |
| 12.2 | *If yes:* `Do until SP` | Control – Do until | Loop until: `empty(variables('varSpId'))` is equal to `false`. Change limits: Count `6`, Timeout `PT10M`. Inside, in order: **(a)** `HTTP Create SP` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP.json`](../powerautomate/actions/HTTP_Create_SP.json); Settings → Retry policy **None**). **(b)** `SP created` (Condition: `outputs('HTTP_Create_SP')?['statusCode']` is equal to *plain text* `201`; **Run after** `HTTP Create SP`: **is successful** + **has failed**). *If yes:* `Set SP id` (Set variable `varSpId` = `body('HTTP_Create_SP')?['id']`). *If no:* `Retry delay` (Delay 10 seconds). |
| 12.3 | *If yes:* `SP done` | Condition | `empty(variables('varSpId'))` is equal to `false`. **If yes:** **Log** `concat('Done: enterprise application created (object ID ', variables('varSpId'), '), assignment required: ', if(equals(outputs('Payload')?['appRoleAssignmentRequired'], false), 'no', 'yes'))`. **If no:** **Log failed** `concat('Failed: enterprise application not created (', coalesce(body('HTTP_Create_SP')?['error']?['message'], concat('HTTP ', string(outputs('HTTP_Create_SP')?['statusCode']))), '). Use Enterprise application on this app to create it.')`. |
| 13 | `For each new role` | Apply to each (concurrency 1) | From `coalesce(outputs('Payload')?['appRoles'], json('[]'))`. Inside, in order: **(a)** `Filter created role` (Filter array: From `body('HTTP_Create_application')?['appRoles']`; condition `item()?['value']` is equal to `items('For_each_new_role')?['value']`). **(b)** `For each new role group` (Apply to each, concurrency 1, From `coalesce(items('For_each_new_role')?['assignGroups'], json('[]'))`). Inside it: `Queue new role assignment` (Variables – **Append to array variable**, Name `varAssignTodo`, Value: the JSON below). |
| 14 | `Result create app final` | Set variable | Name `varResult`; Value (text with tokens) `{"applicationObjectId": "@{body('HTTP_Create_application')?['id']}", "appId": "@{body('HTTP_Create_application')?['appId']}", "identifierUri": "@{if(equals(variables('varExposeOk'), 'yes'), replace(outputs('Payload')?['exposeApi']?['identifierUriTemplate'], '{appId}', body('HTTP_Create_application')?['appId']), '')}", "servicePrincipalId": "@{variables('varSpId')}", "teamGroupId": "@{variables('varTeamGroupId')}", "team": "@{variables('varTeamTag')}"}`. Built from scratch: a Set variable can't read its own variable. |
| 15 | `Catalog new app` | SharePoint – Create item | List `EntraCatalogApps`; Title `outputs('Payload')?['displayName']`; ObjectId `body('HTTP_Create_application')?['id']`; AppId `body('HTTP_Create_application')?['appId']`; AppCatId `triggerOutputs()?['body/AppCatId']`; TeamGroupId `variables('varTeamGroupId')`; TeamGroupName `variables('varTeamGroupName')`; ServicePrincipalId `variables('varSpId')`; IdentifierUri `variables('varResult')?['identifierUri']`; AppRolesJson `string(body('HTTP_Create_application')?['appRoles'])`; ScopesJson `string(body('Select_scopes'))`; TeamMemberUpns `concat(';', outputs('Requester'), ';')`; LastSynced `utcNow()`. ER-03 fills in the full team membership within the hour. The app registration gets **no owners**: access is managed through the owning team and role groups. |

Step 13 `Queue new role assignment` Value (text with tokens):

```
{"roleId": "@{first(body('Filter_created_role'))?['id']}", "roleValue": "@{items('For_each_new_role')?['value']}", "mode": "@{items('For_each_new_role_group')?['mode']}", "id": "@{items('For_each_new_role_group')?['id']}", "displayName": "@{items('For_each_new_role_group')?['displayName']}", "description": "@{items('For_each_new_role_group')?['description']}", "ownerIds": "@{items('For_each_new_role_group')?['ownerIds']}"}
```

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
| `SP already exists` | Condition | `empty(variables('varSpId'))` is equal to `false`. **If yes:** **Stop** `SP exists` with message *plain text* `This app already has an enterprise application. Nothing was changed.` **If no:** leave empty. After `Set SP id sp`: **Log** `concat('Done: enterprise application created (object ID ', variables('varSpId'), '), assignment required: …')`. |
| `HTTP Create SP existing` | Graph | `POST` `https://graph.microsoft.com/v1.0/servicePrincipals`; Body [`HTTP_Create_SP_existing.json`](../powerautomate/actions/HTTP_Create_SP_existing.json) |
| `Set SP id sp` | Set variable | Name `varSpId`; Value `body('HTTP_Create_SP_existing')?['id']` |
| `HTTP Patch tags sp` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{triggerOutputs()?['body/TargetObjectId']}`; Body [`HTTP_Patch_tags.json`](../powerautomate/actions/HTTP_Patch_tags.json) |
| `Result sp` | Set variable | Name `varResult`; Value `{"applicationObjectId": "@{triggerOutputs()?['body/TargetObjectId']}", "servicePrincipalId": "@{body('HTTP_Create_SP_existing')?['id']}"}` |

#### Inside `Try`, after the Switch: role assignments (shared by three cases), then finish

Each assignment is tried on its own and logged; one failure doesn't stop the others.

| # | Action | Type | Configuration |
|---|---|---|---|
| 1 | `Assignments skipped` | Condition | `and(greater(length(variables('varAssignTodo')), 0), empty(variables('varSpId')))` is equal to `true`. **If yes:** **Log failed** `concat('Skipped: ', string(length(variables('varAssignTodo'))), ' role assignment(s), because there is no enterprise application to assign them on')`. **If no:** 1.1. |
| 1.1 | `Apply to each assignment` | Apply to each, **Settings → Concurrency 1** | From `variables('varAssignTodo')`. Inside: 1.2. |
| 1.2 | `Group id missing` | Condition | `empty(items('Apply_to_each_assignment')?['id'])` is equal to `true`. **If yes:** **Log failed** `concat('Failed: ', items('Apply_to_each_assignment')?['displayName'], ' -> role ', items('Apply_to_each_assignment')?['roleValue'], ' (the group has no Object ID: add it with Add existing group and pick it again)')`. **If no:** 1.3 to 1.5. |
| 1.3 | `Set group id` | Set variable | `varGroupId` = `items('Apply_to_each_assignment')?['id']` |
| 1.4 | `HTTP Assign role` | retry pattern | Call `HTTP Assign role` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`; Body [`HTTP_Assign_role.json`](../powerautomate/actions/HTTP_Assign_role.json)), success status `201`, flag `varAssignOk`. In `HTTP Assign role gave up` → If yes: **Log failed** `concat('Failed: ', items('Apply_to_each_assignment')?['displayName'], ' -> role ', items('Apply_to_each_assignment')?['roleValue'], ' (', coalesce(body('HTTP_Assign_role')?['error']?['message'], 'no answer after 6 attempts'), ')')` |
| 1.5 | `Assignment ok` | Condition | `variables('varAssignOk')` is equal to `yes`. **If yes:** `Record assignment` (Append to array variable `varAssignments` = `concat(items('Apply_to_each_assignment')?['displayName'], ' -> ', items('Apply_to_each_assignment')?['roleValue'])`) → **Log** `concat('Done: ', items('Apply_to_each_assignment')?['displayName'], ' -> role ', items('Apply_to_each_assignment')?['roleValue'])` |
| 2 | `Default access` | Condition | `and(equals(triggerOutputs()?['body/RequestType/Value'], 'createAppRegistration'), empty(variables('varAssignments')), not(equals(outputs('Payload')?['appRoleAssignmentRequired'], false)), not(empty(variables('varSpId'))), empty(coalesce(outputs('Payload')?['appRoles'], json('[]'))))` is equal to `true`. **If yes:** the **retry pattern** with call `HTTP Assign default access` (Graph: `POST` `https://graph.microsoft.com/v1.0/servicePrincipals/@{variables('varSpId')}/appRoleAssignedTo`; Body [`HTTP_Assign_default_access.json`](../powerautomate/actions/HTTP_Assign_default_access.json)), success status `201`, flag `varDefaultOk` (String `no`, initialized at the top); gave up → **Log failed** `concat('Failed: default access for ', variables('varTeamGroupName'), ' (', coalesce(body('HTTP_Assign_default_access')?['error']?['message'], 'no answer after 6 attempts'), ') …')`; then `Default access done` → **Log** `Done: default access …`. With assignment required and no roles, the owner (group or user) gets Default Access so someone can sign in. The retry covers **404 Request_ResourceNotFound** while the new enterprise app replicates. Default access (`appRoleId` 0000…) is only accepted for an app **without** app roles. |
| 2b | `Roles without holders` | Condition | Same as 2, but the app **has** roles (`not(empty(…appRoles…))`). **If yes:** **Log** *plain* `Note: assignment is required and no group holds any of the app roles yet, so nobody can sign in. Give a group a role with Role assignments.` (a note, not an error) |
| 3 | `Completion notes` | Compose | `join(variables('varLog'), decodeUriComponent('%0A'))` (one step per line) |
| 4 | `Result json` | Compose | `string(setProperty(variables('varResult'), 'assignmentsText', join(variables('varAssignments'), '; ')))` |
| 5 | `Had errors` | Condition | `variables('varHadErrors')` is equal to `yes`. **If no:** `Mark completed` (Update item: **Status** `Completed`; CompletedAt `utcNow()`; **CompletionNotes** `outputs('Completion_notes')`; ResultJson `outputs('Result_json')`) → `Mail completed` (To the requester; Subject `concat('Your Entra request ', triggerOutputs()?['body/Title'], ' is complete')`; Body below). **If yes:** `Mark partly failed` (Update item: **Status** `Failed`; CompletedAt `utcNow()`; ErrorMessage *plain text* `Some steps failed. The steps marked Done are in place; see the completion notes for what still needs doing.`; CompletionNotes, ResultJson as above) → `Mail partly failed` (To the requester and the Entra ID team, as `Mail failed`; Subject `concat('Entra request ', triggerOutputs()?['body/Title'], ' partly failed')`; Body below). |

### Retry pattern (Expose API and role assignments)

Right after an app, enterprise app or group is created, Graph can answer **404** or **400** for a few seconds, until the object has replicated. Power Automate's retry policy only retries 408, 429 and 5xx errors, so ER-02 retries these calls itself. For a call `<Call>` with success status `<status>` and flag variable `<flag>`:

| Action | Type | Configuration |
|---|---|---|
| `Reset <flag>` | Set variable | Name `<flag>`; Value *plain text* `no` |
| `Until <Call>` | Control – Do until | Loop until `variables('<flag>')` is equal to *plain text* `yes`; Change limits: Count `6`, Timeout `PT10M`. Inside: the next two actions |
| `<Call>` | Graph | As given in the step; Settings → Retry policy **None** |
| `<Call> ok` | Condition, **Run after** `<Call>`: is successful + has failed | `or(equals(outputs('<Call_with_underscores>')?['statusCode'], <status>), contains(string(outputs('<Call_with_underscores>')?['body']), 'already exist'))` is equal to `true`. **If yes:** `Set <flag>` (Set variable `<flag>` = `yes`). **If no:** `<Call> retry delay` (Delay 10 seconds) |
| `<Call> gave up` | Condition, after the Do until | `variables('<flag>')` is equal to *plain text* `no`. **If yes:** the step's **Log failed** actions (see each step). |

"Already exists" counts as success, so re-running a request doesn't fail on assignments that are already there.

### Catch scope

**Control – Scope** named `Catch`, placed after `Try`. **Run after** (new designer: Settings → Run after; classic: *… → Configure run after*): `Try` **has failed** + **has timed out**, with *is successful* unticked.

| Action | Type | Configuration |
|---|---|---|
| `Failed actions` | Filter array | From `union(result('Do_createAppRegistration'), result('Do_exposeApi'), result('Do_addAppRoles'), result('Do_assignGroupsToAppRoles'), result('Do_createServicePrincipal'), result('Try'))`; condition `item()?['status']` is equal to *plain text* `Failed` |
| `Error text` | Compose | Inputs `if(empty(variables('varFailMessage')), concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-02 run history')), variables('varFailMessage'))` (a **Stop** message wins over the technical error of its Throw) |
| `Failure log` | Compose | `if(empty(variables('varFailMessage')), union(variables('varLog'), createArray(concat('Failed: ', outputs('Error_text')))), variables('varLog'))` (a Stop is already logged) |
| `Failure notes` | Compose | `concat(join(outputs('Failure_log'), decodeUriComponent('%0A')), decodeUriComponent('%0A'), 'Not run: every step after the failed one.')` |
| `Mark failed` | SharePoint – Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `Failed`; ErrorMessage `outputs('Error_text')`; **CompletionNotes** `outputs('Failure_notes')`; ResultJson `string(variables('varResult'))` (what was created before the failure, for a manual fix) |
| `Mail failed` | Send an email (V2) | To `concat(triggerOutputs()?['body/Author/Email'], ';', replace(replace(body('Get_settings')?['EntraApproverEmails'], decodeUriComponent('%0D'), ''), decodeUriComponent('%0A'), ';'))`; Subject `concat('Entra request ', triggerOutputs()?['body/Title'], ' failed')`; Body: [failed email body](#er-02-failed-email-body) |

**Requests that never ran** (Approved while ER-02 was off): run **ER-07 Requeue approved** (below).

**Retry a failed request:** fix the cause. Then either re-run ER-02 from its run history with **Resubmit**, or, as the flow account, set Status = `Approved` on the item (ManagerDecision and EntraDecision must still be `Approved`). createAppRegistration is not idempotent: a retry creates a second app unless you delete the first. ResultJson lists what the failed run created.

### ER-02 completed email body

`Mail completed` **Body**, entered with fx:

```
concat('Your request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') is complete.<br><br><b>What was done</b><br>',
  join(variables('varLog'), '<br>'),
  '<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>')
```

`Mail partly failed` is the same with *was only partly applied* and *Steps*, followed by `'<br><br>The steps marked Done are in place. Do not resubmit the whole request: use the matching card (Expose an API, Enterprise application, Role assignments) for the failed steps.'`.

### ER-02 failed email body

`Mail failed` **Body**, entered with fx:

```
concat('Request <b>', triggerOutputs()?['body/Title'], '</b> (', triggerOutputs()?['body/RequestType/Value'], ' – ', triggerOutputs()?['body/TargetDisplayName'], ') failed while being applied.<br><br>Error: ', outputs('Error_text'),
  '<br><br><b>Steps</b><br>', join(outputs('Failure_log'), '<br>'), '<br>Not run: every step after the failed one.',
  '<br><br>IDs of anything created: ', string(variables('varResult')),
  '<br><br><a href="', body('Get_settings')?['PowerAppUrl'], '">Open Entra Self-Service</a>')
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
| 5.4 | `Team tag` / `Team id` / `Owner user id` | Compose ×3 | `Team tag` = `if(empty(body('Filter_app_team')), '', substring(first(body('Filter_app_team')), 5))` (`group\<id>`, `user\<id>`, or a bare group id from 1.2); `Team id` = `if(startsWith(outputs('Team_tag'), 'group\'), substring(outputs('Team_tag'), 6), if(startsWith(outputs('Team_tag'), 'user\'), '', outputs('Team_tag')))`; `Owner user id` = `if(startsWith(outputs('Team_tag'), 'user\'), substring(outputs('Team_tag'), 5), '')` |
| 5.5 | `Reset members` | Set variable | Name `varMembers`; Value: leave empty |
| 5.6 | `Has team` | Condition | `empty(outputs('Team_id'))` is equal to `false`. **If yes:** the actions in [Has team? → If yes](#er-03-has-team--if-yes). **If no:** leave empty. |
| 5.6b | `Has owner user` | Condition | `empty(outputs('Owner_user_id'))` is equal to `false`. **If yes:** `HTTP Owner user` (Graph: `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Owner_user_id')}?$select=userPrincipalName`) → `Set owner member` (Set variable `varMembers` = `concat(';', toLower(body('HTTP_Owner_user')?['userPrincipalName']), ';')`). A user-owned app is visible to that user only. |
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

Makes an **existing** group selectable in the app. Groups are created outside this platform; users add the ones they need with **Add existing group**, by typing the group's **display name or Object ID**. ER-04 finds the group in Entra, checks that the requester is a **member or owner** and that it is **security-enabled**, then creates or updates its `EntraCatalogGroups` row. No approval; nothing changes in Entra. The app shows the result within a few seconds (it polls the request).

**+ Create → Automated cloud flow** → name `ER-04 Onboard group` → trigger **SharePoint – When an item is created** → Site Address = your site, List Name = `EntraRequests`.
Trigger **Settings → Trigger conditions** → **+ Add**: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), equals(triggerOutputs()?['body/RequestType/Value'], 'onboardGroup'))`

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List Name `EntraSettings`; Id *plain text* `1` |
| 2 | `Mark in progress` | SharePoint – Update item | List `EntraRequests`; Id `int(triggerOutputs()?['body/ID'])`; Title `triggerOutputs()?['body/Title']`; **Status Value**: pick `InProgress` |
| 3 | `Requester` | Compose | Inputs `toLower(last(split(triggerOutputs()?['body/Author/Claims'], '\|')))` |
| 4 | `Group query` | Compose | Inputs `trim(coalesce(triggerOutputs()?['body/TargetDisplayName'], triggerOutputs()?['body/TargetObjectId'], ''))` (what the user typed) |
| 5 | `Init varGroup` | Initialize variable | Name `varGroup`; Type Object; Value `{}` |
| 6 | `Try` | Control – Scope | Contains 6.1–6.14 |
| 6.1 | `HTTP Get requester` | Graph | `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Requester')}?$select=id` |
| 6.2 | `Query is object id` | Condition | `and(equals(length(outputs('Group_query')), 36), equals(length(split(outputs('Group_query'), '-')), 5))` is equal to `true`. **If yes:** 6.2y. **If no:** 6.2n. |
| 6.2y | *by Object ID* | | `HTTP Get group by id` (Graph: `GET` `https://graph.microsoft.com/v1.0/groups/@{toLower(outputs('Group_query'))}?$select=id,displayName,description,securityEnabled`; Retry policy **None**) → `Found by id` (Condition, **Run after** HTTP Get group by id: is successful + has failed; `outputs('HTTP_Get_group_by_id')?['statusCode']` is equal to *plain text* `200`). **If yes:** `Set group from id` (Set variable `varGroup` = `body('HTTP_Get_group_by_id')`). **If no:** `Fail id not found` (Update item: Status `Failed`, ErrorMessage `concat('No group with Object ID ', outputs('Group_query'), ' was found. Check the ID (Entra admin center > Groups > the group > Object ID).')`) → `Stop id not found` (Terminate: **Failed**) |
| 6.2n | *by name* | | `HTTP Find group by name` (Graph: `GET` `https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '@{encodeUriComponent(replace(outputs('Group_query'), '''', ''''''))}'&$select=id,displayName,description,securityEnabled&$top=5`) → `No group with that name` (Condition: `empty(body('HTTP_Find_group_by_name')?['value'])` is equal to `true`; **If yes:** `Fail name not found` with ErrorMessage `concat('No group named ', outputs('Group_query'), ' was found. Check the exact name, or enter the group''s Object ID.')` → `Stop name not found`) → `Several groups with that name` (Condition: `length(body('HTTP_Find_group_by_name')?['value'])` is greater than `1`; **If yes:** `Fail name ambiguous` with ErrorMessage `concat(string(length(body('HTTP_Find_group_by_name')?['value'])), ' groups are named ', outputs('Group_query'), '. Enter the Object ID of the one you mean.')` → `Stop name ambiguous`) → `Set group from name` (Set variable `varGroup` = `first(body('HTTP_Find_group_by_name')?['value'])`) |
| 6.3 | `Group id` | Compose | Inputs `variables('varGroup')?['id']` |
| 6.4 | `HTTP Check membership` | Graph | `POST` `https://graph.microsoft.com/v1.0/users/@{body('HTTP_Get_requester')?['id']}/checkMemberGroups`; Body `{"groupIds": ["@{outputs('Group_id')}"]}` (transitive: nested membership counts) |
| 6.5 | `HTTP Group owners` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_id')}/owners/microsoft.graph.user?$select=id,userPrincipalName` |
| 6.6 | `Member or owner` | Condition | `or(not(empty(body('HTTP_Check_membership')?['value'])), contains(string(body('HTTP_Group_owners')?['value']), body('HTTP_Get_requester')?['id']))` is equal to `true`. **If no:** `Fail not member` (ErrorMessage `concat('You are neither a member nor an owner of ', variables('varGroup')?['displayName'], '. Ask one of its owners to add you, or pick another group.')`) → `Stop not member` |
| 6.7 | `Security enabled` | Condition | Left `variables('varGroup')?['securityEnabled']`; is equal to; right **fx** `true`. **If no:** `Fail not security` (ErrorMessage `concat(variables('varGroup')?['displayName'], ' is not a security group. Only security-enabled groups can be used for owning teams and app roles.')`) → `Stop not security` |
| 6.8 | `HTTP Group members` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_id')}/transitiveMembers/microsoft.graph.user?$select=userPrincipalName&$top=999` |
| 6.9 | `Select member upns` / `Select owner upns` | Select ×2 | From `body('HTTP_Group_members')?['value']` / `body('HTTP_Group_owners')?['value']`; Map in text mode `toLower(item()?['userPrincipalName'])` |
| 6.10 | `Get catalog row` | SharePoint – Get items | List `EntraCatalogGroups`; Filter Query `GroupId eq '@{outputs('Group_id')}'`; Top Count `1` |
| 6.11 | `Row missing` | Condition | `empty(body('Get_catalog_row')?['value'])` is equal to `true`. **If yes:** `Create catalog row` (Create item, fields below). **If no:** `Update catalog row` (Update item, Id `first(body('Get_catalog_row')?['value'])?['ID']`, fields below) |
| 6.12 | `Mark completed` | Update item | Id, Title; **Status Value**: pick `Completed`; CompletedAt `utcNow()`; TargetDisplayName `variables('varGroup')?['displayName']`; TargetObjectId `outputs('Group_id')`; ResultJson `string(setProperty(setProperty(json('{}'), 'groupId', outputs('Group_id')), 'groupDisplayName', variables('varGroup')?['displayName']))` |
| 7 | `Catch` | Scope, **Run after** `Try`: has failed + has timed out | `Failed actions` (Filter array: From `result('Try')`; `item()?['status']` is equal to `Failed`) → `Error text` (Compose: `concat(first(body('Failed_actions'))?['name'], ': ', coalesce(first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], first(body('Failed_actions'))?['error']?['message'], 'see the ER-04 run history'))`) → `Mark failed` (Update item: Status `Failed`, ErrorMessage `outputs('Error_text')`) |

Every *Fail …* action is a SharePoint **Update item** on EntraRequests (Id `int(triggerOutputs()?['body/ID'])`, Title `triggerOutputs()?['body/Title']`, **Status Value** `Failed`, ErrorMessage as given) followed by a **Terminate** with Status **Failed**. The app shows that ErrorMessage to the user.

Catalog row fields (6.11):

| Column | Value (fx) |
|---|---|
| Title | `variables('varGroup')?['displayName']` |
| GroupId | `outputs('Group_id')` |
| Description | `variables('varGroup')?['description']` |
| AppCatId | `if(contains(coalesce(variables('varGroup')?['description'], ''), '[appCatID='), first(split(last(split(variables('varGroup')?['description'], '[appCatID=')), ';')), '')` |
| MemberUpns | `concat(';', join(body('Select_member_upns'), ';'), ';')` |
| OwnerUpns | `concat(';', join(body('Select_owner_upns'), ';'), ';')` |
| LastSynced | `utcNow()` |

---

## Ownership check (shared by ER-02, ER-05, ER-06)

An app registration belongs to whoever its **team tag** names. The platform never adds owners to the app registration itself.

| Team tag | Who may change the app |
|---|---|
| `team:user\<user object id>` | That user. Written when an app is created **without** an owning group. |
| `team:group\<group object id>` | Every member of that group (nested membership counts). Written when an owning group is chosen, or by ER-06. |
| `team:<group object id>` | Same as `team:group\…`: the format apps created by 1.2 carry. |

The backslash is a literal character: in expressions, `'team:user\'` is a normal string (Power Automate doesn't treat `\` as an escape).

With a prefix `<P>` (e.g. `App`), the tags expression `<tags>`, the requester's object id `<user>` and a String variable `<flag>` initialized to `no`:

| Action | Type | Configuration |
|---|---|---|
| `<P> team tags` | Filter array | From `coalesce(<tags>, json('[]'))`; condition `startsWith(item(), 'team:')` is equal to `true` |
| `<P> group values` | Select | From `body('<P>_team_tags')`; Map in text mode `if(startsWith(item(), 'team:group\'), substring(item(), 11), if(startsWith(item(), 'team:user\'), '', substring(item(), 5)))` |
| `<P> group ids` | Filter array | From `body('<P>_group_values')`; condition `not(empty(item()))` is equal to `true` |
| `Reset <flag> <P>` | Set variable | `<flag>` = *plain text* `no` |
| `<P> has team groups` | Condition | `length(body('<P>_group_ids'))` is greater than `0`. **If yes:** `HTTP <P> check groups` (Graph: `POST` `https://graph.microsoft.com/v1.0/users/@{<user>}/checkMemberGroups`; Body `{"groupIds": @{take(body('<P>_group_ids'), 20)}}`) → `<P> member of a team group` (Condition: `length(body('HTTP_<P>_check_groups')?['value'])` is greater than `0`; **If yes:** `Set <flag> <P>` = *plain text* `yes`) |

**Owner expression** (used in the next condition): `or(contains(body('<P>_team_tags'), concat('team:user\', toLower(<user>))), equals(variables('<flag>'), 'yes'))`

---

## ER-05 Find app (Premium)

Behind the **Search** button on the change screen. The requester types the app registration's **Application (client) ID or Object ID**; ER-05 finds the app and returns its details **only if the requester is its authorized owner** (ownership check above). Otherwise the request fails with *Not authorized owner*, which the app shows. Read-only in Entra; no approval. These `lookupApp` items are hidden from *My requests*.

**+ Create → Automated cloud flow** → `ER-05 Find app` → **SharePoint – When an item is created** (EntraRequests). Trigger condition: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), equals(triggerOutputs()?['body/RequestType/Value'], 'lookupApp'))`

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Mark in progress` | Update item | Status `InProgress` |
| 2 | `Requester` | Compose | `toLower(last(split(triggerOutputs()?['body/Author/Claims'], '\|')))` |
| 3 | `App query` | Compose | `toLower(trim(coalesce(triggerOutputs()?['body/TargetDisplayName'], triggerOutputs()?['body/TargetObjectId'], '')))` |
| 4 | `Init varApp` / `Init varGroupOwner` | Initialize variable ×2 | `varApp` Object `{}`; `varGroupOwner` String `no` |
| 5 | `Try` | Scope | 5.1–5.9 |
| 5.1 | `Query is a GUID` | Condition | `and(equals(length(outputs('App_query')), 36), equals(length(split(outputs('App_query'), '-')), 5))` is equal to `true`. **If no:** `Fail not a GUID` → `Stop not a GUID` |
| 5.2 | `HTTP Get requester` | Graph | `GET` `https://graph.microsoft.com/v1.0/users/@{outputs('Requester')}?$select=id` |
| 5.3 | *Find the app* | | `HTTP App by appId` (Graph: `GET` `https://graph.microsoft.com/v1.0/applications?$filter=appId eq '@{outputs('App_query')}'&$select=id,appId,displayName,tags,identifierUris,appRoles,api`) → `App found by appId` (Condition: `empty(body('HTTP_App_by_appId')?['value'])` is equal to `false`; **If yes:** `Set App from appId` (`varApp` = `first(body('HTTP_App_by_appId')?['value'])`); **If no:** `HTTP App by object id` (same with `$filter=id eq '…'`) → `App found by object id` (**If yes:** `Set App from object id`; **If no:** `Fail app not found` with ErrorMessage `concat('No app registration has the Application (client) ID or Object ID ', outputs('App_query'), '.')` → `Stop app not found`)) |
| 5.4 | *Ownership check* | | Prefix `App`, tags `variables('varApp')?['tags']`, user `body('HTTP_Get_requester')?['id']`, flag `varGroupOwner` |
| 5.5 | `Requester is owner` | Condition | the owner expression is equal to `true`. **If no:** `Fail not owner` with ErrorMessage `concat('Not authorized owner: ', variables('varApp')?['displayName'], ' is tagged ', coalesce(first(body('App_team_tags')), 'with no team'), '. Only that user, or a member of that group, can use it here.')` → `Stop not owner` |
| 5.6 | `HTTP Find SP` | Graph | `GET` `https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '@{variables('varApp')?['appId']}'&$select=id` |
| 5.7 | `Filter appcat tag`, `Filter team name tag`, `App catid` | Filter array ×2, Compose | tags starting with `appCatID:` / `teamName:`; `App catid` = `if(empty(body('Filter_appcat_tag')), '', substring(first(body('Filter_appcat_tag')), 9))` |
| 5.8 | `Result` | Compose | Object with `objectId`, `appId`, `displayName`, `appCatId`, `team` (the team tag), `teamName`, `identifierUri`, `servicePrincipalId`, and `appRolesJson` / `scopesJson` as **strings** (`string(coalesce(variables('varApp')?['appRoles'], json('[]')))`, `string(coalesce(variables('varApp')?['api']?['oauth2PermissionScopes'], json('[]')))`) |
| 5.9 | `Mark completed` | Update item | Status `Completed`; CompletedAt `utcNow()`; TargetDisplayName = app name; TargetObjectId = app object id; AppCatId `outputs('App_catid')`; ResultJson `string(outputs('Result'))` |
| 6 | `Catch` | Scope, run after `Try` failed / timed out | As in ER-04 (Failed actions → Error text → Mark failed) |

## ER-06 Tag owning group (Premium)

Behind the **Owning group** card. Replaces an app registration's team tag with `team:group\<group id>`, on the app registration and on its enterprise app. Allowed only when the requester is the app's **authorized owner** (the user in `team:user\…`, or a member of the group in its current tag) **and** a member or owner of the new group, which must be a security group. Anyone else gets *Not authorized owner*. No approval.

The app writes `PayloadJson` = `{"app": "<app id>", "group": "<group object id>"}`.

**+ Create → Automated cloud flow** → `ER-06 Tag owning group` → **SharePoint – When an item is created** (EntraRequests). Trigger condition: `@and(equals(triggerOutputs()?['body/Status/Value'], 'Submitted'), equals(triggerOutputs()?['body/RequestType/Value'], 'tagOwnerGroup'))`

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Mark in progress` | Update item | Status `InProgress` |
| 2 | `Requester`, `Payload`, `App query`, `Group query`, `Now` | Compose ×5 | `Payload` = `json(coalesce(triggerOutputs()?['body/PayloadJson'], '{}'))`; `App query` = `toLower(trim(coalesce(outputs('Payload')?['app'], triggerOutputs()?['body/TargetObjectId'], '')))`; `Group query` = `toLower(trim(coalesce(outputs('Payload')?['group'], '')))`; `Now` = `utcNow()` |
| 3 | `Init varApp` / `Init varGroupOwner` | Initialize variable ×2 | as ER-05 |
| 4 | `Try` | Scope | 4.1–4.13 |
| 4.1 | `Inputs are GUIDs` | Condition | both queries are 36 characters with 5 dash-separated parts. **If no:** `Fail not GUIDs` → `Stop not GUIDs` |
| 4.2–4.4 | `HTTP Get requester`, *find the app*, *ownership check*, `Requester is owner` | | exactly as ER-05 steps 5.2–5.5 |
| 4.5 | `HTTP Get group` | Graph | `GET` `https://graph.microsoft.com/v1.0/groups/@{outputs('Group_query')}?$select=id,displayName,securityEnabled`; Retry policy **None** |
| 4.6 | `Group found` | Condition, run after `HTTP Get group` succeeded + failed | `outputs('HTTP_Get_group')?['statusCode']` is equal to `200`. **If no:** `Fail group not found` → `Stop group not found` |
| 4.7 | `Group security enabled` | Condition | `body('HTTP_Get_group')?['securityEnabled']` is equal to **fx** `true`. **If no:** `Fail not security` → `Stop not security` |
| 4.8 | `HTTP Check new group`, `HTTP New group owners`, `Member of new group` | Graph ×2, Condition | checkMemberGroups for the new group, and its owners; condition `or(not(empty(body('HTTP_Check_new_group')?['value'])), contains(string(body('HTTP_New_group_owners')?['value']), body('HTTP_Get_requester')?['id']))`. **If no:** `Fail not in group` → `Stop not in group` |
| 4.9 | `Kept app tags` | Filter array | From `coalesce(variables('varApp')?['tags'], json('[]'))`; condition `not(or(startsWith(item(), 'team:'), startsWith(item(), 'teamName:'), startsWith(item(), 'lastUpdatedBy:'), startsWith(item(), 'lastUpdatedTimestamp:'), startsWith(item(), 'requestId:')))` |
| 4.10 | `Team tags`, `New app tags` | Compose ×2 | `createArray(concat('team:group\', body('HTTP_Get_group')?['id']), concat('teamName:', body('HTTP_Get_group')?['displayName']))`; `union(body('Kept_app_tags'), outputs('Team_tags'), createArray(concat('lastUpdatedBy:', outputs('Requester')), concat('lastUpdatedTimestamp:', outputs('Now')), concat('requestId:', triggerOutputs()?['body/Title'])))` |
| 4.11 | `HTTP Patch app tags` | Graph | `PATCH` `https://graph.microsoft.com/v1.0/applications/@{variables('varApp')?['id']}`; Body `{"tags": @{outputs('New_app_tags')}}` |
| 4.12 | `HTTP Find SP`, `Has SP` | Graph, Condition | `GET …/servicePrincipals?$filter=appId eq '…'&$select=id,tags`; if one exists: `Kept SP tags` (its tags not starting with `team:` / `teamName:`) → `HTTP Patch SP tags` (`PATCH …/servicePrincipals/{id}`, Body `{"tags": @{union(body('Kept_SP_tags'), outputs('Team_tags'))}}`) |
| 4.13 | `Mark completed` | Update item | Status `Completed`; TargetDisplayName / TargetObjectId = the app; ResultJson with `applicationObjectId`, `appId`, `previousTeam`, `groupId`, `groupDisplayName` |
| 5 | `Catch` | Scope | As in ER-04 |

---

## ER-07 Requeue approved (Standard)

Re-saves requests that are **Approved** but were never executed, as the flow account, so ER-02 picks them up. Only people listed in `EntraApproverEmails` may run it. Setup and use: [doc 09 §9.7](09-SOLUTION-IMPORT.md#97-requeue-approved-requests-er-07).

**+ Create → Instant cloud flow** → `ER-07 Requeue approved` → **Manually trigger a flow** → **+ Add an input → Text**: *Request ID (optional)*.

| # | Action (name) | Type | Configuration |
|---|---|---|---|
| 1 | `Get settings` | SharePoint – Get item | List `EntraSettings`; Id `1` |
| 2 | `Runner` | Compose | `toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))` (the signed-in user who pressed Run) |
| 3 | `Entra team` | Compose | `concat(';', toLower(replace(replace(replace(replace(body('Get_settings')?['EntraApproverEmails'], decodeUriComponent('%0D'), ''), decodeUriComponent('%0A'), ';'), ',', ';'), ' ', '')), ';')` |
| 4 | `Runner is in the Entra ID team` | Condition | `and(not(empty(outputs('Runner'))), contains(outputs('Entra_team'), concat(';', outputs('Runner'), ';')))` is equal to `true`. **If no:** `Stop not authorized` (Terminate: **Failed**, Code `NotAuthorized`, Message `Not authorized: only the people listed in EntraSettings.EntraApproverEmails can requeue requests.`) |
| 5 | `Request id` | Compose | `trim(coalesce(triggerBody()?['text'], ''))` |
| 6 | `Filter query` | Compose | `concat('Status eq ''Approved'' and ManagerDecision eq ''Approved'' and EntraDecision eq ''Approved''', if(empty(outputs('Request_id')), '', concat(' and Title eq ''', replace(outputs('Request_id'), '''', ''''''), '''')))` |
| 7 | `Get approved requests` | SharePoint – Get items | List `EntraRequests`; Filter Query `outputs('Filter_query')`; Top Count `500` |
| 8 | `Init varRequeued` / `Init varWrongEditor` | Initialize variable ×2 | Array `[]`; String empty |
| 9 | `Requeue each request` | Apply to each (concurrency 1) | From `body('Get_approved_requests')?['value']`: `Requeue item` (Update item: Id `items('Requeue_each_request')?['ID']`; Title `items('Requeue_each_request')?['Title']`; **Status Value** `Approved`; CompletionNotes `concat('Requeued by ', outputs('Runner'), ' at ', utcNow(), ' (ER-07). Waiting for ER-02.')`) → `Record requeued` (append the Title to `varRequeued`) → `Edited as the flow account` (Condition: `toLower(last(split(coalesce(body('Requeue_item')?['Editor']?['Claims'], ''), '\|')))` is equal to `toLower(body('Get_settings')?['ServiceAccountUpn'])`; **If no:** `Set wrong editor`) |
| 10 | `Mail summary` | Send an email (V2) | To `outputs('Runner')`: the requeued Request IDs, or a warning when the items were saved by someone other than the flow account (run-only connection set to *Provided by run-only user*) |

The re-save is what ER-02 needs: its trigger sees a modified item with Status = Approved, and its guard sees the flow account as the last editor.

---

## Graph calls at a glance

| Step | Request |
|---|---|
| requester id | `GET /users/{upn}?$select=id` |
| team membership | `POST /users/{id}/checkMemberGroups {"groupIds":[…]}` |
| find a group | `GET /groups/{id}` or `GET /groups?$filter=displayName eq '…'` (ER-04) |
| new app | `POST /applications` (tags, notes, appRoles, web/spa, optionalClaims, groupMembershipClaims, api.requestedAccessTokenVersion=2) |
| App ID URI + scopes | `PATCH /applications/{id}` (identifierUris, api.oauth2PermissionScopes) |
| enterprise app | `POST /servicePrincipals` (retried for ~60 s while the new app replicates) |
| role assignment | `POST /servicePrincipals/{spId}/appRoleAssignedTo {principalId, resourceId, appRoleId}` |
| catalog | `GET /applications?$filter=tags/any(...)`, `GET /groups/{id}/transitiveMembers`, `GET …/owners` |
