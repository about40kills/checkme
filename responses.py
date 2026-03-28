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
    """Response when the number is found in the database."""
    if isinstance(entity, dict):
        name = entity.get("display_name", "Unknown User")
        category_hint = _category_hint(entity.get("category"))
    else:
        name = entity
        category_hint = "Hwɛ din no yiye ansa na wo soma sika."

    return (
        f"Number {number} din de {name}. "
        f"Hwɛ sɛ ɛne onipa a wopɛ sɛ wo soma no din na ɛtɔ so "
        f"ansa na wo soma sika. {category_hint}\n\n"
        f"Do you want to send money to them? Reply YES to continue."
    )


def not_found(number):
    """Response when the number is NOT found in the database."""
    return (
        f"Yɛnhuu din bi a ɛne {number} to so. "
        f"Hwɛ number no bio anaasɛ bisa onipa no sɛ ɔkyerɛ wo n'account no. "
        f"Nnka wo PIN nkyerɛ obiara."
    )


def no_number():
    """Response when no valid number was detected in the input."""
    return (
        "Mesrɛ wo, ka number no bio. "
        "Te sɛ: check 0244123456 ama me."
    )


def ask_amount():
    """USSD prompt for amount."""
    return "Enter Amount (e.g. 50):"


def ask_reference():
    """USSD prompt for reference."""
    return "Enter Reference:"


def confirm_transfer(name, number, amount, reference):
    """USSD prompt for final confirmation."""
    return (
        f"Enter MM PIN to confirm transfer of GHS {amount} to "
        f"{name} ({number}) with Reference: {reference}."
    )
