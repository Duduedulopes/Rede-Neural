# -*- coding: utf-8 -*-
"""
AS FRASES DE RESPOSTA: "sim", "nao", "esse ai".

POR QUE ESTE ARQUIVO EXISTE

Antes de escrever a confirmacao em C# eu perguntei pra rede o que ela
responde quando alguem digita "sim" depois de "posso alterar o preco?".
Medido, nas 21 formas mais comuns de dizer sim:

    acertou confirmar_acao em      1 de 21
    passou do limiar (0,97) em     2 de 21   -- e as duas ERRADAS:
        "pode fazer" -> ajuda        99,5%
        "positivo"   -> estoque_baixo 97,7%

Ou seja: a porta de confirmacao nao tinha chave. Escrever
`if (intencao == "confirmar_acao") executar()` daria um sistema onde
NADA executa — e onde "pode fazer" abre a tela de ajuda.

A causa esta no corpus: `confirmar_acao` tinha 12 frases de 4 bases, e as
4 sao formais — "confirmar operacao", "pode prosseguir", "aprovar",
"esta certo". Ninguem digita "confirmar operacao" respondendo a uma
pergunta de sim ou nao. Digita "sim", "pode", "isso", "manda ver".

`cancelar_operacao` tinha 48 frases e acerta 12 de 16. A diferenca entre
as duas classes nao e dificuldade: e quantidade e naturalidade.

DUAS COISAS QUE ESTA CLASSE TEM E AS OUTRAS NAO

1. AS FRASES SAO CURTAS, e a maquina de corrupcao do `gerar_acoes.py`
   quase nao morde: `telegrafica` tira artigo de frase que nao tem
   artigo, `letra_comida` exige palavra de 5+ letras. "sim" nao tem o
   que comer. Entao aqui a variedade vem de FORMA GENUINA — trinta
   jeitos diferentes de dizer sim — e nao de ruido sobre um esqueleto
   so. Que e o que deveria ser sempre; aqui e obrigatorio.

2. ELAS SAO AMBIGUAS FORA DE CONTEXTO, de proposito. "ok" sozinho nao
   quer dizer nada; respondendo a "posso alterar?" quer dizer sim. O
   classificador nao ve contexto, entao ele VAI dizer confirmar_acao
   para um "ok" solto. Isso e seguro por uma razao so, e ela mora no
   C#: `confirmar_acao` sem operacao aberta nao executa nada. Se alguem
   um dia tirar essa guarda, um "ok" perdido vira uma gravacao no banco.

POR QUE "POR FAVOR" QUASE VIROU UM SIM

Medido depois do segundo treino, no mesmo modelo:

    "pode fazer"      -> confirmar_acao  99,4%    (quer dizer SIM)
    "para por favor"  -> confirmar_acao  99,4%    (quer dizer PARE)

Identicos. Nenhum limiar separa os dois, porque nao e questao de corte: a
rede aprendeu errado. A culpa e minha e esta neste arquivo — eu tinha
"sim por favor", "faz por favor" e "por favor" do lado do SIM, e nenhuma
forma educada do lado do NAO. Entao "por favor" virou sinal de sim, e
qualquer recusa educada era arrastada junto.

Educacao nao e concordancia. "Para, por favor" e recusa; "faz, por favor"
e aceite; o que decide e o VERBO, nao a cortesia. Um corpus em que so um
dos lados e educado ensina o contrario disso.

Correcao: as mesmas formas de cortesia dos dois lados, para que ela deixe
de carregar sinal e a rede tenha de olhar o verbo.

O ERRO QUE ESTA MEDIDA ACHOU, E QUE E O PIOR DE TODOS

Depois do primeiro treino, em frases fora do corpus:

    "muda isso"   ->  confirmar_acao   100,0%

Numa confirmacao, "muda isso" quer dizer NAO — mude, esta errado. Lido
como sim, com 100% de confianca, ele GRAVA. Erro de consulta mostra um
numero errado e a pessoa olha de novo; erro aqui escreve no banco.

A causa: eu tinha 65 formas de dizer sim e nenhuma forma de CORRIGIR.
"muda isso" nao e sim nem e cancelamento puro — e "isso ai esta errado,
volta e pergunta de novo". Sem essa familia no corpus, a rede encaixou
no vizinho mais parecido, e o vizinho era o sim.

Correcao vai para `cancelar_operacao` de proposito: no C#, cancelar nao
encerra a conversa, volta a perguntar — que e exatamente o que o Eduardo
pediu ("se nao, ele tenta chegar na melhor solucao ou volta para outra
pergunta"). Cancelar aqui quer dizer "nao grave isso", nao "tchau".

O CUIDADO: "muda isso" e primo de "muda o preco da agua", que e ordem de
verdade. Por isso o controle no fim do arquivo testa as duas familias —
se ensinar a correcao estragar `alterar_preco`, a medida acusa.

A TERCEIRA VEZ QUE O MESMO ERRO APARECEU, AGORA COM "PODE"

Medido na validacao cruzada, frases lidas como SIM acima de 0,995:

    "pode parar"    -> confirmar_acao  99,8%     quer dizer PARE
    "pode deixar"   -> confirmar_acao 100,0%     quer dizer DEIXA
    "pode prar"     -> confirmar_acao  99,9%

E sempre o mesmo mecanismo. Um token aparece quase so de um lado, vira o
sinal daquele lado, e o resto da frase nao consegue desmentir — a rede
faz MEDIA dos pedacos, entao um "pode" muito marcado dilui o verbo que
vem depois.

    "por favor"  estava 11 vezes no sim e 0 no nao  -> recusa educada virou aceite
    "pode"       estava 11 vezes no sim e 5 no nao  -> "pode parar" virou aceite

A licao nao e sobre estas duas palavras. E sobre a forma: SE UMA PALAVRA
QUE NAO DECIDE NADA APARECE SO DE UM LADO, ELA PASSA A DECIDIR. O corpus
precisa de cortesia dos dois lados, de "pode" dos dois lados, e de
qualquer outro molde que sirva as duas respostas.

Por isso as listas abaixo sao emparelhadas de proposito: para cada "pode
<verbo de sim>" existe um "pode <verbo de nao>". O que sobra para
distinguir e o verbo, que e o que de fato distingue.

E O ERRO QUE A CORRECAO DO ERRO CAUSOU

Ensinar "muda isso" como cancelamento envenenou o verbo:

    "muda o preco da agua para 5,50"
        antes:  alterar_preco  99,5%
        depois: alterar_preco  73,5%   e cancelar_operacao 25,5%

"muda" e o verbo principal de `alterar_preco`. Poe-lo do lado do
cancelamento e disputar com a propria acao. Eu tinha ate escrito o aviso
neste arquivo — e a lista de controle nao pegou porque testei "para 5
reais" e nao "para 5,50", que e a forma que quebra.

A SAIDA NAO E O CORPUS, E A ESTRUTURA

O perigo original era "muda isso" ser lido como SIM e gravar. Mas no C#,
na hora da confirmacao, so `confirmar_acao` acima do corte grava —
qualquer outra intencao repete a pergunta sem escrever nada. Entao "muda
isso" cair em `alterar_preco` e SEGURO: nao grava, e o gerente pergunta
de novo.

Ou seja, eu nao preciso que a rede chame "muda isso" de cancelamento.
Preciso apenas que ela NAO chame de confirmacao. Isso e uma exigencia
muito mais barata, e ela nao custa o verbo.

Ficam as formas de correcao que nao roubam verbo de acao: "nao e esse",
"esse nao", "ta errado isso", "errou", "nao era isso".

O QUE ESTE ARQUIVO NAO PODE FAZER

Engolir pergunta de verdade. "pode" e confirmacao; "pode me dizer quanto
tem de agua?" e consulta de estoque. O mesmo erro que ja apareceu neste
projeto com "da pra mudar quanto custa a agua?" — base que embute uma
consulta inteira e faz a rede ler consulta como ordem. Por isso toda
base aqui e curta e tem forma de RESPOSTA, e no fim o programa testa
justamente as perguntas que comecam com as mesmas palavras.
"""
import json, io, random, unicodedata, sys

random.seed(42)

# ─────────────────────────────────────────────────────────────── as bases
# Cada uma e uma forma genuinamente diferente de responder — nao a mesma
# frase com ruido. Curtas e em forma de resposta, nunca de pergunta.

BASES = {
"confirmar_acao": [
    # o sim seco
    "sim", "isso", "certo", "exato", "correto", "positivo",
    # o sim com verbo
    "pode", "pode sim", "pode fazer", "pode alterar", "pode prosseguir",
    "pode ir", "pode mandar", "faz isso", "faz sim", "manda", "manda ver",
    "vai la", "segue", "prossegue", "executa", "confirma", "confirmo",
    # o sim informal
    "aham", "uhum", "ta", "ta certo", "ta bom", "ta ok", "ok", "beleza",
    "blz", "isso mesmo", "isso ai", "e isso", "e isso mesmo", "perfeito",
    "show", "fechado", "combinado", "tranquilo", "por mim ta bom",
    # o sim com pressa
    "sim pode", "sim faz", "claro", "claro que sim", "com certeza",
    "afirmativo", "bora", "vamos", "vai fundo", "manda bala",
    # o sim educado
    "sim por favor", "por favor", "sim obrigado", "isso mesmo obrigado",
    "esta correto", "esta certo", "confirmado", "aprovado", "autorizo",
    "autorizado", "de acordo", "concordo", "aceito",
    # as que a medida em frases novas mostrou fracas ou perdidas
    "pode ir em frente", "pode seguir", "segue em frente", "toca ai",
    "tudo certo", "tudo ok", "ta valendo", "ta tudo certo", "acho que sim",
    "faz ai", "faz por favor", "libera", "libera ai", "autoriza",
    "pode gravar", "pode salvar", "grava", "salva", "aplica",
    "aplica ai", "efetiva", "vai que vai", "e por ai", "eh isso",
],
"cancelar_operacao": [
    # o nao seco  (os que a medida mostrou fracos vem primeiro)
    "nao", "nao quero", "errado", "ta errado", "nao e isso", "nao e bem isso",
    "negativo", "nem", "nada disso", "de jeito nenhum",
    # o nao com verbo
    "cancela", "cancelar", "para", "para tudo", "deixa", "deixa pra la",
    "esquece", "esquece isso", "nao faz", "nao faca", "nao altera",
    "nao precisa", "melhor nao", "prefiro nao",
    # o desvio
    "quero outra coisa", "e outra coisa", "outra coisa", "muda de assunto",
    "deixa eu perguntar outra coisa", "espera", "espera ai", "calma",
    "peraí", "opa nao", "opa errado",
    # o arrependimento
    "me enganei", "errei", "digitei errado", "nao era isso",
    "nao era esse produto", "esse nao", "produto errado", "valor errado",
    "nao era esse valor", "volta", "volta atras", "desfaz", "anula",

    # ── A CORRECAO ────────────────────────────────────────────────────
    # Nao e sim e nao e adeus: e "isso ai esta errado, pergunta de novo".
    # Sem esta familia a rede leu "muda isso" como SIM a 100%.
    # SEM "muda ...", "corrige ...", "troca ...", "arruma ..." — esses sao
    # os verbos de `alterar_preco` e `alterar_estoque`. Ver a nota no topo.
    "refaz", "refaz isso", "de novo", "tenta de novo",
    "pergunta de novo", "outro produto", "outro valor", "nao esse",
    "nao esse produto", "nao esse valor", "esse valor nao", "ta errado isso",
    "isso ta errado", "nao e esse", "nao e esse produto", "errou",
    "voce errou", "nao foi isso que eu pedi", "nao pedi isso",

    # as que a medida em frases novas mostrou fracas ou perdidas
    "para com isso", "para agora", "para ai", "pare", "nem pensar",
    "recusa", "recuso", "desiste", "desisto", "deixa quieto",
    "melhor deixar", "nao vale", "abortar", "aborta",

    # ── A CORTESIA, DOS DOIS LADOS ────────────────────────────────────
    # Sem isto, "por favor" e sinal de SIM e a recusa educada e lida como
    # aceite. Ver a nota no topo do arquivo.
    "para por favor", "nao por favor", "cancela por favor",
    "para ai por favor", "nao faz por favor", "deixa por favor",
    "esquece por favor", "melhor nao por favor", "refaz por favor",
    "outro por favor",
    "nao obrigado", "nao valeu", "assim nao obrigado",
    "prefiro que nao", "poderia nao fazer",

    # ── "PODE" DO LADO DO NAO, em numero parecido com o do lado do sim ──
    # Sao 11 formas de "pode <verbo de sim>" ali em cima. Se aqui houver
    # 5, "pode" continua sendo sinal de sim e "pode parar" grava. Ver a
    # nota no topo.
    "pode parar", "pode cancelar", "pode deixar", "pode esquecer",
    "pode refazer", "pode abortar", "pode anular", "pode desfazer",
    "pode voltar", "pode corrigir", "pode trocar", "pode deixar pra la",
    "pode parar ai", "pode cancelar isso", "pode deixar quieto",
    "pode esquecer isso", "pode voltar atras", "pode nao fazer",
    "pode deixar assim", "pode nao alterar",
],
}

# ────────────────────────────────────────────────────── ruido de digitacao
# Pouco, e so onde cabe: em "sim" nao ha o que comer.

TROCA_VIZINHA = {"a":"s","s":"a","e":"r","r":"e","i":"o","o":"i",
                 "n":"m","m":"n","c":"v","v":"c","t":"y","d":"s"}


def sem_acento(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def dedo_escorregou(f):
    ps = f.split()
    grandes = [i for i, p in enumerate(ps) if len(p) >= 4]
    if not grandes: return f
    i = random.choice(grandes)
    p = list(ps[i]); j = random.randrange(len(p))
    if p[j] in TROCA_VIZINHA:
        p[j] = TROCA_VIZINHA[p[j]]
    ps[i] = "".join(p)
    return " ".join(ps)


def letra_comida(f):
    ps = f.split()
    grandes = [i for i, p in enumerate(ps) if len(p) >= 5]
    if not grandes: return f
    i = random.choice(grandes)
    p = ps[i]; j = random.randint(1, len(p) - 2)
    ps[i] = p[:j] + p[j+1:]
    return " ".join(ps)


def letra_dobrada(f):
    """"simm", "naoo" — o dedo que segura a tecla. Tipico de resposta curta."""
    ps = f.split()
    i = random.randrange(len(ps))
    p = ps[i]
    if len(p) < 2: return f
    ps[i] = p + p[-1]
    return " ".join(ps)


def sem_acento_todo(f):
    return sem_acento(f)


def com_acento_errado(f):
    """O contrario: acento onde nao tem."""
    for a, b in [("nao", "não"), ("sim", "sím"), ("ta", "tá"), ("e isso", "é isso"),
                 ("esta", "está"), ("ai", "aí"), ("la", "lá"), ("voce", "você")]:
        if a in f:
            return f.replace(a, b, 1)
    return f


def maiuscula(f):
    """"SIM" — quem responde com pressa as vezes deixa o caps."""
    return f.upper() if len(f) <= 12 else f


CORRUPCOES = [dedo_escorregou, letra_comida, letra_dobrada,
              sem_acento_todo, com_acento_errado, maiuscula]


def variar(base, quantas):
    saida = {base}
    tent = 0
    while len(saida) < quantas + 1 and tent < quantas * 15:
        tent += 1
        f = base
        for c in random.sample(CORRUPCOES, random.randint(1, 2)):
            f = c(f)
        f = " ".join(f.split())
        if f and f != base:
            saida.add(f)
    return list(saida)


POR_BASE = int(sys.argv[1]) if len(sys.argv) > 1 else 3
destino = "dados/perguntas_respostas.jsonl"

linhas = []
for intencao, bases in BASES.items():
    for b in bases:
        for f in variar(b, POR_BASE):
            linhas.append({"pergunta": f, "intencao": intencao,
                           "origem": "respostas", "base": b})

vistas, unicas = set(), []
for l in linhas:
    ch = sem_acento(l["pergunta"].lower())
    if ch in vistas: continue
    vistas.add(ch); unicas.append(l)

with io.open(destino, "w", encoding="utf-8", newline="") as f:
    for l in unicas:
        f.write(json.dumps(l, ensure_ascii=False) + "\n")

n_bases = sum(len(v) for v in BASES.values())
print(f"{n_bases} bases  ->  {len(unicas)} frases  ({destino})")
for i, bases in BASES.items():
    n = sum(1 for l in unicas if l["intencao"] == i)
    print(f"   {i:<20} {len(bases):3d} bases  {n:4d} frases")

# ───────────────────────────────────────── a colisao que precisa nao existir
# "pode" e confirmacao. "pode me dizer quanto tem de agua?" e consulta.
# Se alguma base aparecer INTEIRA dentro de uma pergunta de verdade, ela
# esta ensinando a rede a ler consulta como resposta.

REAIS = [
    "pode me dizer quanto tem de agua",
    "pode listar os produtos",
    "voce pode adicionar produtos",
    "quanto ta o faturamento",
    "certo entao quantas pessoas tem na loja",
    "ta faltando o que no estoque",
    "para quantas pessoas da a agua",
    "manda o resumo do dia",
    "isso aqui vende bem",
    "e isso que eu queria saber sobre o estoque",
    "nao entendi como funciona o sistema",
    "espera quantos produtos tem",
]
print("\nbases que aparecem inteiras dentro de uma pergunta real:")
achou = 0
for intencao, bases in BASES.items():
    for b in bases:
        alvo = sem_acento(b.lower())
        for r in REAIS:
            # so conta se casar em fronteira de palavra dos dois lados
            rr = f" {sem_acento(r.lower())} "
            if f" {alvo} " in rr:
                print(f"   !! '{b}' ({intencao})  dentro de  '{r}'")
                achou += 1
print("   nenhuma." if not achou else f"   {achou} colisoes — encurte ou remova essas bases.")
