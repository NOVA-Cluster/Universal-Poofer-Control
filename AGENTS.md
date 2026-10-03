# Universal Poofer Control engineering standards

These instructions apply to the entire project, including generated KiCad files,
PCB placement scripts, reviews, documentation, and firmware. The user's latest
electrical requirements take precedence over obsolete revisions.

## Customer documentation is a maintained source of truth

- `docs/hardware-user-guide.md` is the canonical customer-facing source of truth
  for published features, supported uses, wiring and operation. Write for a
  purchaser using the board for the first time, without conversation context.
- Keep it accurate against native schematic/PCB nets, firmware behavior and
  approved qualification. Update it in the same change whenever pin mappings,
  supplies/current limits, polarity, wetting/protection, stop/restart, jumpers,
  expansion/I2C, programming, commands/timeouts or use cases change. Distinguish
  GPIO numbers, physical module pads and header pin numbers explicitly.
- The design/firmware implement behavior; the guide defines the published
  customer contract. Reconcile a disagreement before releasing instructions or
  claiming compatibility. Do not silently use an older README/archive as truth.
- Separate hardware capability, supplied software, application work and tested
  ratings. Preserve preview/qualification limits until evidence supports a new
  release. Nominal wetting, simulated fault survival, relay contact rating and
  software chain allocation are not unconditional operating guarantees.
- Maintain practical features/use cases, pin-accurate diagrams, first-use setup,
  commissioning, troubleshooting and schematic navigation. Account for pulse
  limits, the 500ms lease, explicit rearming and physical valve behavior.
- Generate `output/pdf/Universal_Poofer_Control_Hardware_User_Guide.pdf` from
  the Markdown using `scripts/render_hardware_user_guide.py`; never hand-edit
  the derivative. Synchronize figures, revision/date, links, connector reference
  and README entry points. Inspect every rendered page before delivery.
- Cross-check consequential documentation facts against actual nets and code;
  record verification evidence. Do not rerun unrelated hardware tests for prose
  changes. Accurate customer documentation is part of completing a revision,
  with the same importance as its schematic and firmware.

## Persistent design requirements

- Eight ESP32-S3-controlled mechanical-relay outputs for 12 VDC valves, up to
  1 A per channel; 10 A relay contact capability is not a connector rating.
- Inputs are **dry contacts switched to ground, active low**. The board supplies
  nominal 20 mA wetting current through a closed contact. Preserve continuous
  +100 V and -100 V fault tolerance, including board power transitions.
- An emergency stop must inhibit the output driver and remove relay-coil power
  in hardware. Software observes its protected permissive signal and cannot
  override the hardware stop. Opening or disconnecting the NC loop is a stop.
- Use JLCPCB-assembly parts with exact MPN, manufacturer, LCSC, footprint,
  stock/category evidence, and datasheet. Prefer Basic parts where appropriate.
- Use **0805 or larger** resistors and capacitors. Select easy-to-rework SOIC,
  SOT-23, DPAK, SOT-223, SMA/SMB or larger packages; do not shrink parts to save
  area. Keep exact package dimensions and pad numbering tied to the selected MPN.
- Expansion exposes buffered 595/165 chains and I²C on 2.54 mm headers. Use
  independent module supplies, selectable common I²C pullups, and documented
  power-off isolation. The physical host/expander role cannot be changed by a
  GPIO. Preserve all chain pin assignments in hardware and firmware contracts.
- A restored emergency-stop loop must leave the hardware latch stopped until a
  fresh arm edge. Propagate actual hardware inhibit downstream, so firmware
  cannot prevent a stop reaching expanded output modules.
- Detect loss of the raw 12 V and 5 V supplies with circuitry powered from the
  logic rail, and clear the hardware RUN latch. Do not assume an unpowered
  comparator reports a particular state. Supply restoration must not generate
  an arm clock. Verify the clear path against actual comparator low-voltage
  specifications and power-up recovery timing.
- Expose external interfaces on 2.54 mm headers. Do not claim a 10 A path through
  a 3 A header; valve feed currents are independent external circuits.
- PCB placement is currently authorized; **do not route tracks, add vias, or
  fill copper zones until the user asks for routing**. Antenna keepouts are allowed.

## Schematic quality is a durable engineering requirement

The schematic must be a document a company can retain and review for years.
Treat readability and appearance as deliverables, not optional decoration.

- Organize the hierarchy by function: system overview, controller/programming,
  power, serial I/O, protected contact receivers, wetting/current protection,
  emergency stop, and relay/load drivers. Use a readable page count rather than
  cramming unrelated circuits onto a large sheet.
- Give each sheet a numbered title, revision, date, signal directions, and brief
  engineering notes. Keep the printed page order deterministic.
- Draw clearly bounded functional blocks with short titles and useful design
  intent. Repeated channels use identical layouts, orientation, spacing, and
  reference patterns; shared circuitry is separate from channel circuitry.
- Use actual wires to show local circuit operation. Reserve named labels and
  hierarchical/global ports for interfaces and genuinely distant connections.
  A page made of isolated symbols with labels on every pin is unacceptable.
- Read left-to-right for signal flow, put supplies above circuits and returns
  below, minimize crossings, and show all joins explicitly. Keep labels and
  values horizontal and clear of wires, symbols, and each other.
- Use a 50 mil/1.27 mm electrical grid and consistent text sizes. Keep notes,
  titles, and components inside printable margins; do not overlap the title block.
- Include current directions, input polarity, fault behavior, supply limits,
  connector pin functions, and safety-state truth tables where they aid review.
- Render every changed sheet to a PDF/image, inspect it visually, and correct
  overlap, crowding, bad alignment, and missing information before delivery.

## PCB placement quality

- Choose the smallest practical rectangular board that preserves serviceability,
  field-voltage spacing, antenna clearance, and symmetric channel groups.
- Place footprint origins on a documented 0.5 mm grid; use 90-degree rotations
  unless a package requires otherwise. Preserve package-internal pad geometry.
- Use repeated input and relay cells, edge-accessible connectors, a distinct
  controller region, a power region, and an emergency-stop region. Place bypass
  capacitors at their ICs and keep current paths compact before routing begins.
- Maintain courtyard and mounting clearance. Distinct raw inputs can differ by
  200 V under simultaneous opposite faults; account for that spacing, not only
  each input's 100 V-to-ground limit.
- Keep user-facing silkscreen clean: channel/function labels, connector pin-1
  and polarity, revision, and clear safety markings. Put dense assembly references
  on fabrication/assembly layers when necessary. Verify text is legible and
  does not overlap exposed copper or solder mask openings.
- Preserve the ESP32 module antenna keepout and board-edge antenna placement.
- Check component count, pads/nets, origin grid, board size, orientation, and
  native DRC. Document all unrouted connections as an intentional stage, without
  describing the PCB as fabrication-ready.
- Deliver an editable board and an inspected top-view preview.

## Review, evidence, and change control

- Preserve the prior revision before a broad redesign. Check for manual edits
  and unsaved editor work before running generators; do not overwrite user work.
- Run native KiCad ERC and placement DRC; cross-check schematic and PCB netlists.
  Run applicable schematic, PCB, cross-analysis, EMC, thermal, and SPICE workflows.
  Account explicitly for unrun or inapplicable checks.
- Independently verify critical pin maps, diode polarity, transistor terminals,
  regulator stability, emergency-stop logic, supply sequencing, fault dissipation,
  relay contact mappings, and component voltage/current/thermal derating against
  manufacturer evidence. Analyzer consistency alone is not physical verification.
- Triage heuristic false positives and report their evidence. Fix demonstrated
  design problems; distinguish unresolved hardware qualification from a proven
  schematic error and from work intentionally deferred by the user.
- Keep review reports, source facts, simulations, BOMs, and firmware pin contracts
  consistent with the final revision. Never use an old active-high input contract.
- Make no certification or guaranteed shutdown-time claim without the required
  physical tests. Coil shutdown does not guarantee a welded contact opens; system
  valve power must use an appropriate independent disconnect when required.
- Firmware starts inhibited with zero relay commands, requires explicit arming,
  latches emergency-stop disarm, and uses bounded pulses and command/watchdog
  timeouts. Firmware must never substitute for the hardware emergency stop.

## Repository hygiene

- Keep Git focused on the current editable KiCad design, local libraries, firmware
  source/tests, maintained documentation, final BOM/source data and selected review
  evidence. Retain current customer PDFs and the preview used by the guide.
- Exclude build environments, caches, temporary renders, raw simulation traces,
  downloaded vendor files, sourcing experiments and superseded local revisions.
  Preserve excluded work locally unless deletion is explicitly requested.
- Follow `.gitignore` and `docs/repository-content.md`. Review new untracked files
  before staging; do not force-add ignored artifacts to make a script work.
- Keep source fixtures needed to reproduce reviews, and explain optional local
  evidence versus repository evidence. Do not imply an ignored archive or raw
  report is included in a fresh clone.
