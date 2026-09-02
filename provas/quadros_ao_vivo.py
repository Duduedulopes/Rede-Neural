# -*- coding: utf-8 -*-
"""
O QUADRO AO VIVO E A PORTA QUE ELE ABRE. Prova.

    python provas/quadros_ao_vivo.py

`papel` vem da URL — `/api/camera/alto.jpg`. Entrada de fora, montando um
caminho de arquivo, num servidor que roda na mesma maquina que o
`appsettings.json`. E o desenho classico de leitura de arquivo arbitraria, e
o unico motivo de nao ser uma e a expressao que valida o papel.

Uma guarda que ninguem exercita e uma guarda que alguem simplifica depois.
Estes casos existem para que simplificar quebre a prova.
"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from monitor.fontes import FonteEspacial

ok = fail = 0


def e(cond, oque):
    global ok, fail
    if cond:
        ok += 1
        print("  ok  ", oque)
    else:
        fail += 1
        print("  FALHOU", oque)


def rodar():
    raiz = Path(tempfile.mkdtemp())
    viv = raiz / "dados" / "ao_vivo"
    viv.mkdir(parents=True)
    (viv / "alto.jpg").write_bytes(b"JPEG-ALTO")
    (viv / "frontal.jpg").write_bytes(b"JPEG-FRONTAL")
    # O temporario da escrita atomica. Se ele vazar para a lista, o painel
    # abre uma caixa para uma camera que nao existe.
    (viv / ".frontal.tmp.jpg").write_bytes(b"metade de um jpeg")
    (raiz / "dados" / "segredo.txt").write_text("nao pode sair daqui")

    f = FonteEspacial(raiz)

    papeis = sorted(c["papel"] for c in f.cameras_ao_vivo())
    e(papeis == ["alto", "frontal"], f"lista as cameras que publicam (deu {papeis})")
    e(all("idade_s" in c for c in f.cameras_ao_vivo()),
      "com a IDADE: um jpg de dez minutos atras parece camera viva e nao e")
    e(not any(c["papel"].startswith(".") for c in f.cameras_ao_vivo()),
      "o temporario de escrita nao aparece")

    e(f.quadro("alto") == b"JPEG-ALTO", "entrega o quadro pedido")
    e(f.quadro("nao-existe") is None, "camera inexistente devolve None")

    # ── A GUARDA ─────────────────────────────────────────────────────
    for veneno in ["../segredo", "../../appsettings", "..\\..\\x",
                   "alto/../../segredo", "", "a" * 60]:
        e(f.quadro(veneno) is None, f"recusa {veneno!r}")

    # ── 1 CAMERA E UMA INSTALACAO VALIDA ─────────────────────────────
    # O Espacial abre o que estiver no `cameras.json`: 1, 3 ou 5. O painel
    # tem de aceitar qualquer numero sem tela quebrada.
    solo = Path(tempfile.mkdtemp())
    (solo / "dados" / "ao_vivo").mkdir(parents=True)
    (solo / "dados" / "ao_vivo" / "alto.jpg").write_bytes(b"X")
    e(len(FonteEspacial(solo).cameras_ao_vivo()) == 1, "1 camera so: lista uma")

    cinco = Path(tempfile.mkdtemp())
    (cinco / "dados" / "ao_vivo").mkdir(parents=True)
    for p in ("alto", "frontal", "lateral", "porta", "deposito"):
        (cinco / "dados" / "ao_vivo" / f"{p}.jpg").write_bytes(b"X")
    e(len(FonteEspacial(cinco).cameras_ao_vivo()) == 5, "5 cameras: lista as cinco")

    # ── ANTES DO ESPACIAL RODAR ──────────────────────────────────────
    vazio = Path(tempfile.mkdtemp())
    e(FonteEspacial(vazio).cameras_ao_vivo() == [], "sem pasta: lista vazia, sem excecao")
    e(FonteEspacial(vazio).quadro("alto") is None, "sem pasta: quadro None")

    print(f"\n  ══════ {ok}/{ok + fail} do quadro ao vivo ══════")
    return fail


if __name__ == "__main__":
    sys.exit(1 if rodar() else 0)
