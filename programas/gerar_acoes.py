# -*- coding: utf-8 -*-
"""
As frases de ORDEM, e as variacoes de escrita em cima delas.

DUAS COISAS DIFERENTES, E CONFUNDI-LAS ESTRAGA A MEDIDA

  BASE      uma forma nova de pedir a mesma coisa
            "muda o preco da agua" / "a agua ta com preco errado"

  VARIANTE  a mesma frase escrita com pressa
            "muda o preco da agua" -> "mda o preço d agua"

Gerar 40 variantes de 27 bases da 1080 frases e ensina 27 esqueletos. A
rede decora os esqueletos e a nota fica linda. Por isso a maior parte do
trabalho aqui esta nas BASES — 14 por intencao, escritas com formas de
pedir genuinamente diferentes: imperativo, pedido educado, constatacao
("a agua ta com preco errado"), pergunta indireta, telegrafica.

E cada linha carrega o campo `base`. Sem ele a validacao cruzada poe
"muda o preco da agua" no treino e "mda o preço d agua" no teste, e a nota
mede se a rede sabe desfazer a minha propria corrupcao — nao se ela
entende o Eduardo.
"""
import json, io, random, unicodedata, sys

random.seed(42)

BASES = {
"alterar_preco": [
    "muda o preco da agua para 5 reais",
    "altera o valor do baly",
    "quero mudar o preco do chocolate",
    "poe a agua a 4,50",
    "o preco da coca ta errado, arruma",
    "atualiza o valor do salgadinho",
    "preciso corrigir o preco de um produto",
    "reajusta o preco da agua",
    "coloca o baly por 7 reais",
    "troca o preco do chocolate para 5,90",
    # NAO por aqui uma base do tipo "da pra mudar quanto custa a agua?".
    # Ela embute a consulta "quanto custa a agua" inteira, e a rede passa a
    # ler a pergunta de preco como ordem de alteracao — medido: 98,4% de
    # confianca em `alterar_preco` para "qnt custa a agua". Forma
    # interrogativa pura nao serve de base para ordem.
    "deixa o baly mais barato",
    "aumenta o preco do refrigerante",
    "abaixa o valor do salgadinho",
    "corrige o preco que ta errado",
],
"alterar_estoque": [
    "corrige o estoque da agua para 30",
    "muda a quantidade do baly",
    "chegaram mais 20 chocolates",
    "atualiza o estoque do salgadinho",
    "poe 50 unidades de agua",
    "o estoque da coca ta errado",
    "preciso ajustar a quantidade de um produto",
    "da baixa em 3 aguas",
    "entrou mercadoria nova, atualiza",
    "conta de novo o estoque do baly",
    "acrescenta 10 no estoque do chocolate",
    "diminui a quantidade da coca",
    "repoe o estoque do salgadinho",
    "arruma a quantidade que ta errada",
],
"adicionar_produto": [
    "adiciona um produto novo",
    "cadastra chocolate ao leite",
    "quero por um item novo no catalogo",
    "cria um produto",
    "tem um produto novo pra cadastrar",
    "inclui a agua com gas no sistema",
    "novo produto: suco de uva",
    "preciso adicionar mais um item",
    "cadastra ai um salgadinho novo",
    "poe esse produto no catalogo",
    "da pra criar um produto?",
    "registra um item novo",
    "vou cadastrar uma bebida nova",
    "insere um produto no sistema",
],
"remover_produto": [
    "remove a agua do catalogo",
    "apaga esse produto",
    "tira o baly da lista",
    "exclui o chocolate",
    "quero remover um item",
    "deleta o salgadinho do sistema",
    "esse produto nao vendemos mais, tira",
    "desativa a coca no catalogo",
    "some com esse produto",
    "cancela o cadastro do suco",
    "da pra apagar um produto?",
    "retira o item do catalogo",
    "elimina esse produto da lista",
    "nao quero mais vender agua com gas",
],
"configurar_camera": [
    "configura uma camera nova",
    "adiciona a camera da entrada",
    "muda o endereco da camera lateral",
    "quero configurar a camera do alto",
    "troca a resolucao das cameras",
    "poe uma camera nova no sistema",
    "ajusta a camera frontal",
    "preciso mexer na configuracao da camera",
    "altera o ip da camera lateral",
    "reconfigura a camera que ta caindo",
    "da pra adicionar mais uma camera?",
    "muda a taxa de quadros da camera",
    "instala uma camera na saida",
    "arruma a configuracao das cameras",
],
"configurar_sistema": [
    "muda a configuracao do sistema",
    "altera o limite de estoque baixo",
    "quero mudar uma configuracao",
    "ajusta os parametros do sistema",
    "configura o alerta de estoque",
    "muda o tempo de expiracao do qr code",
    "preciso alterar uma config",
    "troca a configuracao da loja",
    "define o minimo de estoque como 5",
    "mexe nas configuracoes",
    "da pra mudar o ajuste do sistema?",
    "atualiza os parametros",
    "altera a configuracao das zonas",
    "arruma a config que ta errada",
],
"reiniciar_servico": [
    "reinicia o sistema",
    "reinicia o so espacial",
    "da um restart no monitor",
    "para e liga o servico de novo",
    "preciso reiniciar o rastreamento",
    "reinicia a captura das cameras",
    "derruba e sobe o servidor",
    "reseta o servico",
    "da pra reiniciar o sistema?",
    "reinicializa o monitor",
    "sobe o servico de novo",
    "restarta o so espacial",
    "reinicia tudo",
    "para o servico e liga de novo",
],
}

# --------------------------------------------------------------------
# As corrupcoes de escrita. Cada uma imita um jeito real de errar.
# --------------------------------------------------------------------

VIZINHA = {  # teclado abnt2: a letra do lado
    "a":"s","s":"ad","d":"sf","f":"dg","g":"fh","h":"gj","j":"hk","k":"jl","l":"k",
    "q":"w","w":"qe","e":"wr","r":"et","t":"ry","y":"tu","u":"yi","i":"uo","o":"ip","p":"o",
    "z":"x","x":"zc","c":"xv","v":"cb","b":"vn","n":"bm","m":"n",
}

CURTAS = {
    "voce":"vc", "esta":"ta", "estao":"tao", "para":"pra", "pro":"pro",
    "quantidade":"qtd", "quanto":"qnt", "produto":"prod", "camera":"cam",
    "configuracao":"config", "sistema":"sist", "reais":"rs", "hoje":"hj",
    "agora":"agr", "por favor":"pfv", "tambem":"tbm", "muito":"mto",
}

def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def com_acento_errado(f):
    """Poe acento onde nao tem ou tira onde tem — o erro mais comum."""
    trocas = {"preco":"preço", "e":"é", "camera":"câmera", "voce":"você",
              "agua":"água", "sistema":"sistema", "codigo":"código"}
    palavras = f.split()
    for i, p in enumerate(palavras):
        if p in trocas and random.random() < 0.7:
            palavras[i] = trocas[p]
    return " ".join(palavras)


def dedo_escorregou(f):
    """Uma letra trocada pela vizinha no teclado."""
    letras = [c for i, c in enumerate(f) if c.isalpha()]
    if not letras:
        return f
    f = list(f)
    posicoes = [i for i, c in enumerate(f) if c.lower() in VIZINHA]
    if not posicoes:
        return "".join(f)
    i = random.choice(posicoes)
    f[i] = random.choice(VIZINHA[f[i].lower()])
    return "".join(f)


def letra_comida(f):
    """Uma letra faltando no meio de uma palavra."""
    palavras = f.split()
    longas = [i for i, p in enumerate(palavras) if len(p) > 4]
    if not longas:
        return f
    i = random.choice(longas)
    p = palavras[i]
    j = random.randint(1, len(p) - 2)
    palavras[i] = p[:j] + p[j + 1:]
    return " ".join(palavras)


def encurtada(f):
    """Trocas que quem digita rapido faz."""
    for longo, curto in CURTAS.items():
        f = f.replace(longo, curto)
    return f


def telegrafica(f):
    """Sem artigo nem preposicao, como quem tem pressa."""
    fora = {"um","uma","o","a","os","as","do","da","de","no","na","em","para","pro","pra","que"}
    return " ".join(p for p in f.split() if p.lower() not in fora)


def sem_pontuacao(f):
    return f.replace("?", "").replace(",", "").replace(".", "")


CORRUPCOES = [com_acento_errado, dedo_escorregou, letra_comida,
              encurtada, telegrafica, sem_pontuacao]


def variar(base, quantas):
    """Variacoes distintas da mesma base."""
    saida = {base}
    tentativas = 0
    while len(saida) < quantas + 1 and tentativas < quantas * 12:
        tentativas += 1
        f = base
        for c in random.sample(CORRUPCOES, random.randint(1, 2)):
            f = c(f)
        f = " ".join(f.split())
        if f and f != base:
            saida.add(f)
    return list(saida)


POR_BASE = int(sys.argv[1]) if len(sys.argv) > 1 else 3
destino = "dados/perguntas_acoes.jsonl"

linhas = []
for intencao, bases in BASES.items():
    for b in bases:
        for f in variar(b, POR_BASE):
            linhas.append({"pergunta": f, "intencao": intencao,
                           "origem": "acoes", "base": b})

vistas = set()
unicas = []
for l in linhas:
    ch = sem_acento(l["pergunta"].lower())
    if ch in vistas:
        continue
    vistas.add(ch)
    unicas.append(l)

with io.open(destino, "w", encoding="utf-8", newline="") as f:
    for l in unicas:
        f.write(json.dumps(l, ensure_ascii=False) + "\n")

n_bases = sum(len(v) for v in BASES.values())
print(f"{n_bases} bases  ->  {len(unicas)} frases  ({destino})")
for i, bases in BASES.items():
    n = sum(1 for l in unicas if l["intencao"] == i)
    print(f"   {i:<20} {len(bases):3d} bases  {n:4d} frases")
print("\nexemplos:")
for l in random.sample(unicas, 12):
    print(f'   {l["intencao"]:<20} "{l["pergunta"]}"')
