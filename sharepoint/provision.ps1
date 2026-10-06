<#
.SYNOPSIS
  Creates the four SharePoint lists used by the Entra self-service Power App and flows.

    EntraRequests        one item per request (written by the app, then owned by the flows)
    EntraCatalogApps     app registrations the platform manages   (written by flows ER-02 / ER-03)
    EntraCatalogGroups   groups users can pick for roles / teams  (written by flows ER-02 / ER-03)
    EntraSettings        ONE item: tenant id, Graph app id, approvers, service account...

  Safe to re-run:
    - A list that does not exist is created with all its columns, settings and permissions.
    - A list that already exists is SKIPPED: nothing about it is changed. The script reports
      any columns it expects but cannot find. Add -AddMissingColumns to add just those columns
      (existing columns, settings and permissions are still left alone).
    - The EntraSettings item is created only if the list has no items.
    - -CheckOnly reports what exists and what is missing, and changes nothing.

.EXAMPLE
  # Azure Cloud Shell (no browser pop-up): sign in with a device code
  Install-Module PnP.PowerShell -Scope CurrentUser -Force
  ./provision.ps1 -SiteUrl https://contoso.sharepoint.com/teams/m365automationqa `
      -ClientId <PnP app id> -Tenant contoso.onmicrosoft.com -DeviceLogin `
      -TenantId <tenant guid> -GraphClientId <platform app id> -ServiceAccountUpn you@contoso.com `
      -EntraApproverEmails "alice@contoso.com;bob@contoso.com" -FallbackApproverEmail "lead@contoso.com" `
      -PowerAppUrl "https://contoso.sharepoint.com/teams/m365automationqa/Lists/EntraRequests"

.EXAMPLE
  # Local PowerShell 7.4+ with a browser: interactive sign-in
  ./provision.ps1 -SiteUrl https://contoso.sharepoint.com/teams/m365automationqa -ClientId <PnP app id>

.EXAMPLE
  # Report only
  ./provision.ps1 -SiteUrl ... -ClientId ... -Tenant ... -DeviceLogin -CheckOnly

.NOTES
  Run as a SITE OWNER. PnP.PowerShell needs an Entra app registration of your own for sign-in
  (delegated SharePoint AllSites.FullControl, admin-consented; "Allow public client flows" = Yes
  for -DeviceLogin). An admin can create one with:
    Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP PowerShell" -Tenant contoso.onmicrosoft.com -DeviceLogin
#>
param(
  [Parameter(Mandatory)] [string] $SiteUrl,
  [Parameter(Mandatory)] [string] $ClientId,
  [string] $Tenant = "",                 # contoso.onmicrosoft.com or tenant GUID; required with -DeviceLogin
  [switch] $DeviceLogin,                 # use in Azure Cloud Shell
  [switch] $CheckOnly,                   # report only, change nothing
  [switch] $AddMissingColumns,           # add expected columns missing from lists that already exist
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

if ($DeviceLogin) {
  if (-not $Tenant) { throw "-DeviceLogin needs -Tenant (e.g. contoso.onmicrosoft.com or the tenant GUID)." }
  Connect-PnPOnline -Url $SiteUrl -ClientId $ClientId -Tenant $Tenant -DeviceLogin
} else {
  Connect-PnPOnline -Url $SiteUrl -ClientId $ClientId -Interactive
}
Write-Host "Connected to $SiteUrl" -ForegroundColor Cyan
if ($CheckOnly) { Write-Host "CHECK ONLY: nothing will be changed." -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# Expected schema
#   Type: Text | Note | Choice | DateTime
# ---------------------------------------------------------------------------
$types    = "createAppRegistration","exposeApi","addAppRoles","assignGroupsToAppRoles","createServicePrincipal","createGroup"
$statuses = "Submitted","PendingManagerApproval","PendingEntraApproval","Approved","InProgress","Completed","Failed","Rejected"
$decision = "Pending","Approved","Rejected"

function F($name, $type, $choices = @(), $indexed = $false, $default = "") {
  [pscustomobject]@{ Name = $name; Type = $type; Choices = $choices; Indexed = $indexed; Default = $default }
}

$Lists = [ordered]@{
  "EntraRequests" = @{
    Description = "Entra self-service requests. Requester = Created By. Status/decisions/results are written only by the flows."
    TitleName   = "RequestId"; TitleIndexed = $true
    Fields = @(
      (F "RequestType" "Choice" $types $true),
      (F "Status" "Choice" $statuses $true "Submitted"),
      (F "AppCatId" "Text" @() $true),
      (F "TargetDisplayName" "Text"),
      (F "TargetObjectId" "Text"),
      (F "Justification" "Note"),
      (F "TicketReference" "Text"),
      (F "PayloadJson" "Note"),
      (F "ApprovedPayloadJson" "Note"),
      (F "RequestSummary" "Note"),
      (F "ManagerEmail" "Text"),
      (F "ManagerName" "Text"),
      (F "ManagerDecision" "Choice" $decision $false "Pending"),
      (F "ManagerDecisionBy" "Text"),
      (F "ManagerDecisionAt" "DateTime"),
      (F "ManagerComment" "Note"),
      (F "EntraDecision" "Choice" $decision $false "Pending"),
      (F "EntraDecisionBy" "Text"),
      (F "EntraDecisionAt" "DateTime"),
      (F "EntraComment" "Note"),
      (F "ResultJson" "Note"),
      (F "ErrorMessage" "Note"),
      (F "CompletedAt" "DateTime")
    )
  }
  "EntraCatalogApps" = @{
    Description = "App registrations managed by the platform. Written only by flows ER-02 (execute) and ER-03 (sync)."
    TitleName   = "DisplayName"; TitleIndexed = $false
    Fields = @(
      (F "ObjectId" "Text" @() $true),
      (F "AppId" "Text" @() $true),
      (F "AppCatId" "Text" @() $true),
      (F "TeamGroupId" "Text"),
      (F "TeamGroupName" "Text"),
      (F "ServicePrincipalId" "Text"),
      (F "IdentifierUri" "Text"),
      (F "AppRolesJson" "Note"),
      (F "ScopesJson" "Note"),
      (F "TeamMemberUpns" "Note"),      # ";a@contoso.com;b@contoso.com;"  (lower-case, ; at both ends)
      (F "OwnerUpns" "Note"),
      (F "LastSynced" "DateTime")
    )
  }
  "EntraCatalogGroups" = @{
    Description = "Security groups users may pick for owning teams and role assignments. Add a row with just Title and GroupId to onboard an existing group; ER-03 fills the rest."
    TitleName   = "DisplayName"; TitleIndexed = $false
    Fields = @(
      (F "GroupId" "Text" @() $true),
      (F "AppCatId" "Text"),
      (F "Description" "Note"),
      (F "OwnerUpns" "Note"),
      (F "MemberUpns" "Note"),
      (F "LastSynced" "DateTime")
    )
  }
  "EntraSettings" = @{
    Description = "Configuration for the flows. Keep exactly ONE item (ID 1)."
    TitleName   = ""; TitleIndexed = $false
    Fields = @(
      (F "TenantId" "Text"), (F "GraphClientId" "Text"), (F "ManagedByTag" "Text"),
      (F "ServiceAccountUpn" "Text"), (F "FallbackApproverEmail" "Text"), (F "KeyVaultName" "Text"),
      (F "PfxSecretName" "Text"), (F "PfxPasswordSecretName" "Text"), (F "PowerAppUrl" "Text"),
      (F "EntraApproverEmails" "Note")
    )
  }
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Add-ListField([string] $list, $f) {
  switch ($f.Type) {
    "Note" {
      # Plain text, no "append changes": JSON and text written by the app and the flows.
      Add-PnPFieldFromXml -List $list -FieldXml "<Field Type='Note' Name='$($f.Name)' StaticName='$($f.Name)' DisplayName='$($f.Name)' NumLines='6' RichText='FALSE' AppendOnly='FALSE' UnlimitedLengthInDocumentLibrary='TRUE' />" | Out-Null
    }
    "Choice" {
      Add-PnPField -List $list -InternalName $f.Name -DisplayName $f.Name -Type Choice -Choices $f.Choices -AddToDefaultView | Out-Null
      if ($f.Default) { Set-PnPField -List $list -Identity $f.Name -Values @{ DefaultValue = $f.Default } | Out-Null }
    }
    "DateTime" {
      Add-PnPFieldFromXml -List $list -FieldXml "<Field Type='DateTime' Name='$($f.Name)' StaticName='$($f.Name)' DisplayName='$($f.Name)' Format='DateTime' />" | Out-Null
    }
    default { Add-PnPField -List $list -InternalName $f.Name -DisplayName $f.Name -Type $f.Type -AddToDefaultView | Out-Null }
  }
  if ($f.Indexed) { Set-PnPField -List $list -Identity $f.Name -Values @{ Indexed = $true } | Out-Null }
  Write-Host "    + $($f.Name) ($($f.Type))"
}

function Get-MissingFields([string] $list, $fields) {
  $existing = (Get-PnPField -List $list | ForEach-Object { $_.InternalName })
  $fields | Where-Object { $existing -notcontains $_.Name }
}

$created = @(); $skipped = @(); $planned = @()

# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------
foreach ($name in $Lists.Keys) {
  $spec = $Lists[$name]
  $list = Get-PnPList -Identity $name -ErrorAction SilentlyContinue

  if ($list) {
    $missing = @(Get-MissingFields $name $spec.Fields)
    if ($missing.Count -eq 0) {
      Write-Host "= $name exists with all expected columns: skipped" -ForegroundColor Green
    } elseif ($AddMissingColumns -and -not $CheckOnly) {
      Write-Host "= $name exists: adding $($missing.Count) missing column(s), nothing else changed" -ForegroundColor Yellow
      foreach ($f in $missing) { Add-ListField $name $f }
    } else {
      Write-Host "= $name exists but is missing $($missing.Count) column(s): $(($missing | ForEach-Object Name) -join ', ')" -ForegroundColor Yellow
      Write-Host "    skipped. Re-run with -AddMissingColumns to add them." -ForegroundColor Yellow
    }
    $skipped += $name
    continue
  }

  if ($CheckOnly) {
    Write-Host "- $name does not exist: would be created" -ForegroundColor Yellow
    $planned += $name
    continue
  }

  Write-Host "+ Creating $name" -ForegroundColor Cyan
  New-PnPList -Title $name -Template GenericList -EnableVersioning | Out-Null
  Set-PnPList -Identity $name -Description $spec.Description -EnableVersioning $true -MajorVersions 500 | Out-Null
  if ($spec.TitleName) {
    Set-PnPField -List $name -Identity "Title" -Values @{ Title = $spec.TitleName; Indexed = $spec.TitleIndexed } | Out-Null
  }
  foreach ($f in $spec.Fields) { Add-ListField $name $f }

  # Permissions, applied only to lists this run created.
  $web = Get-PnPWeb -Includes AssociatedMemberGroup, AssociatedVisitorGroup
  switch ($name) {
    "EntraRequests" {
      # Item-level permissions: people see and edit only their own items (ER-01 then locks
      # each item to read-only for its requester). Site owners still see everything.
      $l = Get-PnPList -Identity $name
      $l.ReadSecurity  = 2   # Read items that were created by the user
      $l.WriteSecurity = 2   # Create items and edit items that were created by the user
      $l.Update(); Invoke-PnPQuery
    }
    { $_ -in "EntraCatalogApps", "EntraCatalogGroups" } {
      # Members: Read only. Owners keep Full Control.
      Set-PnPList -Identity $name -BreakRoleInheritance -CopyRoleAssignments | Out-Null
      Set-PnPListPermission -Identity $name -Group $web.AssociatedMemberGroup.Title -RemoveRole "Edit" -ErrorAction SilentlyContinue
      Set-PnPListPermission -Identity $name -Group $web.AssociatedMemberGroup.Title -RemoveRole "Contribute" -ErrorAction SilentlyContinue
      Set-PnPListPermission -Identity $name -Group $web.AssociatedMemberGroup.Title -AddRole "Read"
    }
    "EntraSettings" {
      # Owners only: keep the Owners group, remove Members and Visitors.
      Set-PnPList -Identity $name -BreakRoleInheritance -CopyRoleAssignments | Out-Null
      foreach ($g in $web.AssociatedMemberGroup.Title, $web.AssociatedVisitorGroup.Title) {
        foreach ($role in "Edit", "Contribute", "Read") {
          Set-PnPListPermission -Identity $name -Group $g -RemoveRole $role -ErrorAction SilentlyContinue
        }
      }
    }
  }
  $created += $name
}

# ---------------------------------------------------------------------------
# EntraSettings item (only if the list has no items)
# ---------------------------------------------------------------------------
$S = "EntraSettings"
if (Get-PnPList -Identity $S -ErrorAction SilentlyContinue) {
  $items = @(Get-PnPListItem -List $S -PageSize 10)
  if ($items.Count -eq 0) {
    if ($CheckOnly) {
      Write-Host "- $S has no item: would create the settings item" -ForegroundColor Yellow
    } else {
      $missing = @(Get-MissingFields $S $Lists[$S].Fields)
      if ($missing.Count -gt 0) {
        Write-Host "! $S is missing columns ($(($missing | ForEach-Object Name) -join ', ')): settings item not created. Re-run with -AddMissingColumns." -ForegroundColor Red
      } else {
        Add-PnPListItem -List $S -Values @{
          Title = "settings"; TenantId = $TenantId; GraphClientId = $GraphClientId; ManagedByTag = $ManagedByTag
          ServiceAccountUpn = $ServiceAccountUpn.ToLower(); EntraApproverEmails = $EntraApproverEmails
          FallbackApproverEmail = $FallbackApproverEmail; KeyVaultName = $KeyVaultName
          PfxSecretName = "entra-pp-graph-pfx"; PfxPasswordSecretName = "entra-pp-graph-pfx-password"; PowerAppUrl = $PowerAppUrl
        } | Out-Null
        Write-Host "+ Created the $S item" -ForegroundColor Cyan
      }
    }
  } else {
    $ids = ($items | ForEach-Object { $_.Id }) -join ", "
    Write-Host "= $S already has $($items.Count) item(s) (ID $ids): left unchanged" -ForegroundColor Green
    if ($items.Count -gt 1) { Write-Host "! Keep exactly one item: the flows read ID 1." -ForegroundColor Red }
    elseif ($items[0].Id -ne 1) { Write-Host "! The item is ID $($items[0].Id), not 1: change 'Get settings' in each flow to that ID." -ForegroundColor Red }
  }
}

Write-Host ""
Write-Host "Summary" -ForegroundColor Cyan
if ($created) { Write-Host "  created: $($created -join ', ')" }
if ($skipped) { Write-Host "  already existed (skipped): $($skipped -join ', ')" }
if ($planned) { Write-Host "  would create: $($planned -join ', ')" }
Write-Host ""
Write-Host "Next:"
Write-Host "  - Members group: Edit or Contribute on the SITE (they create items in EntraRequests; item-level security limits them to their own)."
Write-Host "  - Make the flow account ($ServiceAccountUpn) a site OWNER (it breaks item permissions and writes every list)."
Write-Host "  - Add the Entra ID team to the site Owners group (they see all requests)."
