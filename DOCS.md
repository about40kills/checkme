# CheckMe — Project Documentation

## Overview

CheckMe is a WhatsApp-based mobile money safety tool designed for Ghanaian users. Before sending money via MTN MoMo, Telecel Cash, or AT Money, a user can verify the registered name behind any phone number by simply messaging the bot. The goal is to reduce misdirected transfers and fraud by giving users a way to confirm recipient identity before committing to a transaction.

The bot supports two local languages — **Twi** and **Ewe** — alongside English, making it accessible to users who are more comfortable in their mother tongue.

---

## How It Works (Text Flow)

### 1. Number Lookup

A user sends any message containing a Ghanaian mobile number to the WhatsApp bot. The message can be typed in any natural form:

| User input | Detected number |
|---|---|
| `check 0244123456` | `0244123456` |
| `024 412 3456` | `0244123456` |
| `+233244123456` | `0244123456` |
| `0244123456 for me please` | `0244123456` |

The extraction logic (`lookup.py`) handles:
- Plain 10-digit local numbers (`0XXXXXXXXX`)
- International format with country code (`+233XXXXXXXXX` or `233XXXXXXXXX`)
- Numbers with spaces, dashes, or parentheses
- 9-digit numbers without the leading zero

All extracted numbers are normalised to canonical `0XXXXXXXXX` format before lookup.

---

### 2. Language Selection

After a valid number is detected, the bot asks the user to select a reply language before revealing the result:

```
Select your language:
1. Twi
2. Ewe
```

A combined bilingual voice prompt is also sent so both Twi and Ewe speakers understand the request without needing to read the text.

The user replies with `1` (Twi) or `2` (Ewe). Their language preference is stored in the session for the rest of that conversation flow.

---

### 3. Lookup Result

**If the number is found:**

The bot replies with:
- The registered display name
- A category hint describing the account type (individual, merchant, church, school, susu group, NGO, or agent)
- A prompt asking whether the user wants to proceed with sending money

Example (Twi):
> Nɔmba 0244123456 din de Kofi Mensah. Hwɛ sɛ ɛne onipa aa wopɛ sɛ wo soma sika no ne nɔmba no yɛ pɛ ansa na wo asoma sika no. Yei yɛ ankorankoro akoanto. Wopɛ sɛ wo soma sika no ma no? Fa YES na kɔ wo anim.

Example (Ewe):
> Nɔmba 0244123456 ŋkɔ nye Kofi Mensah. Kpɔ be eya nye ame si wòdzɔ na la esime ado ga. Esia nye ŋutɔ ame aɖeke tɔ akoanto. Èdi be ado ga na wo? Ŋlɔ YES be wòyi edzi.

**If the number is not found:**

The bot advises the user to double-check the number or ask the recipient to confirm their account details, and explicitly warns never to share a PIN.

---

### 4. Account Category Hints

When a number is found, the bot includes a hint about the account type to help the user make an informed decision:

| Category | Twi hint | Ewe hint |
|---|---|---|
| `individual` | Personal account | Personal account |
| `merchant` | Business / shop account | Business / shop account |
| `church` | Church account | Church account |
| `school` | School account | School account |
| `susu_group` | Savings group account | Savings group account |
| `ngo` | Community organisation account | Community organisation account |
| `agent` | Mobile money agent account | Mobile money agent account |

This matters because sending money to a merchant or agent account by mistake is harder to reverse than a personal transfer.

---

### 5. Transfer Flow (Post-Confirmation)

Once the user confirms they want to proceed (replying `YES` or equivalent), the bot walks them through a simulated transfer:

1. **Amount** — User enters the GHS amount to send
2. **Reference** — User enters an optional reference note (e.g. "school fees", "rent")
3. **PIN prompt** — Bot shows a summary of the transaction and instructs the user to enter their MoMo PIN via the real MTN *170# USSD channel. The bot itself never handles or receives PINs.

The PIN step is intentionally handed back to the real network USSD session for security. CheckMe confirms the name and prepares the transfer details — it does not execute the transaction directly.

---

### 6. USSD Simulation (*170#)

Typing `*170#` triggers a simulated MTN MoMo USSD menu. This is a demo feature that mirrors the real MTN MoMo menu structure:

```
MTN MoMo (*170#)
1. Send Money
2. Cash Out
3. Buy Airtime
4. Check Balance
5. Mini Statement
0. Cancel
```

Each option leads into a guided sub-flow:

| Menu item | Sub-flow |
|---|---|
| **Send Money** | Enter number → name confirmation → amount → reference → PIN handoff |
| **Cash Out** | Enter agent/own number → amount → PIN handoff |
| **Buy Airtime** | Enter target number → amount → confirmation |
| **Check Balance** | PIN entry → demo balance display |
| **Mini Statement** | PIN entry → last 5 demo transactions |

All data shown in balance and statement screens is demo data. No real account values are read or written.

---

### 7. Session State Management

Each user's conversation is tracked in an in-memory session store (`SESSIONS` dict in `app.py`). Sessions are keyed by WhatsApp number and hold:

- Current flow state (e.g. `LANG_SELECT`, `AWAITING_AMOUNT`, `USSD_ENTER_NUMBER`)
- Selected language (`tw` or `ee`)
- Pending number being looked up
- Target name, amount, and reference during a transfer flow

Sessions are cleared when a flow completes, is cancelled, or when the user sends a new number mid-flow (which resets to a fresh lookup).

---

### 8. Language Detection

Incoming text messages are scanned for language markers:

- Presence of Twi-specific characters (`ɛ`, `ɔ`) → Twi
- High proportion of common English words → English
- Defaults to Twi when confidence is low

This is used to log language usage analytics and to select the fallback language for `no_number` prompts when no session exists yet.

---

### 9. No-Number Handling

When the bot receives a message it cannot extract a phone number from, it rotates through a pool of 10 Twi and 10 Ewe prompts asking the user to re-send the number with all digits. The rotation prevents repetitive identical replies.

---

### 10. Analytics

The `/metrics` endpoint exposes usage counters:

| Metric | Description |
|---|---|
| `total_messages` | Total messages received |
| `voice_messages` | Messages that contained audio |
| `text_messages` | Messages that were plain text |
| `lookup_requests` | Number of lookup attempts |
| `found_hits` | Lookups that returned a match |
| `not_found_hits` | Lookups that returned no match |
| `no_number_hits` | Messages where no number was detected |
| `ussd_sessions_started` | Number of *170# sessions initiated |
| `language_counts` | Per-language breakdown of all messages |
| `top_numbers` | Five most-looked-up numbers |

---

### 11. Mock Database

The current database (`data/momo_db.json`) is a hand-crafted set of **85 demo records** covering a realistic spread of account types and networks:

| Category | Count | Networks |
|---|---|---|
| Individual | 20 | MTN, Telecel, AT |
| Merchant | 30 | MTN, Telecel, AT |
| Church | 5 | MTN |
| School | 5 | AT |
| Susu group | 5 | MTN |
| NGO | 5 | AT |
| Agent | 5 | Telecel |

Each record contains: `phone`, `display_name`, `category`, `network`, `notes`.

The database is loaded and validated at startup. Duplicate phone numbers and malformed entries cause the application to refuse to start.

---

### 12. Input Validation

All phone numbers passing through the system are validated against Ghana's mobile number format:

- Must match `^0[2357][0-9]{8}$`
- Accepted prefixes: `024`, `025`, `026`, `027`, `028`, `054`, `055`, `056`, `057`, `059`, `020`, `050` and other active Ghanaian mobile prefixes

Invalid numbers are rejected silently; the user receives a "number not found" prompt rather than an error.

---

## Webhook Endpoint

| Route | Method | Purpose |
|---|---|---|
| `GET /` | GET | Health check — returns `{"status": "running"}` |
| `POST /webhook` | POST | Twilio WhatsApp webhook — receives all inbound messages |
| `GET /test-reply` | GET | Dev tool: sends a test message to `?to=whatsapp:+233XXXXXXXXX` |
| `GET /metrics` | GET | Returns usage analytics as JSON |

All webhook processing runs in a background thread so Twilio receives an immediate HTTP 200 before any logic executes.

---

## Project Structure

```
CheckMe/
├── app.py              # Flask app, webhook handler, session state, send helpers
├── lookup.py           # Number extraction, normalisation, DB lookup
├── responses.py        # All bilingual (Twi/Ewe) reply strings
├── language_support.py # Language detection
├── mock_data.py        # Loads and validates data/momo_db.json
├── asr.py              # GhanaNLP speech-to-text wrapper
├── audio.py            # OGG/WAV/MP3 audio conversion
├── tts.py              # GhanaNLP text-to-speech wrapper
├── data/
│   └── momo_db.json    # Demo contact database (85 records)
├── static/audio/       # Temporary OGG files served to Twilio (auto-cleaned)
├── tests/
│   └── test_lookup.py  # Unit tests for extraction and lookup logic
└── requirements.txt
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `flask` | HTTP server |
| `twilio` | WhatsApp messaging via Twilio API |
| `ghana-nlp` | GhanaNLP ASR (speech-to-text) and TTS (text-to-speech) |
| `pydub` | Audio format conversion |
| `audioop-lts` | Required pydub dependency on Python 3.13+ |
| `requests` | Downloading media from Twilio |
| `python-dotenv` | Environment variable loading |
| `ffmpeg` | OGG/Opus encoding (system dependency, not pip) |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TWILIO_SID` | Yes | Twilio Account SID |
| `TWILIO_TOKEN` | Yes | Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | Yes | Sender number (e.g. `+14155238886`) |
| `GHANANLP_KEY` | Yes | GhanaNLP API key for ASR and TTS |
| `BASE_URL` | Yes | Public base URL for serving audio files (e.g. your ngrok URL) |
| `GHANANLP_ASR_LANGUAGE` | No | ASR language code, defaults to `tw` (Twi) |

---

## Roadmap / Pending Integrations

The current build is a working proof-of-concept using a curated demo database. The following integrations are planned pending external agreements and data access:

### Telco Database Integration

We are in the process of negotiating data-sharing agreements with **MTN Ghana**, **Telecel Ghana**, and **AT (AirtelTigo)** to access their registered MoMo subscriber name databases. Once live, the lookup step will query real, up-to-date subscriber records instead of the 85-entry demo database, covering millions of active Ghanaian MoMo accounts.

### Real-Time Transaction Simulation

The current transfer flow ends with a prompt directing users to MTN *170# to enter their PIN. The next phase will integrate directly with the telco payment APIs to initiate, confirm, and track actual MoMo transactions within the bot conversation — eliminating the need to switch to a separate USSD session.

### Proprietary WhatsApp Bot

The current implementation uses **Twilio** as the WhatsApp messaging layer. We are building our own WhatsApp Business API integration to replace Twilio, which will give us direct control over message delivery, session persistence, media handling, and cost. This also removes the dependency on Twilio's sandbox limitations during the demo phase.

---

## Known Limitations (Current Build)

- Session state is in-memory only — all sessions are lost on server restart
- The mock database covers only 85 numbers; any real Ghanaian number will return "not found"
- USSD menu data (balance, mini-statement) is hardcoded demo data
- The bot runs on a single server process; concurrent high-load scenarios are not yet tested
- `BASE_URL` must be a publicly reachable URL for Twilio to fetch audio files — local-only deployments require ngrok or equivalent
