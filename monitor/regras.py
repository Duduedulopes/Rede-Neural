"""As regras que dao o rotulo inicial. E daqui que a rede aprende — por ora.

POR QUE COMECAR POR REGRAS, E POR QUE ISSO NAO E TRAPACA

Nao existe um conjunto de eventos rotulados por um gerente de loja. Nao ha
como treinar sem rotulo. Entao as regras abaixo fazem o papel de professor:
elas dizem, para cada um dos 14.562 eventos gravados, se aquilo era rotina,
merecia atencao ou merecia alerta.

A rede aprende a REPRODUZIR o professor. Isso parece circular e nao e, por
duas razoes:

  1. A rede generaliza para combinacoes que a regra trata mal, porque ela ve
     o contexto inteiro de uma vez em vez de um `if` por vez.
  2. E o unico jeito de comecar. Depois, quando o Eduardo discordar de um
     aviso no painel e corrigir, aquele caso vira rotulo DELE. A cada
     correcao a rede se afasta da regra e se aproxima do julgamento humano.

Isso tem nome no campo: supervisao fraca. O professor e ruim de proposito, e
existe para ser substituido.

    Enquanto a rede so concordar com estas regras, ela nao esta agregando
    nada. O valor comeca no dia em que ela discordar e estiver certa.

AS TRES CLASSES

    rotina    nao vai para a tela. A maior parte do que acontece.
    atencao   entra no painel, sem interromper ninguem.
    alerta    precisa de um humano agora.
"""

ROTINA, ATENCAO, ALERTA = 0, 1, 2
CLASSES = ["rotina", "atencao", "alerta"]


def rotular(evento, contexto):
    """Devolve (classe, motivo). O motivo aparece no painel e e auditavel."""
    tipo = contexto["tipo"]

    # --- infraestrutura: o gerente e o primeiro a saber que ficou cego ---
    if tipo in ("CAMERA_DISCONNECTED", "CAMERA_ERROR"):
        return ALERTA, "camera fora do ar — o sistema perdeu uma vista"

    if tipo == "SYSTEM_STARTED":
        return ATENCAO, "sistema iniciou"

    if tipo == "CAMERA_CONNECTED":
        return ROTINA, "camera conectou"

    # --- perder o rastro no meio da loja e diferente de perder na saida ---
    if tipo == "TRACK_LOST":
        if contexto["zona"] in ("saida", "fila-checkout"):
            return ROTINA, "pessoa saiu pela saida"
        return ALERTA, "rastro perdido fora da zona de saida"

    if tipo == "TRACK_STARTED":
        return ATENCAO, "pessoa entrou na loja"

    # --- alcance a gondola: o gesto que interessa comercialmente ---
    if tipo == "BRACO_MUDOU":
        if evento.get("estado") == "estendido" and contexto["zona"] in ("frente-a", "frente-b"):
            return ATENCAO, "alcancou a gondola"
        return ROTINA, "movimento de braco"

    # --- agachado por muito tempo: o unico sinal de mal-estar disponivel ---
    if tipo == "POSTURA_MUDOU":
        if evento.get("estado") == "agachado" and contexto["tempo_na_zona"] > 45:
            return ALERTA, "agachado depois de muito tempo parado na mesma zona"
        return ROTINA, "mudanca de postura"

    if tipo == "PERSON_ENTERED_ZONE":
        if contexto["zona"] in ("frente-a", "frente-b"):
            return ATENCAO, "parou na frente de uma gondola"
        return ROTINA, "trocou de zona"

    if tipo == "PERSON_LEFT_ZONE":
        return ROTINA, "saiu de uma zona"

    if tipo == "LOCOMOCAO_MUDOU":
        if evento.get("confianca", 1.0) < 0.35:
            return ROTINA, "locomocao incerta — nao vale reportar"
        return ROTINA, "mudou o jeito de andar"

    return ROTINA, "sem regra especifica"
