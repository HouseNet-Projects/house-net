# HouseNet brand source

## English

This brand layer uses first-party assets served by the official HouseNet website.

## Preserved logo assets

| Asset | First-party source | SHA-256 | Use |
| --- | --- | --- | --- |
| `housenet-main-logo.svg` | `https://www.housenet.am/storage/settings/main-logo.svg` | `a903655a7180e4cbb94145002b391e44c1059cb04b56dde4277ab06f569c8345` | Light surfaces; original source preserved byte-for-byte |
| `housenet-footer-logo.svg` | `https://www.housenet.am/images/logo.svg` | `06ea8739ca3f3aa9759328a776eeae048c8fbf4633ca4b1f51414e2a59842b3b` | Dark surfaces; original source preserved byte-for-byte |

The homepage exposes the first source as its main logo and the second as its footer logo. Both are served from `www.housenet.am`; no third-party host or hotlink is used in this repository.

## Palette provenance

The logo directly contains `#E3003A`, `#1D1D1B`, `#6F6F6E`, `#8A1230`, and white. The official first-party homepage stylesheets also use `#E4003A`, `#1C2125`, `#464F55`, `#EDF3F6`, `#D1DCE2`, `#979FA3`, `#F6F9FB`, `#A9143D`, and `#78AD57`. These values are observable source colors, not guessed corporate colors.

`brand-tokens.json` assigns those observed values to interface roles. The role names are design-system mappings; only the `source` values are claimed as directly observed HouseNet colors. `success`, `warning`, and `critical` are semantic uses of observed colors, not additional official logo colors.

## Design rule

The preserved logo geometry is never redrawn, recolored, or edited. The control-plane hero uses the original files as local `<image>` references and keeps the operational status text separate from the mark.

---

## Հայերեն

# HouseNet բրենդի աղբյուր

Այս շերտը օգտագործում է HouseNet-ի պաշտոնական կայքից ստացված առաջին կողմի asset-ները։ `housenet-main-logo.svg`-ը և `housenet-footer-logo.svg`-ը պահպանված են byte-for-byte անփոփոխ և ունեն աղբյուր URL-ներն ու SHA-256 checksum-ները աղյուսակում։ Ոչ մի երրորդ կողմի host կամ hotlink չի օգտագործվում։

Լոգոյի մեջ դիտվում են `#E3003A`, `#1D1D1B`, `#6F6F6E`, `#8A1230` և սպիտակը։ Պաշտոնական կայքի CSS-ից դիտվում են նաև `#E4003A`, `#1C2125`, `#464F55`, `#EDF3F6`, `#D1DCE2`, `#F6F9FB`, `#A9143D` և `#78AD57`։ Դրանք գրանցված են `brand-tokens.json`-ում՝ դերային mapping-ով։ Լոգոն չի վերագծվում, չի ձգվում և չի վերագունավորվում։
