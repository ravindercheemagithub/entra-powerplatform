# 1. Entra ID: the Graph identity and the service account

You need two identities. Nothing else is created in Entra up front: the app registrations users request are created later, by the flows.

| Identity | What it is | Why |
|---|---|---|
| `entra-pp-graph` | App registration (single tenant) with Microsoft Graph **application** permissions and a **certificate** | The identity flows ER-02 and ER-03 use in their HTTP actions to call Graph. Power Automate cannot use a managed identity. |
| `svc-entra-flows` | A normal user account (service account), licensed for Microsoft 365 + **Power Automate Premium** | Owns the three flows and their connections (SharePoint, Approvals, Outlook, Teams, Key Vault). Automated flows run under the owner's licence. |

## 1.1 `entra-pp-graph`: script

```bash
az login --tenant <tenant> --allow-no-subscriptions
./entra/setup.sh                    # or: KEYVAULT=<vault> ./entra/setup.sh  (also stores the PFX + password)
```

## 1.2 `entra-pp-graph`: by hand in the Entra admin center

1. **Entra ID → App registrations → New registration**: name `entra-pp-graph`, **Single tenant**, no redirect URI → Register. Copy the **Application (client) ID** and the **Directory (tenant) ID**.
2. **API permissions → Add a permission → Microsoft Graph → Application permissions**:

   | Permission | Why |
   |---|---|
   | `Application.ReadWrite.All` | create app registrations and service principals; App ID URI, scopes, app roles, owners, tags |
   | `AppRoleAssignment.ReadWrite.All` | assign groups to app roles on enterprise apps |
   | `Group.ReadWrite.All` | create security groups with owners and members; appCatID in the description |
   | `Directory.Read.All` | `checkMemberGroups` (is the requester in the owning team?), group members for the catalog |
   | `User.Read.All` | the requester's object ID; owners and members |

   → **Grant admin consent for <tenant>** (Global Administrator or Privileged Role Administrator).
   No SharePoint permission is needed: the flows reach SharePoint through the SharePoint connector, as the service account.
3. **Certificates & secrets → Certificates → Upload certificate**. Create one with:
   ```bash
   openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes -subj "/CN=entra-pp-graph" -keyout entra-pp-graph.key -out entra-pp-graph.crt
   openssl pkcs12 -export -legacy -inkey entra-pp-graph.key -in entra-pp-graph.crt -out entra-pp-graph.pfx    # set a password
   base64 -i entra-pp-graph.pfx | tr -d '\n' > entra-pp-graph.pfx.base64.txt
   ```
   Upload the `.crt`. Power Automate needs the **base64 PFX** and its password.
4. Optional: **Branding & properties → Notes**: "Used by flows ER-02/ER-03 in environment <name>. Owner: Entra ID team."

## 1.3 Where the certificate lives

Pick one:

| Option | How | Notes |
|---|---|---|
| **Azure Key Vault** (recommended) | Secrets `entra-pp-graph-pfx` (base64 PFX) and `entra-pp-graph-pfx-password`. Give `svc-entra-flows` *Key Vault Secrets User*. ER-02/ER-03 read them with the **Azure Key Vault → Get secret** action (Premium), with **Secure outputs** on. | The PFX never appears in the flow definition or run history |
| Directly in the HTTP action | Paste the base64 PFX and password into each HTTP action's authentication | Visible to anyone who can edit the flow. Testing only. |

## 1.4 The service account `svc-entra-flows`

1. Create the user (M365 admin center). Licences: **Microsoft 365** (E3/E5 or Business) **+ Power Automate Premium**.
2. Exclude it from interactive MFA prompts the way your organisation does for service accounts. Flow connections refresh silently, but a Conditional Access policy that blocks the account stops the flows.
3. SharePoint: make it a **site owner** of the self-service site (doc 02).
4. Sign in to make.powerautomate.com as this account to create the flows and connections (doc 04). Add the Entra ID team as **co-owners** of the flows, and nobody else.

## 1.5 Power Platform governance (recommended)

- A dedicated environment, e.g. *Entra Self-Service*. Environment Maker role only for the Entra ID team.
- A DLP policy for that environment allowing: SharePoint, Approvals, Office 365 Users, Office 365 Outlook, Microsoft Teams, HTTP, Azure Key Vault.
- Share the app with everyone (or a group) as **User**, never Co-owner.

## 1.6 What gets stamped on created objects

| Object | Where | Values |
|---|---|---|
| App registration | `tags` | `appCatID:…`, `team:<group id>`, `teamName:…`, `createdBy:<upn>`, `createdById:<oid>`, `createdTimestamp`, `lastUpdatedBy`, `lastUpdatedTimestamp`, `managedBy:entra-pp`, `requestId:REQ-…`, plus optional `key:value` tags |
| | `notes` | `appCatID=…; requestId=…; createdBy=…; managedBy=…` |
| Enterprise app | `tags` (same) + `WindowsAzureActiveDirectoryIntegratedApp` | |
| Group | end of `description` | `[appCatID=…; requestId=…; createdBy=…; managedBy=…]` |

The catalog sync (ER-03) finds managed apps by the `managedBy:<tag>` tag. Keep `ManagedByTag` in EntraSettings identical to what the flows stamp.
