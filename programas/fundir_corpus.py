# -*- coding: utf-8 -*-
"""
JUNTA O CORPUS DA OUTRA IA COM O NOSSO, SEM PERDER NADA. Programa.

    python programas/fundir_corpus.py

O QUE ESTAVA ERRADO EM SIMPLESMENTE TROCAR UM PELO OUTRO

O corpus dela nasceu de `perguntas.jsonl`, que e a versao de 593 frases.
Comparado com o que esta em producao, faltam DEZESSEIS intencoes:

    alterar_preco    alterar_estoque    adicionar_produto
    confirmar_acao   cancelar_operacao  remover_produto
    configurar_camera  configurar_sistema  reiniciar_servico
    escolher_solucao   entrada_loja        pagamento
    meu_carrinho       analise_combinada   logs_sistema
    status_api

Treinar so com o dela deixaria o gerente sem saber receber ordem nenhuma
— sem "muda o preco da agua", sem o "sim" que grava, sem cancelamento.
Nao e uma troca, e uma FUSAO.

O CAMPO `base`, QUE O DELA NAO TEM

Ela gera cada frase emocional assim:

    f"{prefixo}, {frase}"      "urgente, quantos itens tem"
    f"{frase}, {sufixo}"       "quantos itens tem, valeu"
    f"{interjeicao}! {frase}"  "nossa! quantos itens tem"

Sao 40 variacoes do mesmo radical. Sem o campo `base`, a validacao
cruzada poe umas no treino e outras no teste, e a rede e avaliada por
desfazer o molde — nao por entender o Eduardo. Ja medimos isso neste
projeto: 27 pontos de nota falsa.

Aqui a base nao e adivinhada por regex: o programa IMPORTA as tabelas
dela e reconstroi a geracao, entao cada variacao sabe exatamente de qual
radical veio. Reconstruir e mais seguro que desmontar.

O ROTULO DE TOM NAS NOSSAS FRASES

O nosso corpus nao tem `estado_emocional` — ele nunca precisou. Para a
saida de tom aprender, toda frase precisa de rotulo.

Uso o `detectar_estado` dela para rotular as nossas. Isso e legitimo, e e
diferente de usar palavra-chave na hora de responder: aqui a regra so
PRODUZ O DADO, e quem decide continua sendo a rede, que generaliza para
frases que a regra nao pega.

E honesto dizer o limite: um rotulo vindo de regra ensina, no maximo, a
regra — mais o que os vetores de palavra conseguirem generalizar em cima.
Tom que a regra nao enxerga, a rede tambem nao vai aprender. Por isso
cada linha leva `tom_origem`, para dar para medir depois quanto do acerto
veio de frase rotulada a mao e quanto veio de regra.
"""
import io, json, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "programas"))

import gerar_corpus_inteligente as dela

# ══════════════════════════════════════════════════════════════════════
#  TODAS AS ENTRADAS, DECLARADAS.
#
#  ESTE ARQUIVO MENTIA. Ele dizia que o corpus vinha de dois arquivos —
#  o nosso e o dela. Vinha de cinco. `perguntas_repor.jsonl`,
#  `perguntas_sobre_sistema.jsonl` e as 88 frases de `sim_educado` foram
#  entrando por fora, uma execucao de cada vez, e nunca voltaram para ca.
#
#  Isso ficou dois dias sem incomodar ninguem, porque o
#  `perguntas_fundido.jsonl` no disco estava certo. Ate alguem rodar a
#  fusao de novo: o arquivo foi refeito a partir das duas entradas
#  declaradas e `repor_estoque` — 198 frases, a intencao que separa somar
#  de definir e que existe por causa de um bug que quase apagou estoque —
#  simplesmente sumiu. 39 intencoes viraram 38 sem uma linha de erro.
#
#  Um pipeline que nao reproduz o proprio resultado nao e pipeline, e
#  sorte. As cinco entradas agora estao aqui, e no fim do programa ha uma
#  conferencia contra o fundido anterior: se alguma intencao encolher, o
#  programa reclama em vez de deixar passar.
# ══════════════════════════════════════════════════════════════════════
D = RAIZ / "dados"

# A ORDEM DECIDE QUEM GANHA, e nao e detalhe.
#
# Em frase repetida, quem chega primeiro fica com o rotulo. Entao as
# CORRECOES vem antes do corpus que elas corrigem.
#
# "chegaram mais 20 chocolates" existe nos dois: em
# `perguntas_confirmacao.jsonl` com o rotulo velho `alterar_estoque`, de
# quando uma intencao so carregava somar, definir e tirar; e em
# `perguntas_repor.jsonl` com `repor_estoque`, que foi a correcao daquele
# bug — o mesmo que quase apagou estoque ao ler "adicione 1 unidade" como
# "deixe 1 unidade".
#
# Com a ordem trocada, 18 frases voltaram ao rotulo antigo e a guarda
# quebrou: 86% para `alterar_estoque`. O arquivo velho nao foi limpo de
# proposito — ele e o registro do que foi gerado. Quem corrige e a ordem.
NOSSAS = [
    D / "perguntas_repor.jsonl",         # CORRECAO: somar contra definir
    D / "perguntas_novas.jsonl",         # listar_produtos, furo_sistema, relatorio_periodo
    D / "perguntas_sobre_sistema.jsonl", # sobre_sistema — "como funciona o sistema?"
    D / "perguntas_sim_educado.jsonl",   # sim_educado — "faz por favor" e as corrupcoes
    D / "perguntas_confirmacao.jsonl",   # o corpus geral, o mais antigo
]

DELA    = D / "perguntas_inteligente.jsonl"
DESTINO = D / "perguntas_fundido.jsonl"


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


# ══════════════════════════════════════════════════════════════════════
#  O ROTULADOR DE TOM, CORRIGIDO
#
#  O `detectar_estado` dela casa por SUBSTRING, e a lista de
#  interjeicoes de `curiosidade` tem as letras soltas 'e' e 'o':
#
#      "e" in "cancela"  ->  True  ->  cancela vira "curiosidade"
#
#  Resultado: 2.617 das 4.291 frases (61%) sairam como curiosidade,
#  incluindo "sim", "cancela" e "muda o preco da agua". Um rotulo que
#  responde "curiosidade" para tres em cada cinco frases nao ensina tom
#  nenhum — ensina a distribuicao.
#
#  A correcao e casar em FRONTEIRA DE PALAVRA. "e" so conta quando e a
#  palavra "e", nao quando e a ultima letra de "cancela". Marcadores de
#  varias palavras continuam casando como frase.
#
#  Nao mexo no arquivo dela: ele fica como registro do que foi gerado.
#  A correcao mora aqui, onde o dado e produzido.
# ══════════════════════════════════════════════════════════════════════
import re as _re

_CACHE = {}

def _casa(marcador, texto):
    m = norm(marcador)
    if not m:
        return False
    if m not in _CACHE:
        _CACHE[m] = _re.compile(r"(?<![a-z0-9])" + _re.escape(m) + r"(?![a-z0-9])")
    return bool(_CACHE[m].search(texto))


def tom_de(frase):
    """O estado emocional da frase, por marcador em fronteira de palavra."""
    t = norm(frase)
    # `?` some no norm(); marca de pergunta se ve antes.
    interroga = "?" in (frase or "")
    for estado, padroes in dela.ESTADOS_EMOCIONAIS.items():
        for marcadores in padroes.values():
            for marcador in marcadores:
                if marcador in ("?", "??", "???"):
                    if interroga:
                        return estado
                    continue
                if _casa(marcador, t):
                    return estado
    return "neutro"


def carregar(p):
    return [json.loads(L) for L in io.open(p, encoding="utf-8") if L.strip()]


# ── reconstruir variacao -> radical ───────────────────────────────────
def mapa_das_bases():
    """Refaz a geracao dela para saber de que radical veio cada frase."""
    mapa = {}
    for intencao, base_emocional in dela.INTENCOES_EMOCIONAIS.items():
        for estado, padroes in dela.ESTADOS_EMOCIONAIS.items():
            if estado not in base_emocional:
                continue
            for frase in base_emocional[estado]:
                for prefixo in padroes["prefixos"]:
                    mapa[norm(f"{prefixo}, {frase}")] = frase
                for sufixo in padroes["sufixos"]:
                    mapa[norm(f"{frase}, {sufixo}")] = frase
                for inter in padroes["interjeicoes"]:
                    mapa[norm(f"{inter}! {frase}")] = frase
                mapa[norm(frase)] = frase
    return mapa


def main():
    # O fundido de antes, para conferir no fim que nada encolheu.
    antes = Counter()
    if DESTINO.exists():
        for o in carregar(DESTINO):
            antes[o["intencao"]] += 1

    nosso = []
    faltando = []
    dono = {}          # frase -> (arquivo, intencao) de quem chegou primeiro
    conflitos = []
    for caminho in NOSSAS:
        if not caminho.exists():
            faltando.append(caminho.name)
            continue
        parte = carregar(caminho)
        for o in parte:
            ch = norm(o["pergunta"])
            if ch in dono:
                antigo, rotulo = dono[ch]
                if rotulo != o["intencao"]:
                    conflitos.append((o["pergunta"], antigo, rotulo, caminho.name, o["intencao"]))
            else:
                dono[ch] = (caminho.name, o["intencao"])
        nosso += parte
        print(f"  {caminho.name:<32} {len(parte):5d} frases")

    if faltando:
        print("\n  !! ENTRADA QUE NAO EXISTE: " + ", ".join(faltando))
        print("     Rodar assim APAGA do corpus tudo que vinha dela.\n")

    # A MESMA FRASE COM DOIS ROTULOS. Nao e erro por si: e assim que uma
    # correcao substitui um rotulo velho. Mas e a unica coisa que a ORDEM
    # da lista decide, entao ela precisa ser vista, nunca suposta.
    if conflitos:
        vistos = set()
        print(f"\n  {len(conflitos)} frase(s) com rotulo diferente entre entradas "
              f"— vence quem vem primeiro:")
        for frase, arq_a, int_a, arq_b, int_b in conflitos:
            ch = (int_a, int_b, arq_a, arq_b)
            if ch in vistos:
                continue
            vistos.add(ch)
            n = sum(1 for c in conflitos if (c[2], c[4], c[1], c[3]) == ch)
            print(f"   {int_a:<18} ({arq_a})")
            print(f"   {int_b:<18} ({arq_b})   <- perde, {n} frase(s)")
            print(f"     ex.: \"{frase}\"")

    dela_l = carregar(DELA)
    mapa = mapa_das_bases()
    print(f"  {DELA.name:<32} {len(dela_l):5d} frases")
    print(f"\nnosso:  {len(nosso)} frases, {len({o['intencao'] for o in nosso})} intencoes")
    print(f"dela:   {len(dela_l)} frases, {len({o['intencao'] for o in dela_l})} intencoes")
    print(f"radicais reconstruidos: {len(mapa)}\n")

    saida, vistas = [], set()
    sem_base = 0

    # 1. o nosso corpus inteiro, com rotulo de tom deduzido. Vem antes do
    #    dela de proposito: em frase repetida, quem chega primeiro fica com
    #    o rotulo, e rotulo nosso vale mais que rotulo de molde.
    for o in nosso:
        ch = norm(o["pergunta"])
        if ch in vistas:
            continue
        vistas.add(ch)
        saida.append({
            "pergunta": o["pergunta"],
            "intencao": o["intencao"],
            "origem": o.get("origem", "nosso"),
            "base": o.get("base") or o["pergunta"],
            "estado_emocional": tom_de(o["pergunta"]),
            "tom_origem": "deduzido",
        })

    # 2. o dela, sem repetir e com a base reconstruida
    for o in dela_l:
        ch = norm(o["pergunta"])
        if ch in vistas:
            continue
        vistas.add(ch)
        base = mapa.get(ch)
        if base is None:
            base = o["pergunta"]          # semente/empatia: cada uma e sua propria base
            if o.get("origem") == "expansao_emocional":
                sem_base += 1
        saida.append({
            "pergunta": o["pergunta"],
            "intencao": o["intencao"],
            "origem": o.get("origem", "dela"),
            "base": base,
            "estado_emocional": o.get("estado_emocional", "neutro"),
            "tom_origem": "rotulado",
        })

    with io.open(DESTINO, "w", encoding="utf-8", newline="") as f:
        for l in saida:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")

    # ── o relatorio ───────────────────────────────────────────────────
    ci = Counter(o["intencao"] for o in saida)
    ct = Counter(o["estado_emocional"] for o in saida)
    bases = defaultdict(set)
    for o in saida:
        bases[o["intencao"]].add(o["base"])

    print(f"FUNDIDO: {len(saida)} frases, {len(ci)} intencoes, "
          f"{len({o['base'] for o in saida})} bases")
    if sem_base:
        print(f"  ATENCAO: {sem_base} frases emocionais sem radical reconhecido")

    perdidas = {o["intencao"] for o in nosso} - set(ci)
    print(f"  intencoes nossas perdidas na fusao: {perdidas or 'nenhuma'}")

    print("\n  intencao                 frases  bases")
    for i, n in ci.most_common():
        b = len(bases[i])
        aviso = "  <-- poucas bases: vai medir mal" if b < 8 else ""
        print(f"  {i:<24} {n:6d} {b:6d}{aviso}")

    print("\n  tom                      frases")
    for t, n in ct.most_common():
        print(f"  {t:<24} {n:6d}")

    # ── A CONFERENCIA QUE FALTAVA ─────────────────────────────────────
    #
    # `repor_estoque` sumiu inteira — 198 frases — porque uma entrada nao
    # estava declarada. O programa terminou com codigo 0 e imprimiu um
    # relatorio bonito. Uma fusao so pode ENCOLHER uma intencao quando
    # alguem quis; caso contrario e entrada faltando, e vale parar.
    if antes:
        encolheu = [(i, antes[i], ci.get(i, 0)) for i in antes if ci.get(i, 0) < antes[i]]
        print("\n  contra o corpus anterior:")
        if not encolheu:
            novas_i = set(ci) - set(antes)
            print(f"   nada encolheu. {len(novas_i)} intencao(oes) nova(s): "
                  f"{', '.join(sorted(novas_i)) or '(nenhuma)'}")
        else:
            for i, a, d in encolheu:
                print(f"   !! {i:<22} {a:5d} -> {d:5d}   PERDEU {a - d}")
            print("\n   Falta entrada declarada em NOSSAS, ou alguem apagou um gerador.")
            print("   NAO treine com este corpus antes de entender o que sumiu.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
