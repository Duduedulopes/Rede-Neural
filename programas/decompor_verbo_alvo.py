# -*- coding: utf-8 -*-
"""
VERBO x ALVO: fazer duas perguntas pequenas em vez de uma grande.

O PROBLEMA

Com 31 intencoes planas, `alterar_preco` tem 4 frases de treino e a rede
nunca a encontra — medido: 0 acertos em 59 frases nas 17 classes novas.
Escrever 40 frases para cada uma resolveria, mas 600 frases e muito
trabalho para um problema que e de DESENHO, nao de quantidade.

    "muda o preco da agua"     alterar   x  preco
    "quanto custa a agua"      consultar x  preco
    "tira a agua do catalogo"  remover   x  produto

`alterar_preco` e `preco` nao sao duas classes sem relacao: elas falam do
MESMO ALVO com verbos diferentes. Tratadas como classes planas, os 37
exemplos de consulta de preco nao ajudam em nada os 4 de alteracao. Com
dois eixos, ajudam: o alvo `preco` passa a ter 41.

E o eixo do verbo fica com uma pergunta bem mais facil do que "qual das
31": "isto manda mudar alguma coisa?" tem pista forte e curta — o
imperativo no comeco da frase.

O QUE ESTE PROGRAMA MEDE

O par completo. Acertar so o verbo nao serve de nada: para responder e
preciso saber o verbo E o alvo. Entao a nota comparavel com os 53,4% das
31 planas e a fracao de frases em que AS DUAS cabecas acertam.

Se o par nao bater 53,4%, o desenho novo nao se justifica e eu digo isso.
"""
import json, io, sys, numpy as np
from collections import Counter

sys.path.insert(0, ".")
sys.path.insert(0, "programas")
from rede.texto import Vocabulario
from rede.classificador import ClassificadorDeIntencao
from rede.treino import taxa_cosseno
from treinar_intencao import dobras

SEMENTE, EPOCAS, TAXA, DIM, OC, DOBRAS = 42, 80, 1.0, 24, 32, 5

# ---------------------------------------------------------------------
# O MAPA. Cada intencao plana vira um par.
#
# `nenhum` no alvo nao e buraco: "confirma" e "cancela" se referem ao que
# esta pendente na conversa, nao a um alvo dito na frase. O alvo dessas
# vem do contexto, nao do texto — e por isso a rede nao deve adivinha-lo.
# ---------------------------------------------------------------------
MAPA = {
    # --- consulta: os 14 que ja funcionavam -------------------------
    "pessoas_na_loja":     ("consultar", "pessoas"),
    "estoque":             ("consultar", "estoque"),
    "estoque_baixo":       ("consultar", "estoque_baixo"),
    "faturamento":         ("consultar", "faturamento"),
    "carrinho":            ("consultar", "carrinho"),
    "cameras":             ("consultar", "cameras"),
    "preco":               ("consultar", "preco"),
    "comparar":            ("consultar", "comparacao"),
    "mais_vendidos":       ("consultar", "mais_vendidos"),
    "status_sistema":      ("consultar", "status"),
    # --- consulta que a outra IA acrescentou ------------------------
    "meu_carrinho":        ("consultar", "carrinho"),
    "pagamento":           ("consultar", "pagamento"),
    "entrada_loja":        ("consultar", "entrada"),
    "status_api":          ("consultar", "status"),
    "logs_sistema":        ("consultar", "logs"),
    "analise_combinada":   ("consultar", "comparacao"),
    # --- explicar: pergunta sobre como funciona ---------------------
    "duvida_sistema":      ("explicar", "sistema"),
    "integracao_sistemas": ("explicar", "sistema"),
    "ajuda":               ("explicar", "ajuda"),
    # --- conversa ---------------------------------------------------
    "saudacao":            ("conversar", "nenhum"),
    "fora_de_escopo":      ("nada", "nenhum"),
    # --- ESCRITA: as que mexem no sistema ---------------------------
    "adicionar_produto":   ("criar", "produto"),
    "alterar_preco":       ("alterar", "preco"),
    "alterar_estoque":     ("alterar", "estoque"),
    "remover_produto":     ("remover", "produto"),
    "configurar_camera":   ("configurar", "cameras"),
    "configurar_sistema":  ("configurar", "sistema"),
    "reiniciar_servico":   ("reiniciar", "sistema"),
    # --- controle do dialogo ----------------------------------------
    "confirmar_acao":      ("confirmar", "nenhum"),
    "cancelar_operacao":   ("cancelar", "nenhum"),
    "escolher_solucao":    ("escolher", "nenhum"),
}

ESCREVE = {"criar", "alterar", "remover", "configurar", "reiniciar"}

arq = sys.argv[1] if len(sys.argv) > 1 else "dados/perguntas_expandido.jsonl"
dados = [json.loads(l) for l in io.open(arq, encoding="utf-8") if l.strip()]

faltando = sorted({d["intencao"] for d in dados} - set(MAPA))
if faltando:
    print("INTENCOES SEM MAPA (o programa para em vez de adivinhar):")
    for f in faltando:
        print("   ", f)
    sys.exit(1)

perguntas = [d["pergunta"] for d in dados]
planas = [d["intencao"] for d in dados]
verbos = [MAPA[i][0] for i in planas]
alvos = [MAPA[i][1] for i in planas]

lista_planas = sorted(set(planas))
lista_verbos = sorted(set(verbos))
lista_alvos = sorted(set(alvos))

print(f"{arq}: {len(dados)} frases\n")
print(f"  desenho antigo   {len(lista_planas)} classes planas")
print(f"  desenho novo     {len(lista_verbos)} verbos  x  {len(lista_alvos)} alvos\n")

print("  como os exemplos se redistribuem")
print("  " + "-" * 58)
cv, ca = Counter(verbos), Counter(alvos)
print("    VERBO                          ALVO")
lv = [f"{v} {n}" for v, n in cv.most_common()]
la = [f"{a} {n}" for a, n in ca.most_common()]
for i in range(max(len(lv), len(la))):
    e = lv[i] if i < len(lv) else ""
    d = la[i] if i < len(la) else ""
    print(f"    {e:<30} {d}")

# quanto cada classe de escrita ganhou
print("\n  o que as classes de escrita ganharam")
print("  " + "-" * 58)
cp = Counter(planas)
for nome in sorted(MAPA):
    v, a = MAPA[nome]
    if v in ESCREVE:
        print(f"    {nome:<20} {cp.get(nome,0):3d} frases  ->  "
              f"verbo '{v}' {cv[v]:3d}   alvo '{a}' {ca[a]:3d}")


def treinar_cabeca(rotulos, nome):
    """Uma cabeca, em validacao cruzada. Devolve a previsao de cada frase."""
    classes = sorted(set(rotulos))
    n_cls = {c: i for i, c in enumerate(classes)}
    previsto = [None] * len(dados)
    g = np.random.default_rng(SEMENTE)
    grupos = dobras(planas, DOBRAS, g)   # MESMAS dobras nas duas cabecas
    for d in range(DOBRAS):
        teste_i = set(grupos[d])
        treino_i = [i for i in range(len(dados)) if i not in teste_i]
        voc = Vocabulario([perguntas[i] for i in treino_i])
        ex = [(voc.indices(perguntas[i]), n_cls[rotulos[i]]) for i in treino_i]
        c = ClassificadorDeIntencao(len(voc), classes, dimensao=DIM,
                                    ocultos=OC, semente=SEMENTE)
        gg = np.random.default_rng(SEMENTE)
        for epoca in range(EPOCAS):
            t = taxa_cosseno(TAXA, epoca, EPOCAS)
            ordem = gg.permutation(len(ex))
            for i in range(0, len(ex), 16):
                c.passo([ex[j] for j in ordem[i:i + 16]], t)
        for i in grupos[d]:
            p = np.asarray(c.prever(voc.indices(perguntas[i]))).ravel()
            previsto[i] = classes[int(np.argmax(p))]
    acerto = sum(1 for i in range(len(dados)) if previsto[i] == rotulos[i]) / len(dados)
    print(f"    {nome:<10} {100*acerto:5.1f}%")
    return previsto


print("\n  ACERTO DE CADA CABECA")
print("  " + "-" * 58)
pv = treinar_cabeca(verbos, "verbo")
pa = treinar_cabeca(alvos, "alvo")
pp = treinar_cabeca(planas, "31 planas")

par = sum(1 for i in range(len(dados)) if pv[i] == verbos[i] and pa[i] == alvos[i])
plano = sum(1 for i in range(len(dados)) if pp[i] == planas[i])

print("\n  O QUE INTERESSA — acertar o suficiente para responder")
print("  " + "-" * 58)
print(f"    31 classes planas          {100*plano/len(dados):5.1f}%")
print(f"    verbo E alvo, os dois      {100*par/len(dados):5.1f}%")
d = 100 * (par - plano) / len(dados)
print(f"    {'ganho' if d>0 else 'PERDA'}                      {d:+5.1f} pontos")

# o que mais importa: as frases de escrita
idx_escreve = [i for i in range(len(dados)) if verbos[i] in ESCREVE]
if idx_escreve:
    pe = sum(1 for i in idx_escreve if pv[i] == verbos[i] and pa[i] == alvos[i])
    pl = sum(1 for i in idx_escreve if pp[i] == planas[i])
    pv_so = sum(1 for i in idx_escreve if pv[i] == verbos[i])
    print(f"\n  SO AS {len(idx_escreve)} FRASES QUE MANDAM MUDAR ALGUMA COISA")
    print("  " + "-" * 58)
    print(f"    31 planas acertaram        {pl:3d} de {len(idx_escreve)}")
    print(f"    verbo E alvo               {pe:3d} de {len(idx_escreve)}")
    print(f"    so o verbo (e acao?)       {pv_so:3d} de {len(idx_escreve)}")

# e o inverso: quantas consultas foram confundidas com escrita?
idx_consulta = [i for i in range(len(dados)) if verbos[i] not in ESCREVE]
falso_escreve = sum(1 for i in idx_consulta if pv[i] in ESCREVE)
print(f"\n  SEGURANCA: consultas tomadas por ordem de mudanca: "
      f"{falso_escreve} de {len(idx_consulta)}")
print("    (cada uma dessas seria uma tela de confirmacao indevida)")
