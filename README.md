# entra-powerplatform

Entra ID self-service built only from **Power Apps + SharePoint + Power Automate + one Entra app registration**. No Azure resources, no code to host.

Sibling of `../entra-portal-next` (Next.js) and `../entra-portal-lite` (Functions). It uses the same request types, the same payload shapes and the same tag vocabulary (`appCatID`, `team`, `createdBy`, `requestId`, `managedBy` …), so objects look identical whichever tool created them.

```
 Power Apps (canvas, standard connectors only)
   │  Patch → SharePoint "EntraRequests" (item-level security: users see only their own)
   ▼
 ER-01 Approvals ─ standard connectors ─────────────────────────────────────────────┐
   lock the item (requester → read-only) · snapshot payload · manager approval      │
   · Entra team approval · Status = Approved                                         │
   ▼                                                                                 │
 ER-02 Execute ─ HTTP (premium) as app "entra-pp-graph" (certificate) ─▶ Microsoft Graph
   checks: approvals + "set by the approval flow" + requester owns the target app     │
   creates app registration / App ID URI / scopes / roles / SP / groups / assignments │
   writes ResultJson, Status = Completed | Failed                                     │
 ER-03 Catalog sync (hourly) ─ HTTP (premium) ─▶ EntraCatalogApps / EntraCatalogGroups ┘
   (what each user's groups own → the app's pickers, without premium in the app)
```

## Does calling Graph from Power Automate cost more?

Graph calls themselves are free. What costs is **the HTTP action, which is a Premium connector**. The licences that come with Microsoft 365 (the "seeded" Power Apps / Power Automate rights in E3/E5) cover **Standard** connectors only.

This design keeps Premium to the minimum:

| Part | Connectors | Licence needed |
|---|---|---|
| Power Apps app | SharePoint, Office 365 Users (Standard) | none beyond Microsoft 365, for every user |
| ER-01 Approvals | SharePoint, Approvals, Office 365 Users, Outlook, Teams (Standard) | none beyond Microsoft 365 |
| ER-02 Execute, ER-03 Catalog sync | **HTTP** (+ Azure Key Vault), both Premium | **one Power Automate Premium licence** (about $15/user/month list price) for the **service account that owns these two flows** |

Why only one licence: ER-02 and ER-03 are *automated* flows (a SharePoint trigger and a schedule), so they run under their **owner's** licence, not the requester's. Nobody who uses the app ever runs a Premium connector. If your licensing team considers ER-02 to be "in the context of the app", the alternative is a Power Automate **Process** licence on ER-02 (per-flow pricing). Confirm with your Microsoft licensing contact; list prices vary by agreement ([pricing overview](https://www.trustradius.com/products/microsoft-power-automate/pricing), [HTTP is Premium](https://comcomponent.com/en/blog/power-automate-license-connector-guide/)).

For comparison, the Azure Function / App Service variants need no Power Platform Premium licence, but they have an Azure bill (small for Functions consumption, roughly $13+/month for an App Service B1) and code to maintain.

> **Security trade-off you are accepting.** The Graph identity (`entra-pp-graph`, with `Application.ReadWrite.All` and friends) is used by the flows. Anyone who can **edit** ER-02 or ER-03 can make arbitrary Graph calls as that identity. So:
> - keep the flows in a dedicated Power Platform environment
> - restrict environment makers
> - keep the certificate in Azure Key Vault (read with secure outputs)
> - limit co-owners to the Entra ID team
>
> With a managed identity on a Function App, the credential cannot be extracted at all.

## What you build

| # | What | Where | Doc |
|---|---|---|---|
| 1 | App registration `entra-pp-graph` (Graph application permissions + certificate) | Entra | [docs/01-ENTRA.md](docs/01-ENTRA.md) · `entra/setup.sh` |
| 2 | Service account `svc-entra-flows` (Microsoft 365 + Power Automate Premium) | Entra / M365 admin | [docs/01-ENTRA.md](docs/01-ENTRA.md) |
| 3 | SharePoint site + 4 lists (`EntraRequests`, `EntraCatalogApps`, `EntraCatalogGroups`, `EntraSettings`) | SharePoint | [docs/02-SHAREPOINT.md](docs/02-SHAREPOINT.md) · `sharepoint/provision.ps1` |
| 4 | Canvas app "Entra Self-Service" (5 screens): import `powerapps/dist/EntraSelfService.msapp`, or paste the screens | Power Apps | [docs/03-POWER-APPS.md](docs/03-POWER-APPS.md) · `powerapps/` |
| 5 | Flows ER-01 Approvals, ER-02 Execute, ER-03 Catalog sync | Power Automate | [docs/04-POWER-AUTOMATE.md](docs/04-POWER-AUTOMATE.md) · `powerautomate/actions/` |
| 6 | End-to-end test | Your tenant | [docs/05-TESTING.md](docs/05-TESTING.md) |
| 6a | Test ER-01 on its own, with copy-paste payloads | Your tenant | [docs/06-TEST-ER01.md](docs/06-TEST-ER01.md) |
| 6b | Test ER-02 (creates objects in Entra) | Your tenant | [docs/07-TEST-ER02.md](docs/07-TEST-ER02.md) |
| 6c | Test ER-03 (read-only sync) | Your tenant | [docs/08-TEST-ER03.md](docs/08-TEST-ER03.md) |
| 5a | Or import the flows as a solution zip (instead of building them by hand) | Power Automate | [docs/09-SOLUTION-IMPORT.md](docs/09-SOLUTION-IMPORT.md) · `solution/dist/` |

## What can be imported, and how

| Part | Import format | How |
|---|---|---|
| SharePoint lists | **PnP PowerShell script** | `sharepoint/provision.ps1` creates all lists, columns, indexes, permissions and the settings item |
| Entra app registration | **az CLI script** | `entra/setup.sh` |
| Power Apps screens | **Power Apps YAML ("paste code")** | Each `powerapps/screens/*.pa.yaml` is one root container: copy it, select the screen in Studio, Ctrl+V. `App.Formulas.fx`, `App.OnStart.fx` and `Screens.OnVisible.fx` are pasted into their properties. |
| Power Automate flows | **Built by hand from the guide** (no hand-made importable package; see below) | Step-by-step guide with every action name, setting and expression. Each HTTP body is a file in `powerautomate/actions/` to paste in. |

Power Automate's importable formats are a solution `.zip` or a legacy package `.zip`. Both are produced by an *export*, and they embed environment-specific connection references. A hand-written package is fragile and can't be tested without your environment. The reliable route is to build each flow once from the guide, then **export it as a solution** to move it between environments.

## The app

- **Home**: a card per operation, plus your recent requests.
- **Register an application**, an Azure-portal-style wizard. Submit / Next / Cancel are always at the bottom; only Basics is required.
  1. **Basics**: name, appCatID, account types, owning team (or "Create new team group"), justification, description, redirect URI.
  2. **Expose an API & claims**: Application ID URI (default `api://{appId}` or custom), scopes (one-click `access_as_user`), optional ID/access-token claims, groups claim.
  3. **App roles & groups**: one click for User + Admin roles, each with a new group. Custom roles. Each role can get an existing group, or a new one via "Create new group".
  4. **Enterprise app & owners**: create the service principal, assignment required, additional owners, optional tags.
  5. **Review + submit**.
- **Security group**: as its own request, or inline from the wizard ("Create new group" returns to the wizard with the group added).
- **Expose an API / App roles / Role assignments / Enterprise application** on apps *your groups own* (from the catalog).
- **My requests**: approval stages, the IDs that were created, and errors.

## Folder map

```
entra/setup.sh                    app registration entra-pp-graph, permissions, certificate (+ Key Vault)
sharepoint/provision.ps1          4 lists, columns, indexes, item-level security, settings item
powerapps/App.Formulas.fx         theme, operations, my groups / my apps (named formulas)
powerapps/App.OnStart.fx          collections and variables
powerapps/Screens.OnVisible.fx    per-screen OnVisible + Fill
powerapps/screens/*.pa.yaml       paste-code YAML, one per screen (generated)
powerapps/tools/build.py          regenerates the YAML (python3 build.py)
powerautomate/actions/*.json      HTTP request bodies for ER-02 / ER-03
docs/                             01 Entra · 02 SharePoint · 03 Power Apps · 04 Power Automate · 05 Testing
```
