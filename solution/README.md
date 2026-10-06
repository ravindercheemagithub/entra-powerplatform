# Power Platform solution

`dist/EntraSelfService_1_1_0_0.zip` is an unmanaged solution with the flows SP-00, ER-01, ER-02, ER-03 and ER-04, five connection references and the `esp_SiteUrl` environment variable. How to import it: [docs/09-SOLUTION-IMPORT.md](../docs/09-SOLUTION-IMPORT.md).

| Path | What |
|---|---|
| `build_solution.py` | Generates `src/` (unpacked solution) from the design in docs/04 and the bodies in `powerautomate/actions/`, then packs `dist/*.zip` with `pac solution pack` |
| `validate.py` | Static checks on the generated flows: every `body()/outputs()/items()/result()` reference, variables, loop scope, runAfter, bracket balance |
| `src/` | Unpacked solution (Solution.xml, Customizations.xml, Workflows/*.json, environment variable) |
| `dist/` | The importable zip |

```bash
export PAC=/path/to/pac        # Power Platform CLI (dotnet tool install Microsoft.PowerApps.CLI.Tool)
python3 build_solution.py && python3 validate.py
```
