"""A funcao de custo: o que significa "certo".

A rede precisa de UM numero que diga o quao ruim ela esta. Esse numero e o
custo, e treinar e minimiza-lo.

A MEDIA E PARTE DA DEFINICAO, NAO UM DETALHE

O custo nao e o erro de um exemplo: e a MEDIA do erro sobre todos os exemplos
de treinamento. Isso e o que impede a rede de acertar um caso e destruir os
outros. Quando dividirmos o treino em minilotes, cada minilote sera uma
ESTIMATIVA dessa media — e e por isso que a tecnica se chama estocastica.

DUAS FUNCOES, E A SEGUNDA EXISTE POR UM MOTIVO ESPECIFICO

QUADRATICO
    C = (1/2n) * soma |y - a|^2
    O erro ao quadrado. Intuitivo, e o ponto de partida do livro.

    O problema: o gradiente dele carrega um fator sigmoid'(z). Quando o
    neuronio erra COM CONVICCAO — saida 0,98 quando devia ser 0 — z esta
    longe de zero, sigmoid'(z) e quase nada, e o gradiente some. A rede
    aprende DEVAGAR justamente onde errou mais feio. E o oposto do que se
    espera de quem esta aprendendo.

ENTROPIA CRUZADA
    C = -(1/n) * soma [ y*ln(a) + (1-y)*ln(1-a) ]

    O fator sigmoid'(z) se cancela na derivada. O gradiente passa a ser
    proporcional ao ERRO (a - y) e nada mais: erro grande, passo grande.

    E tambem a funcao de perda dos modelos de token — a mesma conta que
    mede o quao bem uma distribuicao de probabilidade prevista bate com a
    verdadeira. Por isso ela reaparece na Fase 2 do projeto sem mudar.

CADA CUSTO TRAZ SEU PROPRIO `delta`

Cada classe expoe `fn` (o valor) e `delta` (o erro na camada de saida, ja
com a derivada da ativacao embutida quando for o caso). E assim que trocar
de custo nao exige mexer na retropropagacao — ela pergunta ao custo.
"""

import numpy as np

from rede.ativacao import sigmoid_derivada


class Quadratico:
    """C = (1/2) |a - y|^2 por exemplo."""

    @staticmethod
    def fn(a, y):
        return 0.5 * float(np.sum((a - y) ** 2))

    @staticmethod
    def delta(z, a, y):
        """Erro na camada de saida. Carrega sigmoid_derivada(z) — de proposito.

        E EXATAMENTE ESTE FATOR O PROBLEMA. Quando a rede erra com conviccao,
        z esta longe de zero, sigmoid_derivada(z) tende a zero, e o erro
        inteiro e multiplicado por quase nada.
        """
        return (a - y) * sigmoid_derivada(z)


class EntropiaCruzada:
    """C = -[ y ln a + (1-y) ln(1-a) ] por exemplo."""

    @staticmethod
    def fn(a, y):
        """`nan_to_num` cobre o caso a = 0 ou a = 1.

        Ali aparece 0 * log(0), que em ponto flutuante da `nan` — embora o
        limite matematico seja 0. Sem essa protecao, um neuronio saturado
        envenena o custo inteiro com `nan`.
        """
        # `errstate` silencia o aviso de log(0). Nao e varrer para baixo do
        # tapete: o `nan_to_num` logo abaixo E o tratamento, e ele esta certo
        # (o limite de 0*log(0) e zero). Sem isto, o terminal enche de aviso
        # toda vez que um neuronio satura — e aviso que sempre aparece deixa
        # de ser lido.
        with np.errstate(divide="ignore", invalid="ignore"):
            termos = -y * np.log(a) - (1 - y) * np.log(1 - a)
        return float(np.sum(np.nan_to_num(termos)))

    @staticmethod
    def delta(z, a, y):
        """Erro na camada de saida. Aqui `z` NAO e usado: o fator se cancelou.

        A assinatura mantem `z` para que os dois custos sejam intercambiaveis.
        Que o parametro exista e nao seja usado E a informacao.

        O gradiente e o erro puro: `a - y`. Errou muito, passo grande.
        """
        return a - y


class EntropiaCruzadaCategorica:
    """A entropia cruzada de UMA distribuicao contra outra. Par obrigatorio da softmax.

        C = - soma_i  y_i * ln(a_i)

    Com `y` one-hot, a soma tem um termo so: `-ln(a[classe_certa])`. Ou seja,
    o custo e o log da probabilidade que a rede deu para a resposta certa.

        a = 0,99  ->  C = 0,01     quase nenhum custo
        a = 0,50  ->  C = 0,69
        a = 0,01  ->  C = 4,61     caro
        a -> 0    ->  C -> infinito

    A PENALIDADE E ILIMITADA, E ISSO E O PROJETO E NAO UM EFEITO COLATERAL

    Errar com certeza absoluta custa infinito. A rede aprende a nunca dar
    probabilidade zero para nada — o que e a atitude correta de quem preve.

    O NOME VEM DA TEORIA DA INFORMACAO, E A INTERPRETACAO E LITERAL

    -ln(a) e o numero de nats necessarios para codificar um evento de
    probabilidade `a`. O custo e o tamanho medio da mensagem quando se
    codifica a realidade usando as probabilidades que o modelo acredita.

        Prever bem e comprimir bem. Sao a mesma conta.

    E por isso que "previsao e compressao" nao e metafora: um modelo que
    preve o proximo token com custo baixo E um compressor daquele texto.

    O CANCELAMENTO COM A SOFTMAX

    Derivando C em relacao a z (e nao a `a`), a jacobiana da softmax se
    cancela inteira e sobra:

        dC/dz = a - y

    Identico ao par sigmoid + entropia cruzada binaria. Nao e coincidencia:
    e a mesma familia de funcoes, e essa e a razao de ambas serem usadas.
    """

    @staticmethod
    def fn(a, y):
        # `clip` evita ln(0) = -inf quando a rede zera uma classe. 1e-15 e
        # aproximadamente o menor valor que o float64 distingue de zero perto
        # de 1 — cortar aqui muda o custo na 15a casa e evita um infinito.
        a = np.clip(np.asarray(a, dtype=float), 1e-15, 1.0)
        return float(-np.sum(y * np.log(a)))

    @staticmethod
    def delta(z, a, y):
        """`z` nao e usado: a jacobiana da softmax ja se cancelou."""
        return a - y
