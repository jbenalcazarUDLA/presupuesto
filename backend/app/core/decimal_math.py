from decimal import Decimal, ROUND_HALF_UP
from typing import Union

TWOPLACES = Decimal("0.01")
ZERO_DECIMAL = Decimal("0.00")

def to_decimal(value: Union[str, int, float, Decimal, None]) -> Decimal:
    """
    Convierte de forma segura cualquier valor a Decimal con 2 posiciones decimales.
    Si se pasa un float, se convierte primero a string para no heredar imprecisiones de coma flotante.
    """
    if value is None:
        return ZERO_DECIMAL
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if isinstance(value, float):
        value = str(value)
    try:
        dec = Decimal(str(value).strip())
        return dec.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except Exception:
        raise ValueError(f"Valor monetario no válido para conversión decimal: {value}")

def format_decimal(value: Union[str, int, float, Decimal, None]) -> str:
    """Retorna el importe como string con formato de dos decimales (ej. '12500.50')."""
    return str(to_decimal(value))
