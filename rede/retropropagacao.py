"""O AMAGO: o algoritmo que calcula o gradiente com eficiencia.

POR QUE ELE EXISTE

O gradiente do custo diz, para CADA peso e CADA vies, o quanto o custo muda
se aquele parametro mudar um tiquinho. Uma rede pequena de MNIST tem quase
25 mil parametros. Calcular isso por forca bruta — mexer num parametro,
rodar a rede inteira, medir a diferenca, repetir — custaria 25 mil passagens
por exemplo de treino. Inviavel.

A retropropagacao calcula o gradiente INTEIRO com UMA passagem para frente e
UMA para tras. E so por isso que treinar rede neural e possivel.

    O algoritmo para calcular o gradiente com eficiencia e efetivamente o
    amago de como a rede neural aprende.

A IDEIA, EM UMA FRASE

Regra da cadeia. O erro na camada de saida e conhecido (o custo sabe
calcula-lo). O erro de uma camada anterior e o erro da seguinte, empurrado
para tras pelos mesmos pesos que o empurraram para frente — transpostos.

    erro_saida     = custo.delta(z, a, y)
    erro_da_camada = (pesos_da_proxima.T @ erro_da_proxima) * sigmoid'(z)

E daquele erro saem os dois gradientes que queremos:

    dC/dvies  = erro
    dC/dpesos = erro @ ativacao_da_camada_anterior.T

POR QUE UM ARQUIVO SEPARADO

Contraria o livro, que poe isto como metodo da rede. Foi escolha do Eduardo,
e tem uma razao boa: este e o conceito central do projeto inteiro, e um
conceito central nao deve estar escondido no meio de outros oito metodos.
"""

import numpy as np



def gradiente(rede, x, y, custo):
    """O gradiente do custo para UM exemplo (x, y).

    Devolve (gradientes_pesos, gradientes_vies) — uma entrada por camada,
    na mesma ordem de `rede.camadas`.

    Duas etapas, e a ordem importa:
      1. IDA   — roda a rede guardando z e ativacao de cada camada
      2. VOLTA — o erro da saida para tras, camada a camada
    """
    x = np.asarray(x, dtype=float).reshape(rede.tamanhos[0], 1)
    y = np.asarray(y, dtype=float).reshape(rede.tamanhos[-1], 1)

    # ---- IDA ---------------------------------------------------------
    # Nao guardamos nada aqui: `Camada.frente` ja guarda o que a volta usa.
    rede.frente(x)

    grad_pesos = [None] * len(rede.camadas)
    grad_vies = [None] * len(rede.camadas)

    # ---- VOLTA -------------------------------------------------------
    # O erro da ULTIMA camada e o unico que o custo sabe calcular sozinho.
    # Todos os outros sao derivados dele.
    ultima = rede.camadas[-1]
    erro = custo.delta(ultima.ultimo_z, ultima.ultima_ativacao, y)

    for i in range(len(rede.camadas) - 1, -1, -1):
        camada = rede.camadas[i]

        # dC/dvies = erro.
        # O vies entra em z somado, sem multiplicar nada: a derivada de z em
        # relacao a ele e 1, entao o erro passa inteiro.
        grad_vies[i] = erro

        # dC/dpesos = erro @ entrada.T
        # O peso w[j][k] multiplica a entrada k para produzir o neuronio j.
        # Logo o quanto ele influencia o custo e o erro do neuronio j vezes
        # o valor que passou por ele. O produto externo faz essa tabela
        # inteira de uma vez.
        grad_pesos[i] = erro @ camada.ultima_entrada.T

        if i > 0:
            # O ERRO EMPURRADO PARA TRAS. Este e o passo que da nome ao
            # algoritmo. Na ida a camada multiplicou por `pesos`; na volta o
            # erro atravessa a MESMA matriz transposta — e depois passa pela
            # derivada da ativacao da camada anterior, porque foi ela que
            # transformou z em a.
            anterior = rede.camadas[i - 1]
            erro = (camada.pesos.T @ erro) * anterior.ativacao.derivada(anterior.ultimo_z)

    return grad_pesos, grad_vies


def conferir_numericamente(rede, x, y, custo, epsilon=1e-5):
    """Confere a retropropagacao contra a definicao de derivada.

    Devolve a MAIOR diferenca absoluta encontrada. Abaixo de 1e-7 esta certo.

    POR QUE ISTO EXISTE, E POR QUE NAO E OPCIONAL

    Retropropagacao errada nao levanta excecao. Ela treina — mal, devagar, ou
    ate razoavelmente bem — e o defeito se disfarca de "faltou epoca" ou
    "taxa de aprendizado ruim". E o bug mais caro do campo, porque parece
    outra coisa.

    O antidoto e comparar com a derivada por definicao:

        dC/dw ~= [ C(w + eps) - C(w - eps) ] / (2 eps)

    Lentissimo — duas passagens por PARAMETRO, e e exatamente por isso que a
    retropropagacao existe. Mas numa rede minuscula roda em milissegundos.

    O EPSILON TEM DOIS INIMIGOS OPOSTOS

        grande demais   a diferenca finita deixa de aproximar a derivada
        pequeno demais  C(w+eps) e C(w-eps) ficam tao proximos que a
                        subtracao perde os digitos significativos do float

    1e-5 fica no meio. Com 1e-9 este teste falharia por arredondamento, e
    acusaria de errada uma retropropagacao correta.
    """
    analiticos_p, analiticos_v = gradiente(rede, x, y, custo)
    y_col = np.asarray(y, dtype=float).reshape(rede.tamanhos[-1], 1)

    maior_diferenca = 0.0

    for i, camada in enumerate(rede.camadas):
        for matriz, analitico in ((camada.pesos, analiticos_p[i]),
                                  (camada.vies, analiticos_v[i])):
            iterador = np.nditer(matriz, flags=["multi_index"])
            while not iterador.finished:
                indice = iterador.multi_index
                original = matriz[indice]

                matriz[indice] = original + epsilon
                mais = custo.fn(rede.frente(x), y_col)

                matriz[indice] = original - epsilon
                menos = custo.fn(rede.frente(x), y_col)

                matriz[indice] = original

                numerico = (mais - menos) / (2.0 * epsilon)
                diferenca = abs(numerico - float(analitico[indice]))
                maior_diferenca = max(maior_diferenca, diferenca)
                iterador.iternext()

    # A rede ficou com o cache da ultima perturbacao. Restaura.
    rede.frente(x)
    return maior_diferenca


def gradiente_com_entrada(rede, x, y, custo):
    """Como `gradiente`, mais o erro que chega na PROPRIA ENTRADA.

    POR QUE ISTO PRECISA EXISTIR

    Ate aqui a entrada era um dado fixo: os pixels da imagem, as
    caracteristicas do evento. Nao havia nada a ajustar nela, e o erro
    parava na primeira camada de pesos.

    Num previsor com tabela de embutimento, a entrada E PARAMETRO. Os
    vetores que representam cada token sao aprendidos junto com o resto, e
    para ajusta-los e preciso saber o quanto CADA NUMERO DA ENTRADA
    contribuiu para o erro.

        erro_na_entrada = W0.T @ erro_da_camada_0

    Repare que aqui NAO ha derivada de ativacao multiplicando. Nas camadas
    internas ela aparece porque o valor passou por uma sigmoid; a entrada
    nao passou por nenhuma — ela e o proprio vetor da tabela.

    Esquecer isso e um erro sutil: o treino ainda roda, a perda ainda cai um
    pouco, e a tabela de embutimento aprende torto.
    """
    grad_pesos, grad_vies = gradiente(rede, x, y, custo)

    # grad_vies[0] E o erro da camada 0 — o vies recebe o erro inteiro.
    erro_entrada = rede.camadas[0].pesos.T @ grad_vies[0]
    return grad_pesos, grad_vies, erro_entrada
