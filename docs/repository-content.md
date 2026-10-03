# Repository contents

The first commit contains the current A.3 design and the files needed to inspect,
maintain and use it. `.gitignore` keeps working artifacts out of Git without
deleting them from the local workspace.

| Included | Purpose |
|---|---|
| Root KiCad files, linked sheets, symbol/footprint libraries and library tables | Editable current schematic and placement-only PCB |
| `firmware/` source, tests, configuration and build record | Arduino/PlatformIO project |
| `docs/`, `AGENTS.md`, `README.md` | Customer instructions and engineering practices/reviews |
| Final BOM CSVs, `bom/parts.json`, `bom/design-components.json` | Exact selected assembly parts and generator input |
| `scripts/` except the historical sourcing helper | Current design generation, checks and document rendering |
| Selected `analysis/` fixtures and summaries | Final native netlist, contract checks, placement and analog/stop evidence |
| Selected `datasheets/` fact JSON | Current curated manufacturer facts and source references |
| Current schematic PDF, user-guide PDF and top-view PNG/PDF | Ready-to-read customer/design previews |

Ignored local material includes prior revisions, the older `README 2.md`,
Python/PlatformIO caches and virtual environments, temporary page renders,
downloaded manufacturer documents/models, sourcing candidates, raw simulation
traces/logs and large analyzer dumps. Their absence from a clone does not remove
the qualification limits recorded in the engineering reviews. References to
those raw files in historical review narratives describe the local audit
workspace, not additional files shipped in the repository.

## Regeneration

Use KiCad 10 and Python 3. Export a fresh native verification fixture when the
schematic changes:

```sh
mkdir -p analysis
kicad-cli sch export netlist --format kicadxml --output analysis/Universal_Poofer_Control.net Universal_Poofer_Control.kicad_sch
python3 scripts/validate_a3.py
python3 scripts/verify_hardware_stop.py --self-test
```

The builders overwrite generated design files; first reconcile manual/unsaved
edits as required by `AGENTS.md`. PCB generation/verification uses KiCad's
`pcbnew` Python environment. `scripts/render_pcb_preview.py` uses the selected
placement metadata; guide rendering requires ReportLab and Pillow and uses the
committed preview PNG. Firmware setup/build commands are in `firmware/README.md`.

Simulation scripts regenerate local working decks and traces with ngspice. The
preserved `analysis/source_loop_independent/baseline_native.cir` is deliberately
versioned because the independent comparison needs its pre-correction input.
The optional TI macro-model experiment requires a separately obtained vendor
model; its unresolved result remains documented, not claimed as a passing test.

Before committing, inspect `git status --short` and `git diff --cached --stat`.
Do not use `git add -f` for local working artifacts. Inventory snapshots are
dated evidence and must be rechecked before ordering.
