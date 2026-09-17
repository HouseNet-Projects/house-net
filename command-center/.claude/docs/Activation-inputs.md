# Activation inputs — Deputy integrations (Telegram · WhatsApp · Bitrix24 · MikroBILL)

Everything in code, contracts, tests and evals for these integrations is production-ready. What remains for each is only:

`CONFIGURE → IDENTITY VERIFY → REAL READ → LIVE CERTIFY → OPTIONAL CONTROLLED WRITE CERTIFY`

No secret ever enters Git, the audit, the durable export, an approval card or an error message. Secrets live **outside the repository**, in one of two places (the environment wins over the file):

| Where | Shape |
|---|---|
| Environment | `CC_<INTEGRATION_ID with - → _>_<FIELD>` — e.g. `CC_INT_TG_BOT_TOKEN` |
| File | `~/.command-center/integrations/<INTEGRATION_ID>.json` — a flat JSON object with the field names below |

Check the state at any time (values are never printed, only field NAMES):

```
python .claude/integrations/integration.py readiness
python .claude/integrations/integration.py certify        # real identity + read certification (read-only)
```

---

## INT-TG — Telegram (official Bot API)

**Required**

| field | meaning |
|---|---|
| `bot_token` | the token BotFather gave for Deputy's bot (`123456789:AA…`) |
| `allowed_chat_ids` | comma-separated chat ids (groups are negative, e.g. `-1001234567890`) whose messages count as business evidence |

**Optional**

| field | meaning |
|---|---|
| `allowed_user_ids` | user ids allowed in private chats with the bot |
| `expected_bot_username` | e.g. `deputy_housenet_bot` — identity is VERIFIED only when getMe matches |
| `mode` | `polling` (default, no public endpoint needed) or `webhook` |
| `webhook_secret` | required in webhook mode; Telegram sends it in `X-Telegram-Bot-Api-Secret-Token` |
| `observe_unknown` | `true` to keep messages from non-allowlisted chats as UNTRUSTED evidence (default: dropped) |

Template `~/.command-center/integrations/INT-TG.json`:

```json
{"bot_token": "<BotFather token>", "allowed_chat_ids": "-1001234567890,123456789", "allowed_user_ids": "123456789", "expected_bot_username": "deputy_housenet_bot", "mode": "polling"}
```

**Activation steps** — 1) create the bot in BotFather, 2) add it to the allowed group(s) / start it in private chats, 3) put the config outside Git, 4) `integration.py certify` → identity VERIFIED (getMe = expected username) → `chat.messages` REAL READ → VERIFIED_READ, 5) optional write certification: Deputy prepares one `chat.send` to an allowed chat, Gev approves, the message is sent; the Bot API returns a message id (provider acceptance) — **no independent read-back exists for a bot's own message**, so the action stays `EXECUTED_UNVERIFIED / NO_INDEPENDENT_READBACK` (canonical PARTIAL) until Gev confirms the message is visible in the chat. That confirmation is the second-source evidence a `VERIFIED_WRITE` would need.

---

## INT-TG — Telegram Business / Secretary Mode (same integration, second inbound source)

Business mode does **not** add an integration. The same `INT-TG` stays canonical and gains a second inbound source under one update stream:

| Source mode | What it is |
|---|---|
| `BOT_CHAT` | people write **to the bot** directly (private or allowed group) — the original behaviour, unchanged |
| `BUSINESS` | people write **to Gev's own account**, and the connected bot observes only the chats Gev selected |

**Extra config fields** (same file, `~/.command-center/integrations/INT-TG.json`, or `CC_INT_TG_*`):

| field | meaning |
|---|---|
| `business_allowed_user_ids` | Deputy's OWN second allowlist. A business message counts as evidence only if the sender is here. Telegram-side scope is not Deputy authority |
| `business_allowed_chat_ids` | optional, for business reply targets |
| `business_account_user_id` | optional, Gev's Telegram user id; a connection from another account is refused as WRONG_TENANT |

**Manual activation steps (Telegram UI).**

1. In [@BotFather](https://t.me/botfather), enable **Business Mode** (the docs also call it *Secretary Mode*) for `@HouseNetDeputyBot`.
2. On Gev's own account open **Settings → Telegram Business → Chatbots** and add `@HouseNetDeputyBot`.
3. In the recipient scope choose **only the specific private chats** intended. Do not enable all existing chats, all contacts, or all new chats.
4. Grant the **minimum** rights needed. Reply rights are only required later, for the optional outbound certification.
5. Have one selected person send one harmless message, then run the certification.

Telegram has used more than one label here (`Settings > Telegram Business` in the original announcement, and a newer *Chat Automation* entry point in later builds). If the client shows a different label, report the actual path rather than forcing these names.

**What Deputy will and will not do.** Business messages are read-only observation: no read receipts are sent, nothing is marked read for Gev, and nothing is edited, deleted or pinned. History from before the connection existed is **not** available and is never claimed. Outbound on Gev's behalf stays under the approval law: `rights.can_reply` is a provider capability, never authority, so every reply is still a prepared card that Gev approves, and a changed or disabled connection turns an approved-but-unsent action into `STALE_CONFLICT` instead of a send.

---

## INT-WA — WhatsApp Business (official Cloud API)

**Required**

| field | meaning |
|---|---|
| `access_token` | System-user / app access token with `whatsapp_business_messaging` |
| `phone_number_id` | the business phone number id (Meta app → WhatsApp → API setup) |
| `verify_token` | any secret string; Meta sends it back in the webhook handshake |
| `app_secret` | the Meta app secret used to sign webhook requests (`X-Hub-Signature-256`) |
| `allowed_numbers` | comma-separated E.164 numbers whose messages count as business evidence |

**Optional**

| field | meaning |
|---|---|
| `business_account_id` | WABA id — events for another WABA are rejected as WRONG_TENANT |
| `expected_display_phone` | e.g. `+374 99 000 002` — identity VERIFIED only when the provider matches |
| `webhook_host` / `webhook_port` / `webhook_path` | listener binding (default `127.0.0.1:8788` `/webhooks/whatsapp`) |
| `observe_unknown` | keep messages from non-allowlisted numbers as UNTRUSTED evidence |

Template `~/.command-center/integrations/INT-WA.json`:

```json
{"access_token": "<token>", "phone_number_id": "111222333", "business_account_id": "555", "verify_token": "<random secret>", "app_secret": "<app secret>", "allowed_numbers": "+37499000001,+37499000002", "expected_display_phone": "+374 99 000 002", "webhook_host": "127.0.0.1", "webhook_port": 8788, "webhook_path": "/webhooks/whatsapp"}
```

**Activation steps** — 1) config outside Git, 2) start the listener explicitly (`python .claude/integrations/whatsapp_webhook.py`) behind a public HTTPS reverse proxy/tunnel (deployment, not code), 3) in the Meta app point the webhook at that URL with the `verify_token` → handshake VERIFIED (readiness shows `callback: VERIFIED`), 4) `integration.py certify` → identity VERIFIED → inbound messages arrive through the signed webhook → `chat.messages` REAL READ, 5) optional write certification: one `chat.send_text` (inside the 24-hour customer-service window) or `chat.send_template` (approved template) to an allowed number, Gev approves; the send is `AWAITING_PROVIDER_STATUS` until the delivery status arrives through the webhook, then reconciliation marks it VERIFIED.

---

## INT-B24 — Bitrix24 (incoming webhook, read-only)

| field | meaning |
|---|---|
| `webhook_url` | incoming webhook URL (`https://housenet.bitrix24.ru/rest/<user>/<code>/`) with read scopes only (crm, tasks, user) |
| `portal_domain` | `housenet.bitrix24.ru` — the expected portal; a different portal is refused as WRONG_TENANT |

Template `~/.command-center/integrations/INT-B24.json`:

```json
{"webhook_url": "https://housenet.bitrix24.ru/rest/1/<code>/", "portal_domain": "housenet.bitrix24.ru"}
```

Then `integration.py certify` → identity (profile) VERIFIED → crm.deals / crm.leads / tasks REAL READ. Writes stay declared (`tasks.create`, `crm.deal.update`, `crm.activity.create`) until a Gev-approved live certification.

---

## INT-MB — MikroBILL

**DEFERRED by Gev (2026-09-12).** No implementation work, no activation request, no nag in briefs. Billing-sourced KPIs report `UNAVAILABLE` and `TARGET_UNKNOWN` until the deferral is lifted; the readiness view shows `DEFERRED`.

---

## Scheduler (proactive routines)

Routines exist (`skill.py routine morning|midday|eod|weekly`) and run on demand. The scheduler is reported `NOT_CONFIGURED` until an external trigger (Windows Task Scheduler / cron) invokes `skill.py routine <name> --from-scheduler`, which writes the heartbeat. Nothing runs in the background by itself, and no routine sends anything anywhere: delivering a routine result to a chat or mailbox is an Action Runtime approval.
