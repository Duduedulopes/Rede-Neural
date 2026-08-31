"""Le o que o Eduardo marcou como engano e resume. Programa.

    python programas/revisar_correcoes.py

POR QUE ESTE PROGRAMA EXISTE ANTES DE HAVER CORRECOES

Porque a decisao do que fazer com elas precisa ser tomada olhando dado real,
e nao imaginado. Com dez correcoes na mao da para ver se o alarme erra sempre
no mesmo tipo de evento — e ai o conserto talvez nem seja rede neural, e sim
um limiar por tipo.

    Antes de treinar em cima de uma correcao, e preciso saber se ela e
    sistematica ou avulsa. Correcao avulsa e ruido; correcao sistematica e
    informacao.

O QUE UMA CORRECAO NAO E

Nao e "a rede errou a conta". A surpresa esta certa: aquele evento era mesmo
improvavel. A correcao diz outra coisa — que IMPROVAVEL NAO E O MESMO QUE
IMPORTANTE, e so quem administra a loja sabe a diferenca.

Por isso o previsor NAO e retreinado com estas linhas. Elas alimentam a
decisao de o que interrompe alguem, que e um problema separado.
"""

import json
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "dados" / "correcoes.jsonl"


def ler(caminho):
    if not caminho.exists():
        return []
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            saida.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return saida


def main():
    correcoes = ler(ARQUIVO)

    if not correcoes:
        print("Nenhuma correcao ainda.")
        print()
        print(f"  arquivo: {ARQUIVO}")
        print("  Rode o painel, deixe os eventos passarem e marque 'discordo'")
        print("  nos avisos que nao mereciam interromper ninguem.")
        print()
        print("  Enquanto este arquivo estiver vazio, o alarme decide sozinho")
        print("  por percentil — o que e honesto, e nao e o seu julgamento.")
        return

    print(f"{len(correcoes)} correcoes em {ARQUIVO.name}")
    print()

    por_token = Counter(c.get("token", "?") for c in correcoes)
    por_nivel = Counter(c.get("nivel", "?") for c in correcoes)
    surpresas = [c.get("surpresa", 0.0) for c in correcoes]

    print("  por token marcado como engano:")
    for t, n in por_token.most_common(10):
        print(f"    {n:4d}  {t}")
    print()
    print("  por nivel que o alarme deu:", dict(por_nivel))
    print(f"  surpresa das correcoes: menor {min(surpresas):.2f}   "
          f"maior {max(surpresas):.2f}   media {sum(surpresas)/len(surpresas):.2f}")
    print()

    dominante, quantas = por_token.most_common(1)[0]
    fracao = quantas / len(correcoes)
    if len(correcoes) < 8:
        print("  Poucas correcoes para concluir qualquer coisa. Continue marcando.")
    elif fracao >= 0.5:
        print(f"  SISTEMATICO: {100*fracao:.0f}% das correcoes sao do mesmo token")
        print(f"  ({dominante}). Isto nao pede rede neural — pede um limiar")
        print("  proprio para este tipo de evento. Conserto de uma linha.")
    else:
        print("  ESPALHADO: as correcoes nao se concentram num tipo so.")
        print("  Aqui sim vale treinar um decisor com estas linhas como rotulo,")
        print("  porque a regra que separa 'improvavel' de 'importante' nao e")
        print("  simples o bastante para caber num limiar.")


if __name__ == "__main__":
    main()
