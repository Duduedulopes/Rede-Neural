# -*- coding: utf-8 -*-
"""
Recalibra o limiar CONTANDO COM O BOTAO DE DESAMBIGUACAO.

Ate hoje, ficar abaixo do limiar era um beco sem saida: o gerente dizia
"nao tenho certeza" e a conversa morria ali. Nessa situacao, limiar alto
custa caro — cada abstencao e um atendimento perdido.

Com o botao, abaixo do limiar deixou de ser beco: vira "voce quis dizer X
ou Y?", o Eduardo clica, ele responde na hora E o clique fica gravado como
rotulo humano. O custo da abstencao despencou.

Entao a pergunta certa nao e mais "qual limiar acerta mais quando
responde", e sim:

    quantas perguntas terminam certas — respondidas direto OU
    resolvidas em um clique — e quantas terminam erradas em silencio?

Um erro que passa com 91% de confianca e pior que tres abstencoes, porque
o Eduardo nao tem como saber que aquilo estava errado.
"""
import json, io, sys, numpy as np
from collections import Counter

sys.path.insert(0, ".")
from rede.texto import Vocabulario
from rede.classificador_duplo import ClassificadorDuplo as ClassificadorDeIntencao
from rede.treino import taxa_cosseno

SEMENTE, EPOCAS, TAXA, DIM, OC, DOBRAS = 42, 80, 1.0, 24, 32, 5
N_BOTOES = 3


# AS MESMAS DOBRAS DO TREINO, importadas em vez de reescritas.
#
# Eu tinha escrito uma versao propria aqui e ela deu 65,4% onde o treino
# dava 68,5% — dois numeros para a MESMA medida, por diferenca de sorteio.
# Numero que discorda de si mesmo nao serve para decidir nada.
sys.path.insert(0, "programas")
from treinar_intencao import dobras as dobras_estratificadas, dobras_por_base


# O CORPUS VEM DA LINHA DE COMANDO.
#
# Havia tres arquivos de corpus no projeto e o caminho fixo aqui apontava
# para um deles enquanto o modelo tinha sido treinado com outro. Calibrar
# um modelo com um corpus que nao e o dele produz um limiar que nao vale
# para nada — e sem aviso nenhum.
CORPUS = sys.argv[1] if len(sys.argv) > 1 else "dados/perguntas_fundido.jsonl"
dados = [json.loads(l) for l in io.open(CORPUS, encoding="utf-8") if l.strip()]
perguntas = [d["pergunta"] for d in dados]
rotulos = [d["intencao"] for d in dados]
intencoes = sorted(set(rotulos))
n_int = {n: i for i, n in enumerate(intencoes)}

g = np.random.default_rng(SEMENTE)
# O LIMIAR TAMBEM PRECISA DAS DOBRAS AGRUPADAS.
#
# Calibrar com dobra vazada da um limiar otimista: a rede parece mais
# confiante do que e, entao o corte parece seguro mais baixo do que
# deveria. Limiar errado para baixo e pior que nao ter limiar — ele
# promete uma precisao que nao existe.
bases = [d.get("base", d["pergunta"]) for d in dados]
if len(set(bases)) < len(dados):
    grupos = dobras_por_base(bases, rotulos, DOBRAS, g)
    print(f"dobras agrupadas: {len(set(bases))} bases para {len(dados)} frases\n")
else:
    grupos = dobras_estratificadas(rotulos, DOBRAS, g)

tons = sorted({d.get("estado_emocional", "neutro") for d in dados})
nt = {n: i for i, n in enumerate(tons)}

# guarda, para cada frase de teste, a distribuicao inteira
todas = []
for d in range(DOBRAS):
    teste_i = set(grupos[d])
    treino_i = [i for i in range(len(dados)) if i not in teste_i]
    voc = Vocabulario([perguntas[i] for i in treino_i])
    exemplos = [(voc.indices(perguntas[i]), n_int[rotulos[i]],
                 nt[dados[i].get("estado_emocional","neutro")]) for i in treino_i]

    c = ClassificadorDeIntencao(len(voc), intencoes, tons, dimensao=DIM,
                                ocultos=OC, semente=SEMENTE, peso_tom=0.5)
    gg = np.random.default_rng(SEMENTE)
    for epoca in range(EPOCAS):
        t = taxa_cosseno(TAXA, epoca, EPOCAS)
        ordem = gg.permutation(len(exemplos))
        for i in range(0, len(exemplos), 16):
            c.passo([exemplos[j] for j in ordem[i:i + 16]], t)

    for i in grupos[d]:
        p = np.asarray(c.prever(voc.indices(perguntas[i]))).ravel()
        todas.append((p, n_int[rotulos[i]]))

n = len(todas)

# ---- o que o botao consegue: a resposta certa esta entre os 3 primeiros? ----
print(f"{CORPUS}\n{n} previsoes em validacao cruzada, {len(intencoes)} intencoes\n")
print("  ACERTO ACUMULADO POR POSICAO (o que o botao tem a oferecer)")
for k in (1, 2, 3, 4):
    acc = sum(1 for p, alvo in todas if alvo in np.argsort(p)[::-1][:k])
    print(f"    entre os {k} primeiros   {100*acc/n:5.1f}%")

topo3 = sum(1 for p, alvo in todas if alvo in np.argsort(p)[::-1][:N_BOTOES]) / n
print(f"\n  Ou seja: quando ela erra o primeiro, a resposta certa ainda esta")
print(f"  nos {N_BOTOES} botoes {100*topo3:.1f}% das vezes.\n")

# ---- a conta que importa ----
print("  limiar  responde  |  termina certo  termina ERRADO  precisa clicar")
print("          direto    |   (direto+clique)  em silencio    e nao resolve")
print("  " + "-" * 68)

linhas = []
for limiar in [0.0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.88, 0.90, 0.92, 0.95, 0.97]:
    respondeu = certo_direto = errado_calado = resolve_clique = perdido = 0
    for p, alvo in todas:
        ordem = np.argsort(p)[::-1]
        if p[ordem[0]] >= limiar:
            respondeu += 1
            if ordem[0] == alvo: certo_direto += 1
            else: errado_calado += 1
        else:
            if alvo in ordem[:N_BOTOES]: resolve_clique += 1
            else: perdido += 1
    bom = (certo_direto + resolve_clique) / n
    print(f"   {limiar:4.2f}    {100*respondeu/n:5.1f}%   |     {100*bom:5.1f}%          "
          f"{100*errado_calado/n:5.1f}%          {100*perdido/n:5.1f}%")
    linhas.append((limiar, respondeu / n, bom, errado_calado / n))

# O CRITERIO — e a primeira versao dele estava errada.
#
# Eu tinha posto "minimize o erro silencioso". O resultado foi limiar 0,97,
# respondendo direto em 7,6% das perguntas: quase tudo virava clique. Faz
# sentido e e inutil — minimizar UMA coisa sozinha sempre leva ao extremo
# dela.
#
# O criterio honesto tem duas partes. O acerto final satura: passado certo
# ponto, subir o limiar nao acerta mais nada, so troca resposta direta por
# clique. Entao:
#
#     o MENOR limiar que ainda chega a 99% do teto de acerto
#
# Menor porque responder direto e melhor que pedir clique; 99% do teto
# porque abrir mao de um terco de ponto de acerto para poupar um clique em
# cada tres perguntas e um bom negocio, e abrir mao de cinco pontos nao e.
teto = max(b for _, _, b, _ in linhas)
alvo = 0.99 * teto
candidatos = [x for x in linhas if x[2] >= alvo]
limiar, cob, bom, err = min(candidatos, key=lambda x: x[0])
print(f"\n  teto de acerto (limiar irrelevante acima disso): {100*teto:.1f}%")
print(f"  MENOR LIMIAR QUE CHEGA A 99% DO TETO: {limiar:.2f}")
print(f"    responde direto em {100*cob:.1f}% das perguntas")
print(f"    termina certo (direto ou num clique) em {100*bom:.1f}%")
print(f"    responde errado sem avisar em {100*err:.1f}%")

# ---- grava no modelo, junto dos pesos ----
arq = "modelos/intencao.json"
m = json.load(io.open(arq, encoding="utf-8"))
p_direta = sum(1 for p, alvo in todas
               if p.max() >= limiar and np.argmax(p) == alvo)
n_resp = sum(1 for p, alvo in todas if p.max() >= limiar)
m["limiar"] = round(float(limiar), 2)
m["botoes"] = N_BOTOES

# ══════════════════════════════════════════════════════════════════════
#  O CORTE DO "SIM", QUE E OUTRA DECISAO E POR ISSO TEM OUTRO NUMERO
#
#  `limiar` responde "posso RESPONDER?". Errar mostra um numero errado, e
#  a pessoa confere.
#  Este responde "posso GRAVAR?". Errar escreve no banco uma alteracao
#  que o Chefe recusou.
#
#  POR QUE ELE PRECISA SER CALCULADO AQUI, e nao posto na mao depois:
#  eu tinha escrito o campo direto no JSON uma vez. O treino seguinte
#  regerou o arquivo e levou o campo junto. O C# caiu no padrao
#  fail-closed (corte = 1,0, inalcancavel) e NENHUM "sim" gravava mais.
#  O teste pegou; se nao tivesse pegado, o gerente teria virado um
#  sistema que pergunta e nunca faz.
#
#  Numero medido nao sobrevive fora do programa que o mede. Quinta vez
#  neste projeto.
# ══════════════════════════════════════════════════════════════════════
i_sim = intencoes.index("confirmar_acao") if "confirmar_acao" in intencoes else None
if i_sim is not None:
    print("\n  O CORTE DO \"SIM\" (so `confirmar_acao` grava)")
    print("  corte   reconhece o sim   grava o que NAO era sim")
    # ── CONTRA QUE POPULACAO SE MEDE ISTO ─────────────────────────────
    #
    # Medir contra o corpus INTEIRO da um numero pessimista e inutil: ele
    # conta "salve", "fala ai", "bom trabalho" — frases que sao lidas como
    # sim, sim, mas que ninguem digita respondendo a "posso alterar o
    # preco?". Com elas na conta, nenhum corte fica limpo e o criterio
    # devolve 0,999, que so reconhece um quinto dos sins de verdade. Um
    # gerente que pergunta e quase nunca aceita a resposta e pior que um
    # gerente sem confirmacao.
    #
    # A populacao certa e a que aparece NAQUELE MOMENTO: o Chefe acabou de
    # ler um resumo e vai responder. Ele escreve um sim, um nao, uma
    # correcao, ou repete a ordem de outro jeito. Essas quatro coisas sao
    # `confirmar_acao`, `cancelar_operacao` e as intencoes de acao.
    #
    # Uma saudacao perdida ali continua sendo lida como sim — mas ela nao
    # chega, e desenhar o corte para ela custa o sistema inteiro.
    NA_HORA = {"confirmar_acao", "cancelar_operacao", "alterar_preco",
               "alterar_estoque", "adicionar_produto", "remover_produto"}
    hora = [(p, a) for p, a in todas if intencoes[a] in NA_HORA]
    eram = [(p, a) for p, a in hora if a == i_sim]
    print(f"  (medido nas {len(hora)} frases que aparecem numa confirmacao,")
    print(f"   nao nas {len(todas)} do corpus inteiro)")

    escolhido = None
    for corte in [0.95, 0.97, 0.98, 0.99, 0.995, 0.998, 0.999]:
        pega = sum(1 for p, a in eram if np.argmax(p) == i_sim and p.max() >= corte)
        falso = sum(1 for p, a in hora
                    if a != i_sim and np.argmax(p) == i_sim and p.max() >= corte)
        print(f"  {corte:5.3f}   {pega:4d}/{len(eram):<10d}      {falso:2d}"
              f"   ({100*falso/len(hora):.2f}%)")
        if falso / len(hora) <= 0.01 and escolhido is None:
            escolhido = corte

    # ── POR QUE 1%, E NAO ZERO ────────────────────────────────────────
    #
    # "Zero falsos" parece a exigencia responsavel, e nao e: quem manda no
    # numero passa a ser o pior exemplo do corpus. Os que sobravam eram
    # todos corrupcao que EU gerei — "pode paar" de "pode parar", "nrmm"
    # de "nem", "e outa coisa" de "e outra coisa". Perseguir zero neles
    # empurrava o corte para 0,999, onde so 65 dos 356 sins passam: quatro
    # de cada cinco vezes que o Chefe aceita, o gerente pergunta de novo.
    # Um gerente assim ninguem usa, e um gerente que ninguem usa nao
    # protege nada.
    #
    # A conta dos dois erros, que e a mesma do limiar geral:
    #
    #     falso sim   grava errado — MAS a resposta diz o que gravou
    #                 ("de R$ 3,50 para R$ 5,50"), entao o Chefe ve na
    #                 hora e manda desfazer
    #     nao aceitar o sim   nao grava nada, e ele repete a palavra
    #
    # O primeiro e pior, e por isso o corte e alto. Mas ele nao e
    # catastrofico nem silencioso, e por isso nao vale pagar o sistema
    # inteiro por ele. 1% na populacao da hora e a folga que sobra depois
    # de tirar o ruido que eu mesmo inventei.
    # ── E NUNCA MAIS FROUXO QUE O LIMIAR GERAL ────────────────────────
    #
    # A conta acima devolveu 0,95 nesta rodada, contra um limiar geral de
    # 0,97. Aceitar isso seria dizer que GRAVAR exige menos certeza que
    # RESPONDER, o que e o avesso da razao de existir dos dois numeros.
    #
    # O piso e estrutural, nao um ajuste: escrever no banco nunca custa
    # menos que falar. Se a medida pedir MAIS que o limiar geral, ela
    # ganha — e ai o corte sobe sozinho, que e o comportamento certo
    # quando o corpus piora.
    bruto = escolhido if escolhido is not None else 0.999
    m["limiar_confirmacao"] = max(bruto, m["limiar"])
    print(f"  corte pela taxa: {bruto}   piso (limiar geral): {m['limiar']}")
    print(f"  CORTE DO SIM: {m['limiar_confirmacao']}")
m["medido"] = {
    "epocas": EPOCAS,
    "corpus": len(dados),
    "intencoes": len(intencoes),
    "acerto_validacao_cruzada": round(sum(1 for p, a in todas if np.argmax(p) == a) / n, 4),
    "acerto_nos_botoes": round(float(topo3), 4),
    "precisao_no_limiar": round(p_direta / n_resp, 4) if n_resp else None,
    "cobertura_no_limiar": round(n_resp / n, 4),
    "termina_certo_com_clique": round(float(bom), 4),
    "erro_silencioso": round(float(err), 4),
}
io.open(arq, "w", encoding="utf-8", newline="").write(
    json.dumps(m, ensure_ascii=False, separators=(",", ":")))
print(f"\n  gravado em {arq}:")
for k, v in m["medido"].items():
    print(f"    {k:28} {v}")
print(f"    {'limiar':28} {m['limiar']}")
print(f"    {'limiar_confirmacao':28} {m['limiar_confirmacao']}")
