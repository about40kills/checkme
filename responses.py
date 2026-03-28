def _category_hint(category):
    hints = {
        "individual": "Yei yɛ ankorankoro account.",
        "merchant": "Yei yɛ adwumayɛfo anaa shop account.",
        "church": "Yei yɛ asɔre account.",
        "school": "Yei yɛ sukuu account.",
        "susu_group": "Yei yɛ susu group account.",
        "ngo": "Yei yɛ community organization account.",
        "agent": "Yei yɛ mobile money agent account.",
    }
    return hints.get(category, "Hwɛ din no yiye ansa na wo soma sika.")


def found(number, entity):
    """Response when the number is found — pure Twi, delivered as audio."""
    if isinstance(entity, dict):
        name = entity.get("display_name", "Unknown User")
        category_hint = _category_hint(entity.get("category"))
    else:
        name = entity
        category_hint = "Yei yɛ ankorankoro account."

    return (
        f"Number {number} din de {name}. "
        f"Hwɛ sɛ ɛne onipa a wopɛ sɛ wo soma no na ɛtɔ so ansa na wo soma sika. "
        f"{category_hint} "
        f"Wopɛ sɛ wo soma sika ama won? Tua YES na wɔ anim."
    )


def not_found(number):
    """Response when the number is NOT found in the database."""
    return (
        f"Yɛnhuu din bi a ɛne {number} to so. "
        f"Hwɛ number no bio anaasɛ bisa onipa no sɛ ɔkyerɛ wo n'account no. "
        f"Nnka wo PIN nkyerɛ obiara."
    )


_no_number_replies = [
    "Mesrɛ wo, ka number no bio. Te sɛ: check 0244123456 ama me.",
    "Menhuu number biara wo wo nsɛm mu. Ka number no pɛn bio, na fa digit nyinaa ka.",
    "Number no nte ase. Mesrɛ wo, kyerɛ me number a wopɛ sɛ wo hwɛ no, te sɛ 0244123456.",
    "Mesrɛ wo, soma number no foforo. Hwɛ sɛ wukyerɛ digits nyinaa, te sɛ: 0244123456.",
    "Mente ase number biara. Ka number no bio, na fa digits nyinaa ka, te sɛ 0244123456.",
    "Mesrɛ wo, number no nte ase. Ka number no bio na fa digits nyinaa ka.",
    "Wanhyɛ number biara ama me. Mesrɛ wo, ka number no bio, te sɛ 0244123456.",
    "Menhuu number biara. Xia number no bio, na hwɛ sɛ wukyerɛ digits nyinaa.",
    "Number no nnyɛ number pa. Mesrɛ wo, ka number no bio pɛ.",
    "Mente ase. Mesrɛ wo, fa number no bio na kyerɛ me digits nyinaa, te sɛ 0244123456.",
]
_no_number_index = 0


def no_number():
    """Response when no valid number was detected. Rotates through 10 variants."""
    global _no_number_index
    reply = _no_number_replies[_no_number_index % len(_no_number_replies)]
    _no_number_index += 1
    return reply


def ask_amount():
    return "Enter amount (e.g. 50):"


def ask_reference():
    return "Enter reference (or any note):"


def confirm_transfer(name, number, amount, reference):
    """Final PIN prompt before transfer — Twi."""
    return (
        f"Hyɛ wo MoMo PIN sɛ wo si ho ban.\n"
        f"Wosoma GHS {amount} kɔ {name} ({number}).\n"
        f"Reference: {reference}.\n"
        f"Ɛha na MTN *170# bɛfa wo PIN na atua sika no."
    )


def transfer_success(name, number, amount, reference):
    """Simulated success message after PIN entry — Twi."""
    return (
        f"✅ Sika soma wie ase.\n"
        f"Wosomaa GHS {amount} kɔ {name} ({number}).\n"
        f"Reference: {reference}.\n"
        f"Yɛda wo ase sɛ wohwɛ din no ansa na wosomaae."
    )
