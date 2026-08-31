"""
AS FRASES DE RESPOSTA: "sim", "nao", "muda isso".

POR QUE ESTE ARQUIVO EXISTE

`confirmar_acao` tinha 12 frases, de 4 bases, todas formais — "confirmar
operacao", "pode prosseguir". Ninguem digita isso respondendo a "posso
alterar o preco?". Medido nas 21 formas mais comuns de dizer sim, a rede
acertava 1.

A porta de confirmacao nao tinha chave: `if (intencao == "confirmar_acao")`
daria um sistema onde nada executa.

A REGRA QUE ESTE ARQUIVO EXISTE PARA CUMPRIR

Uma palavra que nao decide nada, se aparece quase so de um lado, PASSA a
decidir — a rede faz media dos pedacos, e um token muito marcado dilui o
verbo que vem depois. Isso aconteceu tres vezes, medido:

    "por favor"  11x no sim, 0 no nao  ->  "para por favor" virou SIM  99,4%
    "muda ..."   posto no cancelar     ->  "muda o preco da agua"  99,5% -> 73,5%
    "pode"       11x no sim, 5 no nao  ->  "pode parar" virou SIM     99,8%

Por isso as listas abaixo sao emparelhadas de proposito: cortesia dos dois
lados, "pode" dos dois lados. O que sobra para distinguir e o verbo, que e
o que de fato distingue. E por isso `dados/guardas_confirmacao.jsonl`
existe — o erro vai voltar, e a guarda e o que impede que ele passe
despercebido.

DUAS COISAS PROPRIAS DESTA CLASSE

1. As frases sao CURTAS, e a maquina de corrupcao mal morde — "sim" nao
   tem letra para comer. Entao a variedade vem de forma genuina, e nao de
   ruido sobre um esqueleto so.

2. Elas sao AMBIGUAS fora de contexto, de proposito. "ok" sozinho nao quer
   dizer nada; respondendo a "posso alterar?" quer dizer sim. O
   classificador nao ve contexto, entao um "ok" solto TAMBEM vira
   confirmacao — e isso so e seguro porque o C# nao executa
   `confirmar_acao` sem operacao aberta. Se essa guarda sair, um "ok"
   perdido vira uma gravacao no banco.

O que este arquivo nao pode fazer: engolir pergunta de verdade. "pode" e
confirmacao; "pode me dizer quanto tem de agua?" e consulta. Toda base
aqui e curta e tem forma de RESPOSTA, e o teste no fim confere.
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
