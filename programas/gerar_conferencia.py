"""Gera os casos de conferencia A PARTIR DO MODELO QUE ESTA GRAVADO. Programa.

    python programas/gerar_conferencia.py

POR QUE ISTO E UM PROGRAMA, E NAO UM PEDACO DO TREINO

Porque eu ja errei assim: gerei os casos com um modelo, retreinei com outra
configuracao, e os casos ficaram para tras. A conferencia entre Python e C#
acusou 18 divergencias — e o errado nao era o porte, era o arquivo velho.

    Arquivo derivado de modelo tem que ser REGERADO do modelo, e nao
    lembrado de gerar.

Rodar isto depois de todo treino e barato. Esquecer custa uma investigacao
inteira atras de um defeito que nao existe.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede.classificador import ClassificadorDeIntencao  # noqa: E402
from rede.texto import pedacos  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "modelos" / "intencao.json"
SAIDA = RAIZ / "modelos" / "conferencia.json"

FRASES = [
    "quantas pessoas estao na loja agora", "o que esta acabando",
    "quanto faturamos hoje", "quanto custa o baly", "as cameras estao ok",
    "o que tem no carrinho", "oi bom dia", "qual a cor do ceu",
    "como funciona o rfid", "vendemos mais que ontem", "o que mais sai",
    "ajuda", "quanto q eu faturei hj", "cade os produtos acabando",
    "tem quantas pessoa ai dentro",
    # Casos de borda: se o C# normalizar diferente, e aqui que aparece.
    "QUANTAS PESSOAS!!!", "  faturmento  ", "xyzzy",
    "câmeras estão boas?", "quanto   custa    a   agua",
]


def main():
    m = json.loads(MODELO.read_text(encoding="utf-8"))
    indice = {p: i for i, p in enumerate(m["pecas"])}

    c = ClassificadorDeIntencao(len(m["pecas"]), m["intencoes"],
                                dimensao=m["dimensao"],
                                ocultos=len(m["camadas"][0]["pesos"]), semente=0)
    c.tabela = np.array(m["tabela"])
    for camada, d in zip(c.rede.camadas, m["camadas"]):
        camada.pesos = np.array(d["pesos"])
        camada.vies = np.array(d["vies"]).reshape(-1, 1)

    casos = []
    for f in FRASES:
        idx = [indice[p] for p in pedacos(f) if p in indice] or [0]
        p = c.prever(idx).ravel()
        k = int(np.argmax(p))
        casos.append({"pergunta": f, "intencao": m["intencoes"][k],
                      "confianca": round(float(p[k]), 6), "n_pecas": len(idx)})
        print(f"  {p[k]*100:5.1f}%  {m['intencoes'][k]:16s} ({len(idx):3d} pecas)  \"{f}\"")

    SAIDA.write_text(json.dumps(casos, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(f"{len(casos)} casos -> {SAIDA.name}, gerados do modelo com "
          f"limiar {m.get('limiar')}")


if __name__ == "__main__":
    main()
