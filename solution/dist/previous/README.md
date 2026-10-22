# Previous versions

Kept so a known-good version can be re-imported while a newer one is being tested. The current version is the zip one folder up.

| File | Version | App to pair it with |
|---|---|---|
| `EntraSelfService_1_7_0_0.zip` | 1.7: API permissions step, users as role holders, owner access, delete app registration | `powerapps/dist/previous/EntraSelfService-1.7.msapp` |
| `EntraSelfService_1_5_0_0.zip` | 1.5: plan-based completion notes (N of M steps), colours in emails | `powerapps/dist/previous/EntraSelfService-1.5.msapp` |

**To roll back,** import the older zip over the solution. If Power Platform refuses to import a lower version over a higher one, delete the solution's flows first, or try it in a test environment. Then re-import the matching `.msapp`. The SharePoint choices and columns added by newer versions can stay; older versions ignore them.
