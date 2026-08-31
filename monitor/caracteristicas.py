"""Transforma um evento do SO Espacial num vetor de numeros.

A REGRA QUE JA VALIA, ATRAVESSANDO A FRONTEIRA

O SO Espacial trata `None` como "esta camera nao votou", e isso e um valor de
primeira classe la. Rede neural nao aceita `None` — precisa de um numero em
toda entrada. As duas saidas obvias estao erradas:

    preencher com 0        a rede le "altura zero", que e uma MEDIDA
    preencher com a media  inventa um dado plausivel e apaga a ausencia

A saida certa e VALOR + MASCARA: cada campo opcional vira duas entradas, o
valor e um bit dizendo se ele existe. A rede aprende sozinha a ignorar o
valor quando o bit e zero.

    A abstencao atravessa a fronteira em vez de ser apagada nela.

CONTEXTO E PARTE DA CARACTERISTICA

Um evento sozinho quase nao diz nada. `POSTURA_MUDOU para agachado` e rotina
na frente de uma gondola e e outra coisa depois de trinta segundos parado.
Por isso o extrator carrega estado: quantas pessoas ha, ha quanto tempo esta
pessoa esta na zona, quanto tempo passou desde o evento anterior.
"""

from datetime import datetime

TIPOS = [
    "TRACK_STARTED", "TRACK_LOST",
    "PERSON_ENTERED_ZONE", "PERSON_LEFT_ZONE",
    "LOCOMOCAO_MUDOU", "POSTURA_MUDOU", "BRACO_MUDOU",
    "CAMERA_CONNECTED", "CAMERA_DISCONNECTED", "CAMERA_ERROR",
    "SYSTEM_STARTED",
]
BRACOS = ["ao_lado", "levantado", "estendido", "desconhecido"]
POSTURAS = ["em_pe", "agachado", "desconhecida"]
LOCOMOCOES = ["parado", "andando", "virando", "desconhecida"]
ZONAS = ["entrada", "saida", "frente-a", "frente-b", "fila-checkout", "outra"]


def _um_de(valor, lista):
    v = [0.0] * len(lista)
    if valor in lista:
        v[lista.index(valor)] = 1.0
    return v


def _familia_locomocao(estado):
    if estado in ("parado",):
        return "parado"
    if estado and estado.startswith("virando") or estado == "meia_volta":
        return "virando"
    if estado and estado.startswith("andando"):
        return "andando"
    return "desconhecida"


def nomes():
    """Os nomes das entradas, na ordem. Serve ao painel e a depuracao."""
    n = ["tipo:" + t for t in TIPOS]
    n += ["braco:" + b for b in BRACOS]
    n += ["postura:" + p for p in POSTURAS]
    n += ["locomocao:" + l for l in LOCOMOCOES]
    n += ["zona:" + z for z in ZONAS]
    for campo in ("confianca", "altura_mao", "proporcao"):
        n += [campo, campo + "?"]
    n += ["pessoas", "tempo_na_zona", "silencio_antes", "tem_pessoa"]
    return n


TAMANHO = len(nomes())


def _instante(e):
    try:
        return datetime.fromisoformat(e["t"]).timestamp()
    except Exception:
        return 0.0


class Extrator:
    """Guarda o contexto necessario para descrever o proximo evento.

    Um extrator por fluxo. Reproduzir um log do comeco exige um extrator novo
    — reaproveitar carrega estado de outra sessao para dentro desta.
    """

    def __init__(self):
        self.pessoas = set()
        self.zona_de = {}
        self.entrou_em = {}
        self.ultimo_t = None

    def descrever(self, e):
        """Devolve (vetor, contexto). O contexto e legivel; o vetor, nao."""
        tipo = e.get("tipo", "")
        t = _instante(e)
        pessoa = e.get("pessoa")

        silencio = 0.0 if self.ultimo_t is None else max(0.0, t - self.ultimo_t)
        self.ultimo_t = t

        if tipo == "TRACK_STARTED" and pessoa is not None:
            self.pessoas.add(pessoa)
        if tipo == "TRACK_LOST" and pessoa is not None:
            self.pessoas.discard(pessoa)
            self.zona_de.pop(pessoa, None)
            self.entrou_em.pop(pessoa, None)
        if tipo == "PERSON_ENTERED_ZONE" and pessoa is not None:
            self.zona_de[pessoa] = e.get("zona")
            self.entrou_em[pessoa] = t
        if tipo == "PERSON_LEFT_ZONE" and pessoa is not None:
            if self.zona_de.get(pessoa) == e.get("zona"):
                self.zona_de.pop(pessoa, None)
                self.entrou_em.pop(pessoa, None)

        zona = self.zona_de.get(pessoa) or e.get("zona")
        tempo_na_zona = 0.0
        if pessoa in self.entrou_em:
            tempo_na_zona = max(0.0, t - self.entrou_em[pessoa])

        v = []
        v += _um_de(tipo, TIPOS)
        v += _um_de(e.get("estado") if tipo == "BRACO_MUDOU" else None, BRACOS)
        v += _um_de(e.get("estado") if tipo == "POSTURA_MUDOU" else None, POSTURAS)
        v += _um_de(_familia_locomocao(e.get("estado")) if tipo == "LOCOMOCAO_MUDOU" else None,
                    LOCOMOCOES)
        v += _um_de(zona if zona in ZONAS else ("outra" if zona else None), ZONAS)

        for campo, escala in (("confianca", 1.0), ("altura_m", 2.0), ("proporcao", 1.0)):
            valor = e.get(campo)
            if valor is None:
                v += [0.0, 0.0]
            else:
                v += [min(1.5, float(valor) / escala), 1.0]

        v.append(min(1.0, len(self.pessoas) / 5.0))
        v.append(min(1.0, tempo_na_zona / 60.0))
        v.append(min(1.0, silencio / 30.0))
        v.append(1.0 if pessoa is not None else 0.0)

        contexto = {
            "tipo": tipo, "pessoa": pessoa, "zona": zona,
            "tempo_na_zona": round(tempo_na_zona, 1),
            "pessoas": len(self.pessoas),
            "silencio": round(silencio, 1),
            "t": e.get("t"),
        }
        return v, contexto
