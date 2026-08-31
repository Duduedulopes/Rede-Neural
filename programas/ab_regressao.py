# -*- coding: utf-8 -*-
"""
Regressao ou lacuna antiga?

Treina DUAS vezes com a mesma semente: uma so com as 508 frases de antes,
outra com as 577 de agora. Se a frase piorou no segundo, a intencao nova
roubou territorio. Se ja estava ruim no primeiro, o buraco sempre existiu
e eu so o enxerguei agora.

Sem esta medida eu estaria adivinhando — e adivinhar sobre o proprio
trabalho e como se defende um defeito.
"""
import json, io, sys, numpy as np
sys.path.insert(0, ".")
from rede.texto import Vocabulario
from rede.classificador import ClassificadorDeIntencao
from rede.treino import taxa_cosseno

SEMENTE = 42
EPOCAS, TAXA, DIM, OC = 80, 1.0, 24, 32

FRASES = [
    "qual o fps da camera alta",
    "quantas cameras tem",
    "as cameras estao boas",
    "qual a resolucao das cameras",
    "tem camera offline",
    "a camera do teto ta boa",
]

dados = [json.loads(l) for l in io.open("dados/perguntas.jsonl", encoding="utf-8") if l.strip()]
antigo = [d for d in dados if d["intencao"] != "status_sistema"][:508]
# reconstroi o corpus de antes: sem status_sistema e sem as 20 novas de duvida
novas_duvida = {"como funciona o sistema?", "como funciona o sistema", "me explica o sistema",
                "explica como o sistema funciona", "me explica como isso funciona",
                "como isso tudo funciona", "como esse sistema funciona", "me conta como funciona",
                "explica o funcionamento", "queria entender como funciona",
                "o que e um embutimento", "o que e o limiar de confianca",
                "por que voce nao entendeu minha pergunta",
                "como voce classifica o que eu pergunto", "o que e uma intencao",
                "como voce foi treinado", "quantas frases voce aprendeu",
                "o que e a rede neural do gerente", "voce usa gemini?",
                "voce e o mesmo chat do aplicativo do cliente"}
antigo = [d for d in dados
          if d["intencao"] != "status_sistema" and d["pergunta"] not in novas_duvida]


def treinar(corpus, etiqueta):
    perguntas = [d["pergunta"] for d in corpus]
    rotulos = [d["intencao"] for d in corpus]
    intencoes = sorted(set(rotulos))
    n_int = {n: i for i, n in enumerate(intencoes)}
    voc = Vocabulario(perguntas)
    exemplos = [(voc.indices(p), n_int[r]) for p, r in zip(perguntas, rotulos)]

    # MESMO treino do programas/treinar_intencao.py: minilote 16, taxa em
    # cosseno, mesma semente. Se o treino diferisse, a comparacao nao valeria.
    c = ClassificadorDeIntencao(len(voc), intencoes, dimensao=DIM,
                                ocultos=OC, semente=SEMENTE)
    g = np.random.default_rng(SEMENTE)
    for epoca in range(EPOCAS):
        t = taxa_cosseno(TAXA, epoca, EPOCAS)
        ordem = g.permutation(len(exemplos))
        for i in range(0, len(exemplos), 16):
            c.passo([exemplos[j] for j in ordem[i:i + 16]], t)
    print(f"\n{etiqueta}: {len(corpus)} frases, {len(intencoes)} intencoes, "
          f"{len(voc)} pecas")
    saida = {}
    for f in FRASES:
        p = np.asarray(c.prever(voc.indices(f))).ravel()
        o = np.argsort(p)[::-1]
        saida[f] = [(intencoes[i], float(p[i])) for i in o[:2]]
        marca = "" if intencoes[o[0]] == "cameras" else "   <- nao e cameras"
        print(f"   {f:<30} {intencoes[o[0]]:<16} {p[o[0]]:5.1%}{marca}")
    return saida


a = treinar(antigo, "CORPUS DE ANTES")
b = treinar(dados, "CORPUS DE AGORA")

print("\nCOMPARACAO — confianca na intencao 'cameras'")
print("   " + "-" * 62)
for f in FRASES:
    ca = dict(a[f]).get("cameras", 0.0)
    cb = dict(b[f]).get("cameras", 0.0)
    d = cb - ca
    seta = "melhorou" if d > 0.02 else ("PIOROU" if d < -0.02 else "igual")
    print(f"   {f:<30} {ca:5.1%} -> {cb:5.1%}   {seta}")
