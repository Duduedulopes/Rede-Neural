# -*- coding: utf-8 -*-
"""
AS PERGUNTAS SOBRE O PROPRIO SISTEMA — e sobre o proprio gerente.

POR QUE ESTE ARQUIVO NASCEU

O Eduardo pediu que o gerente respondesse "me fale como e o sistema" com
uma explicacao leiga. Escrevi a resposta, e antes de comemorar fui medir
se a rede sequer manda essa pergunta para la. A maior parte sim:

    "me fale como e o sistema"     duvida_sistema   99,5%
    "como funciona o sistema"      duvida_sistema   98,5%

Mas dois grupos caiam fora, e sao justo os que uma banca pergunta:

    "voce e o chatgpt"             ajuda            99,9%
    "como voce aprende"            ajuda            99,2%
    "o sistema reconhece rosto"    configurar_camera 81,4%

A resposta sobre o gerente existia e nunca ia disparar.

A LICAO, DE NOVO: escrever a resposta nao e o mesmo que a pergunta
chegar nela. As duas pontas precisam ser medidas separado.

DOIS GRUPOS DE BASES

  sobre o sistema   formas de pedir a visao geral que a rede ainda nao
                    reconhecia com folga ("me fala sobre o sistema" dava
                    23,3%)
  sobre o gerente   quem ele e, se e ChatGPT, se manda dados para fora,
                    como aprende. Isso e `duvida_sistema` e nao `ajuda`:
                    `ajuda` e "o que voce FAZ"; aqui e "o que voce E".
"""
import json, io, random, unicodedata, sys

random.seed(42)

BASES = {
"duvida_sistema": [
    # ---- a visao geral, formas que ficavam fracas ----
    "me fala sobre o sistema", "fala sobre o sistema", "me conta sobre o sistema",
    "como funciona tudo isso", "me explica como funciona", "explica o sistema pra mim",
    "o que e essa loja", "que loja e essa", "como essa loja funciona",
    "como a loja funciona sem caixa", "por que nao tem caixa",
    "me da uma visao geral", "visao geral do sistema", "resumo do sistema",
    "como tudo se conecta", "como as partes conversam",
    "explica pra quem nao entende nada", "explica de forma simples",
    "conta como e por dentro", "o que tem por tras disso",

    # ---- sobre o proprio gerente ----
    "voce e o chatgpt", "voce e o gemini", "voce usa chatgpt",
    "voce e uma inteligencia artificial", "voce e uma ia mesmo",
    "que tipo de ia voce e", "voce e uma rede neural",
    "como voce aprende", "como voce foi treinado", "quem te fez",
    "voce manda meus dados pra fora", "meus dados vao pra internet",
    "voce funciona sem internet", "voce roda onde",
    "como voce entende o que eu escrevo", "como voce sabe o que eu quero",
    "por que as vezes voce nao responde", "por que voce me da tres opcoes",
    "voce pode errar", "o quanto voce acerta",

    # ---- privacidade, que caia em configurar_camera ----
    "o sistema reconhece rosto", "tem reconhecimento facial",
    "voces guardam imagem das pessoas", "o cliente e identificado",
    "isso respeita a privacidade", "e legal gravar os clientes",
    "voces sabem quem e a pessoa",
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
    fora = {"o","a","os","as","de","do","da","em","no","na","que","e","um","uma","pra","para"}
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


POR_BASE = int(sys.argv[1]) if len(sys.argv) > 1 else 4
destino = "dados/perguntas_sobre_sistema.jsonl"

linhas = []
for intencao, bases in BASES.items():
    for b in bases:
        for f in variar(b, POR_BASE):
            linhas.append({"pergunta": f, "intencao": intencao,
                           "origem": "sobre_sistema", "base": b,
                           "estado_emocional": "curiosidade", "tom_origem": "rotulado"})

vistas, unicas = set(), []
for l in linhas:
    ch = sem_acento(l["pergunta"].lower())
    if ch in vistas: continue
    vistas.add(ch); unicas.append(l)

with io.open(destino, "w", encoding="utf-8", newline="") as f:
    for l in unicas: f.write(json.dumps(l, ensure_ascii=False) + "\n")

n = sum(len(v) for v in BASES.values())
print(f"{n} bases -> {len(unicas)} frases  ({destino})")
