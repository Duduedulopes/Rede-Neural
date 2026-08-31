"""O servidor local do monitor. Programa.

    python monitor/servidor.py
    python monitor/servidor.py --espacial "C:/Users/Samsung/Projetos_Eduardo/SO-Espacial"

Serve o painel em http://localhost:8760 e um unico endpoint de dados.

POR QUE UM SERVIDOR, E NAO ABRIR O HTML DIRETO

Um arquivo aberto com file:// nao pode ler outros arquivos do disco nem
chamar a WebApi — o navegador proibe, e com razao. O servidor e a ponte: ele
roda ao lado dos dois sistemas, le o que precisa e entrega ao painel.

E por isso que a MESMA pagina publicada na web nao mostra dado ao vivo: la
nao existe este servidor. Ela cai para o modo de reproducao, e o painel diz
qual dos dois modos esta valendo.

Biblioteca padrao apenas. Sem Flask, sem nada para instalar.
"""

import argparse
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor.fontes import FonteEspacial, FonteLoja  # noqa: E402
from monitor.loja_eventos import (DiferencaDaLoja,  # noqa: E402
                                  eventos_de_estoque)

AQUI = Path(__file__).resolve().parent
PAINEL = AQUI / "painel.html"
CORRECOES = AQUI.parent / "dados" / "correcoes.jsonl"
EVENTOS_LOJA = AQUI.parent / "dados" / "eventos_loja.jsonl"
# As perguntas feitas ao gerente dentro do painel administrativo.
#
# ATE AGORA ELAS MORRIAM. `PerguntasFeitas` vivia so na memoria do
# navegador: fechou a aba, perdeu. E sao exatamente as frases que valem
# para treinar — frase que o Eduardo digitou de verdade, com a pressa e o
# vicio de escrita dele, vale mais que dez que eu invente.
PERGUNTAS = AQUI.parent / "dados" / "perguntas_reais.jsonl"

LIMITE_CORPO = 64 * 1024   # uma correcao nao passa de alguns KB


def construir(espacial, loja):
    diferenca = DiferencaDaLoja()
    estoque_avisado = set()

    def gravar_eventos_loja(eventos):
        """Grava os eventos derivados, para poder treinar com eles depois.

        SEM ISTO, O PREVISOR NUNCA APRENDE A LOJA.

        Os 14.562 eventos que treinaram o modelo nao tem uma unica compra —
        o `eventos.jsonl` e do SO Espacial, que nao sabe o que e produto.
        Entao hoje `PRODUTO:adicionado` chega ao previsor como <?>, e ele se
        surpreende com razao: nunca viu.

        Este arquivo e o que faz isso terminar. Cada compra derivada fica
        gravada com carimbo de tempo, e o proximo treino le os dois logs
        juntos. Ai o modelo aprende que esticar o braco na gondola costuma
        ser seguido de um produto entrando no carrinho — e passa a estranhar
        quando NAO e.
        """
        if not eventos:
            return
        try:
            EVENTOS_LOJA.parent.mkdir(exist_ok=True)
            with open(EVENTOS_LOJA, "a", encoding="utf-8") as f:
                for e in eventos:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
        except OSError:
            pass  # nao derrubar o painel por causa de um log

    class Manipulador(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # o terminal e do usuario, nao do servidor

        def _cors(self):
            """Libera o AdminApp a ler daqui.

            O painel administrativo roda em OUTRA origem (o Blazor sobe numa
            porta propria), e o navegador bloqueia a leitura entre origens a
            menos que o servidor autorize. Sem estes cabecalhos o chat do
            gerente recebe um erro de rede sem explicacao nenhuma.

            `*` porque este servidor SO devolve dado anonimo — estado das
            cameras, quantas pessoas ha no chao. Nada que exija credencial
            passa por aqui: o faturamento e o historico ficam no AdminApp,
            que ja tem o token de admin. Espalhar credencial para um segundo
            servidor seria a troca errada.
            """
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _responder(self, codigo, corpo, tipo):
            self.send_response(codigo)
            self._cors()
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_POST(self):
            """Grava uma discordancia do Eduardo.

            E O UNICO LUGAR ONDE O SISTEMA APRENDE COM UM HUMANO.

            O previsor nao precisa de rotulo: ele treina sozinho, prevendo o
            proximo evento. Mas a decisao de INTERROMPER ALGUEM precisa —
            uma surpresa alta pode ser um furto ou pode ser so um gesto que
            o modelo ainda nao viu. Quem sabe a diferenca e quem administra
            a loja.

            Por isso o arquivo se chama `correcoes` e nao `rotulos`: cada
            linha e um lugar onde o alarme discordou do dono.

            Somente escrita, sempre acrescentando. Nenhuma linha e alterada
            depois — mesma regra do `dados/bruto` do SO Espacial.
            """
            if self.path.startswith("/api/correcao"):
                destino = CORRECOES
            elif self.path.startswith("/api/pergunta"):
                destino = PERGUNTAS
            else:
                self._responder(404, b"nao encontrado", "text/plain; charset=utf-8")
                return

            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                tamanho = 0
            if tamanho <= 0 or tamanho > LIMITE_CORPO:
                self._responder(400, b'{"ok":false,"erro":"tamanho"}',
                                "application/json; charset=utf-8")
                return

            try:
                corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._responder(400, b'{"ok":false,"erro":"json invalido"}',
                                "application/json; charset=utf-8")
                return

            corpo["gravado_em"] = datetime.now().astimezone().isoformat()
            try:
                destino.parent.mkdir(exist_ok=True)
                with open(destino, "a", encoding="utf-8") as f:
                    f.write(json.dumps(corpo, ensure_ascii=False) + "\n")
                total = sum(1 for _ in open(destino, encoding="utf-8"))
            except OSError as erro:
                self._responder(500, json.dumps({"ok": False, "erro": str(erro)}).encode(),
                                "application/json; charset=utf-8")
                return

            self._responder(200, json.dumps({"ok": True, "total": total}).encode(),
                            "application/json; charset=utf-8")

        def do_GET(self):
            if self.path.startswith("/api/estado"):
                estado = espacial.estado()
                da_loja = loja.resumo()

                rastros = []
                if estado.get("online"):
                    rastros = [p.get("id") for p in
                               (estado.get("dados", {}).get("pessoas") or [])]

                derivados = diferenca.comparar(da_loja, rastros)
                derivados += eventos_de_estoque(da_loja, estoque_avisado)
                gravar_eventos_loja(derivados)

                # Os dois fluxos viram um so, em ordem de tempo. O previsor
                # nao deve saber de qual sistema cada evento veio: para ele
                # e uma sequencia unica de coisas que aconteceram na loja.
                eventos = espacial.eventos_novos() + derivados
                eventos.sort(key=lambda e: e.get("t") or "")

                pacote = {
                    "espacial": estado,
                    "eventos": eventos,
                    "loja": da_loja,
                }
                self._responder(200, json.dumps(pacote).encode("utf-8"),
                                "application/json; charset=utf-8")
                return

            if self.path.startswith("/api/gerente/espacial"):
                """O resumo espacial que o chat do AdminApp consome.

                Enxuto de proposito: o AdminApp nao precisa do estado inteiro,
                precisa das respostas. Mandar tudo obrigaria o outro lado a
                saber o formato interno do SO Espacial, e ai mudar um campo la
                quebraria o painel administrativo daqui.
                """
                estado = espacial.estado()
                if not estado.get("online"):
                    self._responder(200, json.dumps({
                        "online": False, "erro": estado.get("erro")}).encode(),
                        "application/json; charset=utf-8")
                    return

                d = estado.get("dados") or {}
                pessoas = d.get("pessoas") or []
                cameras = d.get("cameras") or {}
                resumo = {
                    "online": True,
                    "loja": (d.get("loja") or {}).get("nome"),
                    "pessoas": len(pessoas),
                    "rastros": [
                        {"id": p.get("id"),
                         "velocidade": round(p.get("velocidade") or 0, 2),
                         "acao": (p.get("acao") or {}).get("locomocao"),
                         "postura": (p.get("acao") or {}).get("postura"),
                         "incerteza": round(p.get("incerteza") or 0, 2)}
                        for p in pessoas
                    ],
                    "cameras": {
                        "total": len(cameras),
                        "online": sum(1 for c in cameras.values()
                                      if c.get("estado") == "online"),
                        "detalhe": [{"papel": k, "estado": v.get("estado"),
                                     "fps": round(v.get("fps") or 0, 1)}
                                    for k, v in cameras.items()],
                    },
                    "zonas": [{"id": z.get("id"), "nome": z.get("nome"),
                               "ocupacao": z.get("ocupacao"),
                               "visitas": z.get("visitas")}
                              for z in (d.get("zonas") or [])],
                }
                self._responder(200, json.dumps(resumo).encode(),
                                "application/json; charset=utf-8")
                return

            if self.path in ("/", "/index.html", "/painel.html"):
                try:
                    corpo = PAINEL.read_bytes()
                except OSError:
                    self._responder(500, b"painel.html nao encontrado", "text/plain")
                    return
                self._responder(200, corpo, "text/html; charset=utf-8")
                return

            self._responder(404, b"nao encontrado", "text/plain; charset=utf-8")

    return Manipulador


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8760)
    ap.add_argument("--espacial", default=r"C:\Users\Samsung\Projetos_Eduardo\SO-Espacial")
    ap.add_argument("--loja", default="http://localhost:5071")
    args = ap.parse_args()

    espacial = FonteEspacial(args.espacial)
    loja = FonteLoja(args.loja)

    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), construir(espacial, loja))
    print("monitor do gerente")
    print(f"  SO Espacial   {args.espacial}")
    print(f"  SmartGo       {args.loja}")
    print(f"  correcoes     {CORRECOES}")
    print(f"  eventos loja  {EVENTOS_LOJA}")
    print(f"  painel        http://localhost:{args.porta}")
    print("  ctrl+c para parar")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nparado")


if __name__ == "__main__":
    main()
