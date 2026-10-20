# 12. Testing API permissions, owner access and delete (1.7)

Check each run in ER-02's run history (doc 06 §6.6). The request's **CompletionNotes** (*My requests → What was done*) should show *N of M requested steps done*, then one line per step.

## 12.1 API permissions
| # | Do this | Expected |
|---|---|---|
| 1 | New app, no token claims; on **API permissions** untick `profile`, add `Mail.Read` | Review shows `openid, email, User.Read, Mail.Read`. In Entra: App registrations → the app → **API permissions** lists those four under Microsoft Graph (delegated), *Not granted*. Notes: `Done: API permissions …`, then a *Note* about consent. |
| 2 | New app, tick *email* under ID token claims (step 2), then open step 3 | The four sign-in permissions are shown ticked and greyed out; they're always sent. |
| 3 | Add a made-up name, e.g. `Foo.Read` | Notes: `Failed: unknown Microsoft Graph permission(s) Foo.Read, not added; added …`. The request ends *Failed* (partly), with everything else in place. |

## 12.2 Role holders and owner access
| # | Do this | Expected |
|---|---|---|
| 1 | New app with User + Admin roles; Admin held by a group, User held by a **user** (Add user); *Owner's role* = Admin; owning group chosen | Enterprise app → **Users and groups**: the group as Admin, the user as User, and the owning group as Admin (the owner). *Assignment required* = Yes. Notes include `Done: the owner … has the …Admin role`. |
| 2 | New app with **no roles**, no owning group; Default Access for one extra group | Users and groups: you and that group, both with *Default Access*. |
| 3 | *Role assignments* on an app without roles | The role list offers **Default Access**; a group or user added with it gets Default Access. |
| 4 | Role with *Allowed members = Applications* and a holder | **Next** refuses: *A role that allows only applications can't be held by users or groups…* |

## 12.3 Delete
Use a test app you own (created in 12.2).

| # | Do this | Expected |
|---|---|---|
| 1 | **Delete app registration** → Search its Object ID as someone who doesn't own it | *Not authorized owner…*; nothing else appears. |
| 2 | As the owner: *Disable sign-in only* → **Delete…** → **Yes** | Request goes to the manager, then the Entra ID team. After approval: the enterprise app's *Enabled for users to sign in* = No; the notes explain how to undo it. |
| 3 | *Delete only the enterprise application* | The enterprise app and its role assignments are gone; the app registration stays; its catalog row has no enterprise app ID. |
| 4 | *Delete the app registration…* (soft) | The app registration and enterprise app are gone; they're listed under App registrations → **Deleted applications** (restorable for 30 days); the catalog row is removed. |
| 5 | *Delete permanently*: the confirmation's **Yes** stays disabled until you type `DELETE` | After approval: not under Deleted applications either. If the purge can't run yet, the notes say it will be purged after 30 days. |
| 6 | Change the app's `team:` tag to someone else after submitting but before approval | ER-02 stops with *Not an authorized owner…*; nothing is deleted; the Catch email lists the steps. |
