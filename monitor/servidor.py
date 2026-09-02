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

MODELO = AQUI.parent / "modelos" / "intencao.json"
APRENDIDO = AQUI.parent / "modelos" / "aprendido_na_loja.json"
HISTORICO = AQUI.parent / "dados" / "modelos_recebidos.jsonl"

LIMITE_CORPO = 64 * 1024   # uma correcao nao passa de alguns KB

# O modelo inteiro passa de 600 KB. Limite proprio, e nao o mesmo dos
# relatos: afrouxar o limite geral por causa de UMA rota abriria as outras
# junto.
LIMITE_MODELO = 8 * 1024 * 1024


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
            # ── O MODELO QUE A LOJA APRENDEU ──────────────────────────
            #
            # A OUTRA METADE DA PONTE. Ate aqui o Python so MANDAVA: treinava
            # e o C# copiava o arquivo. Agora o C# devolve o que aprendeu
            # sozinho, e o Python passa a poder medir, recalibrar e retreinar
            # em cima do que aconteceu na loja de verdade.
            #
            # O arquivo do Python (`intencao.json`) NAO e sobrescrito. O que
            # chega vai para `aprendido_na_loja.json`, ao lado. Deixar uma
            # rota HTTP escrever por cima do modelo de origem seria entregar
            # a base a quem quer que alcance a porta 8760.
            if self.path.startswith("/api/modelo"):
                try:
                    tamanho = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    tamanho = 0
                if tamanho <= 0 or tamanho > LIMITE_MODELO:
                    self._responder(400, b'{"ok":false,"erro":"tamanho"}',
                                    "application/json; charset=utf-8")
                    return
                try:
                    modelo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    self._responder(400, b'{"ok":false,"erro":"json invalido"}',
                                    "application/json; charset=utf-8")
                    return

                # Conferencia minima: um modelo sem estas chaves nao e um
                # modelo, e gravar lixo aqui faria o proximo treino partir
                # dele.
                faltando = [c for c in ("intencoes", "pecas", "tabela", "camadas")
                            if c not in modelo]
                if faltando:
                    self._responder(400, json.dumps(
                        {"ok": False, "erro": f"faltam chaves: {faltando}"}).encode(),
                        "application/json; charset=utf-8")
                    return

                modelo["recebido_em"] = datetime.now().astimezone().isoformat()
                try:
                    APRENDIDO.parent.mkdir(exist_ok=True)
                    APRENDIDO.write_text(
                        json.dumps(modelo, ensure_ascii=False), encoding="utf-8")

                    # O historico guarda so o RESUMO, nao o modelo inteiro:
                    # um arquivo de 600 KB por envio encheria o disco em uma
                    # semana, e o que interessa depois e a linha do tempo.
                    HISTORICO.parent.mkdir(exist_ok=True)
                    with open(HISTORICO, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "recebido_em": modelo["recebido_em"],
                            "intencoes": len(modelo["intencoes"]),
                            "pecas": len(modelo["pecas"]),
                            "aprendido_na_loja": modelo.get("aprendido_na_loja"),
                        }, ensure_ascii=False) + "\n")
                except OSError as erro:
                    self._responder(500, json.dumps({"ok": False, "erro": str(erro)}).encode(),
                                    "application/json; charset=utf-8")
                    return

                self._responder(200, json.dumps({
                    "ok": True,
                    "gravado_em": str(APRENDIDO),
                    "kb": round(APRENDIDO.stat().st_size / 1024),
                }).encode(), "application/json; charset=utf-8")
                return

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
            # O caminho de volta: depois de o Python recalibrar, a loja
            # puxa o modelo novo daqui em vez de esperar alguem copiar um
            # arquivo a mao. E o fim da copia manual.
            if self.path.startswith("/api/modelo"):
                try:
                    corpo = MODELO.read_bytes()
                except OSError:
                    self._responder(404, b'{"ok":false,"erro":"sem modelo"}',
                                    "application/json; charset=utf-8")
                    return
                self._responder(200, corpo, "application/json; charset=utf-8")
                return

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

            if self.path.startswith("/api/planta"):
                """O desenho do chao: limites, moveis e zonas.

                Sem isto o painel nao tem como transformar metro em pixel, e
                a pessoa apareceria num quadrado sem contexto. Com isto ele
                desenha a loja e poe a pessoa DENTRO dela.
                """
                planta = espacial.planta()
                if planta is None:
                    self._responder(404, b'{"erro":"planta nao encontrada"}',
                                    "application/json; charset=utf-8")
                    return
                self._responder(200, json.dumps(planta, ensure_ascii=False).encode("utf-8"),
                                "application/json; charset=utf-8")
                return

            # ── as cameras, para o painel ────────────────────────────
            if self.path.startswith("/api/cameras"):
                """Quem esta publicando quadro, e ha quanto tempo.

                O painel precisa saber ANTES de pedir imagem: quantas
                cameras ha nesta instalacao (1, 3 ou 5 — o Espacial abre o
                que estiver no `cameras.json`) e quais estao vivas. Sem
                isto, a tela teria de adivinhar os papeis, e uma tela que
                adivinha mostra caixa vazia quando alguem muda a instalacao.
                """
                self._responder(
                    200,
                    json.dumps({"cameras": espacial.cameras_ao_vivo()}).encode("utf-8"),
                    "application/json; charset=utf-8")
                return

            if self.path.startswith("/api/camera/"):
                """O ultimo quadro de uma camera.

                JPEG SOLTO, e nao MJPEG. O fluxo continuo segura uma conexao
                por camera por aba aberta, e este servidor e um
                `ThreadingHTTPServer` simples servindo tambem o estado do
                gemeo — tres abas com tres cameras seriam nove conexoes
                presas. Com JPEG solto, o painel pede quando quer, para
                quando a aba fecha, e o servidor nao guarda nada.

                Custa uma requisicao a cada atualizacao. A esta taxa, e mais
                barato que a conexao presa.
                """
                papel = self.path.split("/api/camera/", 1)[1].split("?")[0]
                if papel.endswith(".jpg"):
                    papel = papel[:-4]

                dados = espacial.quadro(papel)
                if dados is None:
                    self._responder(404, b'{"erro":"sem quadro dessa camera"}',
                                    "application/json; charset=utf-8")
                    return

                self._responder(200, dados, "image/jpeg")
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
    print(f"  AutonomousStore       {args.loja}")
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
