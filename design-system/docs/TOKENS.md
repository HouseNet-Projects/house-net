# Token contract

## English

`tokens/brand-tokens.json` is the canonical token source. Token names are stable API: products may consume them, but must not redefine the same semantic role locally. Values use observable HouseNet palette values or explicit design mappings. References use `{group.name}` and are checked by CI.

Add a token only when it represents a repeated design decision. Document a breaking rename as a major version change. Keep source/provenance in the token file or the linked brand note.

## Հայերեն

`tokens/brand-tokens.json`-ը token-ների կանոնական աղբյուրն է։ Token անունները կայուն API են․ արտադրանքները կարող են օգտագործել դրանք, բայց նույն semantic role-ը տեղում չվերասահմանեն։ Արժեքները HouseNet-ի դիտվող գույներն են կամ բացահայտ design mapping-ներ։ `{group.name}` reference-ները ստուգվում են CI-ով։

Նոր token ավելացրեք միայն կրկնվող design decision-ի համար։ Breaking rename-ը փաստաթղթավորեք major version-ի փոփոխությամբ։ Աղբյուրն ու provenance-ը պահեք token file-ում կամ կապված brand note-ում։
