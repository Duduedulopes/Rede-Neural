"""Transforma o ESTADO do carrinho em EVENTOS de compra.

O PROBLEMA, DITO COM PRECISAO

O leitor RFID ja sabe quando um produto entra no carrinho: o firmware chama
`POST /api/sessions/{id}/items/by-rfid` e a API acrescenta o item. A
informacao existe e e exata.

O que nao existe e o EVENTO. A WebApi guarda estado — "a sessao tem 3 itens"
— e nao emite "acabou de entrar um Baly". Quem chega depois so ve o
resultado, nunca o instante.

    Estado responde "como esta". Evento responde "o que aconteceu".
    Sao coisas diferentes, e o gerente precisa da segunda.

A SAIDA: DERIVAR O EVENTO DA DIFERENCA

O monitor le a sessao a cada 0,8 s e compara com a leitura anterior. Item que
apareceu ou aumentou virou `PRODUTO:adicionado`. Item que sumiu ou diminuiu
virou `PRODUTO:devolvido`.

Nenhuma linha muda no .NET. O SmartGo continua sem saber que existe monitor —
que e como deve ser: o gerente observa, nao pede para ser servido.

O QUE ESTA ABORDAGEM PERDE, E VALE SABER

    resolucao   dois eventos dentro da mesma janela de 0,8 s aparecem juntos
    ordem       nao da para saber qual dos dois veio primeiro
    perda       se o cliente pega e devolve o mesmo item entre duas leituras,
                nada e visto — e o gesto some

Emitir o evento no proprio .NET, na hora, resolveria os tres. Isso e o degrau
9. Enquanto ele nao vem, derivar da diferenca e honesto e funciona.

SOBRE A IDENTIDADE

O `pessoa` do SO Espacial e um numero de RASTRO; o cliente do SmartGo e uma
`StoreSession`. Sao identidades DIFERENTES, e liga-las e o problema de
atribuicao.

Com UMA sessao aberta a ligacao e trivial: quem esta na loja e quem esta
comprando. Com duas, nao — e ai o evento derivado sai com `pessoa: None` em
vez de chutar. Chutar aqui poria produto no carrinho errado.
"""

from datetime import datetime


def _agora():
    return datetime.now().astimezone().isoformat()


def _itens(sessao):
    """{productId: (quantidade, nome)} — ou vazio se nao ha sessao."""
    if not isinstance(sessao, dict):
        return {}
    saida = {}
    for it in sessao.get("items") or []:
        pid = it.get("productId")
        if pid is None:
            continue
        saida[pid] = (int(it.get("quantity") or 0), it.get("productName") or "?")
    return saida


class DiferencaDaLoja:
    """Guarda a ultima leitura e emite o que mudou desde ela."""

    def __init__(self):
        self.sessao_id = None
        self.itens = {}
        self.status = None

    def comparar(self, loja, rastros_ativos=None):
        """Devolve a lista de eventos derivados desta leitura.

        `rastros_ativos` sao os ids de rastro do SO Espacial. Serve so para
        decidir se da para atribuir a compra a alguem: com exatamente um
        rastro e uma sessao, e ele. Com mais de um, ninguem.
        """
        if not loja or not loja.get("online"):
            return []

        sessao = loja.get("sessao")
        sid = sessao.get("id") if isinstance(sessao, dict) else None
        status = sessao.get("status") if isinstance(sessao, dict) else None
        agora = _itens(sessao)

        pessoa = None
        if rastros_ativos and len(rastros_ativos) == 1:
            pessoa = rastros_ativos[0]

        eventos = []

        # ---- a sessao trocou -------------------------------------------
        if sid != self.sessao_id:
            if self.sessao_id is not None:
                eventos.append({"t": _agora(), "tipo": "SESSAO_FECHADA",
                                "sessao": self.sessao_id, "status": self.status})
            if sid is not None:
                eventos.append({"t": _agora(), "tipo": "SESSAO_ABERTA",
                                "sessao": sid, "pessoa": pessoa})
            # Comeco de sessao: os itens que ja vierem sao estado inicial, e
            # nao entradas que acabaram de acontecer. Sem isto, reabrir o
            # painel no meio de uma compra inventaria N eventos de uma vez.
            self.sessao_id, self.itens, self.status = sid, agora, status
            return eventos

        # ---- o carrinho mudou ------------------------------------------
        for pid, (qtd, nome) in agora.items():
            antes = self.itens.get(pid, (0, nome))[0]
            if qtd > antes:
                eventos.append({"t": _agora(), "tipo": "PRODUTO_ADICIONADO",
                                "produto": nome, "produto_id": pid,
                                "quantidade": qtd - antes, "sessao": sid,
                                "pessoa": pessoa})
            elif qtd < antes:
                eventos.append({"t": _agora(), "tipo": "PRODUTO_DEVOLVIDO",
                                "produto": nome, "produto_id": pid,
                                "quantidade": antes - qtd, "sessao": sid,
                                "pessoa": pessoa})

        for pid, (qtd, nome) in self.itens.items():
            if pid not in agora and qtd > 0:
                eventos.append({"t": _agora(), "tipo": "PRODUTO_DEVOLVIDO",
                                "produto": nome, "produto_id": pid,
                                "quantidade": qtd, "sessao": sid,
                                "pessoa": pessoa})

        # ---- o status mudou --------------------------------------------
        if status != self.status and status is not None:
            eventos.append({"t": _agora(), "tipo": "SESSAO_STATUS",
                            "sessao": sid, "status": status,
                            "de": self.status})

        self.itens, self.status = agora, status
        return eventos


def eventos_de_estoque(loja, ja_avisados):
    """Emite UMA vez por produto que entrou em estoque baixo.

    `ja_avisados` e um conjunto que o chamador guarda entre leituras. Sem
    ele, um produto em baixa geraria um evento a cada 6 segundos, para
    sempre — e o painel viraria uma parede de avisos identicos.

    Quando o produto e reposto, ele sai do conjunto e pode avisar de novo.
    """
    if not loja or not loja.get("online"):
        return []

    baixos = loja.get("estoque_baixo")
    if baixos is None:
        return []

    ids_agora = {p.get("id") for p in baixos}
    eventos = []
    for p in baixos:
        if p.get("id") not in ja_avisados:
            eventos.append({"t": _agora(), "tipo": "ESTOQUE_BAIXO",
                            "produto": p.get("name"), "produto_id": p.get("id"),
                            "restam": p.get("stockQuantity"),
                            "minimo": p.get("minimumStockThreshold")})
    ja_avisados.clear()
    ja_avisados.update(ids_agora)
    return eventos
