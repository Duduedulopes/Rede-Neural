"""Embutimento (embedding): representar uma coisa como um vetor.

O QUE E

Um embutimento e um vetor de numeros que representa alguma coisa — um
digito, um produto, uma palavra, um gesto — de forma que a POSICAO no espaco
carregue significado. Coisas parecidas ficam perto; coisas diferentes ficam
longe.

E a ideia sem a qual "multimodal" nao significa nada. Uma foto e 784 numeros;
um nome de produto e uma sequencia de letras; a altura da mao e um numero so.
Essas tres coisas nao tem como ser comparadas entre si — a menos que cada uma
seja traduzida para um vetor NO MESMO ESPACO. Ai a comparacao vira uma conta.

    Multimodal nao e um tipo de neuronio que se programa. E o que aparece
    quando duas modalidades diferentes sao empurradas para o mesmo espaco.

VOCE JA TEM UM, E NAO PEDIU POR ELE

A rede [784, 30, 10] treinada no MNIST tem uma camada oculta de 30 neuronios.
Para classificar um digito, a ativacao dessa camada e o que a rede achou que
valia a pena guardar sobre a imagem: 784 numeros comprimidos em 30.

Ninguem mandou ela criar uma representacao. Ela criou porque era o caminho
mais barato para acertar a saida. Isso e um embutimento aprendido, e
`representar()` aqui embaixo so vai buscar.

POR QUE COSSENO E NAO DISTANCIA

O que carrega significado num embutimento e a DIRECAO, nao o tamanho. Dois
vetores apontando para o mesmo lado representam a mesma coisa, mesmo que um
seja tres vezes maior — o tamanho costuma refletir so o quanto o neuronio
estava excitado, nao O QUE ele reconheceu.

    cos(a, b) = (a . b) / (|a| |b|)

     1  mesma direcao (mesma coisa)
     0  perpendiculares (nada a ver)
    -1  direcoes opostas

Distancia euclidiana misturaria direcao e intensidade. Cosseno separa as
duas e joga fora a que nao interessa.

NOTA SOBRE ESTA REDE ESPECIFICA

A sigmoid so devolve valores entre 0 e 1, entao todos os vetores daqui caem
no mesmo octante do espaco e o cosseno entre quaisquer dois ja nasce alto.
Isso NAO invalida a medida — o que interessa e a DIFERENCA entre pares
parecidos e pares diferentes, nao o valor absoluto. Com ReLU ou com saidas
centradas em zero a separacao ficaria mais dramatica. Registrado para nao
parecer, mais tarde, que a conta estava errada.
"""

import numpy as np


def normalizar(v):
    """Devolve o vetor com comprimento 1, mantendo a direcao.

    Depois disto, o produto escalar entre dois vetores JA E o cosseno — e
    e por isso que sistemas de busca guardam tudo normalizado: transforma
    uma divisao por vetor numa unica multiplicacao de matriz.
    """
    v = np.asarray(v, dtype=float)
    norma = np.linalg.norm(v)
    if norma == 0.0:
        raise ValueError("vetor nulo nao tem direcao para normalizar")
    return v / norma


def similaridade_cosseno(a, b):
    """cos(a, b), de -1 a 1."""
    return float(normalizar(a).ravel() @ normalizar(b).ravel())


def representar(rede, x, indice_camada=None):
    """O embutimento de `x`: a ativacao de uma camada interna.

    `indice_camada` padrao e a PENULTIMA camada — a ultima antes da saida.
    E a convencao do campo: a camada de saida ja esta comprometida com as
    classes do treino, enquanto a anterior guarda a representacao geral.
    E por isso que se reaproveita a penultima camada de uma rede treinada
    para tarefas que ela nunca viu.

    O `.copy()` NAO E DETALHE: `ultima_ativacao` e sobrescrita na proxima
    chamada de `frente`. Sem a copia, uma lista de embutimentos terminaria
    com todos os elementos apontando para o mesmo vetor — o ultimo.
    """
    if indice_camada is None:
        indice_camada = len(rede.camadas) - 2
    if indice_camada < 0:
        raise ValueError("rede sem camada oculta: nao ha o que representar")

    rede.frente(x)
    return rede.camadas[indice_camada].ultima_ativacao.copy()


def centroide(vetores):
    """O vetor medio de um grupo, normalizado.

    E a "ideia media" daquele grupo no espaco. O centroide dos embutimentos
    de todos os treses e o que a rede entende por tres.
    """
    if len(vetores) == 0:
        raise ValueError("nenhum vetor para o centroide")
    return normalizar(np.mean(np.hstack([np.asarray(v).reshape(-1, 1)
                                         for v in vetores]), axis=1,
                              keepdims=True))


def matriz_de_similaridade(vetores):
    """Matriz n x n com o cosseno entre cada par.

    Feita com UMA multiplicacao de matriz depois de normalizar tudo:

        M = V.T @ V     com as colunas de V ja normalizadas

    Nao ha laco duplo. Comparar mil vetores com mil vetores e uma
    multiplicacao de matriz — e e assim que busca por similaridade escala.
    """
    V = np.hstack([normalizar(np.asarray(v).reshape(-1, 1)) for v in vetores])
    return V.T @ V
