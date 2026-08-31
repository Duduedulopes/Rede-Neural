"""Compara sigmoid+entropia binaria contra softmax+entropia categorica. Programa.

    python programas/comparar_custos.py --epocas 10

A MESMA rede, a MESMA semente, os MESMOS minilotes na mesma ordem. So muda a
camada de saida e o custo. Qualquer diferenca no resultado vem dai — e nao de
outra inicializacao ou de outro embaralhamento.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, treino  # noqa: E402
from rede.ativacao import Softmax  # noqa: E402
from rede.custo import EntropiaCruzada, EntropiaCruzadaCategorica  # noqa: E402
from rede.rede import Rede  # noqa: E402

SEMENTE = 42


def rodar(nome, ativacao_saida, custo, treinamento, teste, epocas):
    r = Rede([784, 30, 10], semente=SEMENTE, ativacao_saida=ativacao_saida)
    inicio = time.time()
    treino.treinar(r, treinamento, epocas=epocas, tamanho_lote=10, taxa=0.5,
                   custo=custo, semente=SEMENTE)
    duracao = time.time() - inicio

    certos = treino.acertos(r, teste)

    # A soma das saidas em MUITOS exemplos, nao em um. Num exemplo facil a
    # sigmoid por acaso soma perto de 1; a variacao so aparece no conjunto.
    somas = np.array([float(np.sum(r.frente(x))) for x, _ in teste[:2000]])

    return {
        "nome": nome,
        "acerto": 100 * certos / len(teste),
        "custo": treino.custo_medio(r, teste, custo),
        "soma_media": float(somas.mean()),
        "soma_min": float(somas.min()),
        "soma_max": float(somas.max()),
        "tempo": duracao,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=10)
    args = ap.parse_args()

    treinamento, _, teste = dados.carregar_mnist()

    linhas = [
        rodar("sigmoid + binaria", None, EntropiaCruzada,
              treinamento, teste, args.epocas),
        rodar("softmax + categorica", Softmax, EntropiaCruzadaCategorica,
              treinamento, teste, args.epocas),
    ]

    print()
    print(f"MNIST [784, 30, 10], {args.epocas} epocas, lote 10, taxa 0.5, semente {SEMENTE}")
    print()
    print("  saida da rede             acerto    custo    soma das saidas (2000 exemplos)   tempo")
    print("  ------------------------  ------   ------   ------------------------------   -----")
    for l in linhas:
        faixa = f"media {l['soma_media']:.3f}   de {l['soma_min']:.3f} a {l['soma_max']:.3f}"
        print(f"  {l['nome']:24s}  {l['acerto']:5.2f}%   {l['custo']:6.4f}   {faixa:30s}   {l['tempo']:4.0f}s")
    print()
    print("  A soma das saidas e a diferenca conceitual, e ela aparece na FAIXA,")
    print("  nao na media: a softmax vale 1 em todo exemplo, por construcao. A")
    print("  sigmoid chega perto na media e passeia nos casos dificeis — que sao")
    print("  exatamente aqueles em que se gostaria de confiar na probabilidade.")


if __name__ == "__main__":
    main()
