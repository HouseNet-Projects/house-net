# HouseNet migration lifecycle

## English

HouseNet intake is staged and non-destructive:

`DISCOVERED → QUARANTINED → AUDITED → PROPOSED → OWNER_APPROVED → MIGRATED → CERTIFIED → CANONICAL`

The provider-neutral `bin/housenet-import` tool inventories a source, records hashes and findings, and validates evidence. It never imports, deletes, rewrites, deploys, or canonicalizes a project. Conflicting source candidates, likely secrets, unknown sensitivity, missing owner approval, and unresolved ownership keep a project out of the canonical state.

Operational class (`A`, `B`, `C`) is separate from data classification (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, or `UNKNOWN`). A legacy project may carry controlled language debt, but new or finalized human-facing HouseNet documentation remains English and Armenian.

## Հայերեն

HouseNet-ի ընդունումը փուլային և ոչ կործանարար է՝

`DISCOVERED → QUARANTINED → AUDITED → PROPOSED → OWNER_APPROVED → MIGRATED → CERTIFIED → CANONICAL`

Մատակարարից անկախ `bin/housenet-import` գործիքը գույքագրում է աղբյուրը, պահպանում հեշերն ու հայտնաբերված խնդիրները և ստուգում ապացույցները։ Այն երբեք չի ներմուծում, ջնջում, վերաշարադրում, տեղակայում կամ ինքնուրույն կանոնականացնում նախագիծը։ Հակասող աղբյուրները, հնարավոր գաղտնիքները, անհայտ զգայունությունը, սեփականատիրոջ հաստատման բացակայությունը և չլուծված սեփականության հարցերը պահում են նախագիծը canonical վիճակից դուրս։

Գործառնական դասը (`A`, `B`, `C`) առանձին է տվյալների դասակարգումից (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED` կամ `UNKNOWN`)։ Հին նախագիծը կարող է ունենալ վերահսկվող լեզվական պարտք, սակայն HouseNet-ի նոր կամ վերջնականացված մարդուն ուղղված փաստաթղթերը շարունակում են լինել անգլերեն և հայերեն։
