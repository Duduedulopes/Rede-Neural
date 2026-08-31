# -*- coding: utf-8 -*-
"""
Treina as DUAS saidas e mede o que importa: o tom atrapalha a intencao?

    python programas/treinar_duplo.py [--peso 0.3] [--varrer]

A PERGUNTA QUE ESTE PROGRAMA RESPONDE

O tronco e compartilhado. Aprender tom muda a representacao que a
intencao usa. Isso pode regularizar (duas tarefas parecidas se ajudam) ou
roubar capacidade da oculta.

Nao da para decidir isso por raciocinio. `--varrer` treina com varios
pesos de tom e mostra as duas notas lado a lado; o peso certo e o que a
tabela mostrar, e a linha `peso 0.0` e a base de comparacao — nela a
saida de tom aprende sem tocar no tronco, entao a intencao fica igual ao
modelo de uma cabeca so.

DOBRAS AGRUPADAS POR BASE, sempre. O corpus fundido tem 40 variacoes do
mesmo radical; espalhadas entre treino e teste, a nota mede se a rede
desfaz o molde, nao se ela entende o Eduardo. Ja custou 27 pontos de nota
falsa neste projeto.
"""
import argparse, io, json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from rede.classificador_duplo import ClassificadorDuplo
from rede.texto import Vocabulario
from rede.treino import taxa_cosseno
from programas.treinar_intencao import dobras_por_base

import os
CORPUS = RAIZ / "dados" / os.environ.get("CORPUS_DUPLO", "perguntas_fundido.jsonl")
SAIDA  = RAIZ / "modelos" / "intencao.json"
SEMENTE, EPOCAS, TAXA, DIM, OC, DOBRAS, LOTE = 42, 80, 1.0, 24, 32, 5, 16


def carregar():
    return [json.loads(L) for L in io.open(CORPUS, encoding="utf-8") if L.strip()]


def treinar(dados, peso_tom, so_uma_dobra=False):
    perg = [d["pergunta"] for d in dados]
    rot_i = [d["intencao"] for d in dados]
    rot_t = [d.get("estado_emocional", "neutro") for d in dados]
    intencoes, tons = sorted(set(rot_i)), sorted(set(rot_t))
    ni = {n: i for i, n in enumerate(intencoes)}
    nt = {n: i for i, n in enumerate(tons)}
    bases = [d.get("base") or d["pergunta"] for d in dados]

    grupos = dobras_por_base(bases, rot_i, DOBRAS, np.random.default_rng(SEMENTE))
    quantas = 1 if so_uma_dobra else DOBRAS
    acc_i, acc_t = [], []

    for d in range(quantas):
        teste = set(grupos[d])
        treino = [i for i in range(len(dados)) if i not in teste]
        voc = Vocabulario([perg[i] for i in treino])
        ex = [(voc.indices(perg[i]), ni[rot_i[i]], nt[rot_t[i]]) for i in treino]

        c = ClassificadorDuplo(len(voc), intencoes, tons, dimensao=DIM,
                               ocultos=OC, semente=SEMENTE, peso_tom=peso_tom)
        g = np.random.default_rng(SEMENTE)
        for e in range(EPOCAS):
            t = taxa_cosseno(TAXA, e, EPOCAS)
            ordem = g.permutation(len(ex))
            for i in range(0, len(ex), LOTE):
                c.passo([ex[j] for j in ordem[i:i + LOTE]], t)

        av = [(voc.indices(perg[i]), ni[rot_i[i]], nt[rot_t[i]]) for i in grupos[d]]
        ai, at = c.avaliar(av)
        acc_i.append(ai); acc_t.append(at)

    return (100 * np.mean(acc_i), 100 * np.std(acc_i),
            100 * np.mean(acc_t), 100 * np.std(acc_t),
            intencoes, tons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peso", type=float, default=0.3)
    ap.add_argument("--varrer", action="store_true")
    ap.add_argument("--rapido", action="store_true", help="uma dobra so, para varrer")
    ap.add_argument("--final", action="store_true", help="treina no corpus inteiro e grava")
    a = ap.parse_args()

    if a.final:
        final(a.peso); return
    dados = carregar()
    print(f"corpus: {len(dados)} frases, "
          f"{len({d['intencao'] for d in dados})} intencoes, "
          f"{len({d.get('estado_emocional','neutro') for d in dados})} tons, "
          f"{len({d.get('base') or d['pergunta'] for d in dados})} bases\n")

    if a.varrer:
        print("  QUANTO O TOM PESA NO TRONCO")
        print("  (peso 0.0 = tom aprende sem tocar na intencao — a base de comparacao)\n")
        print("  peso    intencao        tom")
        for peso in [0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]:
            mi, si, mt, st, *_ = treinar(dados, peso, so_uma_dobra=a.rapido)
            print(f"  {peso:4.1f}   {mi:5.1f}% +-{si:4.1f}   {mt:5.1f}% +-{st:4.1f}")
        return

    mi, si, mt, st, intencoes, tons = treinar(dados, a.peso)
    print(f"  intencao  {mi:.1f}% +- {si:.1f}")
    print(f"  tom       {mt:.1f}% +- {st:.1f}")
    print(f"  tons: {tons}")




# ══════════════════════════════════════════════════════════════════════
#  O MODELO FINAL, treinado com o corpus inteiro (sem dobras).
#
#  A ESCOLHA DAS 960, REGISTRADA COM O NUMERO
#
#  As 960 frases de `expansao_emocional` custam, medido em validacao
#  cruzada agrupada de 5 dobras:
#
#      com elas    intencao 56,9% +-3,6   tom 81,6% +-3,4
#      sem elas    intencao 62,1% +-2,5   tom 85,9% +-1,9
#
#  Cinco pontos em cada saida. Elas ficam porque o Eduardo decidiu que
#  ficam, com esse numero na mao — e o sistema e dele.
#
#  Para reverter, e uma variavel de ambiente:
#      CORPUS_DUPLO=_sem_emocional.jsonl python programas/treinar_duplo.py --final
#
#  O motivo do custo, para quem ler isto depois: sao poucos moldes
#  colados em radicais ("urgente, {frase}" / "{frase}, valeu"). A rede
#  aprende o molde, e a dobra agrupada corretamente se recusa a dar nota
#  por isso.
# ══════════════════════════════════════════════════════════════════════
def final(peso_tom=0.5):
    import json as _json
    dados = carregar()
    perg = [d["pergunta"] for d in dados]
    rot_i = [d["intencao"] for d in dados]
    rot_t = [d.get("estado_emocional", "neutro") for d in dados]
    intencoes, tons = sorted(set(rot_i)), sorted(set(rot_t))
    ni = {n: i for i, n in enumerate(intencoes)}
    nt = {n: i for i, n in enumerate(tons)}

    voc = Vocabulario(perg)
    ex = [(voc.indices(p), ni[a], nt[b]) for p, a, b in zip(perg, rot_i, rot_t)]
    c = ClassificadorDuplo(len(voc), intencoes, tons, dimensao=DIM, ocultos=OC,
                           semente=SEMENTE, peso_tom=peso_tom)
    g = np.random.default_rng(SEMENTE)
    for e in range(EPOCAS):
        t = taxa_cosseno(TAXA, e, EPOCAS)
        ordem = g.permutation(len(ex))
        for i in range(0, len(ex), LOTE):
            c.passo([ex[j] for j in ordem[i:i + LOTE]], t)

    SAIDA.parent.mkdir(exist_ok=True)
    m = c.para_dicionario(voc)
    SAIDA.write_text(_json.dumps(m, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")
    print(f"  {c.n_parametros} parametros  ({c.cabeca_tom.n_parametros} deles sao a saida de tom)")
    print(f"  {len(intencoes)} intencoes, {len(tons)} tons, {len(voc)} pecas")
    print(f"  gravado: {SAIDA}")
    return c, voc

if __name__ == "__main__":
    main()
