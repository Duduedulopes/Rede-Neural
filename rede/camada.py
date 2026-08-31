"""UMA camada: os pesos, o vies e a ativacao.

O QUE E UMA CAMADA, EM ALGEBRA LINEAR

Uma camada com `n_entradas` entradas e `n_neuronios` neuronios guarda:

    pesos   matriz (n_neuronios x n_entradas)
    vies    vetor  (n_neuronios x 1)

e a conta que ela faz e uma so:

    z = pesos @ entrada + vies
    a = sigmoid(z)

Repare que a camada inteira e UMA multiplicacao de matriz. Nao existe laco
sobre neuronios: o neuronio i e a linha i da matriz. E por isso que o campo
inteiro e escrito em algebra linear — nao por elegancia, mas porque a CPU
multiplica matriz muito mais rapido do que percorre uma lista.

O QUE O VIES SIGNIFICA

    O vies diz o quao alta a soma ponderada precisa ser para o neuronio
    ativar de forma significativa.

Sem vies, todo neuronio e obrigado a ativar em torno de z = 0. O vies desloca
esse limiar. Um vies muito negativo faz um neuronio dificil de agradar; um
vies positivo faz um neuronio que dispara facil.

POR QUE UMA CLASSE, E NAO SO LISTAS DE MATRIZES

O Nielsen guarda `self.weights` e `self.biases` como listas na rede. Funciona
e e menos codigo. Escolhemos a classe porque "camada de entrada, camadas
ocultas, camada de saida" e o conceito que estamos estudando — e um conceito
que aparece no codigo se aprende melhor que um que so existe no indice de uma
lista.

Custo dessa escolha, declarado: o codigo daqui nao vai ser identico ao do
livro. Ao comparar, e preciso lembrar que `camadas[2].pesos` daqui e
`weights[1]` la.

O QUE A CAMADA GUARDA DA ULTIMA IDA

`ultimo_z` e `ultima_ativacao` sao memoria da passagem para frente. A
retropropagacao precisa deles: para saber o quanto cada peso contribuiu para
o erro, e preciso saber o que passou por ele. Guardar aqui e o que evita
recalcular a ida inteira na volta.
"""

import numpy as np

from rede.ativacao import Sigmoid


class Camada:
    """Uma camada densa: todos os neuronios ligados a todas as entradas."""

    def __init__(self, n_entradas, n_neuronios, gerador=None, ativacao=None):
        """Cria pesos e vies.

        A INICIALIZACAO NAO E DETALHE. Pesos todos iguais (zero, por exemplo)
        fazem todos os neuronios da camada calcularem a mesma coisa e
        receberem o mesmo gradiente — eles nunca se diferenciam, e a camada
        inteira vira um neuronio so. Isso se chama quebra de simetria, e e
        por isso que a inicializacao e aleatoria.

        POR QUE DIVIDIR POR raiz(n_entradas)

        z e a soma de n_entradas termos. Somando n numeros aleatorios de
        desvio 1, o desvio do total cresce com raiz(n): com 784 entradas,
        z sai tipicamente na casa de +-28. E ali a sigmoid ja esta colada em
        0 ou em 1, e a derivada dela e praticamente zero — a rede nasce
        saturada e nao aprende.

        Dividir os pesos por raiz(n_entradas) devolve z para a casa de +-1,
        que e onde a sigmoid tem inclinacao para aprender.

        O vies NAO e dividido: ele e um termo so, nao uma soma de n.

        `gerador` e um np.random.Generator. Recebe-lo de fora, em vez de
        sortear aqui dentro, e o que torna o treino reproduzivel.
        """
        if n_entradas < 1 or n_neuronios < 1:
            raise ValueError("camada precisa de pelo menos 1 entrada e 1 neuronio")

        if gerador is None:
            gerador = np.random.default_rng()

        self.n_entradas = n_entradas
        self.n_neuronios = n_neuronios

        # Cada camada carrega a SUA ativacao. Antes era sigmoid cravado; com a
        # softmax entrando so na saida, a retropropagacao passa a perguntar a
        # cada camada qual e a dela em vez de supor.
        self.ativacao = ativacao or Sigmoid

        self.pesos = gerador.standard_normal((n_neuronios, n_entradas)) / np.sqrt(n_entradas)
        self.vies = gerador.standard_normal((n_neuronios, 1))

        # Memoria da ultima ida. A volta precisa dela.
        self.ultima_entrada = None
        self.ultimo_z = None
        self.ultima_ativacao = None

    def frente(self, entrada):
        """z = pesos @ entrada + vies ; devolve a = sigmoid(z).

        Guarda `ultima_entrada`, `ultimo_z` e `ultima_ativacao` para a
        retropropagacao.

        UMA MULTIPLICACAO DE MATRIZ, NENHUM LACO

            pesos   (n_neuronios x n_entradas)
            entrada (n_entradas  x 1)
            vies    (n_neuronios x 1)
            z       (n_neuronios x 1)

        O `+ vies` funciona porque as formas batem; nao ha difusao implicita
        escondida aqui, e isso e proposital — difusao silenciosa e como um
        erro de forma vira um resultado errado em vez de uma excecao.
        """
        entrada = np.asarray(entrada, dtype=float).reshape(self.n_entradas, 1)

        self.ultima_entrada = entrada
        self.ultimo_z = self.pesos @ entrada + self.vies
        self.ultima_ativacao = self.ativacao.fn(self.ultimo_z)
        return self.ultima_ativacao

    @property
    def formato(self):
        """(n_entradas, n_neuronios) — util em teste e em mensagem de erro."""
        return (self.n_entradas, self.n_neuronios)

    @property
    def n_parametros(self):
        return self.pesos.size + self.vies.size

    def __repr__(self):
        return (f"Camada({self.n_entradas} -> {self.n_neuronios}, "
                f"{self.ativacao.nome}, {self.n_parametros} params)")
