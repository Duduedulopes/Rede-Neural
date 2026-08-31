"""Treina a rede no MNIST. Programa — nao importe este arquivo.

    python programas/mnist.py                 # 30 epocas
    python programas/mnist.py --epocas 5      # mais rapido, para experimentar

A MESMA REDE DO XOR, SO QUE MAIOR

Nada aqui e novo: sao as mesmas camadas, a mesma sigmoid, a mesma
retropropagacao e a mesma descida do gradiente. Muda a escala.

    XOR     [2, 3, 1]         13 parametros      4 exemplos
    MNIST   [784, 30, 10]     23.860 parametros  50.000 exemplos

Sao 23.860 numeros ajustados a cada passo. Calcular esse gradiente por forca
bruta custaria 23.860 passagens pela rede POR EXEMPLO. A retropropagacao faz
com duas. E so por isso que isto roda.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, treino  # noqa: E402
from rede.custo import EntropiaCruzada  # noqa: E402
from rede.rede import Rede  # noqa: E402

SEMENTE = 42


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=30)
    ap.add_argument("--lote", type=int, default=10)
    ap.add_argument("--taxa", type=float, default=0.5)
    ap.add_argument("--ocultos", type=int, default=30)
    args = ap.parse_args()

    print("carregando MNIST...")
    treinamento, validacao, teste = dados.carregar_mnist()
    print(f"  treino {len(treinamento)}  validacao {len(validacao)}  teste {len(teste)}")
    print()

    r = Rede([784, args.ocultos, 10], semente=SEMENTE)
    print(r)
    print(f"lote {args.lote}   taxa {args.taxa}   epocas {args.epocas}")
    print()

    # A LINHA DE BASE. Uma rede nao treinada acerta ~10% — e o que o acaso
    # daria com 10 classes. Sem esse numero na frente, nao da para dizer se
    # 90% e bom: da para dizer que e melhor que 10%.
    base = treino.acertos(r, teste)
    print(f"antes do treino: {base}/{len(teste)} = {100*base/len(teste):.1f}%  (acaso ~10%)")
    print()

    inicio = time.time()
    treino.treinar(
        r, treinamento,
        epocas=args.epocas,
        tamanho_lote=args.lote,
        taxa=args.taxa,
        custo=EntropiaCruzada,
        dados_teste=teste,
        semente=SEMENTE,
        mostrar=True,
    )
    duracao = time.time() - inicio

    certos = treino.acertos(r, teste)
    print()
    print(f"teste final: {certos}/{len(teste)} = {100*certos/len(teste):.2f}%")
    print(f"tempo: {duracao:.0f}s  ({duracao/args.epocas:.1f}s por epoca)")


if __name__ == "__main__":
    main()
