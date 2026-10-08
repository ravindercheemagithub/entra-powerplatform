# 9. Import the flows as a solution

Instead of building the flows by hand from doc 04, import them. [`solution/dist/EntraSelfService_1_2_1_0.zip`](../solution/dist/EntraSelfService_1_2_1_0.zip) (version 1.2.1) is an **unmanaged** solution containing:

| Component | What it is |
|---|---|
| **SP-00 Create lists** | instant flow: creates the four SharePoint lists if they don't exist (same as doc 02 §2.2b) |
| **ER-01 Approvals** | lock, manager approval, Entra team approval |
| **ER-02 Execute** | applies approved requests in Entra through Microsoft Graph |
| **ER-03 Catalog sync** | hourly refresh of the catalog lists |
| **ER-04 Onboard group** | finds an existing group by name or Object ID and adds it to the catalog when the requester is a member or owner (no approval) |
| 5 connection references | SharePoint, Office 365 Users, Approvals, Office 365 Outlook, HTTP with Microsoft Entra ID |
| Environment variable **SharePoint site URL** (`esp_SiteUrl`) | the site that holds the lists |

The flows are the ones in doc 04, action for action, using **option A** (HTTP with Microsoft Entra ID, client-certificate connection) for Graph. They are imported **turned off**. Unmanaged means you can open and edit everything after import.

Not included:
- the optional Teams notification (ER-01 step 19);
- the Key Vault option B;
- the Power Apps canvas app: import [`powerapps/dist/EntraSelfService.msapp`](../powerapps/dist/EntraSelfService.msapp) as in [doc 03 §3.0](03-POWER-APPS.md#30-fastest-import-the-packed-app-msapp), then optionally add it to this solution.
- the SharePoint lists themselves: solutions only hold Dataverse components, so **SP-00** creates the lists once you run it.

## 9.1 Before you import

| Need | Why |
|---|---|
| A Power Platform environment **with Dataverse** (the default environment usually has one) | Solutions and Approvals both need Dataverse |
| You can import solutions there (Environment Maker or System Customizer) | Import permission |
| Power Automate Premium licence (or trial) for the account that will own the flows | ER-02 and ER-03 use a Premium connector |
| The platform app registration with its certificate and admin-consented Graph permissions (doc 01) | Needed to create the HTTP with Microsoft Entra ID connection during import |
| The `.pfx` file and its password at hand | Same |
| Site owner on the SharePoint site | The SharePoint connection and SP-00 act with your rights |

Import **as the account that should own the flows** (your account while testing, the service account later). The flows run on the connections you pick during import.

## 9.2 Download the zip

On GitHub open [`solution/dist/EntraSelfService_1_2_1_0.zip`](../solution/dist/EntraSelfService_1_2_1_0.zip) → **Download raw file** (the download icon at the top right). Don't unzip it.

## 9.3 Import

1. Go to make.powerautomate.com (or make.powerapps.com) and pick the right **environment** (top right).
2. **Solutions** → **Import solution** → **Browse** → pick the zip → **Next** → **Next**.
3. **Connections.** One row per connection reference. For each, pick an existing connection or **+ New connection**:

| Connection reference | Connection to choose |
|---|---|
| Entra Self-Service: SharePoint | SharePoint, signed in as you (a site owner) |
| Entra Self-Service: Office 365 Users | Office 365 Users |
| Entra Self-Service: Approvals | Approvals |
| Entra Self-Service: Office 365 Outlook | Office 365 Outlook |
| Entra Self-Service: HTTP with Microsoft Entra ID (Graph, client certificate) | HTTP with Microsoft Entra ID (preauthorized), with **Authentication type = Log in using a Client Certificate Auth**: Resource URI `https://graph.microsoft.com`, Base Resource URL `https://graph.microsoft.com`, Tenant = directory (tenant) ID, Client ID = platform app's client ID, certificate = the `.pfx` + password |

   **+ New connection** opens a new tab. Create the connection there, come back, and click **Refresh** if it doesn't appear in the list. Every row needs a green tick before you can continue.

4. **Environment variables.** **SharePoint site URL** = e.g. `https://<tenant>.sharepoint.com/teams/m365automationqa` (no trailing `/`).
5. **Import.** It takes a minute or two. A green banner says the import succeeded.

## 9.4 After import

1. **Solutions → Entra Self-Service → Cloud flows.** The four flows are listed, all **Off**.
2. **Create the lists** (skip if they exist already):
   1. Open **SP-00 Create lists** → **Turn on** → **Run** → **Run flow**.
   2. Then do the *Finish by hand* steps in [doc 02 §2.2b](02-SHAREPOINT.md#finish-by-hand-about-5-minutes): permissions, settings item values, and checking the indexes.
3. **Fill in the EntraSettings item** (ID 1):
   - TenantId, GraphClientId
   - **ServiceAccountUpn** = the UPN of the account you imported as, in lower case. It owns the SharePoint connection, so its name appears in *Modified By*.
   - EntraApproverEmails, FallbackApproverEmail
   - PowerAppUrl (the list URL until the app exists)
4. **Import the app**: [doc 03 §3.0](03-POWER-APPS.md#30-fastest-import-the-packed-app-msapp) (Apps → Import app → From file (.msapp), then add the three lists and Office 365 Users as data sources).
5. **Turn on ER-01** and test it with [doc 06](06-TEST-ER01.md).
6. **Turn on ER-03** and test it with [doc 08](08-TEST-ER03.md). It's read-only in Entra.
   Turn on **ER-04** too, and test it with [doc 10](10-TEST-ER04.md). It's read-only in Entra and needs no approval.
7. **Turn on ER-02** when you are ready for it to create objects in Entra, and test it with [doc 07](07-TEST-ER02.md).

Open each flow once in the designer and check it has no errors before turning it on. If the designer warns that a list can't be found, check the **SharePoint site URL** environment variable (Solutions → Entra Self-Service → **Environment variables** → SharePoint site URL → *Current value*).

## 9.5 If something goes wrong

| Symptom | What to do |
|---|---|
| Import fails with an error message | Copy the full message (*Download log file* on the import page if offered) and share it; the definitions are generated by `solution/build_solution.py` and can be fixed and rebuilt |
| Can't create the HTTP with Microsoft Entra ID connection | Check the auth type is *Client Certificate Auth* and the four values; Microsoft suggests the classic designer if the new one complains about a missing parameter |
| A flow won't turn on | Open it: the designer shows the action with the problem (usually a connection that needs fixing: **… → Edit** the connection reference under Solutions) |
| ER-02 runs end as **Cancelled** | ServiceAccountUpn doesn't match the account that owns ER-01's SharePoint connection (doc 07 §7.7) |
| SharePoint actions fail with *List not found* | The site URL variable is wrong, or SP-00 hasn't created the lists yet |

## 9.6 Updating

**1.2.1:** fixes the import warning *the workflow run action 'Stop_no_group_id' has type 'Terminate' that could not be nested under an action of type 'Foreach'* (ER-02 imported but stayed off). The role-assignment loop now records a failure in `varAssignError` and fails the request once, after the loop. Import over 1.2; then turn ER-02 on.

**1.2:** groups are no longer created by the platform, and app registrations get no owners.
- ER-02 requires an existing owning team and existing role groups.
- ER-04 finds the group to add by **name or Object ID**.
- Expose API retries while the new app replicates.
- The enterprise app's *Assignment required* comes from the request.

Import over 1.1.x and re-import the app (`EntraSelfService.msapp`). The old `createGroup` choice in RequestType can stay; nothing uses it.

**1.1.3:** fixes **404 on HTTP Add owner** (and the same risk on role assignments): ER-02 now waits 15 s after creating the app and retries owners and role assignments up to 6 times, 10 s apart, while new objects replicate. Import over 1.1.2.

**1.1.2:** fixes *InvalidTemplate … createArray expects a comma separated list of parameters* (an empty `createArray()` is not valid; replaced by `json('[]')` in 27 places, e.g. `Select team owner binds`). Import over 1.1.1. Publish or discard any unsaved draft of these flows first, or the import fails with *unpublished active row*.

**1.1.1:** removes `?` from every action name (Power Automate rejects it when you save a flow). Import over 1.1. If you edited ER-01's outcome actions for testing, the import overwrites those edits.

**From 1.0 to 1.1** (adds ER-04 and changes ER-01's trigger to skip `onboardGroup` requests): add the choice `onboardGroup` to the RequestType column of EntraRequests (List settings → RequestType), then import the 1.1 zip over 1.0. Turn on **ER-04** afterwards; ER-01 keeps its state.

A newer zip has a higher version number and the same flow IDs, so importing it **upgrades the flows in place**. Because the solution is unmanaged, an import overwrites changes you made to these four flows. Note or export your own changes first (**Solutions → Entra Self-Service → Export**).

To rebuild the zip after changing the flows' design:

```bash
cd solution
python3 build_solution.py   # needs the Power Platform CLI: set PAC=/path/to/pac
python3 validate.py         # static checks: action references, variables, loops, brackets
```
