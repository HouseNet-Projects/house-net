# HouseNet agent contract

## English

Every engineering agent is an interchangeable execution client of the HouseNet Control Plane. Before changing a target, an agent must:

1. verify the environment and authorized identity;
2. load the current control plane and run preflight;
3. identify whether the task is greenfield or migration;
4. read the target registration, classification, version authority, and applicable rules;
5. verify owner approval before governed changes;
6. use deterministic HouseNet tooling;
7. validate, test, and report the result.

Agent-specific files are thin adapters to this contract. They do not own policy, and a provider used to build software must not become an unapproved runtime dependency.

---

## Հայերեն

Յուրաքանչյուր ինժեներական գործակալ HouseNet Control Plane-ի փոխարինելի կատարող հաճախորդն է։ Թիրախը փոխելուց առաջ գործակալը պետք է՝

1. ստուգի միջավայրը և թույլատրված ինքնությունը,
2. բեռնի ընթացիկ Control Plane-ը և գործարկի preflight-ը,
3. որոշի՝ աշխատանքը նոր է, թե միգրացիա,
4. կարդա թիրախի գրանցումը, դասը, տարբերակի աղբյուրը և կիրառելի կանոնները,
5. կառավարվող փոփոխություններից առաջ ստուգի սեփականատիրոջ հաստատումը,
6. օգտագործի դետերմինիստական HouseNet գործիքները,
7. վավերացնի, թեստավորի և զեկուցի արդյունքը։

Գործակալին հատուկ ֆայլերը այս պայմանագրի բարակ ադապտերներն են։ Դրանք քաղաքականության աղբյուր չեն, և ծրագրային ապահովումը կառուցող մատակարարը չպետք է դառնա չգրանցված runtime կախվածություն։
