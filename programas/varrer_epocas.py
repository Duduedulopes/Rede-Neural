"""Treinar MENOS calibra melhor? Programa.

A confianca da rede saiu inutil: ela erra com 0,66 de mediana e acerta com
0,96, e as duas distribuicoes se sobrepoem quase inteiras.

A suspeita: 150 epocas levam o treino a 99,6% de acerto, e uma rede que
decorou o treino fica CONFIANTE em tudo — inclusive no que erra. Parar antes
costuma custar um pouco de acuracia e devolver muita calibracao.

    Acuracia diz quantas vezes acerta. Calibracao diz se da para confiar no
    numero que ela cospe. Sem a segunda, a primeira nao serve para decidir
    quando calar.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from programas.treinar_intencao import carregar, dobras, treinar  # noqa: E402
from rede.texto import Vocabulario  # noqa: E402

SEMENTE = 42


def medir(epocas, dados, perguntas, rotulos, intencoes, n_int, grupos, d=16, h=24):
    conf, ok, treino_ok = [], [], []
    for k in range(5):
        teste_i = set(grupos[k])
        treino_i = [i for i in range(len(dados)) if i not in teste_i]
        voc = Vocabulario([perguntas[i] for i in treino_i])
        prep = lambda i: (voc.indices(perguntas[i]), n_int[rotulos[i]])

        c = treinar([prep(i) for i in treino_i], len(voc), intencoes,
                    epocas, 1.0, d, h, SEMENTE + k)
        treino_ok.append(c.avaliar([prep(i) for i in treino_i])[0])
        for i in sorted(teste_i):
            idx, alvo = prep(i)
            p = c.prever(idx).ravel()
            e = int(np.argmax(p))
            conf.append(float(p[e])); ok.append(e == alvo)

    conf, ok = np.array(conf), np.array(ok)
    # A melhor precisao alcancavel respondendo pelo menos 40% das perguntas.
    # Limiar que so responde 5% tem precisao alta e serventia nenhuma.
    # Comeca em 0 e nao em 0,3: com poucas epocas a rede fica pouco
    # confiante em TUDO, e nenhum limiar alto alcanca 40% de cobertura.
    # Sem isto o melhor limiar volta vazio e o relatorio quebra.
    melhor_prec, melhor_lim, melhor_cob = 0.0, 0.0, 1.0
    for lim in np.arange(0.0, 0.99, 0.01):
        resp = conf >= lim
        if resp.mean() < 0.40:
            break
        prec = ok[resp].mean()
        if prec > melhor_prec:
            melhor_prec, melhor_lim, melhor_cob = prec, lim, resp.mean()
    return np.mean(treino_ok), ok.mean(), melhor_prec, melhor_lim, melhor_cob


def main():
    dados = carregar()
    perguntas = [d["pergunta"] for d in dados]
    rotulos = [d["intencao"] for d in dados]
    intencoes = sorted(set(rotulos))
    n_int = {n: i for i, n in enumerate(intencoes)}
    grupos = dobras(rotulos, 5, np.random.default_rng(SEMENTE))

    print("  epocas   treino    teste   melhor precisao (respondendo >=40%)")
    print("  " + "-" * 62)
    for epocas in [10, 20, 30, 50, 80, 150]:
        tr, te, prec, lim, cob = medir(epocas, dados, perguntas, rotulos,
                                       intencoes, n_int, grupos)
        alvo = "  <- passa de 90%" if prec >= 0.90 else ""
        print(f"  {epocas:6d}   {100*tr:5.1f}%   {100*te:5.1f}%   "
              f"{100*prec:5.1f}% no limiar {lim:.2f}, respondendo {100*cob:4.1f}%{alvo}")


if __name__ == "__main__":
    main()
