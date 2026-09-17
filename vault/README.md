# HOUSE NET · VAULT

## English

The secure reference and recovery metadata foundation for HouseNet. This repository never stores plaintext passwords, tokens, private keys, provider records or live production secrets. It records encrypted or external references, ownership, recovery requirements and integrity metadata.

### Boundary

- `vault/references/` — non-secret reference metadata
- `vault/manifests/` — recovery manifests
- `vault/intake/` — proposed references awaiting review
- `vault/archive/` — historical references
- `schemas/` and `bin/` — fail-closed validation

The external recovery key and secret backends remain outside Git.

## Հայերեն

HouseNet-ի անվտանգ հղումների և վերականգնման մետատվյալների հիմքն է։ Այս պահոցում երբեք չեն պահվում պարզ տեքստով գաղտնաբառեր, token-ներ, private key-եր, մատակարարների գրառումներ կամ արտադրական գաղտնիքներ։ Պահվում են միայն կոդավորված կամ արտաքին հղումներ, սեփականատերը, վերականգնման պահանջները և ամբողջականության մետատվյալները։

### Սահման

- `vault/references/` — ոչ գաղտնի հղումների մետատվյալներ
- `vault/manifests/` — վերականգնման մանիֆեստներ
- `vault/intake/` — ստուգման սպասող առաջարկված հղումներ
- `vault/archive/` — պատմական հղումներ
- `schemas/` և `bin/` — փակվող վավերացում

Արտաքին recovery key-ը և գաղտնիքների պահոցները մնում են Git-ից դուրս։
