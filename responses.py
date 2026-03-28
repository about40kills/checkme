# ── Twi helpers ──────────────────────────────────────────────────────────────

def _category_hint_tw(category):
    hints = {
        "individual": "Yei yɛ ankorankoro akoanto.",
        "merchant": "Yei yɛ adwumayɛfo anaa shop akoanto.",
        "church": "Yei yɛ asɔre akoanto.",
        "school": "Yei yɛ sukuu akoanto.",
        "susu_group": "Yei yɛ susu group akoanto.",
        "ngo": "Yei yɛ community organization akoanto.",
        "agent": "Yei yɛ mobile money agent akoanto.",
    }
    return hints.get(category, "Hwɛ din no yie ansa na wo soma sika.")


def _category_hint_ee(category):
    hints = {
        "individual": "Esia nye ŋutɔ ame aɖeke tɔ akoanto.",
        "merchant": "Esia nye dɔwɔla abe shop ene akaonto.",
        "church": "Esia nye habobo akaonto.",
        "school": "Esia nye sukuu akaonto.",
        "susu_group": "Esia nye susu group akaonto.",
        "ngo": "Esia nye community organization akaonto.",
        "agent": "Esia nye mobile money agent akaonto.",
    }
    return hints.get(category, "Kpɔ ŋkɔ la nyuie esime ado ga.")


# ── Language selection prompt ─────────────────────────────────────────────────

LANG_SELECT_ENGLISH = "Select your language:\n1. Twi\n2. Ewe"
LANG_SELECT_TW = "fa baako sɛ wo pɛ Twi, fa mmienu sɛ wo pɛ Ewe."
LANG_SELECT_EE = "Tso 1 be nèdi Twi, tso 2 be nèdi Ewe."
# Combined voice prompt so both Twi and Ewe speakers hear their language
LANG_SELECT_VOICE = "fa baako sɛ wo pɛ Twi, fa mmienu sɛ wo pɛ Ewe.                  Tso 1 be nèdi Twi, tso 2 be nèdi Ewe."


# ── Found responses ───────────────────────────────────────────────────────────

def found(number, entity, lang="tw"):
    if isinstance(entity, dict):
        name = entity.get("display_name", "Unknown User")
        category = entity.get("category")
    else:
        name = entity
        category = None

    if lang == "ee":
        hint = _category_hint_ee(category)
        return (
            f"Number {number} ŋkɔ nye {name}. "
            f"Kpɔ be eya nye ame si wòdzɔ na la esime ado ga. "
            f"{hint} "
            f"Èdi be ado ga na wo? Ŋlɔ YES be wòyi edzi."
        )
    else:  # default Twi
        hint = _category_hint_tw(category)
        return (
            f"Number {number} din de {name}. "
            f"Hwɛ sɛ ɛne onipa aa wopɛ sɛ wo soma sika no ne nɔmba no yɛ pɛ ansa na wo asoma sika no "
            f"{hint} "
            f"Wopɛ sɛ wo soma sika ama won? fa YES na wɔ anim."
        )


# ── Not found responses ───────────────────────────────────────────────────────

def not_found(number, lang="tw"):
    if lang == "ee":
        return (
            f"Míawɔ {number} ŋkɔ o. "
            f"Kpɔ afɔ fɔfɔ o, kaka eŋu tso ŋkɔ ɖe ame la ŋu. "
            f"Mégblɔ PIN tɔ ame aɖeke ŋu o."
        )
    return (
        f"Yɛnhuu din bi aa wɔ {number} no so."
        f"Hwɛ number no bio anaasɛ bisa onipa no sɛ ɔnkyerɛ wo n'akoanto no."
        f"ɛnka wo PIN nkyerɛ obiaa"
    )


# ── No number responses ───────────────────────────────────────────────────────

_no_number_tw = [
    "Mesrɛ wo, ka number no bio. Te sɛ: sero tu foɔfoɔ foɔfoɔ wɔn tu tri fɔ faif seks.",
    "Menhuu number biara wo wo nsɛm mu. Ka number no pɛn bio, na fa digit nyinaa ka.",
    "Number no nte ase. Mesrɛ wo, kyerɛ me number a wopɛ sɛ wo hwɛ no.",
    "Mesrɛ wo, soma number no foforo. Hwɛ sɛ w'akyerɛ digits nyinaa.",
    "Mente ase number biara. Ka number no bio, na fa digits nyinaa ka.",
    "Mesrɛ wo, number no nte ase. Ka number no bio na fa digits nyinaa ka.",
    "Wanhyɛ number biara ama me. Mesrɛ wo, ka number no bio.",
    "Menhuu number biara. Xia number no bio, na hwɛ sɛ wukyerɛ digits nyinaa.",
    "Number no nnyɛ number pa. Mesrɛ wo, ka number no bio pɛ.",
    "Mente ase. Mesrɛ wo, fa number no bio na kyerɛ me digits nyinaa.",
]

_no_number_ee = [
    "Meɖo kuku, gblɔ number la megbe. Te: sero eve ene ene ɖeka eve etɔ̃ ene atɔ̃ ade.",
    "Míawɔ number aɖeke ŋu o. Gblɔ number la megbe, kpɔ be digit siwo katã le eme.",
    "Number la mele teƒe o. Meɖo kuku, ŋlɔ number si wòdi be míakpɔe la.",
    "Meɖo kuku, gblɔ number fɔfɔ. Kpɔ be digit siwo katã le eme.",
    "Míate number aɖeke ŋu o. Gblɔ number la megbe, kpɔ digits siwo katã.",
    "Number la meŋlɔ nyuie o. Gblɔ number la megbe.",
    "Meɖo kuku, gblɔ number la megbe. Te: sero eve ene ene ɖeka eve etɔ̃ ene atɔ̃ ade.",
    "Míawɔ number aɖeke ŋu o. Gblɔ number fɔfɔ.",
    "Number la mele teƒe nyuie o. Meɖo kuku, gblɔ number la megbe.",
    "Míate ŋu o. Meɖo kuku, gblɔ number la megbe kpɔ digit siwo katã.",
]

_no_number_index = {"tw": 0, "ee": 0}


def no_number(lang="tw"):
    pool = _no_number_ee if lang == "ee" else _no_number_tw
    idx = _no_number_index[lang] % len(pool)
    _no_number_index[lang] += 1
    return pool[idx]


# ── USSD / flow helpers ───────────────────────────────────────────────────────

def ask_amount():
    return "Enter amount (e.g. 50):"


def ask_reference():
    return "Enter reference (or any note):"


def confirm_transfer(name, number, amount, reference, lang="tw"):
    if lang == "ee":
        return (
            f"Ŋlɔ MoMo PIN tɔ be wòte edzi.\n"
            f"Èdi be ado GHS {amount} na {name} ({number}).\n"
            f"Reference: {reference}.\n"
            f"Esia nye teƒe a MTN *170# ga wò PIN ŋu ado ga la."
        )
    return (
        f"Hyɛ wo MoMo PIN sɛ wo si ho ban.\n"
        f"Wosoma GHS {amount} kɔ {name} ({number}).\n"
        f"Reference: {reference}.\n"
        f"Ɛha na MTN *170# bɛfa wo PIN na atua sika no."
    )


def transfer_success(name, number, amount, reference, lang="tw"):
    if lang == "ee":
        return (
            f"✅ Ga dzo nyuie.\n"
            f"Wodo GHS {amount} na {name} ({number}).\n"
            f"Reference: {reference}.\n"
            f"Akpe be nèkpɔ ŋkɔ la esime ado ga."
        )
    return (
        f"✅ Sika soma wie ase.\n"
        f"Wosomaa GHS {amount} kɔ {name} ({number}).\n"
        f"Reference: {reference}.\n"
        f"Yɛda wo ase sɛ wohwɛ din no ansa na wosomaae."
    )
