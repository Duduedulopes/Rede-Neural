"""O classificador de DUAS SAIDAS: o que a pessoa quer, e em que tom.

    pecas -> tabela -> MEDIA -> oculta (32) ─┬→ softmax das intencoes
                                             └→ softmax dos tons

POR QUE DUAS SAIDAS, E NAO UMA SO MAIOR

Juntar tudo numa saida de 38 faria "urgencia" e "estoque" disputarem o
mesmo lugar. A frase "urgente, quanto tem de agua" e as DUAS coisas ao
mesmo tempo, e uma softmax unica obriga a escolher — a soma da 1.

Com duas saidas, cada uma soma 1 por conta propria e a frase pode ser
`estoque` a 96% E `urgencia` a 88%. Que e a verdade.

POR QUE UM TRONCO SO, E NAO DUAS REDES

A tabela de vetores e 57 mil dos 65 mil parametros. Uma segunda rede
duplicaria tudo isso para reaprender do zero o que "urgente" significa.
Pendurada na mesma oculta, a saida de tom custa

    32 x 7 pesos + 7 vieses = 231 parametros

e ja nasce lendo portugues, porque aproveita a leitura que a primeira faz.

O EFEITO COLATERAL QUE PRECISA SER MEDIDO

O tronco e compartilhado, entao aprender tom MUDA a representacao que a
intencao usa. Isso pode ajudar — duas tarefas relacionadas costumam
regularizar uma a outra — ou atrapalhar, se o tom roubar capacidade da
oculta. Nao da para saber sem medir contra o modelo de uma saida so.

Por isso `peso_tom` existe: quanto o gradiente do tom pesa no tronco.
Em 0 as duas ficam independentes (o tom aprende, a intencao nao sente);
em 1 as duas empurram igual. O valor certo e o que a medida disser, nao
o que parecer razoavel.

O QUE OS ROTULOS DE TOM SAO, HONESTAMENTE

Uma parte veio rotulada a mao no corpus da outra IA; a maior parte foi
deduzida por regra de marcador. Rotulo vindo de regra ensina, no maximo,
a regra — mais o que os vetores generalizarem em cima dela. Tom que a
regra nao enxerga, a rede tambem nao vai aprender.

Isso nao invalida a saida: ela ainda serve para escolher o jeito de
responder, e o campo `tom_origem` no corpus permite medir depois quanto
do acerto veio de frase rotulada a mao. Mas nao se pode dizer que a rede
"entende emocao" — ela aprendeu uma regra e a estendeu um pouco.
"""

import numpy as np

from rede.ativacao import Softmax
from rede.camada import Camada
from rede.custo import EntropiaCruzadaCategorica
from rede.rede import Rede
from rede.retropropagacao import gradiente_com_entrada


class ClassificadorDuplo:
    """Media dos embutimentos -> uma oculta -> duas softmax."""

    def __init__(self, tamanho_vocabulario, intencoes, tons,
                 dimensao=24, ocultos=32, semente=None, peso_tom=0.3):
        self.V = tamanho_vocabulario
        self.intencoes = list(intencoes)
        self.tons = list(tons)
        self.dimensao = dimensao
        self.peso_tom = peso_tom

        g = np.random.default_rng(semente)
        self.tabela = g.standard_normal((tamanho_vocabulario, dimensao)) * 0.1

        # O TRONCO E UM OBJETO SO, USADO PELAS DUAS REDES.
        self.tronco = Camada(dimensao, ocultos, g)
        self.cabeca_intencao = Camada(ocultos, len(self.intencoes), g, ativacao=Softmax)
        self.cabeca_tom = Camada(ocultos, len(self.tons), g, ativacao=Softmax)

        self.rede_intencao = Rede.de_camadas([self.tronco, self.cabeca_intencao])
        self.rede_tom = Rede.de_camadas([self.tronco, self.cabeca_tom])

    # ------------------------------------------------------------------

    def entrada(self, indices):
        return self.tabela[indices].mean(axis=0).reshape(-1, 1)

    def prever(self, indices):
        """So a intencao — mesma assinatura do classificador de uma saida."""
        return self.rede_intencao.frente(self.entrada(indices))

    def prever_tom(self, indices):
        return self.rede_tom.frente(self.entrada(indices))

    def responder(self, indices):
        """(intencao, confianca, tom, confianca_do_tom) — as duas de uma vez."""
        x = self.entrada(indices)
        pi = self.rede_intencao.frente(x)
        pt = self.rede_tom.frente(x)
        i, t = int(np.argmax(pi)), int(np.argmax(pt))
        return (self.intencoes[i], float(pi[i, 0]),
                self.tons[t], float(pt[t, 0]))

    # ------------------------------------------------------------------

    @staticmethod
    def _alvo(k, n):
        y = np.zeros((n, 1))
        y[k] = 1.0
        return y

    def passo(self, lote, taxa):
        """Um passo de descida com os dois erros somados no tronco.

        O TRONCO RECEBE A SOMA DOS DOIS GRADIENTES, e a tabela tambem.
        E o que faz as duas tarefas aprenderem juntas em vez de uma
        desfazer a outra a cada lote.
        """
        g_tronco_p = np.zeros_like(self.tronco.pesos)
        g_tronco_v = np.zeros_like(self.tronco.vies)
        g_int_p = np.zeros_like(self.cabeca_intencao.pesos)
        g_int_v = np.zeros_like(self.cabeca_intencao.vies)
        g_tom_p = np.zeros_like(self.cabeca_tom.pesos)
        g_tom_v = np.zeros_like(self.cabeca_tom.vies)
        g_tabela = np.zeros_like(self.tabela)

        for indices, k_int, k_tom in lote:
            x = self.entrada(indices)

            gp_i, gv_i, err_i = gradiente_com_entrada(
                self.rede_intencao, x, self._alvo(k_int, len(self.intencoes)),
                EntropiaCruzadaCategorica)
            gp_t, gv_t, err_t = gradiente_com_entrada(
                self.rede_tom, x, self._alvo(k_tom, len(self.tons)),
                EntropiaCruzadaCategorica)

            # camada 0 de cada rede E o mesmo tronco: os dois somam nele
            g_tronco_p += gp_i[0] + self.peso_tom * gp_t[0]
            g_tronco_v += gv_i[0] + self.peso_tom * gv_t[0]
            g_int_p += gp_i[1]; g_int_v += gv_i[1]
            g_tom_p += gp_t[1]; g_tom_v += gv_t[1]

            # A DIVISAO POR len(indices) E A DERIVADA DA MEDIA. Sem ela o
            # treino pesaria mais as frases longas.
            parcela = (err_i.ravel() + self.peso_tom * err_t.ravel()) / len(indices)
            for i in indices:
                g_tabela[i] += parcela

        n = len(lote)
        self.tronco.pesos -= (taxa / n) * g_tronco_p
        self.tronco.vies  -= (taxa / n) * g_tronco_v
        self.cabeca_intencao.pesos -= (taxa / n) * g_int_p
        self.cabeca_intencao.vies  -= (taxa / n) * g_int_v
        # A cabeca de tom aprende com a taxa cheia: `peso_tom` regula o
        # quanto ela mexe no TRONCO, nao o quanto ela mesma aprende.
        self.cabeca_tom.pesos -= (taxa / n) * g_tom_p
        self.cabeca_tom.vies  -= (taxa / n) * g_tom_v
        self.tabela -= (taxa / n) * g_tabela

    # ------------------------------------------------------------------

    def avaliar(self, exemplos):
        """(acerto_intencao, acerto_tom)."""
        ci = ct = 0
        for indices, k_int, k_tom in exemplos:
            x = self.entrada(indices)
            ci += int(np.argmax(self.rede_intencao.frente(x)) == k_int)
            ct += int(np.argmax(self.rede_tom.frente(x)) == k_tom)
        n = max(1, len(exemplos))
        return ci / n, ct / n

    @property
    def n_parametros(self):
        return (self.tabela.size + self.tronco.n_parametros +
                self.cabeca_intencao.n_parametros + self.cabeca_tom.n_parametros)

    def para_dicionario(self, vocabulario):
        """O modelo como o C# vai ler.

        `camadas` guarda tronco + cabeca de INTENCAO, na mesma ordem e com
        os mesmos nomes de antes — assim o `ClassificadorDeIntencao.cs`
        continua carregando este arquivo sem mudanca nenhuma. A saida de
        tom entra como um campo NOVO, que quem nao conhece ignora.

        Compatibilidade para tras nao e cortesia aqui: e o que permite
        trocar o modelo sem ter de trocar o C# no mesmo minuto.
        """
        def cam(c):
            return {"ativacao": c.ativacao.nome,
                    "pesos": [[round(float(x), 4) for x in l] for l in c.pesos],
                    "vies": [round(float(x), 4) for x in c.vies.ravel()]}
        return {
            "intencoes": self.intencoes,
            "pecas": vocabulario.pecas,
            "dimensao": self.dimensao,
            "tabela": [[round(float(x), 4) for x in linha] for linha in self.tabela],
            "camadas": [cam(self.tronco), cam(self.cabeca_intencao)],
            "tons": self.tons,
            "camada_tom": cam(self.cabeca_tom),
        }
