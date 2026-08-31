"""Ampliar a rede AJUDA? A varredura que responde com numero. Programa.

    python programas/varrer_tamanho.py

POR QUE VARRER EM VEZ DE SO AUMENTAR

"Ampliar a rede" parece uma melhoria por definicao, e nao e. Com corpus
pequeno, mais parametros so dao mais lugar para DECORAR — o modelo acerta o
treino e piora no teste.

    Rede maior nao e melhor. E maior. Se e melhor, o teste diz.

Cada configuracao passa pela MESMA validacao cruzada, com as MESMAS dobras.
Comparar configuracoes com divisoes diferentes seria comparar sortes.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from programas.treinar_intencao import carregar, dobras, treinar  # noqa: E402
from rede.texto import Vocabulario  # noqa: E402

SEMENTE = 42

CONFIGURACOES = [
    ("minima      ",  8,  16,  120),
    ("pequena     ", 16,  24,  120),
    ("atual       ", 24,  32,  120),
    ("media       ", 32,  48,  120),
    ("grande      ", 48,  64,  120),
    ("muito grande", 64,  96,  120),
    ("atual + tempo", 24, 32,  300),
    ("grande + tempo", 48, 64, 300),
]


def main():
    dados = carregar()
    perguntas = [d["pergunta"] for d in dados]
    rotulos = [d["intencao"] for d in dados]
    intencoes = sorted(set(rotulos))
    n_int = {n: i for i, n in enumerate(intencoes)}

    gerador = np.random.default_rng(SEMENTE)
    grupos = dobras(rotulos, 5, gerador)

    print(f"corpus {len(dados)} frases, {len(intencoes)} intencoes, 5 dobras fixas")
    print()
    print("  configuracao      d    H  epocas   params   treino    teste   +-")
    print("  " + "-" * 66)

    for nome, d, h, epocas in CONFIGURACOES:
        no_teste, no_treino, params = [], [], 0
        for k in range(5):
            teste_i = set(grupos[k])
            treino_i = [i for i in range(len(dados)) if i not in teste_i]

            voc = Vocabulario([perguntas[i] for i in treino_i])
            prep = lambda i: (voc.indices(perguntas[i]), n_int[rotulos[i]])

            c = treinar([prep(i) for i in treino_i], len(voc), intencoes,
                        epocas, 1.0, d, h, SEMENTE + k)
            params = c.n_parametros
            no_teste.append(c.avaliar([prep(i) for i in sorted(teste_i)])[0])
            no_treino.append(c.avaliar([prep(i) for i in treino_i])[0])

        print(f"  {nome}  {d:3d}  {h:3d}  {epocas:6d}  {params:7d}   "
              f"{100*np.mean(no_treino):5.1f}%   {100*np.mean(no_teste):5.1f}%  "
              f"{100*np.std(no_teste):4.1f}")

    print()
    print("  A COLUNA QUE IMPORTA E A DISTANCIA ENTRE TREINO E TESTE.")
    print("  Treino muito acima do teste = a rede decorou em vez de aprender,")
    print("  e ai aumentar mais so piora.")


if __name__ == "__main__":
    main()
