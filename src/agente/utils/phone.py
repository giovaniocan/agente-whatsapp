"""
Utilitários de telefone BR (RN-22).

O WhatsApp ora envia o número com o 9º dígito, ora sem. Para deduplicar/buscar
leads, geramos as duas variantes. Regra portada de `zapiLeadUtils.js` do Trivus.
"""

import re


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def phone_variants(phone: str) -> list[str]:
    """
    Variantes cobrindo presença/ausência do 9º dígito.
    "44999998888" -> ["44999998888", "4499998888"]
    "4499998888"  -> ["4499998888", "44999998888"]
    """
    digits = only_digits(phone)
    if not digits:
        return []

    variants = [digits]
    if len(digits) == 11 and digits[2] == "9":
        # com 9º dígito → variante sem ele
        variants.append(digits[:2] + digits[3:])
    elif len(digits) == 10:
        # sem 9º dígito → variante com ele
        variants.append(digits[:2] + "9" + digits[2:])
    return variants
