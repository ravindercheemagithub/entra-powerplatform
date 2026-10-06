# 2. SharePoint: site, lists and permissions

## 2.1 Site

Create a **team site** (Microsoft 365 group) or a communication site, e.g. `https://contoso.sharepoint.com/sites/entra-selfservice`.

| Who | Site permission | Why |
|---|---|---|
| `svc-entra-flows` | **Owner** | the flows write every list and break per-item permissions |
| Entra ID team | **Owner** | see and fix every request |
| Everyone who may raise requests (e.g. *Everyone except external users*) | **Member** (Edit/Contribute) | the app creates items in `EntraRequests`; item-level security limits them to their own |

## 2.2 Lists: script

`sharepoint/provision.ps1` (PnP PowerShell) creates all four lists with their columns, indexes, versioning, permissions and the EntraSettings item. It is safe to re-run:

| The list... | What the script does |
|---|---|
| doesn't exist | creates it with all columns, settings and permissions |
| already exists | **skips it** and changes nothing; reports any expected columns it cannot find. `-AddMissingColumns` adds only those columns. |
| EntraSettings has no item | creates the settings item; an existing item is never changed |

`-CheckOnly` reports what exists and what is missing, and changes nothing.

### Before you run it: a PnP app registration

PnP PowerShell signs in through an Entra app registration of your own. An Entra admin creates it once (you need it only for this script):

- **Option 1, PowerShell (admin):** `Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP PowerShell" -Tenant <tenant>.onmicrosoft.com -DeviceLogin`
- **Option 2, Entra admin center (admin):**
  1. App registrations → New registration, name `PnP PowerShell`, single tenant. Under Redirect URI choose **Public client/native (mobile & desktop)** with `http://localhost`.
  2. **Authentication** → *Allow public client flows* = **Yes**. Cloud Shell's device-code sign-in needs this.
  3. **API permissions** → Add → **SharePoint** → Delegated → `AllSites.FullControl` → **Grant admin consent**.

The admin sends you the **Application (client) ID**. The script still acts with **your** SharePoint rights, so you must be a **site owner**. Without this app registration, create the lists by hand (2.3).

### Run it in Azure Cloud Shell (no storage needed)

1. Open https://shell.azure.com, or the Cloud Shell icon in the Azure portal, and choose **PowerShell**.
2. If asked about storage, choose **No storage account required** (an *ephemeral session*), and pick any subscription if one is required. Files and installed modules last only for the session, which is fine here.
3. Get the script into the session. Either:
   - **Upload:** toolbar **Manage files → Upload** → pick `sharepoint/provision.ps1` (download it from GitHub first: open the file → **Download raw file**). It lands in your home folder.
   - **Or download it directly**, using a GitHub personal access token (the repo is private):
     ```bash
     curl -H "Authorization: token <your PAT>" -o provision.ps1 https://raw.githubusercontent.com/ravindercheemagithub/entra-powerplatform/main/sharepoint/provision.ps1
     ```
4. Install PnP PowerShell (each new session):
   ```powershell
   Install-Module PnP.PowerShell -Scope CurrentUser -Force
   ```
5. Check first, without changing anything:
   ```powershell
   ./provision.ps1 -SiteUrl https://<tenant>.sharepoint.com/teams/m365automationqa -ClientId <PnP app id> -Tenant <tenant>.onmicrosoft.com -DeviceLogin -CheckOnly
   ```
   It prints a code. Open https://microsoft.com/devicelogin in your browser, enter the code, and sign in as yourself (a site owner).
6. Run it for real. Values you don't have yet can stay empty and be typed into the EntraSettings item later:
   ```powershell
   ./provision.ps1 -SiteUrl https://<tenant>.sharepoint.com/teams/m365automationqa `
     -ClientId <PnP app id> -Tenant <tenant>.onmicrosoft.com -DeviceLogin `
     -TenantId <directory tenant GUID> -GraphClientId <platform app client ID> `
     -ServiceAccountUpn <flow account UPN> `
     -EntraApproverEmails "alice@contoso.com;bob@contoso.com" -FallbackApproverEmail "lead@contoso.com" `
     -PowerAppUrl "https://<tenant>.sharepoint.com/teams/m365automationqa/Lists/EntraRequests"
   ```
7. Read the summary: *created*, *already existed (skipped)*, and any missing columns. If it reports missing columns on an existing list, re-run with `-AddMissingColumns`.

Each line of output starts with a marker: `+` created, `=` already there and left unchanged, `-` would be created (check only), `!` needs your attention (e.g. EntraSettings item is not ID 1).

### Run it locally instead

With PowerShell 7.4+ and a browser on your machine, drop `-Tenant` and `-DeviceLogin`, and a browser sign-in window opens:

```powershell
./provision.ps1 -SiteUrl https://<tenant>.sharepoint.com/teams/m365automationqa -ClientId <PnP app id> -ServiceAccountUpn <flow account UPN>
```

## 2.3 Lists: by hand

**Internal names matter.** The app and flows use internal names. Create each column with exactly the name shown (no spaces), then change the display name if you like. *Multiple lines of text* columns must be **Plain text**, with *Append changes to existing text* = **No**.

### EntraRequests: one item per request

| Column | Type | Notes |
|---|---|---|
| Title | (built-in) | rename display name to *RequestId*; `REQ-2610-K7M4X2`; **index** it |
| RequestType | Choice | `createAppRegistration`, `exposeApi`, `addAppRoles`, `assignGroupsToAppRoles`, `createServicePrincipal`, `createGroup`; **index** |
| Status | Choice | `Submitted` (default), `PendingManagerApproval`, `PendingEntraApproval`, `Approved`, `InProgress`, `Completed`, `Failed`, `Rejected`; **index** |
| AppCatId | Single line | **index** |
| TargetDisplayName | Single line | the app / group name |
| TargetObjectId | Single line | object ID of the existing app (change requests) |
| Justification | Multiple lines (plain) | |
| TicketReference | Single line | |
| PayloadJson | Multiple lines (plain) | written by the app |
| ApprovedPayloadJson | Multiple lines (plain) | snapshot taken by ER-01 after the item is locked; **the only payload ER-02 executes** |
| RequestSummary | Multiple lines (plain) | text sent to approvers |
| ManagerEmail, ManagerName | Single line | |
| ManagerDecision | Choice | `Pending` (default), `Approved`, `Rejected` |
| ManagerDecisionBy | Single line | |
| ManagerDecisionAt | Date and Time (include time) | |
| ManagerComment | Multiple lines (plain) | |
| EntraDecision | Choice | `Pending` (default), `Approved`, `Rejected` |
| EntraDecisionBy | Single line | |
| EntraDecisionAt | Date and Time | |
| EntraComment | Multiple lines (plain) | |
| ResultJson | Multiple lines (plain) | IDs of everything created |
| ErrorMessage | Multiple lines (plain) | |
| CompletedAt | Date and Time | |

The requester is the built-in **Created By**. Users can't fake it, which is why nothing in the payload identifies the requester.

**List settings → Advanced settings → Item-level permissions:**
- Read access: **Read items that were created by the user**
- Create and Edit access: **Create items and edit items that were created by the user**

**Versioning:** on (500 versions). It is the audit trail of every status change.

### EntraCatalogApps: what the platform manages (written by ER-03 / ER-02)

| Column | Type | Notes |
|---|---|---|
| Title | (built-in) | display name of the app |
| ObjectId | Single line | **index** |
| AppId | Single line | **index** |
| AppCatId | Single line | **index** |
| TeamGroupId, TeamGroupName | Single line | from the `team` / `teamName` tags |
| ServicePrincipalId | Single line | empty = no enterprise app |
| IdentifierUri | Single line | first Application ID URI |
| AppRolesJson | Multiple lines (plain) | `[{"id":"…","value":"Orders.Admin",…}]` |
| ScopesJson | Multiple lines (plain) | |
| TeamMemberUpns | Multiple lines (plain) | `;alex@contoso.com;sam@contoso.com;` (lower-case, `;` at both ends) |
| OwnerUpns | Multiple lines (plain) | same format |
| LastSynced | Date and Time | |

### EntraCatalogGroups: groups users can pick

| Column | Type | Notes |
|---|---|---|
| Title | (built-in) | group display name |
| GroupId | Single line | **index**. To onboard an existing group, add a row with just GroupId and Title; ER-03 fills in the rest. |
| AppCatId | Single line | parsed from the description |
| Description | Multiple lines (plain) | |
| OwnerUpns, MemberUpns | Multiple lines (plain) | `;upn;upn;` |
| LastSynced | Date and Time | |

### EntraSettings: exactly one item (ID 1)

| Column | Example |
|---|---|
| Title | `settings` |
| TenantId | `5a5ab110-…` |
| GraphClientId | appId of `entra-pp-graph` |
| ManagedByTag | `entra-pp` |
| ServiceAccountUpn | `svc-entra-flows@contoso.com` (lower-case) |
| EntraApproverEmails (multi-line) | `alice@contoso.com;bob@contoso.com` |
| FallbackApproverEmail | `entra-lead@contoso.com` (when the requester has no manager in Entra) |
| KeyVaultName | `kv-entra-pp` |
| PfxSecretName | `entra-pp-graph-pfx` |
| PfxPasswordSecretName | `entra-pp-graph-pfx-password` |
| PowerAppUrl | the app's *Web link* (from Power Apps → app details) |

### Permissions on the other lists
- `EntraCatalogApps`, `EntraCatalogGroups`: stop inheriting; Members **Read**; Owners Full control.
- `EntraSettings`: stop inheriting; Owners only. Users never read it; the flows read it as the service account.

## 2.4 How a request is protected

1. A user creates the item through the app. Item-level security means only they (and site owners) can see it.
2. Seconds later ER-01 **breaks the item's permissions**: the requester becomes **read-only**, and Owners keep full control. The user can no longer edit their payload, status or decisions.
3. ER-01 copies `PayloadJson` into `ApprovedPayloadJson` after locking. Approvers see the summary of that snapshot, and ER-02 executes only it.
4. ER-02 runs only when `Status = Approved`, **and** both decisions are `Approved`, **and** the last editor is the service account. If a site owner edits the status by hand, nothing executes.

## 2.5 Seed the catalog (optional, first day)

ER-03 discovers apps tagged `managedBy:entra-pp`. Before any app exists, users can still:
- create a **new** team group from the wizard, or
- use groups you add to `EntraCatalogGroups`. Add rows with `Title` + `GroupId` for existing team groups, then run ER-03 once (*Run* on its manual trigger) to fill in members and owners.
