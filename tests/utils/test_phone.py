"""RN-22: variantes de telefone BR cobrindo presença/ausência do 9º dígito.
Regra portada do Trivus (zapiLeadUtils.phoneMatchVariants)."""

from agente.utils.phone import phone_variants


def test_eleven_digits_yields_variant_without_ninth() -> None:
    assert set(phone_variants("44999998888")) == {"44999998888", "4499998888"}


def test_ten_digits_yields_variant_with_ninth() -> None:
    assert set(phone_variants("4499998888")) == {"4499998888", "44999998888"}


def test_strips_non_digits() -> None:
    assert "44999998888" in phone_variants("(44) 99999-8888")


def test_empty_input_yields_empty_list() -> None:
    assert phone_variants("") == []
    assert phone_variants("abc") == []
