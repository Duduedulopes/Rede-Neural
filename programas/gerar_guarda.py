"""Gera o CONJUNTO DE GUARDA que protege o aprendizado na loja. Programa.

    python programas/gerar_guarda.py

O QUE E ISTO, E POR QUE NAO SERVE O conferencia.json

O `conferencia.json` tem 20 casos e um proposito diferente: provar que a
conta do C# bate com a do Python, numero por numero. Vinte casos bastam
para isso — divergencia de porte aparece no primeiro.

A trava do aprendizado pergunta outra coisa: "este passo de gradiente
estragou o que a rede ja sabia?". Medimos isso na loja: consertar UMA frase
quebrou sete de mil cento e noventa e uma. Em vinte casos, sete de mil e
duzentas nao aparecem — a trava aprovaria o estrago.

Entao a guarda precisa ser grande o bastante para ver o dano, e pequena o
bastante para o navegador medir em milissegundos.

DUAS REGRAS NA AMOSTRAGEM, E AS DUAS SAO POR CAUSA DE ERRO JA COMETIDO

1. AMOSTRA POR `base`, NAO POR FRASE. Variantes da mesma frase
   ("chocolates" / "chocolstes") sao a mesma pergunta escrita de dois
   jeitos. Se uma cair na guarda e outra no treino, a guarda esta medindo
   uma frase que a rede acabou de ver — e aprova qualquer coisa. Foi o
   mesmo erro que inflou a acuracia em 27 pontos na validacao cruzada.

2. ESTRATIFICA POR INTENCAO. Uma amostra aleatoria simples deixa de fora as
   intencoes raras — e sao justamente elas que um passo de gradiente
   atropela primeiro, porque tem menos peso para se defender.

O ARQUIVO E DERIVADO. Regerar depois de todo treino e barato; esquecer
custa uma trava que protege o modelo errado.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORPUS = RAIZ / "dados" / "perguntas_fundido.jsonl"
MODELO = RAIZ / "modelos" / "intencao.json"
SAIDA = RAIZ / "modelos" / "guarda.json"

# Quantas frases por intencao. Com 42 intencoes da algo perto de 400 — o
# navegador mede isso em poucos milissegundos, e e sensivel o bastante para
# ver um estrago de meio ponto percentual.
POR_INTENCAO = 30

SEMENTE = 20260902


def main() -> int:
    if not CORPUS.exists():
        print(f"nao achei o corpus em {CORPUS}")
        return 1

    intencoes_do_modelo = set(json.loads(MODELO.read_text(encoding="utf-8"))["intencoes"])

    # ── agrupa por (intencao, base) ───────────────────────────────────
    por_intencao = defaultdict(lambda: defaultdict(list))
    for linha in CORPUS.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        intencao = d["intencao"]
        if intencao not in intencoes_do_modelo:
            continue
        base = d.get("base") or d["pergunta"]
        por_intencao[intencao][base].append(d["pergunta"])

    sorteio = random.Random(SEMENTE)
    guarda = []
    faltantes = []

    for intencao in sorted(por_intencao):
        bases = sorted(por_intencao[intencao])
        sorteio.shuffle(bases)
        escolhidas = bases[:POR_INTENCAO]

        if len(escolhidas) < POR_INTENCAO:
            faltantes.append(f"{intencao} ({len(escolhidas)})")

        for base in escolhidas:
            # UMA variante por base, e a primeira em ordem — nao a mais
            # bonita nem a mais curta. Escolher a "melhor" frase de cada
            # base faria a guarda medir um problema mais facil que o real.
            frases = sorted(por_intencao[intencao][base])
            guarda.append({"pergunta": frases[0], "intencao": intencao, "base": base})

    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(
        json.dumps(guarda, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"  {len(guarda)} frases de guarda, {len(por_intencao)} intencoes")
    print(f"  {SAIDA}  ({SAIDA.stat().st_size / 1024:.0f} KB)")
    if faltantes:
        print(f"  intencoes com menos de {POR_INTENCAO} bases: {', '.join(faltantes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
