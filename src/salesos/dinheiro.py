"""Dinheiro em centavos inteiros (Fase 03, R8). Nunca `float`.

Entrada só em pt-BR: milhar com ponto em grupos de 3, decimal com vírgula e até 2 casas.
Sem sinal, notação científica, símbolo de moeda nem arredondamento: o que não casar
exatamente com o formato é recusado.
"""

import re

MAXIMO_CENTAVOS = 10**12  # R$ 10.000.000.000,00
_TAMANHO_MAXIMO = len("10.000.000.000,00")  # recusa antes de converter milhares de dígitos
_FORMATO = re.compile(  # sem zero à esquerda, exceto o próprio "0" ("0,50")
    r"(?P<inteiro>[1-9][0-9]{0,2}(?:\.[0-9]{3})+|[1-9][0-9]*|0)(?:,(?P<fracao>[0-9]{1,2}))?"
)


def centavos(texto: str) -> int:
    texto = texto.strip()
    casou = _FORMATO.fullmatch(texto) if len(texto) <= _TAMANHO_MAXIMO else None
    if casou is None:
        raise ValueError("Valor inválido")
    inteiro = int(casou["inteiro"].replace(".", ""))
    valor = inteiro * 100 + int((casou["fracao"] or "0").ljust(2, "0"))
    if valor > MAXIMO_CENTAVOS:
        raise ValueError("Valor inválido: acima do máximo")
    return valor


def reais(valor: int) -> str:
    if type(valor) is not int or not 0 <= valor <= MAXIMO_CENTAVOS:
        raise ValueError("Valor fora do intervalo de 0 a 10**12 centavos")
    inteiro, fracao = divmod(valor, 100)
    return f"R$ {inteiro:,}".replace(",", ".") + f",{fracao:02d}"
