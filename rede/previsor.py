"""O previsor: dada uma janela de eventos, qual e o proximo.

E UM MODELO DE LINGUAGEM, COM EVENTOS NO LUGAR DE PALAVRAS

    janela de 6 tokens -> tabela de embutimento -> camada oculta -> softmax

Esta e a arquitetura do Bengio, de 2003 — o primeiro modelo de linguagem
neural, e o avo direto do GPT. Nao e um brinquedo didatico: e o degrau
historico real, e cabe inteiro na CPU.

POR QUE PREVER, EM VEZ DE CLASSIFICAR

Classificar exige alguem dizendo, para cada evento, o que ele e. Ninguem
tem esse rotulo — e quando as regras fizeram o papel de professor, a rede
aprendeu a copiar as regras e acertou 100%, que e o mesmo que nao aprender.

Prever nao precisa de rotulo nenhum: o proximo evento E o rotulo, e ele
chega sozinho um segundo depois.

E O ALARME SAI DE GRACA

    surpresa = -ln( probabilidade que o modelo deu ao que realmente aconteceu )

O que o gerente consegue prever e rotina. O que ele NAO consegue prever e o
que merece atencao. Ninguem precisa definir antes o que e um furto: basta
que ele seja improvavel.

E essa formula ja e conhecida: e a entropia cruzada de um exemplo so.

    Prever bem e comprimir bem. Um alarme e uma conta de compressao que
    deu errado.

A TABELA DE EMBUTIMENTO E A PARTE NOVA

Cada token vira um vetor de `dimensao` numeros, e esses vetores sao
APRENDIDOS. Nada obriga `ENTROU:frente-a` e `ENTROU:frente-b` a ficarem
perto — mas se eles forem seguidos das mesmas coisas, o gradiente vai
empurra-los para perto sozinho. E ai a tabela vira um mapa de significado
que ninguem desenhou.
"""

import numpy as np

from rede.ativacao import Softmax
from rede.custo import EntropiaCruzadaCategorica
from rede.rede import Rede
from rede.retropropagacao import gradiente_com_entrada


class Previsor:
    """Janela fixa de tokens -> distribuicao sobre o proximo token."""

    def __init__(self, tamanho_vocabulario, janela=6, dimensao=16,
                 ocultos=64, semente=None):
        self.V = tamanho_vocabulario
        self.janela = janela
        self.dimensao = dimensao

        gerador = np.random.default_rng(semente)
        # Inicializacao pequena: a tabela entra direto na primeira
        # multiplicacao, sem sigmoid antes. Valores grandes aqui saturariam
        # a camada oculta ja no primeiro passo.
        self.tabela = gerador.standard_normal((tamanho_vocabulario, dimensao)) * 0.1

        self.rede = Rede([janela * dimensao, ocultos, tamanho_vocabulario],
                         semente=semente, ativacao_saida=Softmax)

    # ------------------------------------------------------------------

    def entrada(self, indices):
        """Concatena os vetores da janela num vetor coluna.

        CONCATENAR, E NAO SOMAR. Somar perderia a ORDEM — "entrou, esticou o
        braco" viraria o mesmo que "esticou o braco, entrou". A posicao na
        janela e informacao, e concatenar e o que a preserva.
        """
        return np.concatenate([self.tabela[i] for i in indices]).reshape(-1, 1)

    def frente(self, indices):
        """A distribuicao de probabilidade sobre o proximo token."""
        return self.rede.frente(self.entrada(indices))

    def surpresa(self, indices, alvo):
        """-ln p(alvo). Zero e "eu sabia"; alto e "isso eu nao esperava"."""
        p = float(self.frente(indices)[alvo, 0])
        return -np.log(max(p, 1e-12))

    # ------------------------------------------------------------------

    def _alvo_coluna(self, alvo):
        y = np.zeros((self.V, 1))
        y[alvo] = 1.0
        return y

    def passo(self, lote, taxa):
        """Um passo de descida sobre um minilote de (janela, alvo)."""
        soma_pesos = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        soma_vies = [np.zeros_like(c.vies) for c in self.rede.camadas]
        soma_tabela = np.zeros_like(self.tabela)

        for indices, alvo in lote:
            x = self.entrada(indices)
            y = self._alvo_coluna(alvo)
            gp, gv, erro_entrada = gradiente_com_entrada(
                self.rede, x, y, EntropiaCruzadaCategorica)

            for i in range(len(self.rede.camadas)):
                soma_pesos[i] += gp[i]
                soma_vies[i] += gv[i]

            # O erro da entrada e um vetor de janela*dimensao. Cada pedaco
            # de `dimensao` numeros pertence a UM token da janela, e vai
            # para a linha daquele token na tabela.
            #
            # `+=` e nao `=`: um token que aparece duas vezes na mesma
            # janela recebe as duas contribuicoes. Sobrescrever perderia
            # uma delas em silencio.
            for k, indice in enumerate(indices):
                pedaco = erro_entrada[k*self.dimensao:(k+1)*self.dimensao, 0]
                soma_tabela[indice] += pedaco

        n = len(lote)
        for i, camada in enumerate(self.rede.camadas):
            camada.pesos -= (taxa / n) * soma_pesos[i]
            camada.vies -= (taxa / n) * soma_vies[i]
        self.tabela -= (taxa / n) * soma_tabela

    # ------------------------------------------------------------------

    def avaliar(self, exemplos):
        """(custo medio, perplexidade, acerto em 1, acerto em 3).

        PERPLEXIDADE E O NUMERO QUE SE REPORTA

            perplexidade = e^(custo medio)

        Ela responde: "em media, entre quantas opcoes o modelo ficou em
        duvida". Com 29 tokens, chutar ao acaso da perplexidade 29.
        Perplexidade 4 significa que o modelo reduziu 29 opcoes a umas 4.

        E um numero que se compara entre modelos; o custo cru, nao.
        """
        if not exemplos:
            return 0.0, 1.0, 0.0, 0.0

        soma, em1, em3 = 0.0, 0, 0
        for indices, alvo in exemplos:
            p = self.frente(indices)
            soma += -np.log(max(float(p[alvo, 0]), 1e-12))
            ordem = np.argsort(-p.ravel())
            if ordem[0] == alvo:
                em1 += 1
            if alvo in ordem[:3]:
                em3 += 1

        n = len(exemplos)
        custo = soma / n
        return custo, float(np.exp(custo)), em1 / n, em3 / n

    @property
    def n_parametros(self):
        return self.tabela.size + self.rede.n_parametros
