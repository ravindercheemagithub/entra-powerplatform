# Architecture diagrams (single tenant)

`entra-powerplatform.drawio` has 13 editable pages built from the official Azure2 and Power Platform icons, plus draw.io's Office stencils for SharePoint and Approvals. `entra-powerplatform.pdf` has the same pages as a review pack.

| # | Page | Type | What it shows |
|---|---|---|---|
| 1 | At a glance | overview | Ask → Lock → Approve → Create → Stamp, in plain language |
| 2 | Components | system context | People, the Power Platform environment (app, SharePoint site, 3 flows, Graph connection) and Entra ID |
| 3 | Who runs as whom | identity | Requester (delegated), flow owner (connections), platform app (certificate → token → Graph), plus the connection fields |
| 4 | Sequence: submit and approve | sequence | Submit → ER-01 lock and snapshot → Get manager → manager approval → Entra team approval, including both rejection paths |
| 5 | Sequence: create app registration | sequence | ER-02 guard → token → team group or membership check → app → expose API → owners → enterprise app retry loop → role assignments → catalog |
| 6 | Flow: ER-01 Approvals | flowchart | Decisions, the fallback approver, self-approval rule, rejection exits |
| 7 | Flow: ER-02 Execute | flowchart | Guard, existing-app ownership check, Switch with 6 scopes, shared role-assignment loop, Catch |
| 8 | Flow: ER-03 Catalog sync | flowchart | The hourly app loop and group loop that fill the catalog lists |
| 9 | Request lifecycle | state machine | EntraRequests.Status values and who writes each one |
| 10 | Data model | data | The 4 SharePoint lists, PayloadJson shape, the tags and notes stamped on Entra objects |
| 11 | Security and permissions | security | People's access, Graph permissions, SharePoint permissions, governance, the 6 guards |
| 12 | Deployment and build order | deployment | What exists in Entra, SharePoint and Power Platform, plus the build order |
| 13 | Option: Graph connection | comparison | Certificate in the connection (recommended) vs HTTP action + Key Vault, and what is identical either way |

## Edit and regenerate

```bash
python3 generate.py        # rewrites entra-powerplatform.drawio
./render.sh png            # optional: PNG per page (needs the draw.io desktop app)
python3 preview.py entra-powerplatform.drawio   # optional: view in a browser
```

`generate.py` is the source, with one function per page. You can edit the `.drawio` by hand in draw.io, diagrams.net or the VS Code Draw.io extension, but the next `generate.py` run overwrites those edits.

## Export

In draw.io, use *File → Export as → PDF* with **All pages** for a review pack. For PNG or SVG, tick **Include a copy of my diagram** so the export stays editable.
