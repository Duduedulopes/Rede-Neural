"""Treina o previsor de eventos da loja. Programa.

    python programas/treinar_previsor.py --epocas 12

AS LINHAS DE BASE VEM ANTES DO RESULTADO

Um previsor sozinho nao diz nada. 'Perplexidade 4' e bom ou ruim? So da
para saber comparando com o que se consegue SEM rede nenhuma:

    uniforme   chutar entre os 29 tokens com igual chance      -> 29,0
    unigrama   chutar sempre pela frequencia geral             -> ?
    bigrama    olhar so o token anterior                       -> ?
    a rede     olhar a janela inteira                          -> ?

Se a rede nao bater o bigrama, ela nao esta usando o contexto — esta
reaprendendo, devagar, uma tabela de contagem.
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import vocabulario as V  # noqa: E402
from rede.previsor import Previsor  # noqa: E402
from rede.treino import taxa_cosseno  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
LOG = Path(r"C:\Users\Samsung\Projetos_Eduardo\SO-Espacial\dados\eventos.jsonl")
LOG_LOJA = RAIZ / "dados" / "eventos_loja.jsonl"
SEMENTE = 42


def ler_um(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    saida = []
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            saida.append(json.loads(linha))
        except Exception:
            continue
    return saida


def ler_eventos(caminho_espacial, caminho_loja=None):
    """Junta os dois fluxos numa sequencia unica, em ordem de tempo.

    POR QUE JUNTAR, E NAO TREINAR DOIS MODELOS

    A gramatica que interessa atravessa os dois sistemas:

        BRACO:estendido  ->  PRODUTO:adicionado

    O braco vem do SO Espacial; o produto vem do SmartGo. Dois modelos
    separados nunca aprenderiam essa transicao — cada um veria metade do
    gesto. E ela e justamente a que importa, porque a falta dela e o
    furto: braco esticado na gondola e NADA entrando no carrinho.

    Ordenar por `t` e o que faz os dois virarem um so fluxo. Ambos os
    sistemas carimbam em ISO com fuso, entao a ordenacao textual ja e
    cronologica — mas so porque o fuso e o mesmo nos dois. Se um dia um
    deles gravar em UTC, isto quebra em silencio.
    """
    eventos = ler_um(caminho_espacial)
    da_loja = ler_um(caminho_loja) if caminho_loja else []
    if da_loja:
        eventos += da_loja
        eventos.sort(key=lambda e: e.get("t") or "")
        print(f"  {len(da_loja)} eventos de compra juntados ao fluxo")
    else:
        print("  nenhum evento de compra ainda — o previsor so vera movimento")
    return eventos


def montar_janelas(eventos, indice, janela):
    """(janela de indices, indice do proximo).

    A JANELA REINICIA A CADA `SYSTEM_STARTED`. O log tem varias sessoes
    coladas uma na outra; uma janela que atravessa a emenda pediria ao
    modelo para prever o comeco de uma sessao a partir do fim de outra, que
    e uma pergunta sem resposta. Emenda de sessao nao e contexto.
    """
    i_inicio = indice[V.INICIO]
    i_desc = indice[V.DESCONHECIDO]

    exemplos = []
    contexto = [i_inicio] * janela
    for e in eventos:
        t = V.token(e)
        alvo = indice.get(t, i_desc)
        exemplos.append((list(contexto), alvo))
        if e.get("tipo") == "SYSTEM_STARTED":
            contexto = [i_inicio] * janela
        else:
            contexto = contexto[1:] + [alvo]
    return exemplos


def base_uniforme(tamanho):
    return float(tamanho)


def base_unigrama(treino, teste, tamanho, alfa=1.0):
    """Chuta sempre pela frequencia geral. Ignora contexto por completo."""
    c = Counter(alvo for _, alvo in treino)
    total = len(treino) + alfa * tamanho
    soma = 0.0
    for _, alvo in teste:
        p = (c[alvo] + alfa) / total
        soma += -math.log(p)
    return math.exp(soma / len(teste))


def base_bigrama(treino, teste, tamanho, alfa=0.5):
    """Olha SO o token imediatamente anterior. A memoria mais curta possivel."""
    c = defaultdict(Counter)
    for janela, alvo in treino:
        c[janela[-1]][alvo] += 1
    soma = 0.0
    for janela, alvo in teste:
        linha = c[janela[-1]]
        p = (linha[alvo] + alfa) / (sum(linha.values()) + alfa * tamanho)
        soma += -math.log(p)
    return math.exp(soma / len(teste))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=12)
    ap.add_argument("--janela", type=int, default=6)
    ap.add_argument("--dimensao", type=int, default=16)
    ap.add_argument("--ocultos", type=int, default=64)
    ap.add_argument("--taxa", type=float, default=0.5)
    ap.add_argument("--fixa", action="store_true",
                    help="taxa constante, para comparar com a agenda")
    ap.add_argument("--lote", type=int, default=32)
    ap.add_argument("--log", default=str(LOG))
    ap.add_argument("--log-loja", default=str(LOG_LOJA))
    args = ap.parse_args()

    eventos = ler_eventos(args.log, args.log_loja)
    lista, indice, _ = V.construir(eventos)
    exemplos = montar_janelas(eventos, indice, args.janela)

    corte = int(len(exemplos) * 0.75)
    treino, teste = exemplos[:corte], exemplos[corte:]

    print(f"eventos {len(eventos)}   vocabulario {len(lista)}   janela {args.janela}")
    print(f"treino {len(treino)} (mais antigos)   teste {len(teste)} (mais recentes)")
    print()

    print("linhas de base, no mesmo teste:")
    b_uni = base_uniforme(len(lista))
    b_1g = base_unigrama(treino, teste, len(lista))
    b_2g = base_bigrama(treino, teste, len(lista))
    print(f"  uniforme (puro acaso)      perplexidade {b_uni:6.2f}")
    print(f"  unigrama (so frequencia)   perplexidade {b_1g:6.2f}")
    print(f"  bigrama  (1 token atras)   perplexidade {b_2g:6.2f}")
    print()

    p = Previsor(len(lista), janela=args.janela, dimensao=args.dimensao,
                 ocultos=args.ocultos, semente=SEMENTE)
    print(f"previsor {args.janela}x{args.dimensao} -> {args.ocultos} -> {len(lista)}"
          f"   {p.n_parametros} parametros")
    print()

    print("  taxa " + ("constante" if args.fixa else "em cosseno, de "
          f"{args.taxa} ate ~0"))
    print()

    gerador = np.random.default_rng(SEMENTE)
    melhor = float("inf")
    for epoca in range(args.epocas):
        taxa = args.taxa if args.fixa else taxa_cosseno(args.taxa, epoca, args.epocas)
        ordem = gerador.permutation(len(treino))
        for k in range(0, len(treino), args.lote):
            lote = [treino[i] for i in ordem[k:k + args.lote]]
            p.passo(lote, taxa)
        custo, perp, e1, e3 = p.avaliar(teste)
        melhor = min(melhor, perp)
        marca = "  <- melhor" if perp <= melhor else ""
        print(f"  epoca {epoca+1:3d}   taxa {taxa:.4f}   perplexidade {perp:6.2f}"
              f"   acerto {100*e1:5.1f}%   em 3 {100*e3:5.1f}%{marca}")

    custo, perp, e1, e3 = p.avaliar(teste)
    print()
    print(f"  RESULTADO   perplexidade {perp:.2f}   contra {b_2g:.2f} do bigrama"
          f"   e {b_uni:.0f} do acaso")

    # ---------------------------------------------------------------
    # O ALARME: os eventos que o previsor MENOS esperava.
    #
    # Ninguem definiu o que e suspeito. A lista abaixo sai sozinha de
    # `-ln p(o que aconteceu)` — o que o modelo nao conseguiu prever.
    # ---------------------------------------------------------------
    surpresas = []
    for k, (janela, alvo) in enumerate(teste):
        surpresas.append((p.surpresa(janela, alvo), k, janela, alvo))
    surpresas.sort(reverse=True)

    valores = np.array([s[0] for s in surpresas])
    print()
    print(f"  surpresa: mediana {np.median(valores):.2f} nats   "
          f"percentil 95 {np.percentile(valores,95):.2f}   maxima {valores.max():.2f}")
    print()
    print("  os 8 eventos que o gerente MENOS esperava (ninguem rotulou isto):")
    for s, k, janela, alvo in surpresas[:8]:
        antes = " ".join(lista[i] for i in janela[-3:])
        print(f"    {s:5.2f} nats   ...{antes}  ->  {lista[alvo]}")

    # ---------------------------------------------------------------
    # A TABELA DE EMBUTIMENTO SE ORGANIZOU SOZINHA?
    #
    # Ninguem disse que ENTROU:frente-a e ENTROU:frente-b sao parecidos.
    # Se eles ficaram perto, foi o gradiente que os aproximou — porque sao
    # seguidos das mesmas coisas.
    # ---------------------------------------------------------------
    from rede.embutimento import similaridade_cosseno
    print()
    print("  vizinhos mais proximos na tabela de embutimento:")
    for alvo_token in ["BRACO:estendido", "ENTROU:frente-a", "POSTURA:agachado", "TRACK_LOST"]:
        if alvo_token not in indice:
            continue
        i = indice[alvo_token]
        vizinhos = sorted(
            ((similaridade_cosseno(p.tabela[i], p.tabela[j]), lista[j])
             for j in range(len(lista)) if j != i), reverse=True)[:3]
        conta = "  ".join(f"{n} ({s:.2f})" for s, n in vizinhos)
        print(f"    {alvo_token:20s} -> {conta}")

    saida = RAIZ / "modelos" / "previsor.json"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(json.dumps({
        "vocabulario": lista,
        "janela": args.janela,
        "dimensao": args.dimensao,
        "perplexidade": round(perp, 3),
        "bases": {"uniforme": round(b_uni, 3), "unigrama": round(b_1g, 3),
                  "bigrama": round(b_2g, 3)},
        "acerto": round(e1, 4), "acerto_em_3": round(e3, 4),
        "tabela": [[round(float(x), 4) for x in linha] for linha in p.tabela],
        "camadas": [{"ativacao": c.ativacao.nome,
                     "pesos": [[round(float(x), 4) for x in l] for l in c.pesos],
                     "vies": [round(float(x), 4) for x in c.vies.ravel()]}
                    for c in p.rede.camadas],
    }, separators=(",", ":")), encoding="utf-8")
    print(f"  gravado: {saida.name} ({saida.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
