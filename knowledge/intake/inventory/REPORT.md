# HouseNet Knowledge intake inventory / Knowledge-ի intake inventory

## English

Source: `HouseNet-Projects/house-net-command-center` at merged commit `9078f6a0467275350231615931d25d52c466d730`.
The inventory records 99 document-like source files. Owner decisions retired the Actions and Journal candidates from Knowledge canonicalization, and retired the duplicate Deputy Role/Charter candidates. Actions remains live Command Center / Deputy operational state. Journal is historical/reference material; its current tracked credential-like values were redacted in the source repository, while reachable Git history was reviewed without reproducing values. The detected values are historical Action Runtime APR approval identifiers: exact-action-bound, one-time, consumed or expired; no reusable live credential was found, so rotation is not required and history rewrite is not justified. Role.md and Job-description.md remain supporting human-facing views. One thin canonical Deputy identity reference points to the machine-owned `workspace_policy.json` identity field; it does not duplicate role content. No business fact was promoted without evidence, and encrypted recovery material remains outside Knowledge.

## Հայերեն

Աղբյուրը `HouseNet-Projects/house-net-command-center`-ն է՝ merge արված `9078f6a0467275350231615931d25d52c466d730` commit-ում։ Գույքագրումը ներառում է փաստաթղթային բնույթի 99 աղբյուրային ֆայլ։ Owner-ի որոշմամբ Actions և Journal գրառումները հանվել են Knowledge canonicalization-ի թեկնածուների ցանկից, իսկ Deputy Role/Charter-ի կրկնվող թեկնածուները նույնպես փակվել են։ Actions-ը մնում է Command Center / Deputy-ի live operational state-ը։ Journal-ը historical/reference նյութ է․ ընթացիկ tracked credential-like արժեքները redacted են, իսկ հասանելի Git history-ն վերանայվել է՝ առանց արժեքները վերարտադրելու։ Հայտնաբերված արժեքները historical Action Runtime APR approval identifiers են՝ exact-action-bound, one-time, consumed կամ expired։ Reusable live credential չի հայտնաբերվել, ուստի rotation-ը պահանջված չէ, իսկ history rewrite-ը հիմնավորված չէ։ Role.md և Job-description.md-ը մնում են supporting human-facing views։ Ստեղծվել է մեկ բարակ canonical Deputy identity reference, որը հղվում է մեքենայական `workspace_policy.json` identity դաշտին և չի կրկնօրինակում role-ի բովանդակությունը։ Առանց բավարար ապացույցի business fact չի canonicalized արվել, իսկ կոդավորված recovery նյութը մնացել է Knowledge-ից դուրս։

## Dedupe and contradiction pass / Կրկնությունների և հակասությունների փուլ

- English: Deterministic hash grouping found **0** duplicate source files across **0** repeated groups. No semantic contradiction was inferred from filenames or hashes; owner review remains required before any further canonicalization.
- Հայերեն․ Hash-երի դետերմինիստական խմբավորումը գտել է **0** կրկնվող աղբյուրային ֆայլ՝ **0** խմբում։ Միայն անուններից կամ hash-երից semantic հակասություն չի եզրակացվել․ հետագա canonicalization-ից առաջ owner review-ը շարունակում է պարտադիր մնալ։

## Migration ledger / Միգրացիայի ledger

- English: The 99-source ledger is conservative and concept-oriented. No additional source was promoted to canonical Knowledge. Live Actions remains Command Center state; Journal remains historical; policy/technical files remain with their owners; encrypted/recovery material remains behind the Vault boundary; binary Office pointers remain blocked source snapshots; active and reference material remains intake pending semantic, sensitivity and ownership review.
- Հայերեն․ 99 աղբյուրների ledger-ը պահպանողական է և concept-oriented։ Լրացուցիչ աղբյուր canonical Knowledge չի դարձել։ Live Actions-ը մնում է Command Center-ի state-ը, Journal-ը՝ historical, policy/technical ֆայլերը՝ իրենց սեփականատերերի մոտ, կոդավորված/recovery նյութը՝ Vault boundary-ի հետևում, Office pointer-ները՝ blocked source snapshots, իսկ active/reference նյութը՝ intake՝ semantic, sensitivity և ownership review-ի սպասումով։

Machine ledger: `knowledge/intake/inventory/ledger.json`.
