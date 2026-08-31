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

NOSSO  = RAIZ / "dados" / "perguntas_confirmacao.jsonl"
DELA   = RAIZ / "dados" / "perguntas_inteligente.jsonl"
DESTINO = RAIZ / "dados" / "perguntas_fundido.jsonl"


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
    nosso = carregar(NOSSO)
    dela_l = carregar(DELA)
    mapa = mapa_das_bases()
    print(f"nosso:  {len(nosso)} frases, {len({o['intencao'] for o in nosso})} intencoes")
    print(f"dela:   {len(dela_l)} frases, {len({o['intencao'] for o in dela_l})} intencoes")
    print(f"radicais reconstruidos: {len(mapa)}\n")

    saida, vistas = [], set()
    sem_base = 0

    # 1. o nosso corpus inteiro, com rotulo de tom deduzido
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


if __name__ == "__main__":
    main()
