# Core03 live-domain integration

This is a thin domain extension to existing WorldSession, Store and Live Fabric.
It reuses Core03 two-channel TDSE without changing its numerical kernels.
The electronic curve is a pinned historical first-principles input, not a table
of experiment outputs. Any future nuclear propagation computes a new psi.

`CoupledWorldSession` supports old state types and radial complex chi[2,255].
`prepare_coupled` creates a mathematical prepared state, explicitly unevolved.
`observe`, inherited `fork`, contracted `compare`, persistent exact arrays and
full active pulse/work/time metadata are implemented. No conversion to 2-ket.
`CoupledExecutionFabric` reuses original reservation/transport/failure journal.
Legacy molecular/hydrogen authority remains delegated unchanged. New model
requires its own release, exact source, resource, physical-parent and operation
grant. `CoupledExplorer` exposes this domain to the existing model interface;
no model is invoked by import, setup, tests or context creation.

Cloud worker reuses the inherited cgroup runtime and fixed dependencies.
Each requested propagation is divided into two segments with a real on-disk
checkpoint/readback between them, preserving total requested steps and field.
No timestep/grid changes or additional science are hidden in this check.
Full raw result is saved before numerical QA rejects a run.

Live launch (requires separately approved activated grant and frozen intent):
`python -B -m core03_live.controller ROOT GRANT_SHA INTENT_PATH`

Current preparation is ENGINE_INTEGRATED_NOT_LIVE_PROVEN. No old cloud grant
is reusable. No new cloud run or real-model trial has occurred in this tranche.
W2 remains INCOMPLETE; no novelty/reality or Core04 claim.
