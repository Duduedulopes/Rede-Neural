"""Treina a rede no XOR. Programa — nao importe este arquivo.

    python programas/xor.py

POR QUE O XOR E O PRIMEIRO ALVO

    0,0 -> 0     1,0 -> 1
    0,1 -> 1     1,1 -> 0

Nao existe reta que separe os zeros dos uns. Um perceptron de uma camada so
traca exatamente uma reta, entao ele NAO CONSEGUE — e essa impossibilidade,
publicada em 1969, esfriou o campo por mais de dez anos.

Com uma camada oculta, a rede pode dobrar o espaco antes de separar. Se este
programa acerta as quatro linhas, a camada oculta esta fazendo trabalho de
verdade, e nao enfeitando.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, treino  # noqa: E402
from rede.custo import EntropiaCruzada  # noqa: E402
from rede.rede import Rede  # noqa: E402
from rede.retropropagacao import conferir_numericamente  # noqa: E402

SEMENTE = 42


def main():
    treinamento = dados.carregar_xor()
    r = Rede([2, 3, 1], semente=SEMENTE)

    print(r)
    print()

    # ---- A CONFERENCIA VEM ANTES DO TREINO -------------------------------
    # Treinar com gradiente errado produz um resultado ruim que parece falta
    # de epoca. Confere-se uma vez, aqui, e nunca mais se duvida.
    print("conferindo a retropropagacao contra a derivada numerica...")
    pior = max(conferir_numericamente(r, x, y, EntropiaCruzada)
               for x, y in treinamento)
    print(f"  maior diferenca: {pior:.2e}", "OK" if pior < 1e-7 else "SUSPEITO")
    print()

    antes = treino.custo_medio(r, treinamento, EntropiaCruzada)
    print(f"custo antes do treino: {antes:.6f}")
    print()

    historico = treino.treinar(
        r, treinamento,
        epocas=4000,
        tamanho_lote=4,      # 4 exemplos: o lote e o conjunto inteiro
        taxa=3.0,
        custo=EntropiaCruzada,
        semente=SEMENTE,
    )

    print(f"custo depois do treino: {historico[-1]:.6f}")
    print()

    print("  x1  x2  |  esperado  |  rede")
    print("  --------+------------+--------")
    for x, y in treinamento:
        a = r.frente(x)
        print(f"  {x[0,0]:.0f}   {x[1,0]:.0f}   |     {y[0,0]:.0f}      |  {a[0,0]:.4f}")

    certos = treino.acertos(r, treinamento)
    print()
    print(f"acertos: {certos}/4")


if __name__ == "__main__":
    main()
