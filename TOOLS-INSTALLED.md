# Tools installed for this project

| what | why | uninstall |
|---|---|---|
| `.venv` + **ezdxf 1.4.x** | the DXF generator and audit | `rm -rf ~/work/claude/chore-tracker-mount/.venv` |
| `.venv` + **gmsh 4.15 (pip wheel, bundles the binary)**, **scikit-fem 11**, numpy, scipy, meshio | `plate_fea.py`: a Kirchhoff plate finite-element check of the body plate with its real holes, replacing the strip-beam estimate with a plate answer. Installed 2026-09-01 at Charles's request. Homebrew has no CalculiX formula, so this is the pure-pip route. | same `rm -rf .venv`; nothing outside it was touched |

Nothing was installed system-wide and no system configuration was changed.
