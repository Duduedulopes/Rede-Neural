"""Treina o classificador de intencao do gerente. Programa.

    python programas/treinar_intencao.py

VALIDACAO CRUZADA, E NAO UMA DIVISAO SO

Com 200 exemplos, separar 20% para teste deixa 40 frases — e cinco delas por
intencao. Um acerto a mais ou a menos mexe 2,5 pontos na nota. Numero assim
nao mede modelo, mede sorte de divisao.

Validacao cruzada em 5 dobras usa TODOS os exemplos como teste, um quinto de
cada vez, e reporta media e dispersao. E a mesma disciplina do "5,25 com 5%
de dispersao em 148 amostras".

    Com dado pequeno, um numero sozinho e opiniao. Media e dispersao sao
    medida.

A LINHA DE BASE E A REGRA DE PALAVRA-CHAVE

A pergunta que importa nao e "a rede acerta muito?". E:

    a rede acerta MAIS que o `if` que ela veio substituir?

Se nao acertar, ela nao esta pagando o proprio custo. O baseline abaixo e a
mesma logica que estava no GerenteService em C#, portada para comparar em
condicoes iguais.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede.classificador import ClassificadorDeIntencao  # noqa: E402
from rede.texto import Vocabulario, normalizar  # noqa: E402
from rede.treino import taxa_cosseno  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CORPUS = RAIZ / "dados" / "perguntas_expandido.jsonl"  # Usar corpus expandido com novas intenções
SAIDA = RAIZ / "modelos" / "intencao.json"
SEMENTE = 42

# A regra que a rede precisa bater. Copia fiel do C#.
REGRAS = [
    ("pessoas_na_loja", ["pessoa", "cliente", "gente", "quem esta", "quantos estao", "na loja agora"]),
    ("estoque_baixo",   ["acabando", "baixa", "baixo", "repor", "reposicao", "falta", "acabou"]),
    ("faturamento",     ["faturamento", "faturou", "faturamos", "vendas", "vendeu", "receita", "caixa", "ganhou"]),
    ("carrinho",        ["carrinho", "comprando", "sessao", "sacola", "levando"]),
    ("cameras",         ["camera", "cameras", "visao", "sistema espacial", "so espacial", "rastreio"]),
    ("estoque",         ["estoque", "quantos temos", "quanto tem", "quantidade", "tem de", "produto", "catalogo"]),
    ("ajuda",           ["ajuda", "o que voce faz", "comandos", "pode fazer"]),
]


def por_regra(pergunta):
    t = normalizar(pergunta)
    for intencao, termos in REGRAS:
        if any(termo in t for termo in termos):
            return intencao
    return "nao_entendi"


def carregar():
    linhas = []
    for linha in CORPUS.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha:
            linhas.append(json.loads(linha))
    return linhas


def dobras_por_base(bases, rotulos, k, gerador):
    """Todas as variantes de uma frase-base caem na MESMA dobra.

    Sem isto, "muda o preco da agua" treina e "mda o preço d agua" testa,
    e a nota mede se a rede desfaz a corrupcao que o gerador escreveu —
    nao se ela entende uma forma de pedir que nunca viu. Medido: 94%
    contra 67% nas frases de acao. Vinte e sete pontos de auto-engano.
    """
    from collections import defaultdict
    daBase = {}
    for b, r in zip(bases, rotulos):
        daBase.setdefault(b, r)
    porClasse = defaultdict(list)
    for b, r in daBase.items():
        porClasse[r].append(b)
    dobraDaBase = {}
    for r, bs in porClasse.items():
        for j, b in enumerate(gerador.permutation(sorted(bs))):
            dobraDaBase[b] = j % k
    grupos = [[] for _ in range(k)]
    for i, b in enumerate(bases):
        grupos[dobraDaBase[b]].append(i)
    return grupos


def dobras(rotulos, k, gerador):
    """Divisao ESTRATIFICADA: cada dobra com a mesma proporcao de intencoes.

    Divisao aleatoria simples poderia deixar uma dobra sem nenhum exemplo de
    `saudacao` — e ai a nota daquela dobra nao diz nada sobre saudacao.
    """
    por_classe = defaultdict(list)
    for i, r in enumerate(rotulos):
        por_classe[r].append(i)

    grupos = [[] for _ in range(k)]
    for classe, indices in sorted(por_classe.items()):
        indices = list(gerador.permutation(indices))
        for j, i in enumerate(indices):
            grupos[j % k].append(int(i))
    return grupos


def treinar(exemplos, n_vocab, intencoes, epocas, taxa, dimensao, ocultos, semente):
    c = ClassificadorDeIntencao(n_vocab, intencoes, dimensao=dimensao,
                                ocultos=ocultos, semente=semente)
    gerador = np.random.default_rng(semente)
    for epoca in range(epocas):
        t = taxa_cosseno(taxa, epoca, epocas)
        ordem = gerador.permutation(len(exemplos))
        for i in range(0, len(exemplos), 16):
            lote = [exemplos[j] for j in ordem[i:i + 16]]
            c.passo(lote, t)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=80)
    ap.add_argument("--taxa", type=float, default=1.0)
    ap.add_argument("--dimensao", type=int, default=24)
    ap.add_argument("--ocultos", type=int, default=32)
    ap.add_argument("--dobras", type=int, default=5)
    ap.add_argument("--corpus", default=None,
                    help="jsonl do corpus; sem isto usa dados/perguntas.jsonl")
    args = ap.parse_args()

    global CORPUS
    if args.corpus:
        CORPUS = Path(args.corpus)
    dados = carregar()
    print(f'corpus: {CORPUS}')
    perguntas = [d["pergunta"] for d in dados]
    rotulos = [d["intencao"] for d in dados]
    intencoes = sorted(set(rotulos))
    n_int = {n: i for i, n in enumerate(intencoes)}

    print(f"corpus: {len(dados)} frases, {len(intencoes)} intencoes")
    for nome, n in sorted(Counter(rotulos).items()):
        print(f"  {n:4d}  {nome}")
    print()

    # ---- linha de base: a regra ------------------------------------
    certos_regra = sum(1 for p, r in zip(perguntas, rotulos) if por_regra(p) == r)
    nao_entendeu = sum(1 for p in perguntas if por_regra(p) == "nao_entendi")
    print(f"REGRA DE PALAVRA-CHAVE   acerto {100*certos_regra/len(dados):5.1f}%"
          f"   ({nao_entendeu} frases ela nem tentou responder)")
    print(f"CHUTAR A MAIOR           acerto {100*max(Counter(rotulos).values())/len(dados):5.1f}%")
    print()

    # ---- a rede, em validacao cruzada -------------------------------
    gerador = np.random.default_rng(SEMENTE)
    bases = [d.get("base", d["pergunta"]) for d in dados]
    if len(set(bases)) < len(dados):
        grupos = dobras_por_base(bases, rotulos, args.dobras, gerador)
        print(f"dobras AGRUPADAS por base ({len(set(bases))} bases "
              f"para {len(dados)} frases)")
    else:
        grupos = dobras(rotulos, args.dobras, gerador)
    acertos, matriz = [], np.zeros((len(intencoes), len(intencoes)), dtype=int)

    for d in range(args.dobras):
        teste_i = set(grupos[d])
        treino_i = [i for i in range(len(dados)) if i not in teste_i]

        # O VOCABULARIO SAI SO DO TREINO. Construi-lo com o corpus inteiro
        # deixaria o modelo conhecer palavras do teste antes de ve-lo — e a
        # nota subiria por vazamento, nao por competencia.
        voc = Vocabulario([perguntas[i] for i in treino_i])
        prep = lambda i: (voc.indices(perguntas[i]), n_int[rotulos[i]])

        c = treinar([prep(i) for i in treino_i], len(voc), intencoes,
                    args.epocas, args.taxa, args.dimensao, args.ocultos, SEMENTE + d)
        acerto, _, M = c.avaliar([prep(i) for i in sorted(teste_i)])
        acertos.append(acerto)
        matriz += M
        print(f"  dobra {d+1}   acerto {100*acerto:5.1f}%   ({len(teste_i)} frases)")

    media, desvio = 100*np.mean(acertos), 100*np.std(acertos)
    print()
    print(f"A REDE                   acerto {media:5.1f}%  +- {desvio:.1f}"
          f"   (validacao cruzada em {args.dobras} dobras)")
    print()

    largura = max(len(i) for i in intencoes) + 1
    print("matriz de confusao somada (linha = verdade, coluna = rede)")
    print(" " * (largura + 2) + "".join(f"{i[:6]:>8s}" for i in intencoes))
    for i, nome in enumerate(intencoes):
        print(f"  {nome:<{largura}s}" + "".join(f"{matriz[i, j]:8d}" for j in range(len(intencoes))))
    print()

    # ---- modelo final: treinado em tudo -----------------------------
    voc = Vocabulario(perguntas)
    prep = lambda i: (voc.indices(perguntas[i]), n_int[rotulos[i]])
    final = treinar([prep(i) for i in range(len(dados))], len(voc), intencoes,
                    args.epocas, args.taxa, args.dimensao, args.ocultos, SEMENTE)

    print(f"modelo final: {len(voc)} pecas de texto, {final.n_parametros} parametros")
    print()
    print("teste com frases que NAO estao no corpus:")
    for frase in ["quanto q eu faturei hj", "cade os produtos acabando",
                  "tem quantas pessoa ai dentro", "as camera ta funcionando",
                  "quanto custa o baly", "me fala das vendas de hoje",
                  "oi td bem", "qual a cor do ceu"]:
        intencao, conf = final.responder(voc.indices(frase))
        marca = "  <- baixa confianca" if conf < 0.5 else ""
        print(f"  {conf*100:5.1f}%  {intencao:16s}  \"{frase}\"{marca}")

    SAIDA.parent.mkdir(exist_ok=True)
    modelo = final.para_dicionario(voc)

    # O LIMIAR VIAJA COM O MODELO, e nao no codigo que o consome.
    #
    # Ele foi medido NESTE modelo: `programas/calibrar_limiar.py` e
    # `varrer_epocas.py` mostraram 90,2% de precisao em 0,74 com 80 epocas.
    # Trocar o modelo sem trocar o limiar deixaria o gerente respondendo
    # onde deveria calar — o mesmo erro que ja cometi com os limiares de
    # surpresa do painel.
    #
    # Guardando junto, o limiar nao tem como ficar para tras.
    modelo["limiar"] = 0.74
    modelo["medido"] = {
        "epocas": args.epocas,
        "acerto_validacao_cruzada": round(float(media) / 100, 4),
        "precisao_no_limiar": 0.902,
        "cobertura_no_limiar": 0.404,
        "corpus": len(dados),
    }
    SAIDA.write_text(json.dumps(modelo, separators=(",", ":")), encoding="utf-8")
    print()
    print(f"gravado: {SAIDA.name} ({SAIDA.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
