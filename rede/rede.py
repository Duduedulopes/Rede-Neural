"""A rede: as camadas em sequencia.

CAMADA DE ENTRADA, CAMADAS OCULTAS, CAMADA DE SAIDA

    Rede([2, 3, 1])

le-se: 2 entradas, uma camada oculta de 3 neuronios, 1 saida. Isso cria DUAS
camadas de pesos — a de entrada nao tem pesos, ela e so o dado entrando. E
uma fonte classica de confusao ao contar camadas, e vale registrar: a lista
tem 3 numeros e a rede tem 2 objetos `Camada`.

O QUE ESTE ARQUIVO FAZ

So a passagem para frente. Empilha as camadas e passa a saida de uma como
entrada da proxima.

O QUE ELE NAO FAZ

Nao aprende. Aprender e retropropagacao (`retropropagacao.py`) mais descida
do gradiente (`treino.py`). Separar isso e deliberado: uma rede que so sabe
prever e um objeto simples e testavel; misturar aprendizado aqui esconde o
amago dentro de um metodo qualquer.
"""

import numpy as np

from rede.camada import Camada


class Rede:
    """Camadas densas em sequencia."""

    def __init__(self, tamanhos, semente=None, ativacao_saida=None):
        """`tamanhos` = [entradas, oculta1, ..., saida]. Ex.: [2, 3, 1].

        ATENCAO A CONTAGEM: [2, 3, 1] tem tres numeros e cria DUAS camadas.
        A camada de entrada nao tem pesos — ela e so o dado entrando.
        """
        tamanhos = list(tamanhos)
        if len(tamanhos) < 2:
            raise ValueError("a rede precisa de ao menos entrada e saida")

        self.tamanhos = tamanhos
        gerador = np.random.default_rng(semente)
        ultima = len(tamanhos) - 2
        self.camadas = [
            Camada(tamanhos[i], tamanhos[i + 1], gerador,
                   ativacao=(ativacao_saida if i == ultima else None))
            for i in range(len(tamanhos) - 1)
        ]

    @classmethod
    def de_camadas(cls, camadas):
        """Uma rede montada com camadas JA EXISTENTES, em vez de novas.

        POR QUE ISTO EXISTE: DUAS SAIDAS SOBRE O MESMO TRONCO.

        O gerente precisa responder duas coisas da mesma frase — o que a
        pessoa quer, e em que tom ela esta. Sao duas perguntas, e cada uma
        merece a sua propria softmax; juntar tudo numa saida so faria
        "urgente" e "estoque" competirem pelo mesmo lugar, quando a frase
        "urgente, quanto tem de agua" e as DUAS coisas.

        Mas elas nao precisam de dois cerebros. A parte cara e a tabela de
        vetores e a camada oculta, que e onde a frase vira entendimento —
        e o entendimento serve as duas perguntas igual. Entao:

            vetores -> oculta ─┬→ softmax das intencoes
                               └→ softmax dos tons

        Montar isso pede duas `Rede` que COMPARTILHAM o mesmo objeto
        `Camada` do tronco. Compartilhar de verdade, o mesmo objeto: assim
        o que uma aprende no tronco a outra ja sabe.

        E seguro porque `Camada.frente` reescreve a memoria dela a cada
        chamada, e `gradiente` sempre chama `frente` antes de olhar. Com a
        mesma entrada nas duas, o estado guardado e o mesmo.
        """
        rede = cls.__new__(cls)
        rede.camadas = list(camadas)
        rede.tamanhos = ([camadas[0].n_entradas] +
                         [c.n_neuronios for c in camadas])
        return rede

    def frente(self, entrada):
        """A previsao. Passa a entrada por todas as camadas, em ordem."""
        a = np.asarray(entrada, dtype=float).reshape(self.tamanhos[0], 1)
        for camada in self.camadas:
            a = camada.frente(a)
        return a

    @property
    def n_parametros(self):
        """Quantos numeros o treino precisa ajustar.

        Vale calcular uma vez para sentir a escala: uma rede [784, 30, 10]
        tem 23.860 parametros. E por isso que calcular o gradiente por forca
        bruta esta fora de questao, e por isso que a retropropagacao existe.
        """
        return sum(c.n_parametros for c in self.camadas)

    def __repr__(self):
        forma = "-".join(str(t) for t in self.tamanhos)
        return f"Rede({forma}, {self.n_parametros} parametros)"
