# Architecture diagrams (single tenant)

`entra-powerplatform.drawio` has 14 editable pages for **version 1.2** (what is built today), using the official Azure2 and Power Platform icons plus draw.io's Office stencils for SharePoint and Approvals. `entra-powerplatform.pdf` has the same pages as a review pack.

| # | Page | Type | What it shows |
|---|---|---|---|
| 1 | At a glance | overview | Ask → Lock → Approve → Create → Stamp, in plain language |
| 2 | Components | system context | People, the Power Platform environment (app, SharePoint site, 4 flows, Graph connection) and Entra ID |
| 3 | Who runs as whom | identity | Requester (delegated), flow owner (connections), platform app (certificate → token → Graph), plus the connection fields |
| 4 | Sequence: submit and approve | sequence | Submit → ER-01 lock and snapshot → Get manager → manager approval → Entra team approval, including both rejection paths |
| 5 | Sequence: create app registration | sequence | ER-02 guard → token → team membership check → app → wait 15 s → expose API (retry) → enterprise app (retry) → role assignments (retry) → catalog |
| 6 | Flow: ER-01 Approvals | flowchart | Decisions, the fallback approver, self-approval rule, rejection exits |
| 7 | Flow: ER-02 Execute | flowchart | Guard, existing-app ownership check, Switch with 5 scopes, shared role-assignment loop, Catch |
| 8 | Flow: ER-03 Catalog sync | flowchart | The hourly app loop and group loop that refresh the catalog lists |
| 9 | Flow: ER-04 Onboard group | flowchart | Find an existing group by name or Object ID, member/owner and security checks, catalog row, and how the app shows the result |
| 10 | Request lifecycle | state machine | EntraRequests.Status values and who writes each one, including the onboardGroup shortcut |
| 11 | Data model | data | The 4 SharePoint lists, PayloadJson shape, the tags and notes stamped on app registrations and enterprise apps |
| 12 | Security and permissions | security | People's access, the 4 Graph permissions, SharePoint permissions, governance, the 6 guards |
| 13 | Deployment and build order | deployment | What exists in Entra, SharePoint and Power Platform, plus the build order (solution import, SP-00, .msapp) |
| 14 | Option: Graph connection | comparison | Certificate in the connection (recommended) vs HTTP action + Key Vault, and what is identical either way |

## Future extension (not built)

`entra-powerplatform-future.drawio` (and `.pdf`) is kept separate on purpose, so the main set shows only what exists:

| # | Page | What it shows |
|---|---|---|
| F1 | ServiceNow components | New flows ER-05 Raise change and ER-06 Change sync, the ServiceNow connector, new list columns, the fields set on the normal change, and the gated / record modes |
| F2 | ServiceNow sequence | Entra approval → PendingChange → normal change → CAB → Implement → ER-02 → change closed |

See [docs/00-OVERVIEW.md §8](../docs/00-OVERVIEW.md#8-future-extensions).

## Edit and regenerate

```bash
python3 generate.py        # rewrites entra-powerplatform.drawio
python3 future.py          # rewrites entra-powerplatform-future.drawio
./render.sh png            # optional: PNG per page of both files (needs the draw.io desktop app)
python3 preview.py entra-powerplatform.drawio   # optional: view in a browser
```

`generate.py` and `future.py` are the sources, with one function per page. You can edit the `.drawio` files by hand in draw.io, diagrams.net or the VS Code Draw.io extension, but the next run overwrites those edits. The PNGs in `docs/img/` used by the overview doc are exported from these files.

## Export

In draw.io, use *File → Export as → PDF* with **All pages** for a review pack. For PNG or SVG, tick **Include a copy of my diagram** so the export stays editable.
