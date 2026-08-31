"""O vocabulario de eventos. Cada evento vira UM token.

POR QUE TOKEN, E POR QUE ISSO E O MESMO PROBLEMA DE UM MODELO DE LINGUAGEM

Um modelo de linguagem le uma sequencia de tokens e responde com uma
distribuicao de probabilidade sobre o proximo. Aqui e identico — so muda o
que e um token:

    modelo de linguagem   "a", "loja", "esta", ...   -> proxima palavra
    este modelo           BRACO:estendido, ...       -> proximo evento

A conta e a mesma, a arquitetura e a mesma, a funcao de perda e a mesma.

SO O TIPO NAO BASTA

Onze tipos e pouco: `BRACO_MUDOU` cobre tanto o braco caindo ao lado quanto
o braco esticando para a gondola, que sao coisas completamente diferentes
para quem administra a loja. Entao o token carrega o tipo MAIS o campo que
muda o significado dele.

    BRACO_MUDOU + estado          -> BRACO:estendido
    PERSON_ENTERED_ZONE + zona    -> ENTROU:frente-a
    POSTURA_MUDOU + estado        -> POSTURA:agachado

O vocabulario cresce de 11 para algumas dezenas. Grande o bastante para a
previsao significar alguma coisa, pequeno o bastante para treinar na CPU.

O TOKEN DESCONHECIDO NAO E DETALHE

`<?>` existe para todo evento que nao se encaixa. Sem ele, um evento novo
(um tipo que o SO Espacial passe a emitir amanha) quebraria o previsor em
producao. Com ele, o previsor apenas fica surpreso — que e a resposta certa.
"""

DESCONHECIDO = "<?>"
INICIO = "<inicio>"


def token(evento):
    """Devolve o token de um evento. Sempre devolve algo."""
    tipo = evento.get("tipo")

    if tipo == "BRACO_MUDOU":
        return "BRACO:" + str(evento.get("estado", "?"))
    if tipo == "POSTURA_MUDOU":
        return "POSTURA:" + str(evento.get("estado", "?"))
    if tipo == "LOCOMOCAO_MUDOU":
        e = str(evento.get("estado", "?"))
        # `andando_frente`, `andando_tras`... viram familias. A direcao
        # relativa ao corpo importa para o desenho, nao para prever o que
        # vem depois — e cada variante separada picotaria o vocabulario.
        if e.startswith("andando"):
            e = "andando"
        elif e.startswith("virando") or e == "meia_volta":
            e = "virando"
        return "LOCOMOCAO:" + e
    if tipo == "PERSON_ENTERED_ZONE":
        return "ENTROU:" + str(evento.get("zona", "?"))
    if tipo == "PERSON_LEFT_ZONE":
        return "SAIU:" + str(evento.get("zona", "?"))

    # --- os eventos que vem do SmartGo, derivados do carrinho ---
    #
    # O TOKEN NAO CARREGA O NOME DO PRODUTO, E ISSO E DELIBERADO.
    #
    # `PRODUTO:adicionado` e um token so, para qualquer produto. Se cada
    # produto tivesse o seu, o vocabulario cresceria a cada cadastro, o
    # modelo precisaria de retreino toda vez que a loja mudasse o catalogo,
    # e cada token novo comecaria sem nenhum exemplo.
    #
    # A gramatica que interessa nao e "qual produto": e "pegou algo depois
    # de esticar o braco na gondola". O nome do produto viaja no evento,
    # para a locucao, e fica fora do vocabulario.
    if tipo == "PRODUTO_ADICIONADO":
        return "PRODUTO:adicionado"
    if tipo == "PRODUTO_DEVOLVIDO":
        return "PRODUTO:devolvido"
    if tipo == "SESSAO_ABERTA":
        return "SESSAO:aberta"
    if tipo == "SESSAO_FECHADA":
        return "SESSAO:fechada"
    if tipo == "SESSAO_STATUS":
        return "SESSAO:" + str(evento.get("status", "?")).lower()
    if tipo == "ESTOQUE_BAIXO":
        return "ESTOQUE:baixo"

    if tipo in ("TRACK_STARTED", "TRACK_LOST", "SYSTEM_STARTED",
                "CAMERA_CONNECTED", "CAMERA_DISCONNECTED", "CAMERA_ERROR"):
        return tipo
    return DESCONHECIDO


def construir(eventos, minimo=5):
    """Monta o vocabulario a partir dos eventos.

    `minimo` corta tokens raros demais. Um token que aparece duas vezes em
    catorze mil eventos nao tem como ser aprendido — ele so ocupa uma coluna
    da softmax e recebe gradiente quase nunca. Vira DESCONHECIDO, e a
    surpresa de ve-lo passa a ser a resposta honesta.
    """
    from collections import Counter
    contagem = Counter(token(e) for e in eventos)
    mantidos = sorted(t for t, n in contagem.items() if n >= minimo)

    # INICIO preenche a janela dos primeiros eventos, quando ainda nao ha
    # passado suficiente. DESCONHECIDO precisa existir sempre.
    lista = [INICIO, DESCONHECIDO] + [t for t in mantidos if t not in (INICIO, DESCONHECIDO)]
    indice = {t: i for i, t in enumerate(lista)}
    return lista, indice, contagem
