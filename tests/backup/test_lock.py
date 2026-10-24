"""Trava cooperativa entre processos do SalesOS."""

import subprocess
import sys
from pathlib import Path

import pytest

from salesos.lock import Travado, trava

SEGURAR = """
import sys, time
from pathlib import Path
from salesos.lock import trava
with trava(Path(sys.argv[1])):
    print("ok", flush=True)
    time.sleep(60)
"""


def segurar_em_outro_processo(caminho: Path) -> subprocess.Popen[str]:
    proc = subprocess.Popen(  # noqa: S603 (roteiro fixo, interpretador do próprio teste)
        [sys.executable, "-c", SEGURAR, str(caminho)], stdout=subprocess.PIPE, text=True
    )
    assert proc.stdout is not None and proc.stdout.readline().strip() == "ok"
    return proc


def test_second_holder_in_same_process_is_refused(tmp_path: Path) -> None:
    caminho = tmp_path / "salesos.lock"
    with trava(caminho), pytest.raises(Travado), trava(caminho):
        pass
    with trava(caminho):  # liberada ao sair
        pass


def test_lock_held_by_other_process_is_refused_until_it_is_killed(tmp_path: Path) -> None:
    caminho = tmp_path / "salesos.lock"
    proc = segurar_em_outro_processo(caminho)
    try:
        with pytest.raises(Travado), trava(caminho):
            pass
    finally:
        proc.kill()  # SIGKILL no Linux: o processo não tem chance de liberar a trava
        proc.wait()
    with trava(caminho):
        pass
