# HouseNet monorepo contract / HouseNet մոնոռեպոյի պայմանագիր

This repository is the canonical HouseNet source of truth. The root `house-net-control.json` and `control-plane/policy/*.json` are the governance authority. Component directories preserve ownership boundaries; component files cannot weaken root policy.

Այս ռեպոզիտորին HouseNet-ի միակ կանոնական աղբյուրն է։ Արմատի `house-net-control.json`-ը և `control-plane/policy/*.json`-ը կառավարման հեղինակությունն են։ Բաղադրիչների պանակները պահպանում են սեփականության սահմանները և չեն կարող թուլացնել արմատային քաղաքականությունը։

Before changes, run the Control Plane preflight from `control-plane/bin/housenet-preflight --json`. Never commit secrets or local integration configuration. External writes remain behind the single Command Center Action Runtime and exact Gev approval. Use remote `main` as truth and merge only after all required CI is green.

Փոփոխությունից առաջ գործարկիր Control Plane preflight-ը։ Գաղտնիքներ կամ տեղական ինտեգրման կարգավորումներ երբեք մի commit արա։ Արտաքին գրումները մնում են Command Center-ի միակ Action Runtime-ի և Գևի ճշգրիտ հաստատման հետևում։ Remote `main`-ն է ճշմարտությունը, merge-ը թույլատրելի է միայն ամբողջական կանաչ CI-ից հետո։
