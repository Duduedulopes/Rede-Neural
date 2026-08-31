"""Texto -> numeros. O tokenizador e o vocabulario do classificador.

DUAS DECISOES QUE DEFINEM SE ISTO FUNCIONA COM GENTE DE VERDADE

1. NORMALIZAR SEM PIEDADE. "câmera", "camera", "CAMERA" e "cameras" tem que
   virar a mesma coisa. Quem digita com pressa no painel escreve a segunda,
   e um modelo que trata as quatro como palavras diferentes precisa de
   quatro vezes mais exemplos para aprender a mesma coisa.

2. TRIGRAMAS DE CARACTERE, E NAO SO PALAVRAS. Se o modelo so conhece
   palavras inteiras, "faturmento" (com o erro de digitacao) e uma palavra
   que ele nunca viu — e a frase inteira perde o unico termo que importava.

   Com trigramas, "faturmento" compartilha `fat`, `atu`, `tur`, `ent`, `nto`
   com "faturamento". O erro de digitacao deixa de ser fatal e vira ruido.

   E a ideia do fastText, e ela e o que faz um classificador de texto
   pequeno aguentar gente escrevendo rapido.

POR QUE MEDIA DOS VETORES, E NAO CONCATENACAO COMO NO PREVISOR

No previsor a ORDEM era tudo: "entrou, esticou o braco" e diferente de
"esticou o braco, entrou". Por isso la os vetores sao concatenados.

Aqui nao. "quanto vendi hoje" e "hoje quanto vendi" pedem a mesma coisa, e
as perguntas tem tamanhos diferentes. Media resolve os dois de uma vez:
ignora a ordem e aceita qualquer comprimento.

    A arquitetura muda porque a pergunta mudou. Nao ha uma que sirva
    sempre — e escolher errado aqui custaria exemplos que nao existem.
"""

import re
import unicodedata
from collections import Counter

TAMANHO_NGRAMA = 3


def normalizar(texto):
    """Minusculas, sem acento, so letras e numeros."""
    texto = (texto or "").lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def trigramas(palavra):
    """`<agua>` -> `<ag`, `agu`, `gua`, `ua>`.

    Os sinais `<` e `>` marcam inicio e fim. Sem eles, "gua" apareceria
    igual em "agua" e em "guarda" — e o modelo perderia a informacao de que
    num caso o pedaco esta no fim da palavra e no outro no comeco.
    """
    cercada = "<" + palavra + ">"
    if len(cercada) <= TAMANHO_NGRAMA:
        return [cercada]
    return [cercada[i:i + TAMANHO_NGRAMA]
            for i in range(len(cercada) - TAMANHO_NGRAMA + 1)]


def pedacos(texto):
    """Todas as pecas de uma frase: as palavras e os trigramas delas."""
    palavras = normalizar(texto).split()
    saida = list(palavras)
    for p in palavras:
        saida.extend(trigramas(p))
    return saida


class Vocabulario:
    """Peca de texto -> indice."""

    def __init__(self, frases, minimo=2):
        """`minimo` corta o que aparece pouco demais para ser aprendido.

        Uma peca que sai duas vezes em duzentas frases nao tem como receber
        gradiente suficiente. Ela so ocupa uma linha da tabela e adiciona
        ruido — e pior, faz o modelo decorar aquele exemplo especifico.
        """
        contagem = Counter()
        for f in frases:
            contagem.update(set(pedacos(f)))

        self.pecas = ["<?>"] + sorted(p for p, n in contagem.items() if n >= minimo)
        self.indice = {p: i for i, p in enumerate(self.pecas)}
        self.contagem = contagem

    def __len__(self):
        return len(self.pecas)

    def indices(self, texto):
        """Os indices das pecas conhecidas de uma frase.

        Frase inteiramente desconhecida devolve `[0]` — o indice do `<?>` —
        e nao lista vazia. Lista vazia quebraria a media (divisao por zero);
        `<?>` faz o modelo responder a partir do vies, que e a resposta
        honesta de quem nao reconheceu nada.
        """
        vistos = [self.indice[p] for p in pedacos(texto) if p in self.indice]
        return vistos or [0]
