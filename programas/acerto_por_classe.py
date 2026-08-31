# -*- coding: utf-8 -*-
"""
Acerto POR CLASSE no corpus expandido.

A media esconde. "50,1% de acerto" pode ser 31 classes acertando 50%, ou
14 classes acertando 65% e 17 acertando quase nada. A diferenca decide se
o caminho e treinar mais ou mudar o desenho.

E entre as classes novas ha nove que ESCREVEM no banco. Uma intencao que
altera preco tem de ser julgada por um criterio diferente de uma que
mostra estoque: mostrar errado se corrige olhando de novo, gravar errado
nao.
"""
import json, io, sys, numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "programas")
from rede.texto import Vocabulario
from rede.classificador import ClassificadorDeIntencao
from rede.treino import taxa_cosseno
from treinar_intencao import dobras

SEMENTE, EPOCAS, TAXA, DIM, OC, DOBRAS = 42, 80, 1.0, 24, 32, 5

# as que ESCREVEM: erro aqui nao se desfaz olhando de novo
ESCREVEM = {"adicionar_produto", "alterar_preco", "alterar_estoque",
            "remover_produto", "configurar_camera", "configurar_sistema",
            "reiniciar_servico", "confirmar_acao", "cancelar_operacao"}

arq = sys.argv[1] if len(sys.argv) > 1 else "dados/perguntas_expandido.jsonl"
dados = [json.loads(l) for l in io.open(arq, encoding="utf-8") if l.strip()]
perguntas = [d["pergunta"] for d in dados]
rotulos = [d["intencao"] for d in dados]
intencoes = sorted(set(rotulos))
n_int = {n: i for i, n in enumerate(intencoes)}

g = np.random.default_rng(SEMENTE)
grupos = dobras(rotulos, DOBRAS, g)

certos = {n: 0 for n in intencoes}
totais = {n: 0 for n in intencoes}
# quantas vezes a rede DISSE cada classe, e quantas dessas estavam certas
disse = {n: 0 for n in intencoes}
disse_certo = {n: 0 for n in intencoes}

for d in range(DOBRAS):
    teste_i = set(grupos[d])
    treino_i = [i for i in range(len(dados)) if i not in teste_i]
    voc = Vocabulario([perguntas[i] for i in treino_i])
    exemplos = [(voc.indices(perguntas[i]), n_int[rotulos[i]]) for i in treino_i]

    c = ClassificadorDeIntencao(len(voc), intencoes, dimensao=DIM,
                                ocultos=OC, semente=SEMENTE)
    gg = np.random.default_rng(SEMENTE)
    for epoca in range(EPOCAS):
        t = taxa_cosseno(TAXA, epoca, EPOCAS)
        ordem = gg.permutation(len(exemplos))
        for i in range(0, len(exemplos), 16):
            c.passo([exemplos[j] for j in ordem[i:i + 16]], t)

    for i in grupos[d]:
        p = np.asarray(c.prever(voc.indices(perguntas[i]))).ravel()
        prev = intencoes[int(np.argmax(p))]
        verdade = rotulos[i]
        totais[verdade] += 1
        disse[prev] += 1
        if prev == verdade:
            certos[verdade] += 1
            disse_certo[prev] += 1

print(f"{arq}: {len(dados)} frases, {len(intencoes)} intencoes\n")
print(f"  ACERTO GERAL  {100*sum(certos.values())/len(dados):.1f}%\n")
print("  classe                 treino  encontrou  quando disse, acertou")
print("  " + "-" * 66)

grupos_saida = [("--- as que SO CONSULTAM ---", lambda n: n not in ESCREVEM),
                ("--- as que ESCREVEM no sistema ---", lambda n: n in ESCREVEM)]
for titulo, filtro in grupos_saida:
    print(f"\n  {titulo}")
    for n in sorted(intencoes, key=lambda x: -totais[x]):
        if not filtro(n):
            continue
        rec = 100 * certos[n] / totais[n] if totais[n] else 0
        prec = 100 * disse_certo[n] / disse[n] if disse[n] else float("nan")
        prec_txt = f"{prec:5.0f}%" if disse[n] else "  nunca"
        alarme = "  <-- nunca encontra" if rec == 0 else ""
        print(f"  {n:<22} {totais[n]:4d}   {rec:5.0f}%     {prec_txt}{alarme}")

novas = [n for n in intencoes if totais[n] <= 5]
if novas:
    enc = sum(certos[n] for n in novas)
    tot = sum(totais[n] for n in novas)
    print(f"\n  AS {len(novas)} CLASSES NOVAS (3-4 frases cada):")
    print(f"    {enc} acertos em {tot} frases = {100*enc/tot:.0f}%")
    escrevem_ok = sum(certos[n] for n in novas if n in ESCREVEM)
    escrevem_tot = sum(totais[n] for n in novas if n in ESCREVEM)
    print(f"    das que ESCREVEM: {escrevem_ok} de {escrevem_tot}")
