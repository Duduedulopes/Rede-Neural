# -*- coding: utf-8 -*-
"""
A medida final, e a prova de que o agrupamento importa.

Roda TUDO duas vezes:

  SEM AGRUPAR   as variantes de uma mesma frase caem em dobras diferentes.
                "muda o preco da agua" treina, "mda o preço d agua" testa.
                A rede so precisa desfazer a corrupcao que EU escrevi.

  AGRUPANDO     toda variante de uma base fica na MESMA dobra. Para acertar
                no teste, a rede tem de generalizar de OUTRAS formas de
                pedir — que e o que o Eduardo vai fazer.

A diferenca entre os dois numeros e exatamente o tamanho da mentira que
eu contaria se nao agrupasse. Publicar a nota sem agrupar seria dizer que
o gerente entende girias quando ele so sabe desfazer o meu dicionario.
"""
import json, io, sys, numpy as np
from collections import Counter, defaultdict

sys.path.insert(0, ".")
sys.path.insert(0, "programas")
from rede.texto import Vocabulario
from rede.classificador import ClassificadorDeIntencao
from rede.treino import taxa_cosseno

SEMENTE, EPOCAS, TAXA, DIM, OC, DOBRAS = 42, 80, 1.0, 24, 32, 5

ESCREVEM = {"adicionar_produto", "alterar_preco", "alterar_estoque",
            "remover_produto", "configurar_camera", "configurar_sistema",
            "reiniciar_servico"}

arq = sys.argv[1] if len(sys.argv) > 1 else "dados/perguntas_com_acoes.jsonl"
dados = [json.loads(l) for l in io.open(arq, encoding="utf-8") if l.strip()]
perg = [d["pergunta"] for d in dados]
plan = [d["intencao"] for d in dados]
base = [d.get("base", d["pergunta"]) for d in dados]
bina = ["acao" if p in ESCREVEM else "consulta" for p in plan]


def dobras_soltas(rotulos, k, g):
    """Estratificada por classe, ignorando a base. Vaza."""
    porClasse = defaultdict(list)
    for i, r in enumerate(rotulos):
        porClasse[r].append(i)
    grupos = [[] for _ in range(k)]
    for r, idxs in porClasse.items():
        for j, i in enumerate(g.permutation(idxs)):
            grupos[j % k].append(int(i))
    return grupos


def dobras_agrupadas(rotulos, k, g):
    """A base inteira vai para uma dobra so. Nao vaza."""
    # cada base pertence a uma classe; distribui BASES, nao frases
    daBase = {}
    for i, b in enumerate(base):
        daBase.setdefault(b, rotulos[i])
    porClasse = defaultdict(list)
    for b, r in daBase.items():
        porClasse[r].append(b)

    dobraDaBase = {}
    for r, bs in porClasse.items():
        for j, b in enumerate(g.permutation(sorted(bs))):
            dobraDaBase[b] = j % k

    grupos = [[] for _ in range(k)]
    for i, b in enumerate(base):
        grupos[dobraDaBase[b]].append(i)
    return grupos


def rodar(rotulos, fazer_dobras, etiqueta):
    classes = sorted(set(rotulos))
    n_cls = {c: i for i, c in enumerate(classes)}
    prev = [None] * len(dados)
    g = np.random.default_rng(SEMENTE)
    grupos = fazer_dobras(plan, DOBRAS, g)
    for d in range(DOBRAS):
        te = set(grupos[d])
        tr = [i for i in range(len(dados)) if i not in te]
        if not tr or not te:
            continue
        voc = Vocabulario([perg[i] for i in tr])
        ex = [(voc.indices(perg[i]), n_cls[rotulos[i]]) for i in tr]
        c = ClassificadorDeIntencao(len(voc), classes, dimensao=DIM,
                                    ocultos=OC, semente=SEMENTE)
        gg = np.random.default_rng(SEMENTE)
        for e in range(EPOCAS):
            t = taxa_cosseno(TAXA, e, EPOCAS)
            o = gg.permutation(len(ex))
            for i in range(0, len(ex), 16):
                c.passo([ex[j] for j in o[i:i + 16]], t)
        for i in grupos[d]:
            p = np.asarray(c.prever(voc.indices(perg[i]))).ravel()
            prev[i] = classes[int(np.argmax(p))]
    return prev


print(f"{arq}: {len(dados)} frases, {len({b for b in base})} bases\n")

for etiqueta, fazer in [("SEM AGRUPAR (a nota bonita e falsa)", dobras_soltas),
                        ("AGRUPANDO POR BASE (a nota que vale)", dobras_agrupadas)]:
    print(f"  {etiqueta}")
    print("  " + "-" * 60)

    pb = rodar(bina, fazer, etiqueta)
    idx_acao = [i for i in range(len(dados)) if bina[i] == "acao"]
    idx_cons = [i for i in range(len(dados)) if bina[i] == "consulta"]
    achou = sum(1 for i in idx_acao if pb[i] == "acao")
    falso = sum(1 for i in idx_cons if pb[i] == "acao")
    print(f"    e ordem de mudanca?   acha {achou:3d} de {len(idx_acao)} "
          f"({100*achou/len(idx_acao):.0f}%)   falso alarme {falso} de {len(idx_cons)}")

    pp = rodar(plan, fazer, etiqueta)
    geral = sum(1 for i in range(len(dados)) if pp[i] == plan[i])
    acao_ok = sum(1 for i in idx_acao if pp[i] == plan[i])
    print(f"    31 intencoes          geral {100*geral/len(dados):.1f}%   "
          f"nas de acao {acao_ok} de {len(idx_acao)} ({100*acao_ok/len(idx_acao):.0f}%)")
    print()

print("  A distancia entre os dois blocos e o tamanho do auto-engano.")
print("  So o segundo pode ser dito em voz alta.")
