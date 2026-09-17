# -*- coding: utf-8 -*-
"""A REDE AO VIVO, NO TERMINAL. Programa.

    python programas/ao_vivo.py              tudo: servidor + rede + treino
    python programas/ao_vivo.py --sem-treino olha e nao treina
    python programas/ao_vivo.py --sem-servidor   so le o arquivo (2a janela)

O QUE ELE MOSTRA

Tudo que atravessa a ponte entre o C# e o Python, no instante em que
atravessa:

    PERGUNTA   a frase que a pessoa escreveu, as pecas que a rede
               reconheceu, os neuronios que acenderam, os tres palpites
               com probabilidade, o tom, e se passou do limiar
    CORRECAO   alguem discordou: a rede ANTES, o passo de gradiente com a
               taxa e o estrago medido, e a rede DEPOIS respondendo a
               MESMA frase
    MODELO     a loja devolvendo o que aprendeu, ou puxando o recalibrado
    LEITURAS   o painel lendo estado, cameras e espacial — resumidas numa
               linha, porque sao dezenas por minuto

POR QUE INTERCEPTAR EM VEZ DE VIGIAR O ARQUIVO

A primeira versao ficava relendo o `correcoes.jsonl` procurando linha nova.
Isso tinha dois defeitos. O pequeno: meio segundo de atraso e um monte de
contabilidade de posicao em bytes. O grande: **so a correcao passa por
arquivo.** Pergunta, modelo e leitura do painel nao deixam rastro nenhum em
disco — entao uma tela que so le arquivo fica muda enquanto o sistema
inteiro trabalha, e quem esta olhando conclui que quebrou.

Como o servidor roda numa thread DESTE processo, da para envolver a classe
que ele devolve e ver cada requisicao chegando. O `servidor.py` nao muda uma
linha.

A ORDEM QUE NAO PODE INVERTER: `super().do_POST()` PRIMEIRO

O original grava no disco e responde ao C#. So depois disso este programa
mostra e treina. Se fosse ao contrario, um erro no treino comeria a
correcao antes de ela existir em lugar nenhum — e o C# engole falha em
silencio, entao voce nunca saberia.

E POR QUE UMA FILA, E NAO IMPRIMIR NA HORA

O servidor e `ThreadingHTTPServer`: duas requisicoes podem chegar juntas, em
threads diferentes. Duas threads imprimindo ao mesmo tempo embaralham o
desenho na tela, e o treino rodando dentro da thread da requisicao
seguraria a resposta ao C# por um a dois segundos. Com fila, quem atende
HTTP so empurra e volta na hora; quem imprime e treina e a thread
principal, uma de cada vez, em ordem.
"""
import argparse
import io
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from rede.texto import pedacos  # noqa: E402

BASE = RAIZ / "modelos" / "intencao.json"
LOJA = RAIZ / "modelos" / "aprendido_na_loja.json"
SAIDA = RAIZ / "modelos" / "treinado_ao_vivo.json"
GUARDA = RAIZ / "modelos" / "guarda.json"
CORRECOES = RAIZ / "dados" / "correcoes.jsonl"
PERGUNTAS = RAIZ / "dados" / "perguntas_reais.jsonl"

TAXAS = (0.5, 0.25, 0.1, 0.05, 0.02, 0.01)
PASSOS_POR_TENTATIVA = 5
RESUMO_A_CADA = 15.0   # segundos entre duas linhas de resumo das leituras

FILA = queue.Queue()


# ══════════════════════════════════════════════════════════════════════
#  O TERMINAL DO WINDOWS, QUE NAO E O TERMINAL DO LINUX
#
#  Neste projeto um programa ja morreu com UnicodeEncodeError no meio de
#  uma demonstracao: o console abre em cp1252 quando nao negocia UTF-8, e
#  a barra derruba tudo. Mesma defesa do `perguntar.py` — tenta UTF-8, e
#  se nao der troca os desenhos por ASCII e segue.
# ══════════════════════════════════════════════════════════════════════
def _tem_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        return True
    except Exception:
        pass
    try:
        "\u2192\u2588".encode(sys.stdout.encoding or "ascii")
        return True
    except Exception:
        return False


BONITO = _tem_utf8()
_COR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
VERDE, AMAR, VERM, AZUL, CINZA, FORTE, FIM = (
    ("\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[90m", "\033[1m", "\033[0m")
    if _COR else ("", "", "", "", "", "", ""))

CHEIO = "\u2588" if BONITO else "#"
VAZIO = "\u00b7" if BONITO else "-"
SETA = "\u2192" if BONITO else ">"
SOBE = "\u2191" if BONITO else "^"
DESCE = "\u2193" if BONITO else "v"
CERTO = "\u2713" if BONITO else "ok"
TRACO = "\u2500" if BONITO else "-"
PONTO = "\u00b7" if BONITO else "."
NIVEIS = ("\u2589", "\u2593", "\u2592", "\u2591") if BONITO else ("#", "+", ":", ".")


def barra(p, largura=22):
    return CHEIO * int(round(p * largura)) + VAZIO * (largura - int(round(p * largura)))


def agora():
    return datetime.now().strftime("%H:%M:%S")


def regua(titulo, cor, quando=None):
    print()
    print(f"  {CINZA}{TRACO * 54}{FIM}  {CINZA}{quando or agora()}{FIM}")
    print(f"  {cor}{FORTE}{titulo}{FIM}", end="")


# ══════════════════════════════════════════════════════════════════════
#  A REDE — a mesma conta do `RedeTreinavel.cs`
# ══════════════════════════════════════════════════════════════════════
def _sig(z):
    """Sigmoide estavel: `exp` de positivo grande estoura."""
    return np.where(z >= 0, 1 / (1 + np.exp(-np.abs(z))),
                    np.exp(-np.abs(z)) / (1 + np.exp(-np.abs(z))))


class Rede:
    """Tabela de embutimento -> tronco (sigmoide) -> intencao (softmax).

    A CABECA DE TOM VIAJA JUNTO MAS NAO TREINA AQUI. Decisao antiga do
    projeto: o clique de quem corrige rotula INTENCAO, nao tom. Treinar o
    tom com esse rotulo seria ensinar uma coisa com a etiqueta de outra.
    Ela e usada so para MOSTRAR o tom na tela; quem a reajusta e o treino
    completo, do lado do Python.
    """

    def __init__(self, modelo):
        self.m = modelo
        self.pecas = {p: i for i, p in enumerate(modelo["pecas"])}
        self.intencoes = list(modelo["intencoes"])
        self.tabela = np.array(modelo["tabela"], dtype=float)
        c0, c1 = modelo["camadas"]
        self.w0 = np.array(c0["pesos"], dtype=float)
        self.b0 = np.array(c0["vies"], dtype=float).ravel()
        self.w1 = np.array(c1["pesos"], dtype=float)
        self.b1 = np.array(c1["vies"], dtype=float).ravel()
        self.limiar = modelo.get("limiar", 0.5)
        self.tons = modelo.get("tons")
        if self.tons:
            ct = modelo["camada_tom"]
            self.wt = np.array(ct["pesos"], dtype=float)
            self.bt = np.array(ct["vies"], dtype=float).ravel()

    def copiar(self):
        nova = Rede.__new__(Rede)
        nova.__dict__.update(self.__dict__)
        nova.tabela = self.tabela.copy()
        nova.w0, nova.b0 = self.w0.copy(), self.b0.copy()
        nova.w1, nova.b1 = self.w1.copy(), self.b1.copy()
        return nova

    def indices(self, frase):
        return [self.pecas[p] for p in pedacos(frase) if p in self.pecas]

    def frente(self, ids):
        if not ids:
            return None, None, None
        x = self.tabela[ids].mean(axis=0)
        a0 = _sig(self.w0 @ x + self.b0)
        z1 = self.w1 @ a0 + self.b1
        e = np.exp(z1 - z1.max())
        return x, a0, e / e.sum()

    def tom(self, a0):
        if not self.tons:
            return None, 0.0
        zt = self.wt @ a0 + self.bt
        et = np.exp(zt - zt.max())
        pt = et / et.sum()
        j = int(pt.argmax())
        return self.tons[j], float(pt[j])

    def melhor(self, ids):
        _, _, a1 = self.frente(ids)
        return int(a1.argmax()) if a1 is not None else -1

    def passo(self, lote, taxa):
        """Um passo. Espelho do `Passo` do `Retropropagacao.cs`.

        A DIVISAO POR len(ids) NA TABELA E A DERIVADA DA MEDIA — sem ela o
        treino pesaria mais as frases longas. O comentario esta no C# e o
        motivo vale igual aqui.
        """
        if not lote:
            return
        g_w0 = np.zeros_like(self.w0)
        g_b0 = np.zeros_like(self.b0)
        g_w1 = np.zeros_like(self.w1)
        g_b1 = np.zeros_like(self.b1)
        g_tab = {}

        for ids, certa in lote:
            if not ids:
                continue
            x, a0, a1 = self.frente(ids)
            dz1 = a1.copy()
            dz1[certa] -= 1.0          # softmax + entropia cruzada: (a - y)
            g_w1 += np.outer(dz1, a0)
            g_b1 += dz1
            dz0 = (self.w1.T @ dz1) * a0 * (1.0 - a0)
            g_w0 += np.outer(dz0, x)
            g_b0 += dz0
            parcela = (self.w0.T @ dz0) / len(ids)
            for i in ids:
                if i not in g_tab:
                    g_tab[i] = np.zeros_like(parcela)
                g_tab[i] += parcela

        p = taxa / len(lote)
        self.w0 -= p * g_w0
        self.b0 -= p * g_b0
        self.w1 -= p * g_w1
        self.b1 -= p * g_b1
        for i, linha in g_tab.items():
            self.tabela[i] -= p * linha

    def acerto(self, guarda):
        if not guarda:
            return 0.0
        return sum(1 for ids, c in guarda if self.melhor(ids) == c) / len(guarda)

    def distancia(self, outra):
        """RMS peso a peso. Mesma conta do `DistanciaDaBase()` do C#."""
        soma = n = 0.0
        for a, b in ((self.w0, outra.w0), (self.b0, outra.b0),
                     (self.w1, outra.w1), (self.b1, outra.b1),
                     (self.tabela, outra.tabela)):
            d = (a - b).ravel()
            soma += float(d @ d)
            n += d.size
        return (soma / n) ** 0.5 if n else 0.0

    def como_json(self, boletim):
        """De volta a JSON. Guarda TUDO que veio e troca so os pesos.

        Um arquivo que perdesse o limiar ou os tons responderia com o padrao
        errado — e sem levantar excecao nenhuma.
        """
        saida = dict(self.m)
        saida["tabela"] = self.tabela.tolist()
        c0, c1 = saida["camadas"]
        saida["camadas"] = [
            {**c0, "pesos": self.w0.tolist(), "vies": self.b0.tolist()},
            {**c1, "pesos": self.w1.tolist(), "vies": self.b1.tolist()},
        ]
        saida["treinado_ao_vivo"] = boletim
        return saida


# ══════════════════════════════════════════════════════════════════════
#  O APRENDIZ — espelho do `Aprendiz.cs`
# ══════════════════════════════════════════════════════════════════════
class Aprendiz:
    """Deixa aprender, e impede de desaprender.

    O PISO E A BASE DO PYTHON, e nao o estado de agora. O `Aprendiz.cs`
    explica: comparar so com o presente mede a inclinacao e ignora a
    altura — o modelo desce um degrau de cada vez, cada degrau passa no
    teste, e no fim quebrou onze frases sem nenhum passo isolado ter sido
    o culpado.
    """

    def __init__(self, rede_base, rede_atual, guarda):
        self.base = rede_base
        self.atual = rede_atual
        self.guarda = guarda
        self.acerto_da_base = rede_base.acerto(guarda)
        self.aceitas = 0
        self.recusadas = 0

    def acerto_agora(self):
        return self.atual.acerto(self.guarda)

    def ensinar(self, ids, certa):
        if not ids:
            return ("Recusado", 0.0, 0.0, 0.0, 0.0, 0.0)

        antes = self.acerto_agora()
        conf_antes = float(self.atual.frente(ids)[2][certa])

        if self.atual.melhor(ids) == certa:
            return ("JaSabia", 0.0, antes, antes, conf_antes, conf_antes)

        for taxa in TAXAS:
            # Sempre a partir do estado ATUAL, nunca acumulando tentativas:
            # senao a terceira taxa treinaria por cima do estrago da
            # primeira, e a medicao nao valeria nada.
            tentativa = self.atual.copiar()
            for _ in range(PASSOS_POR_TENTATIVA):
                tentativa.passo([(ids, certa)], taxa)

            depois = tentativa.acerto(self.guarda)
            if (tentativa.melhor(ids) == certa
                    and depois >= antes and depois >= self.acerto_da_base):
                self.atual = tentativa
                self.aceitas += 1
                return ("Aceito", taxa, antes, depois, conf_antes,
                        float(tentativa.frente(ids)[2][certa]))

        self.recusadas += 1
        return ("Recusado", 0.0, antes, antes, conf_antes, conf_antes)


# ══════════════════════════════════════════════════════════════════════
#  A TELA
# ══════════════════════════════════════════════════════════════════════
def palpites(rede, ids, alvo=None, quantos=3):
    _, _, a1 = rede.frente(ids)
    if a1 is None:
        return []
    ordem = list(a1.argsort()[::-1][:quantos])
    if alvo is not None and alvo not in ordem:
        ordem.append(alvo)
    return [(rede.intencoes[k], float(a1[k])) for k in ordem]


def mostrar(rotulo, linhas, destaque=None, limiar=None):
    for i, (nome, pr) in enumerate(linhas):
        if nome == destaque:
            cor = VERDE
        elif limiar is not None and i == 0:
            cor = VERDE if pr >= limiar else AMAR
        else:
            cor = CINZA
        marca = rotulo if i == 0 else " " * len(rotulo)
        ponta = f"{FORTE}{SETA}{FIM}" if i == 0 else " "
        print(f"  {CINZA}{marca}{FIM} {ponta} {cor}{nome:<20}{FIM} "
              f"{barra(pr)} {pr:6.2%}")


def mostrar_pensamento(rede, frase, ids):
    """As pecas, os neuronios e os palpites — a rede pensando.

    ISTO E O QUE A INTERFACE NAO MOSTRA. No painel do Admin aparece a
    RESPOSTA; a rede fica atras da cortina. Aqui ela aparece, e e o que
    prova que existe uma rede ali — uma tela bonita poderia ser um monte
    de `if`.
    """
    todas = pedacos(frase)
    _, a0, _ = rede.frente(ids)
    acesos = int((a0 > 0.5).sum())
    print(f"  {CINZA}pecas    {FIM} {len(ids)} de {len(todas)} conhecidas")
    print(f"  {CINZA}neuronios{FIM} {acesos} de {len(a0)} acesos   " +
          "".join(NIVEIS[0] if v > .75 else NIVEIS[1] if v > .5
                  else NIVEIS[2] if v > .25 else NIVEIS[3] for v in a0))


def ver_pergunta(rede, dado):
    frase = dado.get("pergunta") or ""
    quando = (dado.get("gravado_em") or "")[11:19] or agora()
    de = dado.get("de") or dado.get("origem") or "?"

    regua("PERGUNTA", AZUL, quando)
    print(f"  \"{frase}\"   {CINZA}de {de}{FIM}")

    ids = rede.indices(frase)
    if not ids:
        print(f"  {VERM}nenhum pedaco dessa frase existe no vocabulario{FIM}")
        return
    mostrar_pensamento(rede, frase, ids)
    print()
    mostrar("", palpites(rede, ids), limiar=rede.limiar)

    _, a0, a1 = rede.frente(ids)
    nome_tom, p_tom = rede.tom(a0)
    if nome_tom:
        print(f"  {CINZA}tom      {FIM}   {nome_tom} ({p_tom:.0%})")

    conf = float(a1.max())
    if dado.get("escolhida_por_voce"):
        print(f"  {VERDE}voce escolheu nos botoes{FIM}")
    elif conf >= rede.limiar:
        print(f"  {VERDE}responde sozinho{FIM} {CINZA}— {conf:.1%} passa do "
              f"limiar de {rede.limiar:.0%}, entao nao ha botao para corrigir{FIM}")
    else:
        print(f"  {AMAR}oferece os botoes{FIM} {CINZA}— {conf:.1%} nao passa "
              f"do limiar de {rede.limiar:.0%}{FIM}")


def ver_correcao(aprendiz, dado, treinar):
    frase = dado.get("pergunta") or ""
    escolhida = dado.get("escolhida")
    quando = (dado.get("gravado_em") or "")[11:19] or agora()
    de = dado.get("origem") or dado.get("de") or "?"

    regua("CORRECAO", AMAR, quando)
    print(f"  \"{frase}\"   {CINZA}de {de}{FIM}")

    rede = aprendiz.atual
    ids = rede.indices(frase)
    if not ids:
        print(f"  {VERM}nenhum pedaco dessa frase existe no vocabulario{FIM}")
        return False
    if escolhida not in rede.intencoes:
        print(f"  {VERM}intencao '{escolhida}' nao existe neste modelo{FIM}")
        return False

    certa = rede.intencoes.index(escolhida)
    mostrar_pensamento(rede, frase, ids)
    print()
    mostrar("ANTES ", palpites(rede, ids, certa), escolhida)
    print(f"  {CINZA}quis  {FIM}   {VERDE}{escolhida}{FIM}")

    if not treinar:
        print(f"  {CINZA}--sem-treino: nao treinei{FIM}")
        return False

    conf_antes = float(rede.frente(ids)[2][certa])
    res, taxa, g_antes, g_depois, _, conf_depois = aprendiz.ensinar(ids, certa)

    print()
    if res == "JaSabia":
        print(f"  {CINZA}JA SABIA{FIM}  palpite igual a escolha — sem passo")
    elif res == "Recusado":
        print(f"  {AMAR}RECUSADO{FIM}  nenhuma das {len(TAXAS)} taxas ensinou "
              f"sem derrubar a guarda ({g_antes:.4f})")
    else:
        d = g_depois - g_antes
        sinal = SOBE if d > 0 else (DESCE if d < 0 else " ")
        print(f"  {VERDE}TREINOU{FIM}   taxa {taxa}  {PASSOS_POR_TENTATIVA} passos")
        print(f"  {CINZA}guarda   {FIM} {g_antes:.4f} {TRACO}> {g_depois:.4f}  "
              f"{sinal}{abs(d):.4f}   piso da base {aprendiz.acerto_da_base:.4f} {CERTO}")
        print()
        mostrar("DEPOIS", palpites(aprendiz.atual, ids, certa), escolhida)
        print(f"  {CINZA}      {FIM}   {VERDE}{escolhida}{FIM} subiu "
              f"{conf_antes:.2%} {TRACO}> {conf_depois:.2%}")

    # O veredito do C# viaja na propria linha. A TAXA tambem e comparada, e
    # ela e o teste mais fino: a escada tem seis degraus e so um e aceito.
    # Os dois lados caírem no MESMO degrau, cada um por sua conta, so
    # acontece se gradiente, guarda e criterio forem iguais nos dois.
    do_csharp = dado.get("resultado")
    if do_csharp:
        taxa_cs = dado.get("taxa")
        if do_csharp != res:
            marca = f"{VERM}DIVERGIU — o C# disse {do_csharp}, eu disse {res}{FIM}"
        elif res == "Aceito" and taxa_cs is not None and abs(taxa_cs - taxa) > 1e-9:
            marca = f"{AMAR}mesma decisao, taxa diferente — C# {taxa_cs}, eu {taxa}{FIM}"
        else:
            extra = f" (taxa {taxa})" if res == "Aceito" else ""
            marca = f"{VERDE}{CERTO} os dois concordam{extra}{FIM}"
        print(f"  {CINZA}veredito {FIM} {marca}")

    return res == "Aceito"


def ver_modelo(dado):
    regua("MODELO RECEBIDO", VERDE)
    n_int = len(dado.get("intencoes") or [])
    n_pec = len(dado.get("pecas") or [])
    print(f"  a loja devolveu o que aprendeu {CINZA}— {n_int} intencoes "
          f"{PONTO} {n_pec} pecas{FIM}")
    ap = dado.get("aprendido_na_loja") or {}
    if ap:
        print(f"  {CINZA}aceitas{FIM} {ap.get('correcoes_aceitas', '?')}   "
              f"{CINZA}recusadas{FIM} {ap.get('correcoes_recusadas', '?')}   "
              f"{CINZA}guarda{FIM} {ap.get('acerto_na_guarda', '?')}   "
              f"{CINZA}distancia da base{FIM} {ap.get('distancia_da_base', '?')}")
    print(f"  {CINZA}gravado em modelos/aprendido_na_loja.json "
          f"(o intencao.json nao e tocado){FIM}")


def gravar(aprendiz, base):
    boletim = {
        "aceitas": aprendiz.aceitas,
        "recusadas": aprendiz.recusadas,
        "acerto_na_guarda": round(aprendiz.acerto_agora(), 6),
        "acerto_da_base": round(aprendiz.acerto_da_base, 6),
        "distancia_da_base": round(aprendiz.atual.distancia(base), 6),
        "gravado_em": datetime.now().astimezone().isoformat(),
    }
    SAIDA.write_text(json.dumps(aprendiz.atual.como_json(boletim), ensure_ascii=False),
                     encoding="utf-8")
    print(f"  {VERDE}gravado  {FIM} {SAIDA.name}  "
          f"{SAIDA.stat().st_size / 1024:.0f} KB  "
          f"{CINZA}distancia da base {boletim['distancia_da_base']:.5f}{FIM}")


# ══════════════════════════════════════════════════════════════════════
#  O SERVIDOR, ENVOLVIDO
# ══════════════════════════════════════════════════════════════════════
def ultima_linha(caminho):
    """A ultima linha do .jsonl, que o servidor acabou de gravar."""
    try:
        linhas = [l for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
        return json.loads(linhas[-1]) if linhas else None
    except (OSError, ValueError, IndexError):
        return None


def envolver(alca):
    """A classe do servidor, com um olho em cima. O `servidor.py` nao muda.

    `super()` PRIMEIRO, SEMPRE. O original grava no disco e responde ao C#;
    so depois este programa olha. Inverter faria um erro daqui comer a
    correcao antes de ela existir em qualquer lugar.

    E o que vai para a fila e o MINIMO — um rotulo e, no caso do POST, a
    linha que acabou de ser gravada. Ler o `rfile` aqui roubaria o corpo do
    original e quebraria o servidor.
    """
    class Espia(alca):
        def do_POST(self):
            caminho = self.path
            super().do_POST()
            if caminho.startswith("/api/correcao"):
                FILA.put(("correcao", ultima_linha(CORRECOES)))
            elif caminho.startswith("/api/pergunta"):
                FILA.put(("pergunta", ultima_linha(PERGUNTAS)))
            elif caminho.startswith("/api/modelo"):
                FILA.put(("modelo", ler_json_silencioso(
                    RAIZ / "modelos" / "aprendido_na_loja.json")))

        def do_GET(self):
            super().do_GET()
            if self.path.startswith("/api/"):
                # Resumidas, e nao uma linha cada: o painel pede estado umas
                # cinco vezes por segundo. Impressas uma a uma, elas
                # empurrariam a pergunta para fora da tela em dois minutos.
                FILA.put(("leitura", self.path.split("?")[0]))

    return Espia


def subir_servidor(porta, espacial, loja):
    """O `monitor/servidor.py` numa thread deste processo.

    Thread `daemon` de proposito: sem isso o ctrl+c fecharia o treinador e
    deixaria o servidor de pe segurando a porta 8760 — e a proxima vez que
    voce rodasse daria "endereco em uso" sem motivo aparente.
    """
    from http.server import ThreadingHTTPServer

    from monitor.fontes import FonteEspacial, FonteLoja
    from monitor.servidor import construir

    alca = construir(FonteEspacial(espacial), FonteLoja(loja))
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), envolver(alca))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def ler_json_silencioso(caminho):
    try:
        return json.load(io.open(caminho, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ler_json(caminho):
    return json.load(io.open(caminho, encoding="utf-8"))


def montar_guarda(rede, caminho):
    """As 764 frases de guarda viram (indices, certa), uma vez so."""
    saida = []
    for g in ler_json(caminho):
        ids = rede.indices(g["pergunta"])
        if ids and g["intencao"] in rede.intencoes:
            saida.append((ids, rede.intencoes.index(g["intencao"])))
    return saida


def linhas_novas(caminho, posicao):
    """Para o modo --sem-servidor: le o que cresceu desde `posicao`."""
    if not caminho.exists():
        return [], posicao
    tamanho = caminho.stat().st_size
    if tamanho < posicao:
        posicao = 0     # arquivo encolheu: alguem apagou. Recomeca.
    if tamanho == posicao:
        return [], posicao
    with io.open(caminho, "r", encoding="utf-8") as f:
        f.seek(posicao)
        bruto, posicao = f.read(), f.tell()
    saida = []
    for linha in bruto.splitlines():
        if linha.strip():
            try:
                saida.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return saida, posicao


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-treino", action="store_true",
                    help="mostra tudo e nao treina nada")
    ap.add_argument("--sem-servidor", action="store_true",
                    help="nao sobe o monitor; so le os arquivos (2a janela)")
    ap.add_argument("--do-inicio", action="store_true",
                    help="com --sem-servidor, trata tambem o que ja existe")
    ap.add_argument("--porta", type=int, default=8760)
    ap.add_argument("--espacial",
                    default=r"C:\Users\Samsung\Projetos_Eduardo\SO-Espacial")
    ap.add_argument("--loja", default="http://localhost:5071")
    args = ap.parse_args()

    if not BASE.exists():
        print(f"nao achei {BASE}")
        return 1

    base = Rede(ler_json(BASE))
    # Treina em cima do que a LOJA aprendeu, e nao da base: o da loja e o
    # que esta valendo no navegador. Treinar em cima da base desfaria
    # calado tudo o que o C# ja tinha ajustado.
    atual = Rede(ler_json(LOJA)) if LOJA.exists() else base.copiar()
    guarda = montar_guarda(base, GUARDA)
    aprendiz = Aprendiz(base, atual, guarda)

    if not args.sem_servidor:
        try:
            subir_servidor(args.porta, args.espacial, args.loja)
        except OSError as erro:
            print(f"\n  {VERM}nao consegui subir o servidor na porta "
                  f"{args.porta}{FIM}")
            print(f"  {CINZA}{erro}{FIM}\n")
            print("  Quase sempre e um monitor JA rodando em outra janela.")
            print("  Ou feche aquela janela, ou rode assim:")
            print(f"    {FORTE}python programas\\ao_vivo.py --sem-servidor{FIM}\n")
            return 1
        except ImportError as erro:
            print(f"\n  {VERM}nao achei o monitor: {erro}{FIM}")
            print(f"  {CINZA}rode a partir da raiz do Rede-Neural{FIM}\n")
            return 1

    print(f"\n  {FORTE}a rede ao vivo{FIM}")
    if not args.sem_servidor:
        print(f"  {CINZA}monitor  {FIM} http://localhost:{args.porta}   "
              f"{VERDE}no ar, nesta janela{FIM}")
    print(f"  {CINZA}modelo   {FIM} {(LOJA if LOJA.exists() else BASE).name}   "
          f"{len(atual.intencoes)} intencoes {PONTO} {len(atual.pecas)} pecas "
          f"{PONTO} limiar {atual.limiar:.0%}")
    print(f"  {CINZA}guarda   {FIM} {GUARDA.name}   {len(guarda)} frases "
          f"{PONTO} a base acerta {aprendiz.acerto_da_base:.2%}")
    print(f"  {CINZA}grava    {FIM} {SAIDA.name}"
          f"{'   (--sem-treino: nao grava)' if args.sem_treino else ''}")
    print(f"\n  {CINZA}use o gerente em qualquer um dos tres apps "
          f"{PONTO} ctrl+c para parar{FIM}")

    leituras = {}
    ultimo_resumo = time.time()
    pos_c = 0 if args.do_inicio else (CORRECOES.stat().st_size if CORRECOES.exists() else 0)
    pos_p = 0 if args.do_inicio else (PERGUNTAS.stat().st_size if PERGUNTAS.exists() else 0)

    try:
        while True:
            if args.sem_servidor:
                novas, pos_p = linhas_novas(PERGUNTAS, pos_p)
                for d in novas:
                    FILA.put(("pergunta", d))
                novas, pos_c = linhas_novas(CORRECOES, pos_c)
                for d in novas:
                    FILA.put(("correcao", d))

            mudou = False
            try:
                while True:
                    tipo, dado = FILA.get(timeout=0.4)
                    if dado is None:
                        continue
                    if tipo == "pergunta":
                        ver_pergunta(aprendiz.atual, dado)
                    elif tipo == "correcao":
                        mudou |= ver_correcao(aprendiz, dado, not args.sem_treino)
                    elif tipo == "modelo":
                        ver_modelo(dado)
                    elif tipo == "leitura":
                        leituras[dado] = leituras.get(dado, 0) + 1
            except queue.Empty:
                pass

            if mudou:
                gravar(aprendiz, base)

            # O resumo das leituras: uma linha discreta de vez em quando, so
            # para a tela nunca parecer morta enquanto o painel trabalha.
            if leituras and time.time() - ultimo_resumo >= RESUMO_A_CADA:
                partes = " ".join(f"{v}{PONTO}{k.rsplit('/', 1)[-1]}"
                                  for k, v in sorted(leituras.items()))
                print(f"  {CINZA}{PONTO} {agora()}  o painel leu: {partes}{FIM}")
                leituras.clear()
                ultimo_resumo = time.time()
    except KeyboardInterrupt:
        pass

    print(f"\n\n  {CINZA}parado. {aprendiz.aceitas} aceitas, "
          f"{aprendiz.recusadas} recusadas{FIM}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
