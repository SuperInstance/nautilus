# Trail 001 — Next Session Targets

## Immediate (holodeck-studio)

1. **Fix the 3 bugs** — double-self in handler.handle(), missing Projection import, OOC mask inconsistency. All have xfail tests ready to flip green.
2. **Wire flux_lcar.py gauges** — Call `flux_lcar.wire(handler)` in server.py startup. Verify gauge rendering in MUD sessions.
3. **Wire comms_system** — Fleet message relay inside the MUD. Low-hanging integration.
4. **Wire algorithmic_npcs** — Procedural NPC spawning. Depends on flux_lcar for status display.

## Infrastructure

5. **GitHub Actions CI for holodeck-studio** — Run the 167-test suite on push and PR. Gate merges on green. Python 3.11, pip install -r requirements, pytest.

## Fleet Engagement

6. **Claim a P1 task from oracle1-index** — Review TASKS.md, pick an unclaimed P1, leave a claim comment in oracle1-vessel issues.
7. **Explore Lucineer org** — 401 forked repos. Scan for: active development, test gaps, patterns worth adopting. Likely low-hanging fruit for archaeology work.
8. **Check lcar_scheduler status** — Critical-path dependency for holodeck-studio's tick system. If it's stable, begin integration work.
