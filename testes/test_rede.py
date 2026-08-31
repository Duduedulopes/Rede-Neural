"""Testes de comportamento da Fase 1.

O teste que vale mais que todos os outros e `test_gradiente_bate_com_o_numerico`.
Os demais pegam erro de forma e de sinal; esse pega erro de MATEMATICA, que e
a classe de defeito que nao levanta excecao e se disfarca de treino ruim.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, embutimento, treino
from rede.ativacao import Softmax, sigmoid, sigmoid_derivada, softmax
from rede.camada import Camada
from rede.custo import EntropiaCruzada, EntropiaCruzadaCategorica, Quadratico
from rede.rede import Rede
from rede.retropropagacao import conferir_numericamente, gradiente


# ---------------------------------------------------------------- ativacao

def test_sigmoid_no_zero_vale_meio():
    assert sigmoid(0.0) == pytest.approx(0.5)


def test_sigmoid_fica_entre_zero_e_um():
    z = np.linspace(-50, 50, 201)
    a = sigmoid(z)
    assert np.all(a >= 0.0) and np.all(a <= 1.0)


def test_sigmoid_e_estritamente_interna_na_faixa_util():
    """Na matematica a sigmoid NUNCA chega a 0 nem a 1. No float, chega.

    A partir de z ~ 37 o `1 + e^-z` arredonda para 1,0 e a saida vira 1,0
    exato. Nao e defeito desta implementacao: e o alcance do float64.

    Registrar isso importa porque a entropia cruzada calcula log(1 - a), e
    log(0) e -inf. E dai que vem o `nan_to_num` no custo.
    """
    z = np.linspace(-30, 30, 201)
    a = sigmoid(z)
    assert np.all(a > 0.0) and np.all(a < 1.0)


def test_sigmoid_e_crescente():
    z = np.linspace(-10, 10, 100)
    assert np.all(np.diff(sigmoid(z)) > 0)


def test_sigmoid_nao_estoura_em_valores_extremos():
    """A versao ingenua devolveria `nan` e um aviso de overflow aqui."""
    with np.errstate(over="raise"):
        a = sigmoid(np.array([-800.0, 800.0]))
    assert not np.any(np.isnan(a))
    assert a[0] == pytest.approx(0.0)
    assert a[1] == pytest.approx(1.0)


def test_derivada_tem_teto_de_um_quarto():
    """0,25 e o maximo. Esse teto e a origem do gradiente que se desvanece."""
    z = np.linspace(-10, 10, 1001)
    assert sigmoid_derivada(z).max() == pytest.approx(0.25)
    assert sigmoid_derivada(0.0) == pytest.approx(0.25)


# ------------------------------------------------------------------- custo

def test_entropia_cruzada_nao_carrega_a_derivada():
    """O delta e o erro puro: a - y. E o motivo de existir esse custo."""
    z = np.array([[5.0]])
    a = np.array([[0.98]])
    y = np.array([[0.0]])
    assert EntropiaCruzada.delta(z, a, y) == pytest.approx(a - y)


def test_quadratico_carrega_a_derivada_e_por_isso_encolhe():
    """Errar com conviccao encolhe o gradiente do custo quadratico."""
    z = np.array([[5.0]])          # neuronio bem saturado
    a = sigmoid(z)
    y = np.array([[0.0]])          # e completamente errado
    q = abs(float(Quadratico.delta(z, a, y)[0, 0]))
    e = abs(float(EntropiaCruzada.delta(z, a, y)[0, 0]))
    assert q < e / 10


def test_custo_zero_quando_acerta_em_cheio():
    a = np.array([[1.0]])
    y = np.array([[1.0]])
    assert Quadratico.fn(a, y) == pytest.approx(0.0)
    assert EntropiaCruzada.fn(a, y) == pytest.approx(0.0)


# ------------------------------------------------------------ camada e rede

def test_formas_da_camada():
    c = Camada(4, 3, np.random.default_rng(0))
    assert c.pesos.shape == (3, 4)
    assert c.vies.shape == (3, 1)
    assert c.formato == (4, 3)
    assert c.n_parametros == 12 + 3


def test_camada_devolve_coluna():
    c = Camada(4, 3, np.random.default_rng(0))
    assert c.frente(np.zeros((4, 1))).shape == (3, 1)


def test_camada_guarda_a_ida_para_a_volta():
    c = Camada(2, 2, np.random.default_rng(0))
    c.frente(np.array([[1.0], [0.0]]))
    assert c.ultimo_z is not None
    assert c.ultima_ativacao is not None
    assert c.ultima_entrada is not None


def test_inicializacao_quebra_a_simetria():
    """Neuronios identicos receberiam gradientes identicos para sempre."""
    c = Camada(5, 4, np.random.default_rng(0))
    for i in range(1, 4):
        assert not np.allclose(c.pesos[0], c.pesos[i])


def test_tres_tamanhos_criam_duas_camadas():
    """A camada de entrada nao tem pesos. Fonte classica de confusao."""
    r = Rede([2, 3, 1], semente=0)
    assert len(r.camadas) == 2
    assert r.n_parametros == (3 * 2 + 3) + (1 * 3 + 1)


def test_rede_precisa_de_ao_menos_duas_medidas():
    with pytest.raises(ValueError):
        Rede([3], semente=0)


def test_mesma_semente_mesma_rede():
    a = Rede([3, 4, 2], semente=7)
    b = Rede([3, 4, 2], semente=7)
    for ca, cb in zip(a.camadas, b.camadas):
        assert np.array_equal(ca.pesos, cb.pesos)
        assert np.array_equal(ca.vies, cb.vies)


# --------------------------------------------------------- retropropagacao

@pytest.mark.parametrize("custo", [Quadratico, EntropiaCruzada])
@pytest.mark.parametrize("tamanhos", [[2, 3, 1], [3, 4, 4, 2]])
def test_gradiente_bate_com_o_numerico(custo, tamanhos):
    """O TESTE QUE IMPORTA.

    Compara a retropropagacao com a definicao de derivada. Retropropagacao
    errada nao levanta excecao — ela so treina mal, e o defeito se disfarca
    de "faltou epoca". Este teste e o unico jeito de saber.
    """
    r = Rede(tamanhos, semente=1)
    gerador = np.random.default_rng(2)
    x = gerador.random((tamanhos[0], 1))
    y = gerador.random((tamanhos[-1], 1))

    assert conferir_numericamente(r, x, y, custo) < 1e-7


def test_gradiente_tem_a_forma_dos_parametros():
    r = Rede([2, 3, 1], semente=0)
    gp, gv = gradiente(r, np.zeros((2, 1)), np.ones((1, 1)), EntropiaCruzada)
    for i, c in enumerate(r.camadas):
        assert gp[i].shape == c.pesos.shape
        assert gv[i].shape == c.vies.shape


# ------------------------------------------------------------------ treino

def test_minilotes_cobrem_todos_os_dados_uma_vez():
    d = [(np.zeros((1, 1)), np.zeros((1, 1))) for _ in range(10)]
    lotes = minilotes_de(d, 3)
    assert sum(len(l) for l in lotes) == 10
    assert [len(l) for l in lotes] == [3, 3, 3, 1]


def minilotes_de(d, tamanho):
    return treino.minilotes(d, tamanho, np.random.default_rng(0))


def test_embaralhamento_muda_a_ordem():
    d = [(np.full((1, 1), i, dtype=float), np.zeros((1, 1))) for i in range(20)]
    a = [float(x[0, 0])
         for lote in treino.minilotes(d, 5, np.random.default_rng(1))
         for x, _ in lote]
    assert a != list(range(20))
    assert sorted(a) == list(range(20))


def test_um_passo_reduz_o_custo():
    r = Rede([2, 3, 1], semente=3)
    d = dados.carregar_xor()
    antes = treino.custo_medio(r, d, EntropiaCruzada)
    treino.passo(r, d, taxa=3.0, custo=EntropiaCruzada)
    assert treino.custo_medio(r, d, EntropiaCruzada) < antes


def test_a_rede_aprende_o_xor():
    """Uma camada so nao consegue. Se passa, a camada oculta esta trabalhando."""
    d = dados.carregar_xor()
    r = Rede([2, 3, 1], semente=42)
    historico = treino.treinar(r, d, epocas=4000, tamanho_lote=4,
                               taxa=3.0, custo=EntropiaCruzada, semente=42)

    assert historico[-1] < historico[0]
    assert historico[-1] < 0.01
    assert treino.acertos(r, d) == 4


# ------------------------------------------------------------------- dados

def test_xor_vem_em_coluna():
    d = dados.carregar_xor()
    assert len(d) == 4
    for x, y in d:
        assert x.shape == (2, 1)
        assert y.shape == (1, 1)


def test_mnist_esta_no_lugar():
    assert dados.CAMINHO_MNIST.exists(), "mnist.pkl.gz nao encontrado"


# ------------------------------------------------------------------- mnist

def test_vetorizar_digito():
    v = dados.vetorizar_digito(5)
    assert v.shape == (10, 1)
    assert v[5, 0] == 1.0
    assert v.sum() == 1.0


def test_mnist_carrega_com_as_formas_certas():
    """Le o arquivo de verdade. Leva ~3s — e o unico teste lento do projeto.

    Vale o custo: e aqui que o `encoding="latin1"` do pickle do Python 2 e
    verificado. Sem ele, `UnicodeDecodeError` — e o erro apareceria so no
    meio de um treino de minutos.
    """
    treinamento, validacao, teste = dados.carregar_mnist()

    assert (len(treinamento), len(validacao), len(teste)) == (50000, 10000, 10000)

    for conjunto in (treinamento, validacao, teste):
        x, y = conjunto[0]
        assert x.shape == (784, 1)
        assert y.shape == (10, 1)
        assert 0.0 <= x.min() and x.max() <= 1.0
        assert y.sum() == 1.0


# ------------------------------------------------------------- embutimento

def test_normalizar_da_comprimento_um():
    v = np.array([[3.0], [4.0]])
    n = embutimento.normalizar(v)
    assert np.linalg.norm(n) == pytest.approx(1.0)


def test_normalizar_preserva_a_direcao():
    v = np.array([[3.0], [4.0]])
    n = embutimento.normalizar(v)
    assert embutimento.similaridade_cosseno(v, n) == pytest.approx(1.0)


def test_vetor_nulo_nao_tem_direcao():
    with pytest.raises(ValueError):
        embutimento.normalizar(np.zeros((3, 1)))


def test_cosseno_nos_tres_casos_de_referencia():
    a = np.array([[1.0], [0.0]])
    assert embutimento.similaridade_cosseno(a, a) == pytest.approx(1.0)
    assert embutimento.similaridade_cosseno(a, np.array([[0.0], [1.0]])) == pytest.approx(0.0)
    assert embutimento.similaridade_cosseno(a, -a) == pytest.approx(-1.0)


def test_cosseno_ignora_o_tamanho():
    """Direcao carrega o significado; tamanho nao."""
    a = np.array([[1.0], [2.0]])
    assert embutimento.similaridade_cosseno(a, 100 * a) == pytest.approx(1.0)


def test_representar_devolve_a_camada_oculta():
    r = Rede([4, 3, 2], semente=0)
    v = embutimento.representar(r, np.ones((4, 1)))
    assert v.shape == (3, 1)


def test_representar_devolve_copia_e_nao_referencia():
    """Sem o .copy(), uma lista de embutimentos ficaria toda igual ao ultimo."""
    r = Rede([4, 3, 2], semente=0)
    a = embutimento.representar(r, np.ones((4, 1)))
    b = embutimento.representar(r, np.zeros((4, 1)))
    assert not np.array_equal(a, b)


def test_rede_sem_camada_oculta_nao_tem_o_que_representar():
    r = Rede([4, 2], semente=0)
    with pytest.raises(ValueError):
        embutimento.representar(r, np.ones((4, 1)))


def test_centroide_e_normalizado_e_fica_entre_os_vetores():
    a = np.array([[1.0], [0.0]])
    b = np.array([[0.0], [1.0]])
    c = embutimento.centroide([a, b])
    assert np.linalg.norm(c) == pytest.approx(1.0)
    assert embutimento.similaridade_cosseno(c, a) == pytest.approx(
        embutimento.similaridade_cosseno(c, b))


def test_matriz_de_similaridade_e_simetrica_com_diagonal_um():
    vetores = [np.array([[1.0], [0.0]]),
               np.array([[0.0], [1.0]]),
               np.array([[1.0], [1.0]])]
    M = embutimento.matriz_de_similaridade(vetores)
    assert M.shape == (3, 3)
    assert np.allclose(M, M.T)
    assert np.allclose(np.diag(M), 1.0)


# --------------------------------------------------- softmax e categorica

def test_softmax_soma_um():
    p = softmax(np.array([[1.0], [2.0], [3.0]]))
    assert float(p.sum()) == pytest.approx(1.0)
    assert np.all(p > 0)


def test_softmax_nao_muda_ao_somar_constante():
    """A constante aparece em cima e embaixo da fracao e se cancela.

    E exatamente essa propriedade que autoriza subtrair o maximo para nao
    estourar o float.
    """
    z = np.array([[1.0], [2.0], [3.0]])
    assert np.allclose(softmax(z), softmax(z + 100.0))


def test_softmax_nao_estoura():
    """e^1000 seria `inf`. Com a subtracao do maximo, nao chega perto."""
    p = softmax(np.array([[1000.0], [1001.0], [999.0]]))
    assert float(p.sum()) == pytest.approx(1.0)
    assert not np.any(np.isnan(p))


def test_softmax_preserva_a_ordem():
    z = np.array([[0.5], [3.0], [-1.0]])
    assert np.array_equal(np.argsort(z.ravel()), np.argsort(softmax(z).ravel()))


def test_derivada_da_softmax_recusa_em_vez_de_mentir():
    """Ela e uma matriz, nao um vetor. Recusar avisa na hora; devolver algo
    plausivel produziria um treino que nao converge sem dizer por que."""
    with pytest.raises(NotImplementedError):
        Softmax.derivada(np.zeros((3, 1)))


def test_categorica_e_menos_log_da_probabilidade_certa():
    a = np.array([[0.1], [0.7], [0.2]])
    y = np.array([[0.0], [1.0], [0.0]])
    assert EntropiaCruzadaCategorica.fn(a, y) == pytest.approx(-np.log(0.7))


def test_categorica_pune_muito_o_erro_confiante():
    y = np.array([[1.0], [0.0]])
    quase_certo = EntropiaCruzadaCategorica.fn(np.array([[0.99], [0.01]]), y)
    muito_errado = EntropiaCruzadaCategorica.fn(np.array([[0.01], [0.99]]), y)
    assert quase_certo < 0.02
    assert muito_errado > 4.0


def test_categorica_nao_estoura_com_probabilidade_zero():
    """Sem o clip, ln(0) = -inf contaminaria o custo inteiro."""
    c = EntropiaCruzadaCategorica.fn(np.array([[0.0], [1.0]]),
                                     np.array([[1.0], [0.0]]))
    assert np.isfinite(c)


def test_delta_da_categorica_e_o_erro_puro():
    z = np.array([[9.0], [9.0]])          # ignorado de proposito
    a = np.array([[0.3], [0.7]])
    y = np.array([[1.0], [0.0]])
    assert np.allclose(EntropiaCruzadaCategorica.delta(z, a, y), a - y)


def test_softmax_so_entra_na_camada_de_saida():
    r = Rede([4, 5, 3], semente=0, ativacao_saida=Softmax)
    assert r.camadas[0].ativacao.nome == "sigmoid"
    assert r.camadas[-1].ativacao.nome == "softmax"


def test_rede_com_softmax_devolve_distribuicao():
    r = Rede([4, 5, 3], semente=0, ativacao_saida=Softmax)
    assert float(r.frente(np.ones((4, 1))).sum()) == pytest.approx(1.0)


def test_gradiente_da_softmax_com_categorica_bate_com_o_numerico():
    """Prova o cancelamento da jacobiana: se ele nao valesse, daria diferente."""
    r = Rede([4, 5, 3], semente=1, ativacao_saida=Softmax)
    g = np.random.default_rng(2)
    x = g.random((4, 1))
    y = np.zeros((3, 1))
    y[1, 0] = 1.0
    assert conferir_numericamente(r, x, y, EntropiaCruzadaCategorica) < 1e-7


# ------------------------------------------------------ taxa decrescente

def test_taxa_comeca_no_inicial_e_termina_no_final():
    assert treino.taxa_cosseno(0.5, 0, 10) == pytest.approx(0.5)
    assert treino.taxa_cosseno(0.5, 9, 10) == pytest.approx(0.0, abs=1e-12)


def test_taxa_so_desce():
    valores = [treino.taxa_cosseno(0.5, e, 20) for e in range(20)]
    assert all(a >= b for a, b in zip(valores, valores[1:]))


def test_cosseno_e_quase_plano_nas_pontas():
    """A forma e o motivo de usar cosseno: as pontas rendem mais devagar.

    Primeiro decimo do treino cai bem menos que o decimo do meio.
    """
    v = [treino.taxa_cosseno(1.0, e, 101) for e in range(101)]
    queda_inicio = v[0] - v[10]
    queda_meio = v[45] - v[55]
    assert queda_inicio < queda_meio


def test_uma_epoca_so_nao_quebra():
    assert treino.taxa_cosseno(0.5, 0, 1) == pytest.approx(0.5)
