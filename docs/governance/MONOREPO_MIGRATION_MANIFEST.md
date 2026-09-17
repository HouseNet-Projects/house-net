# HouseNet monorepo migration manifest / Միգրացիայի մատյան

Migration target: `HouseNet-Projects/house-net` (private). Method: non-squashed `git subtree add`, preserving each donor repository's commit history beneath its component prefix.

| Component | Donor repository | Donor main SHA at migration |
|---|---|---|
| control-plane | `HouseNet-Projects/house-net-control-plane` | `cfde3fb2533f03bb36364bb0db784e53016e4e4e` |
| design-system | `HouseNet-Projects/house-net-design-system` | `b686e920133a02460d199984b7498b25fced6faf` |
| command-center | `HouseNet-Projects/house-net-command-center` | `74a95615ee282501e1f1eb06a3675efae2bd4682` |
| knowledge | `HouseNet-Projects/house-net-knowledge` | `a6655e3c0070ee08c64d2799b6e31896d559672d` |
| vault | `HouseNet-Projects/house-net-vault` | `0caab9de9a8f46800a5f2f96a76d4ac0ca8b302e` |

Migration timestamp: 2026-09-17. The original repositories remain historical donors until cutover verification completes. No secrets or `~/.command-center` state are imported.

Միգրացիայի սկզբնական ռեպոզիտորիաները պահվում են որպես պատմական աղբյուրներ մինչև cutover-ի ամբողջական ստուգումը։ Գաղտնիքներ և `~/.command-center` վիճակ չեն ներմուծվել։
