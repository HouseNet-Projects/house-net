# HouseNet agent map

This repository is governed by `HouseNet-Projects/house-net-control-plane`.
Read `house-net-control.json` for the approved classification and immutable policy lock.
Load `/home/gevorg/house-net-control-plane` and run its `bin/housenet-preflight --json` before HouseNet work. Stop on any mandatory failure.
Read current `policy/manifest.json`, `policy/authority.json`, `policy/repository-classes.json` and the applicable domain rules. Never substitute remembered policy for current authority.
Validate this repository with `bin/validate-repository <repository-path> --expected-repository <owner/name>` from the control-plane.
Owner approval is required for configuration, repository creation, reclassification and exact destructive actions. A template or registry entry does not independently prove owner consent.
Human-facing HouseNet artifacts require complete English and Armenian content under the current control-plane policy; machine and agent files may remain English-only.
Never manually invent or synchronize HouseNet versions. Read the repository canonical version authority and use the approved version/release tooling; keep own and consumed versions distinct.
Follow the provider-neutral contract in `docs/AGENT-CONTRACT.md`; Claude and future agents are adapters, not policy authorities.
