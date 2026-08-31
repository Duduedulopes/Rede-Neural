# -*- coding: utf-8 -*-
"""
Vocabulario mais largo, a partir dos buracos que o uso real mostrou.

O QUE AS PERGUNTAS DELE REVELARAM

  "vc pode adicionar produtos ao estoque?"    -> estoque_baixo 74%
  "você pode adicionar produtos ao sistema?"  -> alterar_estoque 26%

Nenhuma das duas e ordem. "VOCE PODE fazer X" pergunta o que o gerente e
CAPAZ de fazer — a resposta certa e a mesma de "ajuda", listar o que ele
sabe. Meu corpus de acao so tinha imperativo ("adiciona um produto"), e a
forma interrogativa caiu onde deu.

Nao criei classe nova para isso. `ajuda` ja e a resposta certa, e uma
classe a mais com vinte frases seria o erro que ja medi duas vezes. As
frases de capacidade entram em `ajuda`.

Fica uma ambiguidade real: "pode adicionar um produto pra mim?" e pedido,
nao pergunta. Essa nao se resolve com mais dado — se resolve com o botao,
oferecendo as duas e deixando o dono escolher.
"""
import json, io, unicodedata, sys, random

sys.path.insert(0, "programas")
from gerar_acoes import variar, sem_acento

random.seed(11)

NOVAS = {

# ---- capacidade: "voce consegue...?" -> mesma resposta de ajuda -------
"ajuda": [
    "voce pode adicionar produtos ao estoque?",
    "vc pode adicionar produtos ao sistema?",
    "voce consegue cadastrar produto",
    "da pra voce mudar preco",
    "voce consegue alterar o estoque",
    "vc consegue remover produto",
    "o que voce sabe fazer",
    "o que voce consegue fazer",
    "quais suas funcoes",
    "voce pode mexer no sistema?",
    "voce so responde ou tambem faz?",
    "vc altera as coisas ou so consulta",
    "quais comandos voce aceita",
    "me diz tudo que voce faz",
    "voce tem permissao para alterar",
    "posso pedir pra voce mudar alguma coisa",
    "voce e so consulta?",
    "do que voce e capaz",
    "voce faz alteracao no estoque?",
    "consegue configurar camera?",
],

# ---- duvida_sistema: a pergunta guarda-chuva que faltava --------------
"duvida_sistema": [
    "o que e esse sistema",
    "me explica tudo",
    "explica o projeto",
    "como tudo isso se conecta",
    "quais sao as partes do sistema",
    "do que o sistema e feito",
    "me da uma visao geral",
    "resume o funcionamento pra mim",
    "como os dois sistemas conversam",
    "o que e o smart store",
    "o que faz o autonomous store",
    "qual a diferenca entre os dois sistemas",
    "quem cuida das cameras e quem cuida da venda",
    "como voce sabe das coisas",
    "de onde voce tira os dados",
],

# ---- as consultas que apareceram fracas -------------------------------
"estoque_baixo": [
    "quais produtos preciso repor",
    "o que precisa de reposicao",
    "tem produto perto de acabar",
    "me avisa o que ta baixo",
    "quais itens estao no minimo",
    "lista o que precisa comprar",
    "o que ta faltando no estoque",
    "produtos abaixo do minimo",
],
"estoque": [
    "quantas unidades tem de cada produto",
    "me mostra o estoque completo",
    "quanto tem de agua",
    "qual a quantidade do baly",
    "situacao do estoque",
    "estoque de todos os produtos",
],
"faturamento": [
    "quanto vendemos ate agora",
    "qual o total de vendas",
    "quanto entrou de dinheiro",
    "me da o resumo financeiro",
    "as vendas do dia",
    "quanto a loja faturou",
],
}


def chave(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn").strip()


arq = "dados/perguntas_com_acoes.jsonl"
linhas = [json.loads(l) for l in io.open(arq, encoding="utf-8") if l.strip()]
tem = {chave(l["pergunta"]) for l in linhas}

acrescentadas = 0
with io.open(arq, "a", encoding="utf-8", newline="") as f:
    for intencao, frases in NOVAS.items():
        for base in frases:
            # a MESMA variacao de escrita das outras: se a abreviacao so
            # existisse num canto do corpus, ela viraria o rotulo — foi o
            # erro do "qnt" de ontem
            for v in variar(base, 2):
                if chave(v) in tem:
                    continue
                tem.add(chave(v))
                f.write(json.dumps({"pergunta": v, "intencao": intencao,
                                    "origem": "vocabulario", "base": base},
                                   ensure_ascii=False) + "\n")
                acrescentadas += 1

print(f"acrescentadas: {acrescentadas} frases")

import collections
todas = [json.loads(l) for l in io.open(arq, encoding="utf-8") if l.strip()]
c = collections.Counter(d["intencao"] for d in todas)
print(f"corpus: {len(todas)} frases, {len({d['base'] for d in todas})} bases, "
      f"{len(c)} intencoes")
for k, v in c.most_common(8):
    print(f"   {k:<20} {v}")
