# -*- coding: utf-8 -*-
"""
Acrescenta ao corpus a intencao NOVA `status_sistema` e reforca
`duvida_sistema`, que era a mais magra das treze.

A FRONTEIRA IMPORTA MAIS QUE A QUANTIDADE.

Tres intencoes vizinhas, e a rede so aprende a diferenca se o corpus
mostrar a diferenca:

    cameras          detalhe DAS CAMERAS      "qual o fps da camera alta"
    status_sistema   saude DO SISTEMA TODO    "esta tudo funcionando"
    duvida_sistema   como uma coisa FUNCIONA  "como o rfid identifica"

Por isso quase nenhuma frase de `status_sistema` diz "camera": se dissesse,
ela roubaria o territorio de `cameras` e as duas ficariam piores. As poucas
que dizem sao as em que a camera aparece dentro de "tudo".
"""
import json, io, unicodedata, pathlib, collections

STATUS = [
    # --- a pergunta que ele realmente fez, e as irmas dela ---
    "esta tudo funcionando?",
    "está tudo funcionando?",
    "ta tudo funcionando",
    "tudo funcionando?",
    "esta tudo certo?",
    "ta tudo certo",
    "tudo ok?",
    "ta tudo ok",
    "esta tudo rodando?",
    "ta rodando tudo?",
    # --- no ar / de pe ---
    "o sistema esta no ar?",
    "o sistema ta no ar",
    "o sistema esta de pe?",
    "os sistemas estao no ar",
    "esta tudo online?",
    "ta tudo online",
    "tudo conectado?",
    "esta tudo conectado",
    # --- pedido explicito de diagnostico ---
    "diagnostico",
    "diagnostico do sistema",
    "faz um diagnostico",
    "me da um diagnostico geral",
    "status",
    "status do sistema",
    "qual o status geral",
    "me mostra o status de tudo",
    "checagem geral",
    "faz uma checagem",
    "saude do sistema",
    "como esta a saude do sistema",
    # --- procurando problema ---
    "tem algum problema?",
    "algum problema no sistema",
    "ta tudo bem com o sistema",
    "algo fora do ar?",
    "tem alguma coisa caida?",
    "caiu alguma coisa?",
    "alguma falha?",
    "tem alguma falha agora",
    "algum erro no sistema",
    "esta tudo saudavel",
    # --- as pecas nomeadas, mas perguntando por TODAS ---
    "a api esta respondendo?",
    "a webapi ta no ar",
    "o so espacial esta rodando?",
    "o so espacial ta ligado",
    "o monitor esta ligado?",
    "os dois sistemas estao funcionando",
    "smart store e so espacial estao no ar",
    "esta tudo integrado e funcionando",
    "o sistema todo esta operando normal",
    "tudo operacional?",
]

DUVIDA = [
    # --- a pergunta que ele fez e ficou a 4 pontos do limiar ---
    "como funciona o sistema?",
    "como funciona o sistema",
    "me explica o sistema",
    "explica como o sistema funciona",
    "me explica como isso funciona",
    "como isso tudo funciona",
    "como esse sistema funciona",
    "me conta como funciona",
    "explica o funcionamento",
    "queria entender como funciona",
    # --- conceitos que faltavam ---
    "o que e um embutimento",
    "o que e o limiar de confianca",
    "por que voce nao entendeu minha pergunta",
    "como voce classifica o que eu pergunto",
    "o que e uma intencao",
    "como voce foi treinado",
    "quantas frases voce aprendeu",
    "o que e a rede neural do gerente",
    "voce usa gemini?",
    "voce e o mesmo chat do aplicativo do cliente",
]

AQUI = pathlib.Path(__file__).resolve().parent.parent
ARQ = AQUI / "dados" / "perguntas.jsonl"


def normalizar_chave(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


linhas = [json.loads(l) for l in io.open(ARQ, encoding="utf-8") if l.strip()]
existentes = {normalizar_chave(l["pergunta"]) for l in linhas}

novas, repetidas = [], []
for frase, intencao in ([(f, "status_sistema") for f in STATUS] +
                        [(f, "duvida_sistema") for f in DUVIDA]):
    chave = normalizar_chave(frase)
    if chave in existentes:
        repetidas.append(frase)
        continue
    existentes.add(chave)
    novas.append({"pergunta": frase, "intencao": intencao, "origem": "semente"})

with io.open(ARQ, "a", encoding="utf-8", newline="") as f:
    for n in novas:
        f.write(json.dumps(n, ensure_ascii=False) + "\n")

print("acrescentadas: %d   ja existiam: %d" % (len(novas), len(repetidas)))
for r in repetidas:
    print("   repetida (nao gravada):", r)

c = collections.Counter(l["intencao"] for l in linhas + novas)
print("\nCORPUS: %d frases, %d intencoes\n" % (sum(c.values()), len(c)))
for k, v in c.most_common():
    print("  %-18s %3d  %s" % (k, v, "#" * v))
