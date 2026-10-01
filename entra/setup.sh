#!/usr/bin/env bash
# =============================================================================
# The one Entra identity this solution needs: "entra-pp-graph", the app
# registration Power Automate's HTTP actions use to call Microsoft Graph.
#
#   - single-tenant app registration + service principal
#   - Microsoft Graph APPLICATION permissions, admin-consented
#   - certificate credential (no client secret); PFX for Power Automate
#   - optional: PFX + password into Azure Key Vault for the flows to read
#
# Run: az login --tenant <tenant> --allow-no-subscriptions   (Application Admin to create;
#      Global Admin / Privileged Role Admin for the consent step)
#   ./setup.sh                      create/update app, permissions, certificate
#   KEYVAULT=<name> ./setup.sh      ... and store the PFX + password as Key Vault secrets
# =============================================================================
set -euo pipefail

NAME="${NAME:-entra-pp-graph}"
CERT_DIR="${CERT_DIR:-./certs}"
GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"
GRAPH="https://graph.microsoft.com/v1.0"
say()  { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

TENANT=$(az account show --query tenantId -o tsv)
say "App registration $NAME in tenant $TENANT"
APP_ID=$(az ad app list --display-name "$NAME" --query "[0].appId" -o tsv)
[[ -z "$APP_ID" ]] && APP_ID=$(az ad app create --display-name "$NAME" --sign-in-audience AzureADMyOrg --query appId -o tsv)
OBJ_ID=$(az ad app show --id "$APP_ID" --query id -o tsv)
SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv 2>/dev/null || az ad sp create --id "$APP_ID" --query id -o tsv)
GRAPH_SP=$(az ad sp show --id "$GRAPH_APP_ID" --query id -o tsv)

# Permission -> why it is needed (Power Automate flows ER-02 execute and ER-03 sync)
PERMS=(
  "Application.ReadWrite.All:create app registrations + service principals; App ID URI, scopes, app roles, owners, tags"
  "AppRoleAssignment.ReadWrite.All:assign groups to app roles on enterprise apps"
  "Group.ReadWrite.All:create security groups with owners/members; stamp appCatID in the description"
  "Directory.Read.All:checkMemberGroups (is the requester in the owning team?), group members for the catalog"
  "User.Read.All:resolve the requester's object id; owners and members by UPN"
)
access=""
for e in "${PERMS[@]}"; do
  v="${e%%:*}"
  id=$(az ad sp show --id "$GRAPH_APP_ID" --query "appRoles[?value=='$v' && contains(allowedMemberTypes,'Application')].id | [0]" -o tsv)
  access+="{\"id\":\"$id\",\"type\":\"Role\"},"
done
az rest --method PATCH --uri "$GRAPH/applications/$OBJ_ID" --headers 'Content-Type=application/json' --body "{
  \"notes\": \"Graph identity for the Entra self-service Power Automate flows (ER-02 execute, ER-03 catalog sync). Certificate credential only.\",
  \"requiredResourceAccess\": [{\"resourceAppId\":\"$GRAPH_APP_ID\",\"resourceAccess\":[${access%,}]}]
}" -o none

say "Admin consent (app role assignments on the service principal)"
for e in "${PERMS[@]}"; do
  v="${e%%:*}"; why="${e#*:}"
  id=$(az ad sp show --id "$GRAPH_APP_ID" --query "appRoles[?value=='$v' && contains(allowedMemberTypes,'Application')].id | [0]" -o tsv)
  if [[ -n "$(az rest --method GET --uri "$GRAPH/servicePrincipals/$SP_ID/appRoleAssignments" --query "value[?appRoleId=='$id'].id | [0]" -o tsv)" ]]; then
    note "$v already granted"; continue
  fi
  az rest --method POST --uri "$GRAPH/servicePrincipals/$SP_ID/appRoleAssignments" \
    --body "{\"principalId\":\"$SP_ID\",\"resourceId\":\"$GRAPH_SP\",\"appRoleId\":\"$id\"}" -o none \
    && note "granted $v -- $why" || note "!! could not grant $v (needs Global Admin / Privileged Role Admin)"
done

say "Certificate credential"
mkdir -p "$CERT_DIR"; chmod 700 "$CERT_DIR"
if [[ ! -f "$CERT_DIR/$NAME.pfx" ]]; then
  PASS=$(openssl rand -base64 24)
  openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes -subj "/CN=$NAME" -keyout "$CERT_DIR/$NAME.key" -out "$CERT_DIR/$NAME.crt" 2>/dev/null
  # -legacy keeps the PFX readable by Power Automate's certificate auth on all OpenSSL 3 builds.
  openssl pkcs12 -export -inkey "$CERT_DIR/$NAME.key" -in "$CERT_DIR/$NAME.crt" -out "$CERT_DIR/$NAME.pfx" -passout "pass:$PASS" -legacy 2>/dev/null \
    || openssl pkcs12 -export -inkey "$CERT_DIR/$NAME.key" -in "$CERT_DIR/$NAME.crt" -out "$CERT_DIR/$NAME.pfx" -passout "pass:$PASS"
  printf '%s' "$PASS" > "$CERT_DIR/$NAME.pfx-password.txt"
  base64 < "$CERT_DIR/$NAME.pfx" | tr -d '\n' > "$CERT_DIR/$NAME.pfx.base64.txt"
  chmod 600 "$CERT_DIR"/*
  az ad app credential reset --id "$APP_ID" --cert "@$CERT_DIR/$NAME.crt" --append -o none
  note "uploaded public certificate; private material in $CERT_DIR (move to Key Vault, then delete)"
fi

if [[ -n "${KEYVAULT:-}" ]]; then
  say "Key Vault $KEYVAULT"
  az keyvault secret set --vault-name "$KEYVAULT" -n entra-pp-graph-pfx --file "$CERT_DIR/$NAME.pfx.base64.txt" -o none
  az keyvault secret set --vault-name "$KEYVAULT" -n entra-pp-graph-pfx-password --file "$CERT_DIR/$NAME.pfx-password.txt" -o none
  note "secrets entra-pp-graph-pfx and entra-pp-graph-pfx-password stored"
fi

say "Values for EntraSettings and the HTTP actions"
note "TenantId      = $TENANT"
note "GraphClientId = $APP_ID"
note "HTTP action > Authentication: Active Directory OAuth | Authority https://login.microsoftonline.com | Tenant $TENANT"
note "                Audience https://graph.microsoft.com | Client ID $APP_ID | Credential Type: Certificate"
note "                Pfx = contents of $CERT_DIR/$NAME.pfx.base64.txt | Password = $CERT_DIR/$NAME.pfx-password.txt"
