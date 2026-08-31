# -*- coding: utf-8 -*-
"""
AS FRASES QUE NAO PODEM QUEBRAR DE NOVO. Programa.

    python programas/conferir_guardas.py

POR QUE ISTO EXISTE

Tres vezes seguidas, num unico dia, o mesmo erro voltou com outra roupa:

    "por favor"  so no lado do sim  ->  "para por favor" virou SIM  (99,4%)
    "muda ..."   posto no cancelar  ->  "muda o preco da agua" caiu de
                                        99,5% para 73,5%
    "pode"       11 vezes no sim    ->  "pode parar" virou SIM  (99,8%)

Nenhum foi achado por raciocinio: os tres apareceram porque eu medi.
E cada um foi CAUSADO pela correcao do anterior — mexer no corpus de um
lado desloca o outro, e nao da para prever qual.

Uma lista de guardas troca sorte por rotina. Ela nao impede o erro; ela
impede que ele passe DESPERCEBIDO, que e a parte que custa caro.

Cada linha diz uma de duas coisas:

    precisa_ser    a rede tem de acertar esta intencao, e com confianca
                   suficiente para o sistema agir sozinho
    nao_pode_ser   a rede pode errar aqui, MENOS para este lado

A distincao importa. "pode parar" nao precisa dar `cancelar_operacao` —
se der `alterar_preco`, o C# na hora da confirmacao nao grava e
repergunta, que e seguro. O que nao pode e dar `confirmar_acao`, porque
ai grava. A guarda cobra o que e perigoso, nao o que e bonito.
"""
import json, io, sys, unicodedata
import numpy as np

MOD = "modelos/intencao.json"
GUA = "dados/guardas_confirmacao.jsonl"

M = json.load(io.open(MOD, encoding="utf-8"))
idx = {p: i for i, p in enumerate(M["pecas"])}
tab = np.array(M["tabela"])
c0, c1 = M["camadas"]
W0, b0 = np.array(c0["pesos"]), np.array(c0["vies"]).reshape(-1, 1)
W1, b1 = np.array(c1["pesos"]), np.array(c1["vies"]).reshape(-1, 1)
LIM = M["limiar"]
SIM = M.get("limiar_confirmacao", 1.0)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def tri(p):
    c = "<" + p + ">"
    return [c] if len(c) <= 3 else [c[i:i + 3] for i in range(len(c) - 2)]


def sig(z):
    return np.where(z >= 0, 1/(1+np.exp(-np.abs(z))),
                    np.exp(-np.abs(z))/(1+np.exp(-np.abs(z))))


def classificar(t):
    ps = norm(t).split()
    ids = [idx[p] for p in ps + [g for p in ps for g in tri(p)] if p in idx]
    if not ids:
        return ("(nenhuma peça conhecida)", 0.0)
    x = tab[ids].mean(axis=0).reshape(-1, 1)
    z = W1 @ sig(W0 @ x + b0) + b1
    e = np.exp(z - z.max())
    p = (e / e.sum()).ravel()
    i = int(p.argmax())
    return (M["intencoes"][i], float(p[i]))


print(f"modelo: limiar {LIM}   corte do sim {SIM}\n")
falhas = []
for L in io.open(GUA, encoding="utf-8"):
    L = L.strip()
    if not L:
        continue
    g = json.loads(L)
    nome, conf = classificar(g["frase"])

    if "precisa_ser_no_topo" in g:
        # Terceira forma de cobranca: a intencao certa tem de ser o PRIMEIRO
        # palpite, sem exigir que passe do corte. Serve para a frase cujo
        # valor esta em qual lado ela cai, nao em quanta confianca tem —
        # "faz por favor" so precisa nao ser lida como cancelamento; ficar
        # abaixo do corte de gravacao apenas re-pergunta, que e seguro.
        preciso = g["precisa_ser_no_topo"]
        ruim = nome != preciso
        alvo = f"{preciso} em 1o"
    elif "nao_pode_ser" in g:
        proibido = g["nao_pode_ser"]
        # So e falha se a rede fosse AGIR nisso. Errar abaixo do corte e
        # seguro: o C# repergunta em vez de gravar.
        corte = SIM if proibido == "confirmar_acao" else LIM
        ruim = nome == proibido and conf >= corte
        alvo = f"nunca {proibido}"
    else:
        preciso = g["precisa_ser"]
        # ── O QUE SE EXIGE DEPENDE DE COMO O SISTEMA USA A RESPOSTA ────
        #
        # Para o sim e o nao, a rede decide sozinha: tem de passar do
        # corte, senao nada acontece.
        #
        # Para uma ORDEM, nao. Abaixo do limiar o gerente oferece os tres
        # melhores palpites, e o clique entra no mesmo fluxo de
        # confirmacao — foi feito assim de proposito, porque ordem abaixo
        # do limiar e o caso comum, nao a excecao. Entao o que a guarda
        # precisa cobrar e que a intencao certa seja o PRIMEIRO palpite,
        # isto e, o primeiro botao. Exigir 97% de uma ordem seria cobrar
        # do modelo uma coisa que a tela ja resolve.
        if preciso in ("confirmar_acao", "cancelar_operacao"):
            corte = SIM if preciso == "confirmar_acao" else LIM
            ruim = not (nome == preciso and conf >= corte)
            alvo = f"{preciso} >= {corte}"
        else:
            ruim = nome != preciso
            alvo = f"{preciso} em 1o (botao)"

    if ruim:
        falhas.append((g["frase"], alvo, nome, conf, g["por_que"]))
    print(f"  {'FALHOU' if ruim else '  ok  '}  {g['frase']:<34} "
          f"{nome:<20} {conf:6.1%}   ({alvo})")

print()
if falhas:
    print(f"  {len(falhas)} GUARDA(S) QUEBRADA(S) — nao publique este modelo:\n")
    for f, alvo, nome, conf, por_que in falhas:
        print(f'   "{f}"')
        print(f"      esperado: {alvo}")
        print(f"      deu:      {nome} a {conf:.1%}")
        print(f"      importa porque: {por_que}\n")
    sys.exit(1)

print(f"  as {sum(1 for _ in io.open(GUA, encoding='utf-8') if _.strip())} guardas passaram.")
