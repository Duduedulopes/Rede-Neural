"""Treina a rede que avalia os eventos da loja. Programa.

    python programas/treinar_gerente.py

Le o log real do SO Espacial, extrai as caracteristicas, rotula com as regras
de `monitor/regras.py` e treina uma rede pequena para reproduzir o julgamento.

O NUMERO QUE IMPORTA NAO E A ACURACIA GERAL

As classes sao muito desbalanceadas: quase tudo e rotina. Uma rede que
respondesse "rotina" para TUDO ja acertaria a maior parte — e seria inutil,
porque nunca avisaria nada. Por isso o relatorio traz o acerto POR CLASSE e a
matriz de confusao, e nao so um numero.

    Num problema desbalanceado, a acuracia geral e o numero que esconde o
    fracasso.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor import regras  # noqa: E402
from monitor.caracteristicas import TAMANHO, Extrator  # noqa: E402
from rede import treino  # noqa: E402
from rede.ativacao import Softmax  # noqa: E402
from rede.custo import EntropiaCruzadaCategorica  # noqa: E402
from rede.rede import Rede  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
LOG = Path(r"C:\Users\Samsung\Projetos_Eduardo\SO-Espacial\dados\eventos.jsonl")
SAIDA = RAIZ / "modelos" / "gerente.json"
SEMENTE = 42


def carregar(caminho):
    extrator = Extrator()
    dados, contextos = [], []
    for linha in Path(caminho).read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            e = json.loads(linha)
        except Exception:
            continue
        v, ctx = extrator.descrever(e)
        classe, motivo = regras.rotular(e, ctx)
        ctx["motivo"] = motivo
        y = np.zeros((3, 1))
        y[classe] = 1.0
        dados.append((np.array(v, dtype=float).reshape(TAMANHO, 1), y))
        contextos.append(ctx)
    return dados, contextos


def matriz_confusao(rede, dados):
    M = np.zeros((3, 3), dtype=int)
    for x, y in dados:
        M[int(np.argmax(y)), int(np.argmax(rede.frente(x)))] += 1
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=25)
    ap.add_argument("--ocultos", type=int, default=16)
    ap.add_argument("--log", default=str(LOG))
    args = ap.parse_args()

    dados, _ = carregar(args.log)
    print(f"eventos: {len(dados)}")

    contagem = np.zeros(3, dtype=int)
    for _, y in dados:
        contagem[int(np.argmax(y))] += 1
    for i, c in enumerate(regras.CLASSES):
        print(f"  {c:8s} {contagem[i]:6d}  ({100*contagem[i]/len(dados):5.1f}%)")
    maioria = 100 * contagem.max() / len(dados)
    print(f"  chutar sempre a classe maior acertaria {maioria:.1f}%")
    print()

    # Divisao CRONOLOGICA, nao aleatoria: eventos vizinhos no tempo sao quase
    # identicos, e embaralhar antes de dividir colocaria primos do treino
    # dentro do teste. A nota subiria e nao significaria nada.
    corte = int(len(dados) * 0.75)
    tr, te = dados[:corte], dados[corte:]
    print(f"treino {len(tr)} (mais antigos)   teste {len(te)} (mais recentes)")
    print()

    r = Rede([TAMANHO, args.ocultos, 3], semente=SEMENTE, ativacao_saida=Softmax)
    print(r)
    treino.treinar(r, tr, epocas=args.epocas, tamanho_lote=16, taxa=0.5,
                   custo=EntropiaCruzadaCategorica, semente=SEMENTE)

    M = matriz_confusao(r, te)
    total = M.sum()
    print()
    print("matriz de confusao no teste (linha = verdade, coluna = rede)")
    print("            " + "".join(f"{c:>10s}" for c in regras.CLASSES))
    for i, c in enumerate(regras.CLASSES):
        print(f"  {c:9s} " + "".join(f"{M[i, j]:10d}" for j in range(3)))
    print()
    for i, c in enumerate(regras.CLASSES):
        linha = M[i].sum()
        col = M[:, i].sum()
        rec = 100 * M[i, i] / linha if linha else 0.0
        pre = 100 * M[i, i] / col if col else 0.0
        print(f"  {c:8s} encontrou {rec:5.1f}% dos casos   |   quando avisou, acertou {pre:5.1f}%")
    print()
    print(f"  acerto geral: {100 * np.trace(M) / total:.2f}%   (chutar a maior daria {maioria:.1f}%)")

    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps({
        "arquitetura": r.tamanhos,
        "classes": regras.CLASSES,
        "acerto": round(float(100 * np.trace(M) / total), 2),
        "confusao": M.tolist(),
        "camadas": [{"ativacao": c.ativacao.nome,
                     "pesos": [[round(float(v), 4) for v in l] for l in c.pesos],
                     "vies": [round(float(v), 4) for v in c.vies.ravel()]}
                    for c in r.camadas],
    }, separators=(",", ":")), encoding="utf-8")
    print(f"  gravado: {SAIDA.name} ({SAIDA.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
