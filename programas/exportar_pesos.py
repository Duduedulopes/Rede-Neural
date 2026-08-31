"""Treina e exporta a rede para JSON, para a interface consumir. Programa.

    python programas/exportar_pesos.py --epocas 10

POR QUE JSON E NAO O OBJETO PYTHON

A interface roda no navegador. Ela nao importa Python — ela recebe numeros e
refaz a MESMA conta em JavaScript. Duas implementacoes da mesma matematica,
e e por isso que a interface e uma verificacao a mais: se o navegador
discordar do Python, uma das duas esta errada.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede import dados, treino  # noqa: E402
from rede.ativacao import Softmax  # noqa: E402
from rede.custo import EntropiaCruzadaCategorica  # noqa: E402
from rede.rede import Rede  # noqa: E402

SEMENTE = 42
SAIDA = Path(__file__).resolve().parents[1] / "modelos" / "rede_mnist.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=10)
    ap.add_argument("--ocultos", type=int, default=30)
    ap.add_argument("--exemplos", type=int, default=24)
    args = ap.parse_args()

    treinamento, _, teste = dados.carregar_mnist()
    r = Rede([784, args.ocultos, 10], semente=SEMENTE, ativacao_saida=Softmax)

    print(f"treinando {r} por {args.epocas} epocas...")
    treino.treinar(r, treinamento, epocas=args.epocas, tamanho_lote=10,
                   taxa=0.5, custo=EntropiaCruzadaCategorica, semente=SEMENTE)

    certos = treino.acertos(r, teste)
    acerto = 100 * certos / len(teste)
    print(f"  teste: {acerto:.2f}%")

    # Exemplos de teste para a interface: alguns de cada digito, em uint8.
    exemplos = []
    por_digito = {d: 0 for d in range(10)}
    limite = max(1, args.exemplos // 10)
    for x, y in teste:
        d = int(np.argmax(y))
        if por_digito[d] >= limite:
            continue
        por_digito[d] += 1
        exemplos.append({
            "rotulo": d,
            "pixels": [int(round(v * 255)) for v in x.ravel()],
        })
        if len(exemplos) >= args.exemplos:
            break

    modelo = {
        "arquitetura": r.tamanhos,
        "acerto_teste": round(acerto, 2),
        "epocas": args.epocas,
        "semente": SEMENTE,
        "parametros": r.n_parametros,
        "camadas": [
            {
                "ativacao": c.ativacao.nome,
                "pesos": [[round(float(v), 4) for v in linha] for linha in c.pesos],
                "vies": [round(float(v), 4) for v in c.vies.ravel()],
            }
            for c in r.camadas
        ],
        "exemplos": exemplos,
    }

    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(modelo, separators=(",", ":")), encoding="utf-8")
    print(f"  gravado: {SAIDA}  ({SAIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
