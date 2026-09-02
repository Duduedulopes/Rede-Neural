# -*- coding: utf-8 -*-
"""
A REDE RESPONDENDO, NO TERMINAL. Programa.

    python programas/perguntar.py                    modo conversa
    python programas/perguntar.py "quanto faturei"   uma pergunta so

PARA QUE ISTO SERVE

O gerente ja aparece bonito no painel do Admin. Mas ali o que se ve e a
RESPOSTA — o numero, o texto. A rede em si fica atras da cortina.

Aqui ela aparece: os pedacos da frase, quantos ela conhecia, os tres
palpites com as probabilidades, o tom, e se passou ou nao do limiar. E o
mesmo modelo que o navegador carrega, o mesmo `intencao.json`, a mesma
conta — so que sem interface na frente.

Serve para tres coisas:

    estudar     ver o efeito de trocar uma palavra na frase
    depurar     descobrir por que uma pergunta foi para o lugar errado
    mostrar     em video, o terminal prova que existe uma rede ali;
                a interface sozinha poderia ser um monte de `if`
"""
import io, json, os, sys, unicodedata
from pathlib import Path
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "modelos" / "intencao.json"

M = json.load(io.open(MODELO, encoding="utf-8"))
IDX = {p: i for i, p in enumerate(M["pecas"])}
TAB = np.array(M["tabela"])
C0, C1 = M["camadas"]
W0, B0 = np.array(C0["pesos"]), np.array(C0["vies"]).reshape(-1, 1)
W1, B1 = np.array(C1["pesos"]), np.array(C1["vies"]).reshape(-1, 1)
TONS = M.get("tons")
WT = np.array(M["camada_tom"]["pesos"]) if TONS else None
BT = np.array(M["camada_tom"]["vies"]).reshape(-1, 1) if TONS else None
LIM = M["limiar"]
CORTE = M.get("limiar_confirmacao", 1.0)

# ══════════════════════════════════════════════════════════════════════
#  O TERMINAL DO WINDOWS, QUE NAO E O TERMINAL DO LINUX
#
#  Neste mesmo projeto um programa ja morreu com
#
#      UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'
#
#  O console do Windows abre em cp1252 quando nao negocia UTF-8, e ai a
#  seta e os blocos derrubam o programa inteiro — no meio de uma
#  demonstracao, na frente de quem estiver assistindo.
#
#  Duas defesas, nesta ordem:
#    1. pedir UTF-8 ao stdout, que resolve na maioria dos casos
#    2. se nao der, trocar os desenhos por ASCII e seguir. Um grafico de
#       `#` e `-` diz a mesma coisa; um traceback nao diz nada.
# ══════════════════════════════════════════════════════════════════════
def _tem_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        return True
    except Exception:
        pass
    try:
        "\u2192\u2588".encode(sys.stdout.encoding or "ascii")
        return True
    except Exception:
        return False


BONITO = _tem_utf8()

# Cor so quando ha terminal de verdade do outro lado: redirecionar para
# arquivo com codigo de cor dentro suja o arquivo sem avisar.
_COR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
VERDE, AMAR, VERM, CINZA, FORTE, FIM = (
    ("\033[32m", "\033[33m", "\033[31m", "\033[90m", "\033[1m", "\033[0m")
    if _COR else ("", "", "", "", "", ""))

SETA   = "\u2192" if BONITO else ">"
CHEIO  = "\u2588" if BONITO else "#"
VAZIO  = "\u00b7" if BONITO else "-"
MEIO   = "\u00b7" if BONITO else "-"
NIVEIS = ("\u2589", "\u2593", "\u2592", "\u2591") if BONITO else ("#", "+", ":", ".")


def normalizar(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def trigramas(p):
    c = "<" + p + ">"
    return [c] if len(c) <= 3 else [c[i:i + 3] for i in range(len(c) - 2)]


def sig(z):
    return np.where(z >= 0, 1 / (1 + np.exp(-np.abs(z))),
                    np.exp(-np.abs(z)) / (1 + np.exp(-np.abs(z))))


def barra(p, largura=26):
    cheio = int(round(p * largura))
    return CHEIO * cheio + VAZIO * (largura - cheio)


def pensar(frase):
    palavras = normalizar(frase).split()
    pecas = palavras + [g for p in palavras for g in trigramas(p)]
    ids = [IDX[p] for p in pecas if p in IDX]
    conhecidas = [p for p in palavras if p in IDX]

    if not ids:
        print(f"  {VERM}nenhum pedaço dessa frase existe no vocabulário.{FIM}")
        return

    x = TAB[ids].mean(axis=0).reshape(-1, 1)
    oculta = sig(W0 @ x + B0).ravel()
    z = W1 @ oculta.reshape(-1, 1) + B1
    e = np.exp(z - z.max())
    p = (e / e.sum()).ravel()
    ordem = p.argsort()[::-1]

    print(f"\n  {CINZA}palavras{FIM}   " + "  ".join(
        (VERDE + w + FIM) if w in conhecidas else (CINZA + w + FIM) for w in palavras))
    print(f"  {CINZA}pedaços{FIM}    {len(ids)} de {len(pecas)} conhecidos "
          f"({len(palavras)} palavras + {len(pecas)-len(palavras)} trigramas de letra)")

    acesos = int((oculta > 0.5).sum())
    print(f"  {CINZA}neurônios{FIM}  {acesos} de {len(oculta)} acesos   " +
          "".join(NIVEIS[0] if a > .75 else NIVEIS[1] if a > .5
                          else NIVEIS[2] if a > .25 else NIVEIS[3] for a in oculta))

    print()
    for k in ordem[:3]:
        nome, pr = M["intencoes"][k], p[k]
        cor = VERDE if pr >= LIM else (AMAR if pr >= 0.5 else CINZA)
        marca = FORTE + SETA + FIM if k == ordem[0] else " "
        print(f"  {marca} {cor}{nome:<22}{FIM} {barra(pr)} {pr:6.2%}")

    if TONS:
        zt = WT @ oculta.reshape(-1, 1) + BT
        et = np.exp(zt - zt.max())
        pt = (et / et.sum()).ravel()
        j = int(pt.argmax())
        print(f"\n  {CINZA}tom{FIM}        {TONS[j]} ({pt[j]:.0%})")

    vencedor, conf = M["intencoes"][ordem[0]], p[ordem[0]]
    print()
    if conf >= LIM:
        print(f"  {VERDE}responde sozinho{FIM} — {conf:.1%} passa do limiar de {LIM:.0%}")
    else:
        tres = ", ".join(M["intencoes"][k] for k in ordem[:3])
        print(f"  {AMAR}oferece os botões{FIM} — {conf:.1%} não passa do limiar de {LIM:.0%}")
        print(f"  {CINZA}mostraria: {tres}{FIM}")

    if vencedor == "confirmar_acao":
        ok = conf >= CORTE
        print(f"  {(VERDE if ok else AMAR)}{'GRAVA' if ok else 'não grava'}{FIM} — "
              f"o corte para escrever no banco é {CORTE:.1%}")


def main():
    print(f"\n  {FORTE}{MODELO.name}{FIM}  "
          f"{len(M['intencoes'])} intenções {MEIO} {M['medido']['corpus']} frases {MEIO} "
          f"limiar {LIM:.0%}" + (f" {MEIO} {len(TONS)} tons" if TONS else ""))
    n = (TAB.size + W0.size + len(C0['vies']) + W1.size + len(C1['vies']))
    # `.replace(",", ".")` na frase inteira comia a virgula do texto tambem
    # ("73.334 parametros. todos treinados"). O separador se troca so no
    # numero, antes de entrar na frase.
    milhar = f"{n:,}".replace(",", ".")
    print(f"  {CINZA}{milhar} parâmetros, todos treinados neste projeto{FIM}")

    if len(sys.argv) > 1:
        pensar(" ".join(sys.argv[1:]))
        return

    print(f"\n  {CINZA}escreva uma pergunta (Enter vazio para sair){FIM}")
    while True:
        try:
            f = input(f"\n  {FORTE}você>{FIM} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not f: break
        pensar(f)


if __name__ == "__main__":
    main()
