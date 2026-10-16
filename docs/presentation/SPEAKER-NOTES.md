# Speaker notes: "App registrations in minutes, not days"

Talk track for [`EntraSelfService-overview.pptx`](EntraSelfService-overview.pptx). Each section gives:
- **Clicks:** how many clicks reveal the slide's content, and what each one shows;
- **Say:** the talk track;
- **If asked:** likely questions with short answers.

The slides carry a one-line reminder in their speaker notes; this document is the full version. Plan **about 30 minutes**, plus questions: roughly 1.5–2 minutes per main slide. The appendix is for questions only.

Before presenting:
- Replace the five dashed **Screenshot** frames on slide 8 with real screenshots of the wizard steps.
- Put your name, team and date on slide 1.
- Check the savings numbers on slide 13 against your real request volume.

---

## 1. App registrations in minutes, not days
**Clicks:** none.

**Say:**
- "Today an app registration is a ticket that takes about two weeks. What I'll show you turns it into a form a project team fills in, two approvals, and a flow that builds everything in Entra ID in minutes."
- "It runs entirely on Microsoft 365 services we already license: Power Apps, Power Automate and SharePoint."
- The five steps on the right are the whole idea: **ask, lock, approve, create, stamp**.

## 2. What we'll cover
**Clicks:** none.

**Say:** "Nine short sections. First why we need this and how it works, then what it delivers and saves, how tags fix ownership, what comes next, and how we'd like to work with your team."

## 3. Today an app registration is a 10-day ticket
**Clicks:** 5. One per card (10 working days, 1 person-day, back-and-forth, no visibility), then the result line.

**Say:**
- **10 working days:** "From the request to a usable app registration takes about ten working days. Projects plan around it or wait."
- **1 person-day:** "Each request costs the Entra ID team at least a day: clarifying, creating the app, exposing the API, roles, the enterprise app, group assignments, replying."
- **Back-and-forth:** "Requirements arrive in email or a ticket and are rarely complete, so there are several rounds of questions."
- **No visibility:** "Project teams can't see Entra ID, so they can't check what exists or what was built. Mistakes, such as a wrong redirect URI or a missing role, are found late."
- **Result:** "So teams work around the process, for example by reusing one app for many purposes. And because every engineer builds it slightly differently, names, owners and settings are inconsistent."

**Tip:** have one real example ready, such as a project that waited or an app reused across environments.

**If asked:**
- *"Where does 10 days come from?"* It's the average lead time we see on app registration tickets today. Use your own ticket data if you have it.
- *"Is one person-day realistic?"* It covers the full cycle across several conversations, not just the clicks in the portal.

## 4. Built with the M365 team, on services we already license
**Clicks:** 4. Power Apps, Power Automate, SharePoint, then the asks.

**Say:**
- "This is a collaboration with the M365 team. We use capabilities that are already licensed and keep the footprint small."
- **Power Apps:** "The form and the request tracker. It uses only Standard connectors, so no user needs an extra licence."
- **Power Automate:** "Approvals arrive in Outlook and Teams. The flows then create everything in Entra ID through Microsoft Graph."
- **SharePoint:** "Lists hold the requests, which become the audit trail with full version history, the catalog of apps and groups people can pick, and the settings."
- **What we needed:**
  - a Power Platform environment with Dataverse, which Approvals requires;
  - the connectors allowed in the DLP policy;
  - one Power Automate Premium licence, for the flow account only;
  - a SharePoint site.

**If asked:**
- *"Why does only one account need Premium?"* The Graph calls are made by automated flows, which run under their owner's licence. Users only ever use Standard connectors.
- *"Who owns the flows?"* A dedicated flow account. The Entra ID team are co-owners. The flows live in their own environment.

## 5. Three ways to build it: why we chose the Power stack
**Clicks:** 1, the decision box. Walk through the table first.

**Say:**
- "We compared three approaches: CI/CD pipelines in Azure DevOps or GitHub; an Azure Function App with a web portal; and Power Apps with Power Automate and SharePoint."
- Go through the criteria row by row:
  - **Familiar to M365 users:** people already use Outlook and Teams approvals and SharePoint lists. Pipelines and custom portals are developer tools.
  - **Easy to extend flows:** a new request type is a new branch in a flow, with no build or release pipeline. A Function App can do anything but needs developers.
  - **Keeps data in M365:** requests, approvals and history stay in SharePoint, next to the rest of our M365 data.
  - **Low maintenance:** there are no servers, containers or runtimes to patch. The Power stack is fully managed.
  - **Approvals built in:** the Approvals connector gives approvals in Outlook and Teams for free. With the other options we'd build them ourselves.
  - **Running cost:** one Premium licence. Pipelines are also cheap; a Function App adds an Azure bill.
- **Click, decision:** "On balance the Power stack wins on every factor that matters for adoption and long-term ownership."

**If asked:**
- *"Isn't low-code harder to version-control?"* The flows are packaged as a solution and kept in the repository, and new versions are imported over the old ones. The solution is generated from source and validated before each release.
- *"What if we outgrow it?"* The request lists and tags are the same whichever engine runs them. A pipeline or Function App could take over execution later without changing the user experience.

## 6. How it works: five steps from request to Entra ID
**Clicks:** 6, one per step plus its arrow, then the result.

**Say:**
1. **Ask:** "The requester fills in the wizard in the Power App."
2. **Lock:** "The request is saved in SharePoint, and the first flow immediately makes it read-only for the requester. What gets approved can't change afterwards."
3. **Manager approves** in Outlook or Teams.
4. **Entra team approves:** "the second approval. If someone tries to approve their own request, it counts as a rejection."
5. **Create:** "Only then does the execution flow call Microsoft Graph, as a dedicated platform identity, and build what was approved."
- **Result:** "Minutes later: the app registration, URI and scopes, app roles with their groups, the enterprise app, and the tags. The requester sees each step in *My requests* and gets an email that says exactly what was done."

**Note:** every box and arrow is a PowerPoint shape, so you can edit them directly.

## 7. Requests and execution are kept apart
**Clicks:** 4: request side, approval gate, execution side, then the guards.

**Say:**
- **Request side:** "The requester works with their own sign-in and a standard licence. They can only create and read their own requests, and they need no Entra ID rights at all."
- **Approval gate:** "The request is locked and snapshotted. The snapshot is the only thing that is ever executed. Then the two approvals."
- **Execution side:** "Execution runs as the platform: a flow account that isn't a person's account, using an app identity with a certificate and no client secrets. That identity is the only thing with Graph write permissions."
- **Guards:** "Before it changes anything, the execution flow checks four things:
  - the requester is the item's built-in *Created By*, which can't be faked;
  - the last edit was made by the flow account, not someone editing the list by hand;
  - both decisions are *Approved*;
  - for a change, the app's owner tag names the requester or their group."

**If asked:**
- *"What's the biggest risk?"* Whoever can edit the execution flow can use its Graph identity. So the flows sit in their own environment, with only the Entra ID team as co-owners.
- *"Certificate rotation?"* Yearly: upload the new certificate, update the connection, then remove the old one.

## 8. Core flow: register an application in one request
**Clicks:** 5, one per wizard step.

**Say:**
1. **Basics:** "The only required step. The display name follows our convention, appCatID-environment-BoR short name-free text. The prefix is built from the fields and can't be typed over. The owning group is optional: without one, the app is owned by the requester."
2. **Expose an API:** the Application ID URI, `api://{appId}` by default, plus scopes and optional token claims.
3. **App roles:** "One click adds User and Admin roles. Each role is held by an existing group, so the group's owners manage access afterwards without another request."
4. **Enterprise app:** created for the same app, with *assignment required* by default, plus account types and optional tags.
5. **Review + submit:** a summary of everything, and what happens next.

**Before presenting:** replace the dashed frames with screenshots.

## 9. What one request delivers
**Clicks:** 2, the top row then the bottom row.

**Say:**
- "Manually, these are eight separate tasks in the Entra admin center, and each one is a chance for a mistake. Here they all come from one validated form."
- **Standard name**, **Application ID URI**, **scopes**, **app roles**, **role assignments to existing groups**, **enterprise app with assignment required**, **token claims and redirect URIs**, **tags and notes**.
- "The flow builds them in the right order. It waits and retries while Entra replicates new objects, and records every step."

## 10. The complete picture
**Clicks:** none.

**Say:**
- "People on the left; in the middle, the Power Platform environment with the app, the SharePoint lists and the flows; Entra ID on the right."
- "Only the platform app registration holds Graph permissions, four of them, admin-consented, with a certificate."

**Editable source:** `diagrams/entra-powerplatform.drawio`, page 2.

## 11. Beyond new apps: the other flows
**Clicks:** 3: core flows, self-service helpers, operations.

**Say:**
- **Core:** ER-01 Approvals, ER-02 Execute, ER-03 Catalog sync. The catalog refreshes hourly who can pick which apps and groups.
- **Self-service helpers, no approval needed:**
  - ER-04 *Add existing group*: members make their group selectable.
  - ER-05 *Find app*: search by app ID; only the owner can continue.
  - ER-06 *Owning group*: hand an app from a person to a group.
- **Operations:**
  - ER-07 *Requeue*: the Entra ID team re-runs requests approved while execution was paused.
  - **Change requests**: expose an API, add roles, assign groups, create a missing enterprise app.

## 12. From a 10-day ticket to a same-day request
**Clicks:** 5, one row each.

**Say:** each row answers a pain point from slide 3:
- **Lead time:** about 10 days becomes the same day. The remaining time is how fast the two approvers respond.
- **Effort:** at least a day becomes about five minutes of review and approval.
- **Requirements:** one validated form, captured once.
- **Visibility:** *My requests* shows status, approvals, and step-by-step notes, with Done in green and Failed or Not run in red.
- **Consistency:** the same names, tags and settings every time.

## 13. What it saves
**Clicks:** 4: three stats, then the chart.

**Say:**
- "About nine working days shorter per request, and about 7.9 hours of Entra ID team effort saved per request: eight hours manual, minus five minutes of review."
- "The only extra running cost is one Power Automate Premium licence."
- **Chart:** "At 50, 100 or 200 new apps a year that's roughly 49, 99 or 198 person-days, about 0.2, 0.45 or 0.9 of a full-time person. Change requests add to this."

**Adjust:** replace the volumes with your real yearly numbers before presenting.

**If asked:** *"What's the licence cost?"* List price is about US$15 per user per month for Power Automate Premium; check your agreement.

## 14. Ownership by tags, not by naming convention
**Clicks:** 4: today, the app card, the tags, the benefits.

**Say:**
- **Today:** "Ownership is only implied by the app's name. There's no reliable link to the business application, it's hard to know who to ask or what to clean up, and there's no record of who requested it."
- **The app card:** "Every app the platform creates, and its enterprise app, carries the same tags."
- **The tags:**
  - `appCatID` links the app to the business application;
  - `team:group\<id>` (or `team:user\<id>`) decides **who may change it**, and the platform enforces this;
  - `appEnv`, `managedBy`, `requestId` and `createdBy` give the environment and the audit trail.
- **Benefits:** "Ownership enforced, a full audit trail, apps you can find and report on, and a basis for chargeback by appCatID."

**If asked:** *"Why not Entra owners?"* Security policy: we don't add owners to app registrations. The tag gives the same "who owns this" answer without granting anyone rights in Entra ID.

## 15. Future path
**Clicks:** 4, one phase each.

**Say:**
1. **Complete the remaining flows:** credentials (certificates and federated credentials, still no secrets), decommissioning, and a periodic review that asks owners whether each app is still needed.
2. **AppCatID on every identity:** "Extend the same ownership model to every identity the automation manages, not only app registrations."
3. **ServiceNow change, automatically:** "After manager approval, a normal change is raised in ServiceNow. Next slide."
4. **Easier approvals in Teams:** non-production approvals posted to a Teams channel or chat, approved with one tap.

**Say:** "The order and timing are ours to agree together."

## 16. Phase 3 design: ServiceNow normal change
**Clicks:** none.

**Say:**
- "After both approvals, a new flow raises a normal change in ServiceNow, with the approved summary, the CI from the appCatID, plans from a template, and the approvals as work notes."
- "There are two modes:
  - **gated**: the app is created only when the change reaches *Implement*, after CAB approval and inside the window;
  - **record-only**: create straight away and close the change for the audit trail.
  A common mix is to gate production and record everything else."
- "Not built yet. We'd agree the assignment group, the CI mapping and the template with change management first."

**Editable source:** `diagrams/entra-powerplatform-future.drawio`.

## 17. What helps us deliver quickly
**Clicks:** 2, one pillar each.

**Say:**
- **Knowledge:** "Your platform standards and naming conventions, how environments, DLP and licensing are set up, and who to ask when something is blocked."
- **Willingness to help and collaborate:** "Quick answers on environment questions, joint testing in QA before production, and shared ownership of the outcome."
- "Most of our delays so far were environment questions: a connector blocked by DLP, a licence, or access to a site. Fast answers there are what speeds everything up."

## 18. Our working model: 51 : 49
**Clicks:** 4, one point each.

**Say:**
- "We work on a 51 : 49 model."
- **We respect your knowledge:** you know the platform best; we build on it, not around it.
- **We work the way your team works:** your processes, tools and change rules come first.
- **You unblock environment issues quickly:** licences, DLP, access.
- **You get 51% of the credit:** "We present the delivery as your team's success. We bring the build effort, you bring the knowledge and the unblocking, and you take the larger share of the credit."

## 19. Questions
**Clicks:** none.

**Say:** "Thank you. Questions?"

Keep the appendix ready.

---

## Appendix slides (for questions)

| Slide | Shows | Editable source |
|---|---|---|
| Submit and approve (ER-01) | Sequence from the form to *Approved*, including both rejection paths | `diagrams/entra-powerplatform.drawio`, page 4 |
| Creating an app registration (ER-02) | Graph calls in order, with the retries | page 5 |
| ER-02 Execute flowchart | Guard, one branch per request type, role assignments, Catch | page 7 |
| Request lifecycle | Status values and who writes each one | page 10 |
| Security and permissions | People's access, Graph permissions, the guards | page 12 |

## Editing the deck
- **Native shapes, edit directly in PowerPoint:** every card, icon, arrow and table on slides 2–9, 11–15 and 17–18. The roadmap, the 51 : 49 doughnut and the savings chart are native PowerPoint charts and shapes; right-click the chart, then **Edit Data**.
- **Diagram images** (slides 10, 16 and the appendix): edit the `.drawio` source in draw.io (desktop, web or the VS Code extension), export the page as PNG, then right-click the picture in PowerPoint and choose **Change Picture**.
- **Animations:** **Animations → Animation Pane** lists each click's shapes. They're simple *Fade* entrances, so you can reorder or remove them.
- **Regenerating the whole deck:** see [`source/README.md`](source/README.md).
