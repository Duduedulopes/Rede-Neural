"""Qual confianca separa acerto de erro? Medido, nao escolhido. Programa.

    python programas/calibrar_limiar.py

POR QUE ISTO PRECISA EXISTIR

Sem Gemini no admin, o gerente nao tem para onde cair. Entao ele precisa
saber CALAR — e calar na hora certa, que e quando a resposta provavelmente
esta errada.

A softmax sempre devolve uma confianca. A pergunta e: a partir de qual valor
essa confianca merece credito?

    Escolher 70% porque e um numero redondo nao se defende. Medir onde os
    erros moram, sim.

O CUSTO DOS DOIS ERROS NAO E O MESMO

    responder errado    o administrador recebe um numero que nao pediu, e
                        pode agir com base nele
    calar sem precisar  o administrador reformula a pergunta

O segundo custa um incomodo. O primeiro custa uma decisao errada. Por isso o
limiar pende para calar mais, e nao menos.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from programas.treinar_intencao import carregar, dobras, treinar  # noqa: E402
from rede.texto import Vocabulario  # noqa: E402

SEMENTE = 42


def main():
    dados = carregar()
    perguntas = [d["pergunta"] for d in dados]
    rotulos = [d["intencao"] for d in dados]
    intencoes = sorted(set(rotulos))
    n_int = {n: i for i, n in enumerate(intencoes)}

    grupos = dobras(rotulos, 5, np.random.default_rng(SEMENTE))
    confiancas, acertou = [], []

    for k in range(5):
        teste_i = set(grupos[k])
        treino_i = [i for i in range(len(dados)) if i not in teste_i]
        voc = Vocabulario([perguntas[i] for i in treino_i])
        prep = lambda i: (voc.indices(perguntas[i]), n_int[rotulos[i]])

        c = treinar([prep(i) for i in treino_i], len(voc), intencoes,
                    150, 1.0, 16, 24, SEMENTE + k)
        for i in sorted(teste_i):
            idx, alvo = prep(i)
            p = c.prever(idx).ravel()
            escolhido = int(np.argmax(p))
            confiancas.append(float(p[escolhido]))
            acertou.append(escolhido == alvo)

    conf = np.array(confiancas)
    ok = np.array(acertou)

    print(f"{len(conf)} previsoes em validacao cruzada")
    print()
    print("  confianca quando ACERTOU     mediana {:.2f}   percentil 10 {:.2f}".format(
        np.median(conf[ok]), np.percentile(conf[ok], 10)))
    print("  confianca quando ERROU       mediana {:.2f}   percentil 90 {:.2f}".format(
        np.median(conf[~ok]), np.percentile(conf[~ok], 90)))
    print()
    print("  limiar   responde   dos que responde, acerta   erros que escapam")
    print("  " + "-" * 62)
    melhor = None
    for lim in [0.0, 0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
        responde = conf >= lim
        if responde.sum() == 0:
            continue
        precisao = ok[responde].mean()
        escapam = int((~ok & responde).sum())
        print(f"  {lim:5.2f}    {100*responde.mean():5.1f}%          {100*precisao:5.1f}%"
              f"              {escapam:4d}")
        # Alvo: 90% de precisao entre as respostas dadas. Abaixo disso, o
        # gerente esta enganando mais do que ajudando.
        if precisao >= 0.90 and melhor is None:
            melhor = (lim, responde.mean(), precisao, escapam)

    print()
    if melhor:
        lim, cobertura, precisao, escapam = melhor
        print(f"  LIMIAR MEDIDO: {lim:.2f}")
        print(f"    responde {100*cobertura:.0f}% das perguntas")
        print(f"    do que responde, acerta {100*precisao:.1f}%")
        print(f"    ainda escapam {escapam} erros — nenhum limiar zera isso")
        print()
        print(f"    e cala em {100*(1-cobertura):.0f}%, que viram pergunta guardada")
        print("    para treino. Calar nao e perder: e coletar.")
    else:
        print("  Nenhum limiar chega a 90% de precisao. O modelo ainda nao esta")
        print("  bom o bastante para responder sozinho — precisa de mais dado.")


if __name__ == "__main__":
    main()
