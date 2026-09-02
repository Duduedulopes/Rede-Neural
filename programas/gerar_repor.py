# -*- coding: utf-8 -*-
"""
SEPARA `repor_estoque` DE `alterar_estoque`. Programa.

O QUE ESTAVA ERRADO

Uma intencao so carregava tres operacoes diferentes:

    somar    "chegaram mais 20 chocolates"     +20
    definir  "corrige o estoque para 30"       =30
    tirar    "da baixa em 3 aguas"             -3

E o codigo tratava todas como DEFINIR. Entao:

    "chegaram mais 20 chocolates"  tinha 5  ->  definia 20   (era 25)
    "adicione 1 unidade de agua"   tinha 4  ->  definia 1    (era 5)

O segundo aconteceu de verdade. A confirmacao mostrou "saem 3 unidades",
o Chefe respondeu "pode fazer", e o que impediu a perda foi a API nao
saber reduzir estoque — sorte de limitacao, nao desenho.

A CORRECAO E SEPARAR, E NAO ADIVINHAR

Sao operacoes que GRAVAM diferente: uma chama `RestockAsync(+n)`, a outra
precisa calcular a diferenca. Elas merecem nomes diferentes, e a rede
merece a chance de distinguir — hoje ela nao tem, porque o corpus ensina
as duas com o mesmo rotulo.

O QUE CADA UMA GANHA

  repor_estoque    tudo que soma: chegou, entrou, acrescenta, repoe,
                   adiciona N unidades
  alterar_estoque  tudo que define um total: corrige para N, conta de
                   novo, o estoque certo e N

A PALAVRA QUE PRECISA FICAR DOS DOIS LADOS

"estoque" e "quantidade" aparecem nas duas — e tem de aparecer, senao
viram sinal de uma delas so. O que distingue e o VERBO e a preposicao
("mais 20" contra "para 20"), e e isso que a rede tem de aprender.
Mesma licao de "por favor", "muda" e "pode".
"""
import json, io, random, unicodedata, sys

random.seed(42)

BASES = {
"repor_estoque": [
    # chegou mercadoria
    "chegaram mais 20 chocolates", "chegou mais agua", "chegou mercadoria nova",
    "chegaram 10 caixas de salgadinho", "entrou mercadoria", "entrou mais estoque",
    "recebi mais 30 unidades", "recebemos mercadoria hoje",
    # adicionar explicito
    "adiciona 1 unidade de agua", "adicione mais 1 unidade", "adiciona 5 no estoque",
    "adicionar 10 unidades", "acrescenta 10 no estoque do chocolate",
    "acrescentar 20 unidades de coca", "soma 5 no estoque da agua",
    "somar 15 unidades", "poe mais 20 no estoque", "coloca mais 3 aguas",
    "inclui mais 10 unidades", "mete mais 5 no estoque",
    # repor
    "repoe o estoque do salgadinho", "repor o estoque da agua",
    "repoe 20 unidades", "faz a reposicao do chocolate",
    "precisa repor a agua", "vou repor 15 unidades de coca",
    # informal
    "mais 5 de agua", "mais 20 chocolate", "bota mais 10 ai",
    "sobe o estoque em 5", "aumenta o estoque em 12",
    "subir 30 unidades no estoque", "somar mais uma agua",
],
"alterar_estoque": [
    # definir o total, sem ambiguidade
    "corrige o estoque da agua para 30", "corrige o estoque para 12",
    "o estoque certo da agua e 25", "o estoque da coca deveria ser 40",
    "define o estoque do baly em 18", "deixa o estoque em 50",
    "conta de novo o estoque do baly", "recontei, tem 22 de chocolate",
    "atualiza o estoque do salgadinho para 8",
    "muda a quantidade do baly para 15", "ajusta a quantidade para 60",
    "o estoque da coca ta errado", "arruma a quantidade que ta errada",
    "fiz o inventario, agua tem 9", "inventario deu 33 de chocolate",
    "quantidade certa e 44", "poe o estoque em 100",
    "preciso ajustar a quantidade de um produto",
    # as de TIRAR ficam aqui: elas definem um alvo menor, e o codigo
    # recusa explicando que baixa sai por venda. Errado seria fingir
    # que consegue.
    "da baixa em 3 aguas", "diminui a quantidade da coca",
    "tira 5 do estoque", "baixa 2 unidades de agua",
],
}

TROCA = {"a":"s","s":"a","e":"r","r":"e","i":"o","o":"i","n":"m","m":"n","c":"v","t":"y","d":"s"}
CURTAS = {"quantidade":"qtd","unidades":"un","unidade":"un","estoque":"estq",
          "para":"pra","mais":"+","adiciona":"add","chegaram":"chegou"}


def sem_acento(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def dedo(f):
    ps = f.split(); g = [i for i, p in enumerate(ps) if len(p) >= 4]
    if not g: return f
    i = random.choice(g); p = list(ps[i]); j = random.randrange(len(p))
    if p[j] in TROCA: p[j] = TROCA[p[j]]
    ps[i] = "".join(p); return " ".join(ps)


def comida(f):
    ps = f.split(); g = [i for i, p in enumerate(ps) if len(p) >= 5]
    if not g: return f
    i = random.choice(g); p = ps[i]; j = random.randint(1, len(p) - 2)
    ps[i] = p[:j] + p[j+1:]; return " ".join(ps)


def curta(f):
    for a, b in CURTAS.items(): f = f.replace(a, b)
    return f


def telegrafica(f):
    fora = {"o","a","os","as","de","do","da","em","no","na","que","um","uma","pra","para"}
    return " ".join(p for p in f.split() if p not in fora)


CORRUP = [dedo, comida, curta, telegrafica]


def variar(base, n):
    saida = {base}; t = 0
    while len(saida) < n + 1 and t < n * 14:
        t += 1
        f = base
        for c in random.sample(CORRUP, random.randint(1, 2)): f = c(f)
        f = " ".join(f.split())
        if f and f != base: saida.add(f)
    return list(saida)


POR_BASE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
destino = "dados/perguntas_repor.jsonl"

linhas = []
for intencao, bases in BASES.items():
    for b in bases:
        for f in variar(b, POR_BASE):
            linhas.append({"pergunta": f, "intencao": intencao, "origem": "repor",
                           "base": b, "estado_emocional": "neutro", "tom_origem": "rotulado"})

vistas, unicas = set(), []
for l in linhas:
    ch = sem_acento(l["pergunta"].lower())
    if ch in vistas: continue
    vistas.add(ch); unicas.append(l)

with io.open(destino, "w", encoding="utf-8", newline="") as f:
    for l in unicas: f.write(json.dumps(l, ensure_ascii=False) + "\n")

for i, bases in BASES.items():
    n = sum(1 for l in unicas if l["intencao"] == i)
    print(f"  {i:<18} {len(bases):3d} bases  {n:4d} frases")

# ── a colisao que precisa NAO existir ──────────────────────────────────
# "estoque" nas duas e proposital. Mas se um VERBO de somar aparecer numa
# base de definir (ou vice-versa), a rede nao tem como aprender a
# diferenca — e o erro volta.
SOMA = ("chegar", "chegou", "entrou", "adicion", "acrescent", "repo", "repor",
        "mais ", "soma", "sobe", "aumenta", "inclui", "bota mais", "coloca mais")
print("\n  verbo de SOMAR dentro de uma base de DEFINIR:")
ruim = [b for b in BASES["alterar_estoque"] if any(v in b for v in SOMA)]
print("   " + ("\n   ".join(f"!! {b}" for b in ruim) if ruim else "nenhuma."))
