"""Carregar os dados. Nada de matematica aqui.

XOR
    4 exemplos, 2 entradas, 1 saida:

        0,0 -> 0     1,0 -> 1
        0,1 -> 1     1,1 -> 0

    E o menor problema que uma rede de uma camada so NAO consegue resolver —
    as quatro respostas nao se separam por uma reta. Foi essa impossibilidade
    que travou o campo nos anos 70. Precisa de camada oculta, e por isso e o
    primeiro alvo: se a rede acerta XOR, a camada oculta esta fazendo o seu
    trabalho de verdade.

MNIST
    `dados/mnist.pkl.gz`, copiado do repositorio do Nielsen.
    50 mil de treino, 10 mil de validacao, 10 mil de teste.
    Cada imagem: 28x28 = 784 entradas, achatadas num vetor coluna.
    Cada rotulo vira um vetor de 10 posicoes com 1 na posicao certa.

    O arquivo foi gravado com pickle do Python 2. Ao ler no Python 3 e
    preciso `encoding="latin1"` — sem isso, estoura UnicodeDecodeError. E a
    unica cicatriz que a idade do repositorio deixa na gente.
"""

import gzip
import pickle
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_MNIST = RAIZ / "dados" / "mnist.pkl.gz"


XOR = (
    ((0.0, 0.0), 0.0),
    ((0.0, 1.0), 1.0),
    ((1.0, 0.0), 1.0),
    ((1.0, 1.0), 0.0),
)


def carregar_xor():
    """Devolve [(x, y), ...] com 4 pares. x e (2,1); y e (1,1).

    Vetor COLUNA, nao linha. Toda a algebra do projeto assume coluna:
    `pesos @ entrada` so fecha se `entrada` for (n_entradas x 1). Deixar um
    (2,) passar aqui produz uma forma errada la na frente, longe da causa.
    """
    return [
        (np.array(x, dtype=float).reshape(2, 1),
         np.array([[y]], dtype=float))
        for x, y in XOR
    ]


def vetorizar_digito(d):
    """5 -> vetor (10,1) com 1,0 na posicao 5 e zero no resto.

    POR QUE O ROTULO VIRA VETOR

    A rede tem 10 saidas, uma por digito. Ela nao devolve "5": devolve dez
    numeros entre 0 e 1. Para comparar previsao com resposta, a resposta
    precisa ter a mesma forma da previsao.

    Isso se chama codificacao one-hot, e nao e so conveniencia: ela diz que
    os digitos sao categorias SEM ordem. Se o rotulo fosse o numero 5 cru, a
    rede seria empurrada a achar que 4 e 6 sao "quase certos" quando a
    resposta e 5 — o que e verdade para distancia, e falso para digito.
    """
    v = np.zeros((10, 1))
    v[int(d)] = 1.0
    return v


def _pares(conjunto):
    imagens, rotulos = conjunto
    return [(x.reshape(784, 1).astype(float), vetorizar_digito(d))
            for x, d in zip(imagens, rotulos)]


def carregar_mnist(caminho=CAMINHO_MNIST):
    """Devolve (treino, validacao, teste), cada um [(x, y), ...].

    50.000 / 10.000 / 10.000. Cada x e (784,1) com valores ja entre 0 e 1;
    cada y e (10,1) one-hot.

    O `encoding="latin1"` NAO E OPCIONAL: o arquivo foi gravado com o pickle
    do Python 2, onde str era bytes. Sem ele, `UnicodeDecodeError`.

    DIFERENCA DELIBERADA EM RELACAO AO LIVRO: o Nielsen vetoriza o rotulo so
    no treino e deixa validacao e teste como inteiro, o que obriga cada
    funcao consumidora a saber de qual conjunto veio o dado. Aqui os tres
    conjuntos tem a mesma forma. Uma forma so e menos coisa para errar.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"MNIST nao encontrado em {caminho}")

    with gzip.open(caminho, "rb") as arquivo:
        treino, validacao, teste = pickle.load(arquivo, encoding="latin1")

    return _pares(treino), _pares(validacao), _pares(teste)
