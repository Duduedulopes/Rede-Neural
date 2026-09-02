"""Le os dois sistemas. Cada fonte responde por si e falha sozinha.

O PRINCIPIO ATRAVESSA DAQUI TAMBEM

Se o SO Espacial nao esta no ar, o painel nao inventa pessoas: ele diz que
aquela fonte esta fora. Se a WebApi nao responde, o estoque aparece como
desconhecido, e nao como zero. E se UM endpoint falha, os outros continuam.

    Abster-se e resultado de primeira classe. Vale para camera, vale para
    fonte de dados, vale para endpoint.

SEM CREDENCIAL NENHUMA, E ISSO FOI CONFERIDO NO CODIGO

`ProductsController` nao tem `[Authorize]` na classe: so nos metodos de
escrita. Entao `GET /api/products` e anonimo — e ele ja devolve
`stockQuantity`, `minimumStockThreshold` e `isLowStock`.

Ou seja: da para ter o estoque inteiro sem senha de admin. O endpoint
`/low-stock`, que EXIGE admin, e calculado aqui a partir da lista completa.
Um pedido a menos e uma credencial a menos guardada em disco.

Nenhuma dependencia externa: so a biblioteca padrao.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

TEMPO_LIMITE = 1.5


import re as _re
_PAPEL_VALIDO = _re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class FonteEspacial:
    """O gemeo digital: estado atual completo e o fluxo de eventos."""

    def __init__(self, raiz):
        self.raiz = Path(raiz)
        self.arquivo_estado = self.raiz / "dados" / "estado_atual.json"
        self.arquivo_eventos = self.raiz / "dados" / "eventos.jsonl"
        self.pasta_ao_vivo = self.raiz / "dados" / "ao_vivo"
        self.posicao = None

    def estado(self):
        """O `estado_atual.json` inteiro — pessoas, zonas, cameras.

        Devolve TUDO, sem filtrar. Quem decide o que mostrar e o painel; a
        fonte nao deve escolher por ele, senao acrescentar um campo na tela
        vira mexer em dois lugares.
        """
        try:
            bruto = self.arquivo_estado.read_text(encoding="utf-8")
            return {"online": True, "dados": json.loads(bruto)}
        except FileNotFoundError:
            return {"online": False, "erro": "estado_atual.json nao encontrado"}
        except json.JSONDecodeError:
            # O arquivo e reescrito a cada 200 ms; ler no meio da escrita
            # acontece. Nao e falha do sistema, e uma leitura perdida.
            return {"online": False, "erro": "leitura no meio da escrita"}
        except OSError as erro:
            return {"online": False, "erro": str(erro)}

    def planta(self):
        """A planta da loja: limites do chao, moveis e zonas.

        SERVIDA A PARTE DO ESTADO, e de proposito. A planta muda quando a
        loja muda — talvez uma vez por mes. O estado muda cinco vezes por
        segundo. Empacotar as duas juntas mandaria a mesma gondola pela rede
        432 mil vezes por dia para nada.

        Qual planta esta em uso vem do proprio estado, no campo `loja.id`:
        assim o painel nao precisa saber o nome do arquivo, e trocar de loja
        nao exige mexer no painel.
        """
        try:
            estado = self.estado()
            alvo = ((estado.get("dados") or {}).get("loja") or {}).get("id")
        except Exception:
            alvo = None

        try:
            for arq in sorted((self.raiz / "loja").glob("*.json")):
                try:
                    d = json.loads(arq.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if alvo is None or d.get("id") == alvo:
                    return {k: v for k, v in d.items() if not k.startswith("_")}
        except OSError:
            pass
        return None

    def cameras_ao_vivo(self):
        """Quais cameras estao publicando quadro AGORA, e ha quanto tempo.

        A idade importa mais que a existencia: um `alto.jpg` de dez minutos
        atras parece uma camera funcionando e nao e. Quem mostra decide o que
        e velho demais — a fonte so informa.
        """
        try:
            arquivos = sorted(self.pasta_ao_vivo.glob("*.jpg"))
        except OSError:
            return []
        agora = time.time()
        saida = []
        for a in arquivos:
            if a.name.startswith("."):
                continue          # temporario de escrita atomica
            try:
                idade = agora - a.stat().st_mtime
            except OSError:
                continue
            saida.append({"papel": a.stem, "idade_s": round(idade, 1)})
        return saida

    def quadro(self, papel):
        """Os bytes do ultimo JPEG de uma camera, ou None.

        `papel` vem da URL, entao e entrada de fora: so letra, numero, hifen
        e sublinhado. Sem isto, "../../appsettings.json" seria um caminho
        valido e o servidor entregaria arquivo de fora da pasta.
        """
        if not papel or not _PAPEL_VALIDO.match(papel):
            return None
        caminho = self.pasta_ao_vivo / f"{papel}.jpg"
        try:
            return caminho.read_bytes()
        except OSError:
            return None

    def eventos_novos(self, limite=40):
        """So o que apareceu desde a ultima chamada.

        Na primeira, devolve a cauda do arquivo, para o painel abrir com
        contexto em vez de tela vazia.
        """
        try:
            tamanho = self.arquivo_eventos.stat().st_size
        except OSError:
            return []

        primeira = self.posicao is None
        if primeira or self.posicao > tamanho:
            # Arquivo recomecou (sessao nova do SO Espacial) ou primeira vez.
            self.posicao = max(0, tamanho - 60000)

        try:
            with open(self.arquivo_eventos, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.posicao)
                bruto = f.read()
                self.posicao = f.tell()
        except OSError:
            return []

        linhas = []
        for linha in bruto.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            try:
                linhas.append(json.loads(linha))
            except json.JSONDecodeError:
                continue  # linha pela metade: volta na proxima leitura

        return linhas[-limite:] if primeira else linhas


class FonteLoja:
    """A WebApi do SmartGo, so pelos endpoints anonimos.

    CADA COISA TEM SEU PROPRIO RITMO

    A sessao aberta muda a cada gesto do cliente; o catalogo de produtos
    muda quando alguem cadastra algo. Pedir os dois na mesma frequencia
    castigaria a API sem motivo — o painel atualiza a cada 700 ms.

    Por isso cada endpoint tem um tempo de validade proprio, e a fonte
    devolve o valor guardado enquanto ele nao vence.
    """

    VALIDADE = {
        "/api/sessions/current-open": 0.8,
        "/api/sessions/pending-entry": 3.0,
        "/api/products": 6.0,
        "/api/categories": 30.0,
    }

    def __init__(self, base):
        self.base = base.rstrip("/")
        self._cache = {}

    def _pegar(self, caminho):
        """Devolve (valor, erro). Nunca levanta."""
        agora = time.monotonic()
        guardado = self._cache.get(caminho)
        if guardado and agora - guardado[0] < self.VALIDADE.get(caminho, 2.0):
            return guardado[1], guardado[2]

        url = self.base + caminho
        pedido = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as r:
                valor, erro = json.loads(r.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            valor, erro = None, f"HTTP {e.code}"
        except (urllib.error.URLError, OSError):
            valor, erro = None, "sem resposta"
        except ValueError:
            valor, erro = None, "resposta nao e JSON"

        self._cache[caminho] = (agora, valor, erro)
        return valor, erro

    def resumo(self):
        """Tudo que a loja sabe e o gerente precisa ver."""
        produtos, erro_produtos = self._pegar("/api/products")
        sessao, erro_sessao = self._pegar("/api/sessions/current-open")
        pendente, _ = self._pegar("/api/sessions/pending-entry")
        categorias, _ = self._pegar("/api/categories")

        # A API esta no ar se QUALQUER endpoint respondeu. Sessao ausente e
        # uma resposta legitima (ninguem na loja), nao uma falha.
        online = produtos is not None or sessao is not None or categorias is not None

        estoque_baixo = None
        if isinstance(produtos, list):
            # Calculado aqui: `/low-stock` exigiria token de admin, e a
            # lista completa ja traz o campo.
            estoque_baixo = [p for p in produtos if p.get("isLowStock")]

        return {
            "online": online,
            "erro": None if online else (erro_produtos or erro_sessao or "sem resposta"),
            "produtos": produtos,
            "categorias": categorias,
            "sessao": sessao,
            "pendente": pendente,
            "estoque_baixo": estoque_baixo,
        }
