"""O classificador de intencao: pergunta escrita -> o que a pessoa quer.

A ARQUITETURA, E POR QUE ELA E DIFERENTE DA DO PREVISOR

    pecas da frase -> tabela de embutimento -> MEDIA -> oculta -> softmax

O previsor CONCATENA os vetores da janela, porque la a ordem e tudo. Aqui a
media, por duas razoes que so valem para texto de pergunta:

    tamanho variavel   "oi" tem 1 palavra, "quanto faturamos hoje no total"
                       tem 5. Concatenacao exige comprimento fixo.
    ordem nao importa  "quanto vendi hoje" e "hoje quanto vendi" pedem a
                       mesma coisa.

E o modelo do fastText. Ele e simples de um jeito que engana: com poucas
centenas de exemplos ele bate coisas muito maiores, justamente porque tem
pouco o que decorar.

O GRADIENTE DA MEDIA TEM UMA DIVISAO QUE E FACIL ESQUECER

    x = (1/k) * soma dos k vetores usados

Entao cada vetor recebe `erro_entrada / k`, e nao `erro_entrada`. Sem
dividir, uma frase longa empurraria os vetores dela com forca k vezes maior
que uma frase curta — e o modelo aprenderia mais com quem escreve mais.

Sutil, nao levanta excecao, e enviesa o treino inteiro.
"""

import numpy as np

from rede.ativacao import Softmax
from rede.custo import EntropiaCruzadaCategorica
from rede.rede import Rede
from rede.retropropagacao import gradiente_com_entrada


class ClassificadorDeIntencao:
    """Media dos embutimentos das pecas -> distribuicao sobre as intencoes."""

    def __init__(self, tamanho_vocabulario, intencoes, dimensao=24, ocultos=32,
                 semente=None):
        self.V = tamanho_vocabulario
        self.intencoes = list(intencoes)
        self.dimensao = dimensao

        gerador = np.random.default_rng(semente)
        self.tabela = gerador.standard_normal((tamanho_vocabulario, dimensao)) * 0.1
        self.rede = Rede([dimensao, ocultos, len(self.intencoes)],
                         semente=semente, ativacao_saida=Softmax)

    # ------------------------------------------------------------------

    def entrada(self, indices):
        """A media dos vetores das pecas presentes, em coluna."""
        return self.tabela[indices].mean(axis=0).reshape(-1, 1)

    def prever(self, indices):
        """A distribuicao de probabilidade sobre as intencoes."""
        return self.rede.frente(self.entrada(indices))

    def responder(self, indices):
        """(intencao, confianca)."""
        p = self.prever(indices)
        k = int(np.argmax(p))
        return self.intencoes[k], float(p[k, 0])

    # ------------------------------------------------------------------

    def _alvo(self, k):
        y = np.zeros((len(self.intencoes), 1))
        y[k] = 1.0
        return y

    def passo(self, lote, taxa):
        soma_pesos = [np.zeros_like(c.pesos) for c in self.rede.camadas]
        soma_vies = [np.zeros_like(c.vies) for c in self.rede.camadas]
        soma_tabela = np.zeros_like(self.tabela)

        for indices, k in lote:
            x = self.entrada(indices)
            gp, gv, erro_entrada = gradiente_com_entrada(
                self.rede, x, self._alvo(k), EntropiaCruzadaCategorica)

            for i in range(len(self.rede.camadas)):
                soma_pesos[i] += gp[i]
                soma_vies[i] += gv[i]

            # A DIVISAO POR len(indices) E A DERIVADA DA MEDIA.
            # Sem ela o treino pesaria mais as frases longas.
            parcela = erro_entrada.ravel() / len(indices)
            for i in indices:
                soma_tabela[i] += parcela

        n = len(lote)
        for i, camada in enumerate(self.rede.camadas):
            camada.pesos -= (taxa / n) * soma_pesos[i]
            camada.vies -= (taxa / n) * soma_vies[i]
        self.tabela -= (taxa / n) * soma_tabela

    # ------------------------------------------------------------------

    def avaliar(self, exemplos):
        """(acerto, custo medio, matriz de confusao)."""
        n_int = len(self.intencoes)
        M = np.zeros((n_int, n_int), dtype=int)
        soma, certos = 0.0, 0
        for indices, k in exemplos:
            p = self.prever(indices)
            escolhido = int(np.argmax(p))
            M[k, escolhido] += 1
            soma += -np.log(max(float(p[k, 0]), 1e-12))
            certos += int(escolhido == k)
        n = max(1, len(exemplos))
        return certos / n, soma / n, M

    @property
    def n_parametros(self):
        return self.tabela.size + self.rede.n_parametros

    def para_dicionario(self, vocabulario):
        return {
            "intencoes": self.intencoes,
            "pecas": vocabulario.pecas,
            "dimensao": self.dimensao,
            "tabela": [[round(float(x), 4) for x in linha] for linha in self.tabela],
            "camadas": [{"ativacao": c.ativacao.nome,
                         "pesos": [[round(float(x), 4) for x in l] for l in c.pesos],
                         "vies": [round(float(x), 4) for x in c.vies.ravel()]}
                        for c in self.rede.camadas],
        }
