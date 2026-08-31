"""Mostra que a camada oculta JA E um embutimento. Programa.

    python programas/embeddings.py --epocas 5

A PERGUNTA QUE ESTE PROGRAMA RESPONDE

A rede foi treinada so para classificar digitos. Ninguem pediu a ela que
organizasse nada. A camada oculta aprendeu, por conta propria, uma
representacao em que digitos parecidos ficam perto?

O metodo: pegar os 30 numeros da camada oculta para milhares de imagens de
teste, tirar o centroide de cada digito, e medir o cosseno entre eles.

A COMPARACAO CONTRA OS PIXELS CRUS E O QUE FECHA O ARGUMENTO

Se so o espaco de 30 dimensoes fosse mostrado, restaria a duvida: sera que
qualquer espaco separaria? Por isso a mesma conta e feita nos 784 pixels
crus. Se os pixels ja separassem bem, a rede nao teria aprendido nada de
util — teria so encolhido o vetor.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, treino  # noqa: E402
from rede.custo import EntropiaCruzada  # noqa: E402
from rede.embutimento import (centroide, matriz_de_similaridade,  # noqa: E402
                              normalizar, representar)
from rede.rede import Rede  # noqa: E402

SEMENTE = 42
POR_DIGITO = 400


def intra_e_inter(vetores, rotulos):
    """(cosseno medio dentro do mesmo digito, cosseno medio entre digitos).

    ERRO CORRIGIDO AQUI, 30/08. A primeira versao usava a diagonal da matriz
    de centroides como "mesmo digito". A diagonal e o cosseno do centroide
    com ELE MESMO: 1,000 sempre, por construcao, em qualquer espaco. Um
    numero que nao pode variar nao mede nada.

    O certo e comparar exemplos INDIVIDUAIS entre si: pares do mesmo digito
    contra pares de digitos diferentes.
    """
    V = np.hstack([normalizar(np.asarray(v).reshape(-1, 1)) for v in vetores])
    S = V.T @ V
    r = np.asarray(rotulos)

    mesmo = r[:, None] == r[None, :]
    fora_da_diagonal = ~np.eye(len(r), dtype=bool)

    intra = float(np.mean(S[mesmo & fora_da_diagonal]))
    inter = float(np.mean(S[~mesmo]))
    return intra, inter


def acerto_por_centroide(vetores, rotulos, centros):
    """Classifica cada vetor pelo centroide mais proximo em cosseno.

    O CLASSIFICADOR MAIS BURRO POSSIVEL — nenhum treino, nenhum parametro,
    so "de qual media voce esta mais perto". E exatamente por ser burro que
    ele mede o ESPACO em vez de medir o classificador.

    Rodar o mesmo classificador burro nos dois espacos e o que separa
    "a rede aprendeu uma representacao util" de "a rede so encolheu o vetor".
    """
    V = np.hstack([normalizar(np.asarray(v).reshape(-1, 1)) for v in vetores])
    C = np.hstack([np.asarray(c).reshape(-1, 1) for c in centros])
    previsto = np.argmax(C.T @ V, axis=0)
    return float(np.mean(previsto == np.asarray(rotulos)))


def imprimir_matriz(M, titulo):
    print(titulo)
    print("      " + "".join(f"{j:>7d}" for j in range(10)))
    for i in range(10):
        linha = "".join(f"{M[i, j]:>7.3f}" for j in range(10))
        print(f"  {i}  {linha}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=5)
    args = ap.parse_args()

    treinamento, _, teste = dados.carregar_mnist()
    r = Rede([784, 30, 10], semente=SEMENTE)

    print(f"treinando {r} por {args.epocas} epocas...")
    treino.treinar(r, treinamento, epocas=args.epocas, tamanho_lote=10,
                   taxa=0.5, custo=EntropiaCruzada, semente=SEMENTE)
    certos = treino.acertos(r, teste)
    print(f"  teste: {100 * certos / len(teste):.2f}%")
    print()

    # Separa exemplos de teste por digito.
    por_digito = {d: [] for d in range(10)}
    for x, y in teste:
        d = int(np.argmax(y))
        if len(por_digito[d]) < POR_DIGITO:
            por_digito[d].append(x)

    # --- O espaco aprendido: 30 dimensoes da camada oculta ---------------
    centros_ocultos = [centroide([representar(r, x) for x in por_digito[d]])
                       for d in range(10)]
    M_oculto = matriz_de_similaridade(centros_ocultos)

    # --- A linha de base: os 784 pixels crus -----------------------------
    centros_pixels = [centroide(por_digito[d]) for d in range(10)]
    M_pixels = matriz_de_similaridade(centros_pixels)

    imprimir_matriz(M_pixels, "PIXELS CRUS (784 dimensoes) — cosseno entre centroides")
    imprimir_matriz(M_oculto, "CAMADA OCULTA (30 dimensoes) — cosseno entre centroides")

    # Vetores individuais e seus rotulos, para as medidas honestas.
    brutos, ocultos, rotulos = [], [], []
    for d in range(10):
        for x in por_digito[d]:
            brutos.append(x)
            ocultos.append(representar(r, x))
            rotulos.append(d)

    i_px, e_px = intra_e_inter(brutos, rotulos)
    i_oc, e_oc = intra_e_inter(ocultos, rotulos)

    print("  cosseno entre exemplos INDIVIDUAIS")
    print("                        mesmo digito   digitos diferentes   separacao")
    print(f"  pixels crus (784)        {i_px:.3f}            {e_px:.3f}           {i_px - e_px:.3f}")
    print(f"  camada oculta (30)       {i_oc:.3f}            {e_oc:.3f}           {i_oc - e_oc:.3f}")
    print()

    a_px = acerto_por_centroide(brutos, rotulos, centros_pixels)
    a_oc = acerto_por_centroide(ocultos, rotulos, centros_ocultos)
    print("  classificador burro (centroide mais proximo, zero treino)")
    print(f"  nos pixels crus:     {100 * a_px:.1f}%")
    print(f"  no espaco aprendido: {100 * a_oc:.1f}%")
    print()

    # O par mais confundido em cada espaco.
    def pior_par(M):
        fora = M - np.eye(10) * 2
        i, j = np.unravel_index(np.argmax(fora), fora.shape)
        return int(i), int(j), float(fora[i, j])

    i, j, s = pior_par(M_pixels)
    print(f"  par mais parecido nos pixels:  {i} e {j}  ({s:.3f})")
    i, j, s = pior_par(M_oculto)
    print(f"  par mais parecido no aprendido: {i} e {j}  ({s:.3f})")


if __name__ == "__main__":
    main()
