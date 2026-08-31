"""A funcao de ativacao: sigmoid, tambem chamada curva logistica.

O QUE ELA FAZ

Espreme qualquer numero real para o intervalo (0, 1):

    sigmoid(z) = 1 / (1 + e^-z)

    z = -inf  ->  0
    z =    0  ->  0,5
    z = +inf  ->  1

O neuronio calcula a soma ponderada das entradas mais o vies, e a sigmoid
transforma esse numero num valor entre 0 e 1 — a "ativacao" do neuronio.

POR QUE PRECISA SER NAO LINEAR

Sem ela, cada camada seria uma multiplicacao de matriz, e uma pilha de
multiplicacoes de matriz colapsa numa unica matriz. Mil camadas lineares tem
exatamente o mesmo poder de uma camada linear so. A nao linearidade e o que
faz camada ocultas valerem alguma coisa.

POR QUE A DERIVADA IMPORTA TANTO

A retropropagacao precisa saber o quanto a saida muda quando z muda. Essa e
a derivada, e para a sigmoid ela tem uma forma notavelmente conveniente:

    sigmoid'(z) = sigmoid(z) * (1 - sigmoid(z))

Ou seja: a derivada se calcula a partir do valor JA CALCULADO na ida. Nao e
preciso guardar z, so a ativacao. E por isso que a sigmoid dominou o campo
por decadas.

O DEFEITO, REGISTRADO DESDE JA

Repare que o maximo dessa derivada e 0,25 (em z = 0), e ela vai a zero nas
duas pontas. Num empilhamento de camadas, os gradientes sao multiplicados
uns pelos outros: 0,25 x 0,25 x 0,25 encolhe rapido. E o problema do
gradiente que se desvanece, e e o motivo pelo qual redes profundas modernas
usam ReLU. Nao e motivo para nao comecar pela sigmoid — e motivo para saber
por que ela sera trocada mais tarde.
"""

import numpy as np


def sigmoid(z):
    """1 / (1 + e^-z). Funciona com escalar, vetor ou matriz.

    ESCRITA DE FORMA ESTAVEL, E NAO COMO NA FORMULA

    A traducao ingenua seria `1 / (1 + np.exp(-z))`. Ela esta certa na
    matematica e quebra no computador: com z = -800, `np.exp(800)` estoura o
    float e vira `inf`, com aviso de overflow no meio do treino.

    O truque: `-abs(z)` nunca e positivo, entao `exp(-abs(z))` nunca estoura.
    As duas formas abaixo sao algebricamente identicas — uma e usada quando
    z >= 0 e a outra quando z < 0.

            z >= 0    1 / (1 + e^-z)
            z <  0    e^z / (1 + e^z)

    Nao e preciosismo: a primeira vez que um peso ficar grande, a versao
    ingenua enche o terminal de aviso e devolve `nan` — e `nan` contamina
    tudo que encostar nele daquele ponto em diante.
    """
    z = np.asarray(z, dtype=float)
    e = np.exp(-np.abs(z))
    return np.where(z >= 0, 1.0 / (1.0 + e), e / (1.0 + e))


def sigmoid_derivada(z):
    """sigmoid(z) * (1 - sigmoid(z)).

    Vale reparar no valor maximo: em z = 0 a sigmoid vale 0,5, entao a
    derivada vale 0,5 x 0,5 = 0,25. Nunca passa disso. Esse teto e a origem
    do gradiente que se desvanece em redes profundas.
    """
    s = sigmoid(z)
    return s * (1.0 - s)


def softmax(z):
    """Transforma um vetor de numeros numa DISTRIBUICAO DE PROBABILIDADE.

    A DIFERENCA PARA A SIGMOID, QUE E O PONTO

    A sigmoid trata cada saida SOZINHA. Com 10 saidas sigmoid, a rede pode
    dizer 0,9 para o digito 3 e 0,9 para o 8 ao mesmo tempo, e nao ha nada de
    errado nisso do ponto de vista dela: sao dez perguntas independentes de
    sim ou nao.

    Mas o problema nao e esse. Um digito e UM so — as dez respostas competem.
    A softmax e o que escreve essa competicao na propria arquitetura:

        softmax(z)_i = e^(z_i) / soma_j e^(z_j)

    Todas as saidas positivas, somando exatamente 1. Subir uma OBRIGA a
    descer as outras. A rede deixa de responder dez perguntas e passa a
    responder uma: "qual e a distribuicao de probabilidade sobre as classes?"

    E ESTA E A SAIDA DE UM MODELO DE TOKENS

        "produz como saida uma distribuicao de probabilidades sobre todos os
        tokens possiveis"

    E isto. A unica diferenca entre o MNIST e um modelo de linguagem, nesta
    camada, e que la o vetor tem dezenas de milhares de posicoes em vez de
    dez. A conta e a mesma.

    A SUBTRACAO DO MAXIMO NAO MUDA O RESULTADO E SALVA A CONTA

    e^z estoura o float por volta de z = 710. E subtrair uma constante de
    TODOS os z nao altera a saida — a constante aparece em cima e embaixo da
    fracao e se cancela. Subtraindo o maximo, o maior expoente vira e^0 = 1 e
    nada mais estoura.

    Mesma licao da sigmoid escrita com exp(-|z|): a formula certa na
    matematica pode ser a formula errada no computador.
    """
    z = np.asarray(z, dtype=float)
    e = np.exp(z - np.max(z))
    return e / np.sum(e)


class Sigmoid:
    """A ativacao como objeto, para a camada poder carregar a sua.

    Ate aqui toda camada era sigmoid, cravado. Com a softmax entrando so na
    camada de SAIDA, a camada precisa saber qual e a dela — e a
    retropropagacao precisa perguntar em vez de supor.
    """

    nome = "sigmoid"

    @staticmethod
    def fn(z):
        return sigmoid(z)

    @staticmethod
    def derivada(z):
        return sigmoid_derivada(z)


class Softmax:
    """So na camada de saida, e sempre acompanhada da entropia cruzada."""

    nome = "softmax"

    @staticmethod
    def fn(z):
        return softmax(z)

    @staticmethod
    def derivada(z):
        """NAO EXISTE COMO VETOR, E NAO PRECISA EXISTIR.

        Cada saida da softmax depende de TODAS as entradas, entao a derivada
        e uma matriz (a jacobiana), nao um vetor — nao cabe na multiplicacao
        elemento a elemento que a retropropagacao faz.

        E nunca e preciso calcula-la: junto com a entropia cruzada
        categorica, a jacobiana se cancela e o erro da camada de saida vira
        `a - y`, direto. Por isso as duas andam sempre juntas.

        Levantar aqui e deliberado: se alguem usar softmax com outro custo,
        vai descobrir na hora, e nao com um treino que nao converge.
        """
        raise NotImplementedError(
            "softmax nao tem derivada elemento a elemento; "
            "use-a com EntropiaCruzadaCategorica, que ja embute o cancelamento")
