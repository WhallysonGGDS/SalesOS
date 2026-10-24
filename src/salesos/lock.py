"""Trava cooperativa entre processos do SalesOS (servidor, restore e recover).

Só protege contra outros processos do próprio SalesOS: programas externos não a respeitam.
No Linux (`flock`) ela é apenas cooperativa; no Windows usa `msvcrt.locking`.
O sistema operacional libera a trava quando o processo morre, mesmo sem chance de limpar.
"""

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Travado(RuntimeError):
    pass


def caminho_trava(db: Path) -> Path:
    return db.with_suffix(".lock")


@contextmanager
def trava(caminho: Path) -> Iterator[None]:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    arquivo = open(caminho, "a+b")  # noqa: SIM115 (fechado no finally)
    try:
        try:
            if sys.platform == "win32":
                import msvcrt

                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as erro:
            raise Travado(
                "Outro processo do SalesOS está usando este banco (servidor, restore ou recover)."
            ) from erro
        try:
            yield
        finally:
            if sys.platform == "win32":
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        arquivo.close()  # no Linux, fechar o descritor libera o flock
