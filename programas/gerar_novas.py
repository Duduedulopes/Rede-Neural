# -*- coding: utf-8 -*-
"""
AS TRES INTENCOES QUE FALTAVAM, E O REFORCO DO FATURAMENTO. Programa.

    python programas/gerar_novas.py [variacoes_por_base]

DE ONDE VEIO CADA UMA

  listar_produtos   O Chefe perguntou "quais sao os produtos?" tres vezes
                    seguidas e recebeu "3 produtos, 17 unidades, R$ 92,70"
                    nas tres. O C# ja lista; a rede ainda nao entende o
                    pedido — cai em `estoque_baixo` a 78,1%, e ele tem de
                    clicar num botao para ver a resposta.

  furo_sistema      "Tivemos algum furo no sistema?". Furo, para esta loja,
                    e ESTOQUE QUE NAO BATE — foi a escolha do Chefe entre
                    quatro definicoes possiveis.

  relatorio_periodo "Puxe no sistema todas as informacoes sobre <periodo>".
                    Nao e faturamento: faturamento e dinheiro, isto e tudo.

  faturamento       Reforco. "Me fale qual o faturamento de hoje, da semana
                    e do mes?" chegava a 51,4% — e o palpite era `comparar`.
                    O leitor de periodo ja sabe ler tres recortes de uma
                    frase so; faltava a rede reconhecer a frase.

AS COLISOES QUE PRECISAM NAO EXISTIR

Cada intencao nova nasce vizinha de uma que ja funciona, e uma palavra no
lugar errado derruba a vizinha. Ja aconteceu tres vezes: "por favor" so no
lado do sim, "muda ..." no cancelar, "pode" onze vezes no sim. Nenhuma foi
achada por raciocinio — todas por medicao.

Entao aqui a checagem vem junto do gerador, no fim do arquivo:

  listar_produtos    x  estoque_baixo   nao pode falar de acabar/faltar
  listar_produtos    x  adicionar/remover  nao pode ter verbo de acao
  furo_sistema       x  status_sistema  nao pode falar de rodar/online
  furo_sistema       x  alterar_estoque nao pode ter numero de destino
  relatorio_periodo  x  faturamento     nao pode falar de dinheiro
"""
import json, io, random, unicodedata, sys, re

random.seed(42)

BASES = {

# ── QUAIS sao os produtos, e nao QUANTO tem de um ─────────────────────
"listar_produtos": [
    "quais sao os produtos?", "quais produtos temos?", "quais sao os itens?",
    "liste todos os produtos", "lista os produtos", "lista de produtos",
    "me mostra os produtos", "me mostra o catalogo", "mostra o catalogo da loja",
    "qual o catalogo da loja?", "catalogo completo", "ver produtos",
    "o que tem na loja?", "o que a loja vende?", "o que temos a venda?",
    # "cadastrados" saiu daqui. O particípio parece inofensivo, mas divide
    # trigramas com "cadastra" e "cadastrar produto", que sao de
    # `adicionar_produto` — e aquela intencao tem 58 frases contra as 191
    # daqui. E a mesma forma do erro do "por favor": a palavra existe dos
    # dois lados, mas o peso esta todo de um.
    "quais itens a loja tem?", "quais produtos tem no sistema?",
    "me da a lista de produtos", "me passa os produtos da loja",
    "quero ver todos os produtos", "quero a relacao dos produtos",
    "me fala os produtos", "me diz quais produtos tem", "me lista o que tem",
    "todos os produtos", "quais mercadorias temos?",
    "que produtos existem no sistema?", "abre a lista de produtos",
    "me mostra tudo que a loja tem", "quais sao as mercadorias da loja?",
    "enumera os produtos", "lista tudo que temos a venda",
],

# ── o estoque bate com a prateleira? ──────────────────────────────────
"furo_sistema": [
    "tivemos algum furo no sistema?", "teve furo?", "tem furo no estoque?",
    "deu furo hoje?", "tem buraco no estoque?", "teve quebra de estoque?",
    "o estoque bate?", "o estoque esta batendo?", "o inventario bate?",
    "o sistema bate com a prateleira?",
    "o numero do sistema confere com a prateleira?",
    "confere o estoque com o fisico", "conferencia de estoque",
    "sumiu algum produto?", "esta sumindo produto?", "quanto sumiu?",
    "teve divergencia de estoque?", "tem divergencia?",
    "perdemos alguma coisa?", "teve perda?", "tivemos perda de produto?",
    "alguem levou sem pagar?", "saiu produto sem pagamento?",
    "tem produto saindo sem venda?", "teve roubo?",
    "contei a prateleira e nao bate", "o estoque do sistema esta errado",
    "tem produto a menos do que deveria?", "o que nao esta batendo?",
    "algo errado com o estoque?", "o sistema esta perdendo produto?",
    "tem venda que nao entrou na conta?",
],

# ── tudo sobre um periodo, e nao so o dinheiro ────────────────────────
"relatorio_periodo": [
    "puxe todas as informacoes de hoje", "puxa tudo do mes",
    "puxe no sistema tudo sobre ontem", "puxa os dados do mes",
    "me da um relatorio de agosto", "quero um relatorio do dia",
    "relatorio da semana", "relatorio completo", "relatorio geral",
    "faz um relatorio", "gera um relatorio do mes",
    "me passa o resumo geral de hoje", "resumo do mes",
    "resumo completo da semana", "me da um apanhado do dia",
    "me da o panorama de hoje", "informacoes gerais de hoje",
    "me traz todas as informacoes da semana", "todas as informacoes do mes",
    "quero tudo sobre o dia 15", "tudo sobre ontem",
    "quero ver tudo que aconteceu hoje", "o que aconteceu essa semana?",
    "me conta como foi a semana inteira", "quero o balanco da semana",
    "consolida as informacoes de agosto", "junta tudo do mes num relatorio",
    "me mostra tudo do dia",
],

# ── REFORCO: a mesma intencao de sempre, com recorte de tempo ─────────
"faturamento": [
    "me fale qual o faturamento de hoje, da semana e do mes?",
    "qual o faturamento de hoje da semana e do mes?",
    "quanto faturamos hoje, essa semana e esse mes?",
    "me diz o faturamento do dia, da semana e do mes",
    "faturamento de hoje e da semana",
    "quanto foi hoje e ontem?",
    "faturamento da semana passada",
    "quanto faturamos essa semana?",
    "quanto faturamos esse mes?",
    "quanto faturamos no mes passado?",
    "quanto vendemos em agosto?",
    "faturamento de julho",
    "faturamento dos ultimos 7 dias",
    "quanto entrou este ano?",
    "quanto faturamos no dia 15?",
    "qual foi o faturamento de ontem?",
    "quanto vendeu na semana?",
    "faturamento do mes ate agora",
],
}

TROCA = {"a":"s","s":"a","e":"r","r":"e","i":"o","o":"i","n":"m","m":"n","c":"v","t":"y"}
CURTAS = {"voce":"vc","voces":"vcs","porque":"pq","por que":"pq","para":"pra",
          "esta":"ta","como":"cm","nao":"n","sistema":"sist","que":"q"}


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
destino = "dados/perguntas_novas.jsonl"

linhas = []
for intencao, bases in BASES.items():
    for b in bases:
        for f in variar(b, POR_BASE):
            linhas.append({"pergunta": f, "intencao": intencao, "origem": "novas",
                           "base": b, "estado_emocional": "neutro", "tom_origem": "rotulado"})

vistas, unicas = set(), []
for l in linhas:
    ch = sem_acento(l["pergunta"].lower())
    if ch in vistas: continue
    vistas.add(ch); unicas.append(l)

with io.open(destino, "w", encoding="utf-8", newline="") as f:
    for l in unicas: f.write(json.dumps(l, ensure_ascii=False) + "\n")

print(f"  {destino}")
for i, bases in BASES.items():
    n = sum(1 for l in unicas if l["intencao"] == i)
    print(f"  {i:<19} {len(bases):3d} bases  {n:4d} frases")


# ══════════════════════════════════════════════════════════════════════
#  AS COLISOES QUE PRECISAM NAO EXISTIR
#
#  A vizinha de cada intencao nova ja funciona. Uma palavra no lugar
#  errado derruba a vizinha, e o estrago so aparece depois do treino —
#  quando ja custou uma hora. Barato conferir aqui.
# ══════════════════════════════════════════════════════════════════════
PROIBIDO = {
    ("listar_produtos", "estoque_baixo"):
        ("acaba", "acabando", "faltando", "falta", "baixo", "repor", "minimo"),
    ("listar_produtos", "adicionar/remover_produto"):
        ("adicion", "cadastr", "cria", "remov", "apaga", "exclui", "deleta"),
    ("furo_sistema", "status_sistema"):
        ("rodando", "online", "no ar", "funcionando", "de pe", "ativo", "respondendo"),
    ("furo_sistema", "alterar_estoque"):
        ("para 1", "para 2", "para 3", "para 5", "corrige o estoque para"),
    ("relatorio_periodo", "faturamento"):
        ("fatur", "vendemo", "receita", "quanto", "ticket", "lucro", "dinheiro"),
    ("relatorio_periodo", "listar_produtos"):
        ("catalogo", "lista os produtos", "quais produtos"),
}

print("\n  colisao com a vizinha:")
achou = False
for (intencao, vizinha), palavras in PROIBIDO.items():
    for b in BASES.get(intencao, []):
        for w in palavras:
            if w in sem_acento(b.lower()):
                print(f"   !! [{intencao}] \"{b}\"  ->  \"{w}\" e de {vizinha}")
                achou = True
if not achou:
    print("   nenhuma.")

# A palavra "estoque" aparece de proposito em `furo_sistema` e em
# `alterar_estoque`. O que separa e o VERBO: bater/sumir/conferir de um
# lado, corrigir para N do outro. Mesma licao de "mais 20" contra
# "para 20" — a palavra compartilhada nao e o problema; a palavra
# compartilhada SEM verbo que a distinga e que e.
