<#
.SYNOPSIS
  Creates the four SharePoint lists used by the Entra self-service Power App and flows.

    EntraRequests        one item per request (written by the app, then owned by the flows)
    EntraCatalogApps     app registrations the platform manages   (written by flow ER-03)
    EntraCatalogGroups   groups users can pick for roles / teams  (written by flows ER-02 / ER-03)
    EntraSettings        ONE item: tenant id, Graph app id, approvers, service account...

  Idempotent: re-run safely; existing lists/columns are left as they are.

.EXAMPLE
  Install-Module PnP.PowerShell -Scope CurrentUser        # PowerShell 7.4+
  ./provision.ps1 -SiteUrl https://contoso.sharepoint.com/sites/entra-selfservice -ClientId <PnP app id> `
      -TenantId <tenant guid> -GraphClientId <entra-pp-graph appId> -ServiceAccountUpn svc-entra-flows@contoso.com `
      -EntraApproverEmails "alice@contoso.com;bob@contoso.com" -FallbackApproverEmail "entra-lead@contoso.com"

.NOTES
  Run as a site owner. PnP.PowerShell 2.x needs your own Entra app for interactive login:
  Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP PowerShell" -Tenant contoso.onmicrosoft.com
#>
param(
  [Parameter(Mandatory)] [string] $SiteUrl,
  [Parameter(Mandatory)] [string] $ClientId,
  [string] $TenantId = "",
  [string] $GraphClientId = "",
  [string] $ServiceAccountUpn = "",
  [string] $EntraApproverEmails = "",
  [string] $FallbackApproverEmail = "",
  [string] $ManagedByTag = "entra-pp",
  [string] $KeyVaultName = "",
  [string] $PowerAppUrl = ""
)
$ErrorActionPreference = "Stop"
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

function Ensure-List([string] $title, [string] $description) {
  $list = Get-PnPList -Identity $title -ErrorAction SilentlyContinue
  if (-not $list) {
    $list = New-PnPList -Title $title -Template GenericList -EnableVersioning
    Write-Host "Created list $title"
  }
  Set-PnPList -Identity $title -Description $description -EnableVersioning $true -MajorVersions 500 | Out-Null
  return $list
}

# Type: Text | Note | Choice | DateTime | Number | Boolean
function Ensure-Field([string] $list, [string] $name, [string] $type, [string[]] $choices = @(), [bool] $indexed = $false, [string] $default = "") {
  if (-not (Get-PnPField -List $list -Identity $name -ErrorAction SilentlyContinue)) {
    switch ($type) {
      "Note" {
        # Plain text, no "append changes": JSON and text written by the app and the flows.
        Add-PnPFieldFromXml -List $list -FieldXml "<Field Type='Note' Name='$name' StaticName='$name' DisplayName='$name' NumLines='6' RichText='FALSE' AppendOnly='FALSE' UnlimitedLengthInDocumentLibrary='TRUE' />" | Out-Null
      }
      "Choice" {
        $f = Add-PnPField -List $list -InternalName $name -DisplayName $name -Type Choice -Choices $choices -AddToDefaultView
        if ($default) { Set-PnPField -List $list -Identity $name -Values @{ DefaultValue = $default } | Out-Null }
      }
      "DateTime" {
        Add-PnPFieldFromXml -List $list -FieldXml "<Field Type='DateTime' Name='$name' StaticName='$name' DisplayName='$name' Format='DateTime' />" | Out-Null
      }
      default { Add-PnPField -List $list -InternalName $name -DisplayName $name -Type $type -AddToDefaultView | Out-Null }
    }
    Write-Host "  + $list.$name ($type)"
  }
  if ($indexed) { Set-PnPField -List $list -Identity $name -Values @{ Indexed = $true } | Out-Null }
}

# ---------------------------------------------------------------------------
# 1. EntraRequests
# ---------------------------------------------------------------------------
$R = "EntraRequests"
Ensure-List $R "Entra self-service requests. Requester = Created By. Status/decisions/results are written only by the flows." | Out-Null
Set-PnPField -List $R -Identity "Title" -Values @{ Title = "RequestId"; Indexed = $true } | Out-Null

$types    = "createAppRegistration","exposeApi","addAppRoles","assignGroupsToAppRoles","createServicePrincipal","createGroup"
$statuses = "Submitted","PendingManagerApproval","PendingEntraApproval","Approved","InProgress","Completed","Failed","Rejected"
$decision = "Pending","Approved","Rejected"

Ensure-Field $R "RequestType"         "Choice"   $types    $true
Ensure-Field $R "Status"              "Choice"   $statuses $true "Submitted"
Ensure-Field $R "AppCatId"            "Text"     @() $true
Ensure-Field $R "TargetDisplayName"   "Text"
Ensure-Field $R "TargetObjectId"      "Text"
Ensure-Field $R "Justification"       "Note"
Ensure-Field $R "TicketReference"     "Text"
Ensure-Field $R "PayloadJson"         "Note"
Ensure-Field $R "ApprovedPayloadJson" "Note"
Ensure-Field $R "RequestSummary"      "Note"
Ensure-Field $R "ManagerEmail"        "Text"
Ensure-Field $R "ManagerName"         "Text"
Ensure-Field $R "ManagerDecision"     "Choice"   $decision $false "Pending"
Ensure-Field $R "ManagerDecisionBy"   "Text"
Ensure-Field $R "ManagerDecisionAt"   "DateTime"
Ensure-Field $R "ManagerComment"      "Note"
Ensure-Field $R "EntraDecision"       "Choice"   $decision $false "Pending"
Ensure-Field $R "EntraDecisionBy"     "Text"
Ensure-Field $R "EntraDecisionAt"     "DateTime"
Ensure-Field $R "EntraComment"        "Note"
Ensure-Field $R "ResultJson"          "Note"
Ensure-Field $R "ErrorMessage"        "Note"
Ensure-Field $R "CompletedAt"         "DateTime"

# Item-level permissions: people see and edit only their own items (the flow then locks
# each item to read-only for its requester). Site owners still see everything.
$list = Get-PnPList -Identity $R
$list.ReadSecurity  = 2   # Read items that were created by the user
$list.WriteSecurity = 2   # Create items and edit items that were created by the user
$list.Update(); Invoke-PnPQuery

# ---------------------------------------------------------------------------
# 2. EntraCatalogApps  (flow ER-03 keeps it in sync with Entra)
# ---------------------------------------------------------------------------
$A = "EntraCatalogApps"
Ensure-List $A "App registrations managed by the platform. Written only by flow ER-03 (sync) and ER-02 (execute)." | Out-Null
Set-PnPField -List $A -Identity "Title" -Values @{ Title = "DisplayName" } | Out-Null
Ensure-Field $A "ObjectId"           "Text" @() $true
Ensure-Field $A "AppId"              "Text" @() $true
Ensure-Field $A "AppCatId"           "Text" @() $true
Ensure-Field $A "TeamGroupId"        "Text"
Ensure-Field $A "TeamGroupName"      "Text"
Ensure-Field $A "ServicePrincipalId" "Text"
Ensure-Field $A "IdentifierUri"      "Text"
Ensure-Field $A "AppRolesJson"       "Note"
Ensure-Field $A "ScopesJson"         "Note"
Ensure-Field $A "TeamMemberUpns"     "Note"   # ";a@contoso.com;b@contoso.com;"  (lower-case, ; at both ends)
Ensure-Field $A "OwnerUpns"          "Note"
Ensure-Field $A "LastSynced"         "DateTime"

# ---------------------------------------------------------------------------
# 3. EntraCatalogGroups
# ---------------------------------------------------------------------------
$G = "EntraCatalogGroups"
Ensure-List $G "Security groups users may pick for owning teams and role assignments. Add a row with just GroupId to onboard an existing group; ER-03 fills the rest." | Out-Null
Set-PnPField -List $G -Identity "Title" -Values @{ Title = "DisplayName" } | Out-Null
Ensure-Field $G "GroupId"     "Text" @() $true
Ensure-Field $G "AppCatId"    "Text"
Ensure-Field $G "Description" "Note"
Ensure-Field $G "OwnerUpns"   "Note"
Ensure-Field $G "MemberUpns"  "Note"
Ensure-Field $G "LastSynced"  "DateTime"

# ---------------------------------------------------------------------------
# 4. EntraSettings  (exactly one item, ID 1)
# ---------------------------------------------------------------------------
$S = "EntraSettings"
Ensure-List $S "Configuration for the flows. Keep exactly ONE item." | Out-Null
foreach ($f in "TenantId","GraphClientId","ManagedByTag","ServiceAccountUpn","FallbackApproverEmail","KeyVaultName","PfxSecretName","PfxPasswordSecretName","PowerAppUrl") { Ensure-Field $S $f "Text" }
Ensure-Field $S "EntraApproverEmails" "Note"
if (-not (Get-PnPListItem -List $S -PageSize 1)) {
  Add-PnPListItem -List $S -Values @{
    Title = "settings"; TenantId = $TenantId; GraphClientId = $GraphClientId; ManagedByTag = $ManagedByTag
    ServiceAccountUpn = $ServiceAccountUpn.ToLower(); EntraApproverEmails = $EntraApproverEmails; FallbackApproverEmail = $FallbackApproverEmail
    KeyVaultName = $KeyVaultName; PfxSecretName = "entra-pp-graph-pfx"; PfxPasswordSecretName = "entra-pp-graph-pfx-password"; PowerAppUrl = $PowerAppUrl
  } | Out-Null
  Write-Host "Created the EntraSettings item"
}

# ---------------------------------------------------------------------------
# Permissions on the catalog and settings lists: read-only for everyone but owners.
# ---------------------------------------------------------------------------
$web = Get-PnPWeb -Includes AssociatedMemberGroup, AssociatedVisitorGroup
foreach ($l in $A, $G) {
  Set-PnPList -Identity $l -BreakRoleInheritance -CopyRoleAssignments | Out-Null
  Set-PnPListPermission -Identity $l -Group $web.AssociatedMemberGroup.Title -RemoveRole "Edit" -ErrorAction SilentlyContinue
  Set-PnPListPermission -Identity $l -Group $web.AssociatedMemberGroup.Title -AddRole "Read"
}
Set-PnPList -Identity $S -BreakRoleInheritance | Out-Null   # owners only

Write-Host ""
Write-Host "Done. Next:"
Write-Host "  - Members group: Contribute on the SITE (they need it to create items in $R; item-level security limits them to their own)."
Write-Host "  - Make the flow service account ($ServiceAccountUpn) a site OWNER (it breaks item permissions and writes every list)."
Write-Host "  - Add the Entra ID team to the site Owners group (they see all requests)."
