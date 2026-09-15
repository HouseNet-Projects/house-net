# HouseNet vault agent contract

This repository is governed by `HouseNet-Projects/house-net-control-plane`.
Run the current control-plane preflight before work. Vault stores references and encrypted recovery metadata only; it is never a password store. Never write, print, decrypt, rotate or test with live secret values. Fail closed when required material is unavailable.

Run `/home/gevorg/house-net-control-plane/bin/housenet-preflight --json` before work.
Read `house-net-control.json` for the immutable repository lock.
