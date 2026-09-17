# UI Design System

## English

Use tokens first, components second. Layouts use a responsive 12-column grid on wide screens and a single column below 720px. Prefer clear hierarchy, generous spacing, and one primary action per surface.

### Foundations

- **Navigation:** persistent product identity, current location, and a visible keyboard focus state.
- **Cards and tables:** use `radius.md`, `shadow.card`, cool-gray borders, and a restrained red authority accent.
- **Forms:** label every input, show required state, validation text, and a recovery action.
- **States:** active/success uses green, attention uses muted HouseNet red, critical uses primary red; never rely on color alone.
- **Dashboards:** show the time range, unit, source, and comparison for every KPI. Charts use the chart palette in `tokens/brand-tokens.json`.
- **Responsive behavior:** preserve reading order, collapse sidebars into labeled navigation, and keep tables horizontally scrollable rather than truncating values.

Reference markup lives in `examples/ui/`. It is portable HTML/CSS guidance, not a framework mandate.

## Հայերեն

Օգտագործեք նախ token-ները, հետո՝ components-ը։ Layout-ները լայն էկրանին օգտագործում են responsive 12-սյուն grid, իսկ 720px-ից ցածր՝ մեկ սյուն։ Պահեք հստակ hierarchy, բավարար տարածք և յուրաքանչյուր surface-ում մեկ հիմնական action։

### Հիմքեր

- **Նավիգացիա․** տեսանելի product identity, ընթացիկ տեղադրություն և keyboard focus-ի հստակ վիճակ։
- **Cards և tables․** օգտագործեք `radius.md`, `shadow.card`, սառը մոխրագույն եզրագծեր և զուսպ կարմիր accent։
- **Forms․** յուրաքանչյուր input պետք է ունենա label, required վիճակ, validation text և վերականգնման action։
- **States․** active/success-ը կանաչ է, attention-ը՝ մուգ HouseNet կարմիր, critical-ը՝ հիմնական կարմիր․ միայն գույնի վրա մի հիմնվեք։
- **Dashboards․** յուրաքանչյուր KPI-ի համար ցույց տվեք ժամանակահատվածը, միավորը, աղբյուրը և համեմատությունը։
- **Responsive վարք․** պահպանեք ընթերցման հերթականությունը, sidebar-ը փոխարինեք labeled navigation-ով և table-ի արժեքները մի կտրեք։

Օրինակ markup-ը `examples/ui/`-ում portable HTML/CSS guidance է և չի պարտադրում framework։
