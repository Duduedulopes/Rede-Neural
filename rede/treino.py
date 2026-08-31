"""Descida do gradiente estocastica: como os parametros efetivamente mudam.

A DESCIDA DO GRADIENTE

O gradiente aponta para onde o custo SOBE mais rapido. Entao andamos no
sentido contrario:

    parametro <- parametro - taxa * gradiente

Repetidamente. Cada passo desce um pouco a superficie do custo. Isso converge
para um MINIMO LOCAL — nao necessariamente o global, e na pratica isso quase
nunca e o problema que parece ser.

`taxa` (a taxa de aprendizado) e o tamanho do passo. Grande demais e a conta
salta por cima do vale e diverge; pequena demais e o treino nao termina.

O "ESTOCASTICA"

Calcular o gradiente sobre TODOS os exemplos a cada passo e correto e lento —
50 mil imagens por passo, no MNIST.

Entao: embaralha os dados, corta em minilotes de tamanho fixo, e usa cada
minilote como uma ESTIMATIVA do gradiente verdadeiro. A estimativa e ruidosa
e barata. Muitos passos ruidosos e baratos chegam mais longe que poucos
passos exatos e caros.

O EMBARALHAMENTO E OBRIGATORIO, A CADA EPOCA

Sem embaralhar, os minilotes sao sempre os mesmos e na mesma ordem — e o
treino aprende a sequencia junto com o problema. E no MNIST, que vem
agrupado, um minilote inteiro pode cair com o mesmo digito.

EPOCA

Uma passagem completa por todos os minilotes. Contar epocas e como se mede o
progresso do treino.
"""

import math

import numpy as np

from rede.retropropagacao import gradiente


def minilotes(dados, tamanho, gerador):
    """Embaralha `dados` e devolve a lista de minilotes.

    Recebe o gerador de fora — reproduzir um treino exige reproduzir tambem a
    ordem do embaralhamento.

    O ultimo lote pode sair menor que `tamanho`, e tudo bem: `passo` divide
    pelo tamanho REAL do lote, nao pelo nominal.
    """
    if tamanho < 1:
        raise ValueError("tamanho de lote precisa ser >= 1")

    indices = gerador.permutation(len(dados))
    return [
        [dados[j] for j in indices[k:k + tamanho]]
        for k in range(0, len(dados), tamanho)
    ]


def taxa_cosseno(taxa_inicial, epoca, epocas, taxa_final=0.0):
    """A taxa de aprendizado descendo suavemente ate o fim do treino.

    POR QUE A TAXA NAO DEVE SER CONSTANTE

    MEDIDO no previsor de eventos: epoca 4 deu perplexidade 2,78 e a epoca 5
    deu 2,84. PIOROU. Nao foi azar nem falta de treino — e o que acontece
    quando o passo continua grande depois de o modelo ja estar perto do
    fundo do vale.

        Passo grande atravessa terreno. Passo grande perto do minimo
        atravessa o minimo.

    No comeco, passo grande e bom: e preciso percorrer distancia. No fim, o
    mesmo passo faz a conta pular de um lado para o outro do vale sem nunca
    assentar. E o custo fica oscilando em vez de convergir.

    POR QUE COSSENO, E NAO UMA QUEDA RETA

        taxa(t) = final + (inicial - final) * (1 + cos(pi * t / T)) / 2

    O cosseno comeca quase plano — nao desperdica as primeiras epocas, que
    e onde o passo grande rende mais. Depois cai rapido no meio. E chega ao
    fim quase plano de novo, o que da varias epocas de ajuste fino em vez de
    uma parada seca.

    Uma queda reta faria as tres fases com a mesma pressa, o que e pior nas
    duas pontas.
    """
    if epocas <= 1:
        return taxa_inicial
    fracao = min(1.0, max(0.0, epoca / (epocas - 1)))
    return taxa_final + (taxa_inicial - taxa_final) * (1 + math.cos(math.pi * fracao)) / 2


def custo_medio(rede, dados, custo):
    """A media do custo sobre TODOS os exemplos.

    A media faz parte da definicao do custo, nao e um detalhe de relatorio.
    E o que impede a rede de acertar um exemplo destruindo os outros.
    """
    if not dados:
        return 0.0
    return sum(custo.fn(rede.frente(x), y) for x, y in dados) / len(dados)


def passo(rede, lote, taxa, custo):
    """Um passo de descida sobre UM minilote.

    Soma os gradientes dos exemplos do lote, tira a media, e desloca cada
    parametro por `-taxa * media`.

    O SINAL NEGATIVO E O CORACAO DA COISA. O gradiente aponta para onde o
    custo SOBE mais rapido. Andar no sentido contrario e descer.
    """
    soma_pesos = [np.zeros_like(c.pesos) for c in rede.camadas]
    soma_vies = [np.zeros_like(c.vies) for c in rede.camadas]

    for x, y in lote:
        grad_p, grad_v = gradiente(rede, x, y, custo)
        for i in range(len(rede.camadas)):
            soma_pesos[i] += grad_p[i]
            soma_vies[i] += grad_v[i]

    n = len(lote)
    for i, camada in enumerate(rede.camadas):
        camada.pesos -= (taxa / n) * soma_pesos[i]
        camada.vies -= (taxa / n) * soma_vies[i]


def treinar(rede, dados_treino, epocas, tamanho_lote, taxa, custo,
            dados_teste=None, semente=None, mostrar=False, agenda=False):
    """O laco completo. Devolve o historico de custo por epoca.

    O historico e o que permite DIZER se o treino melhorou; sem ele, so
    sobra a impressao de que melhorou.

    Uma epoca = uma passagem por todos os minilotes. O embaralhamento
    acontece a cada epoca, nao uma vez so: lotes sempre iguais fariam a rede
    aprender a sequencia junto com o problema.
    """
    gerador = np.random.default_rng(semente)
    historico = []

    for epoca in range(epocas):
        # `agenda=False` mantem o comportamento antigo, para os treinos ja
        # medidos continuarem reproduzindo o mesmo numero.
        taxa_agora = taxa_cosseno(taxa, epoca, epocas) if agenda else taxa

        for lote in minilotes(dados_treino, tamanho_lote, gerador):
            passo(rede, lote, taxa_agora, custo)

        c = custo_medio(rede, dados_treino, custo)
        historico.append(c)

        if mostrar:
            linha = f"epoca {epoca + 1:4d}   taxa {taxa_agora:.4f}   custo {c:.6f}"
            if dados_teste:
                linha += f"   acertos {acertos(rede, dados_teste)}/{len(dados_teste)}"
            print(linha)

    return historico


def acertos(rede, dados, limiar=0.5):
    """Quantos exemplos a rede acerta.

    Para uma saida unica (XOR), acerta quando cai do lado certo do limiar.
    Para varias saidas (MNIST), acerta quando o neuronio de maior ativacao e
    o certo — o `argmax`.
    """
    total = 0
    for x, y in dados:
        a = rede.frente(x)
        y = np.asarray(y, dtype=float).reshape(-1, 1)
        if a.size == 1:
            total += int((a[0, 0] >= limiar) == (y[0, 0] >= limiar))
        else:
            total += int(np.argmax(a) == np.argmax(y))
    return total
