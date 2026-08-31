"""Gera corpus massivo com perguntas mal formuladas, gírias e erros.

O sistema precisa ser treinado para interpretar:
- Perguntas mal formuladas
- Gírias e linguagem informal
- Erros de digitação
- Abreviações
- Perguntas incompletas
- Contexto implícito

Este script gera centenas de variações para cada intenção.
"""

import json
import random
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAIZ = Path(__file__).resolve().parents[1]
CORPUS_EXPANDIDO = RAIZ / "dados" / "perguntas_expandido.jsonl"
CORPUS_ROBUSTO = RAIZ / "dados" / "perguntas_robusto.jsonl"
SEMENTE = 42

random.seed(SEMENTE)

# Variações de gírias e linguagem informal
GIRIAS_ABREVIACOES = [
    "td", "tudo", "cê", "vc", "tava", "pra", "pro", "tô", "né", "sim", "agora",
    "hoje", "ontem", "amanhã", "aki", "esse", "pó", "vai", "faz", "mim", "cmg"
]

# Erros de digitação comuns - formato simples para fácil acesso
ERROS_DIGITACAO_DICT = {
    "adicionar": ["add", "adi", "adcionar", "adiciona"],
    "criar": ["cria", "crir", "criaar", "criari"],
    "alterar": ["altera", "altarr", "alt", "modificar"],
    "mudar": ["muda", "mudaar", "mdar", "trocar"],
    "remover": ["remove", "removi", "remv", "apagar"],
    "apagar": ["apaga", "apg", "excluir", "deletar"],
    "preço": ["preco", "prec", "preç", "valor"],
    "quantidade": ["qtd", "quant", "qnt", "qtdade"],
    "câmera": ["camera", "cam", "cmera", "cameras"],
    "sistema": ["sist", "sitema", "sistems", "config"]
}

# Perguntas base para cada intenção
PERGUNTAS_BASE = {
    "adicionar_produto": [
        "adiciona um produto novo",
        "criar novo produto",
        "cadastrar produto",
        "novo item no estoque",
        "adicionar produto ao catálogo"
    ],
    "alterar_preco": [
        "alterar preço do produto",
        "mudar valor",
        "atualizar preço",
        "modificar preço",
        "trocar valor"
    ],
    "alterar_estoque": [
        "alterar estoque",
        "atualizar quantidade",
        "corrigir estoque",
        "mudar quantidade",
        "ajustar estoque"
    ],
    "remover_produto": [
        "remover produto",
        "apagar item",
        "excluir produto",
        "deletar produto",
        "tirar produto"
    ],
    "configurar_camera": [
        "adicionar câmera",
        "nova câmera",
        "configurar câmera",
        "instalar câmera",
        "adicionar camera"
    ],
    "configurar_sistema": [
        "configurar sistema",
        "alterar configuração",
        "mudar settings",
        "ajustar configuração",
        "modificar sistema"
    ],
    "reiniciar_servico": [
        "reiniciar serviço",
        "reiniciar sistema",
        "resetar serviço",
        "restart no serviço",
        "reiniciar servico"
    ]
}

def gerar_variacao_giria(pergunta):
    """Adiciona gírias à pergunta."""
    gírias = random.sample(GIRIAS_ABREVIACOES, random.randint(1, 3))
    return f"{pergunta}, {', '.join(gírias)}"

def gerar_variacao_erro_digitacao(pergunta):
    """Adiciona erros de digitação à pergunta."""
    palavras = pergunta.split()
    if len(palavras) < 2:
        return pergunta
    
    # Escolhe uma palavra para corromper
    palavra_idx = random.randint(0, len(palavras) - 1)
    palavra_original = palavras[palavra_idx]
    
    # Tenta encontrar uma correção correspondente
    for tupla in ERROS_DIGITACAO:
        correta = tupla[0]
        if correta in palavra_original.lower():
            substituicoes = [e for e in ERROS_DIGITACAO if e[0] == correta]
            if substituicoes:
                # Escolhe uma das formas erradas (índice 1 ou 2)
                indice_errada = random.choice([1, 2])
                palavra_errada = substituicoes[0][indice_errada]
                palavras[palavra_idx] = palavra_errada
                break
    
    return ' '.join(palavras)

def gerar_variacao_abreviada(pergunta):
    """Cria versão abreviada da pergunta."""
    palavras = pergunta.split()
    if len(palavras) <= 3:
        return pergunta
    
    # Remove artigos e preposições
    palavras = [p for p in palavras if p.lower() not in ["um", "uma", "o", "a", "do", "da", "no", "na", "de", "em"]]
    
    # Abrevia algumas palavras
    abreviacoes = {
        "produto": "prod",
        "preço": "preço",
        "quantidade": "qtd",
        "câmera": "cam",
        "sistema": "sist"
    }
    
    for i, palavra in enumerate(palavras):
        if palavra.lower() in abreviacoes:
            palavras[i] = abreviacoes[palavra.lower()]
    
    return ' '.join(palavras)

def gerar_variacao_incompleta(pergunta):
    """Cria versão incompleta da pergunta."""
    palavras = pergunta.split()
    if len(palavras) <= 2:
        return pergunta
    
    # Remove a última palavra
    return ' '.join(palavras[:-1])

def gerar_variacao_informal(pergunta):
    """Cria versão muito informal da pergunta."""
    return pergunta.replace("adicionar", "add").replace("criar", "cria").replace("alterar", "muda")

def gerar_todas_variacoes(pergunta):
    """Gera todas as variações de uma pergunta base."""
    variacoes = [pergunta]
    
    # Adiciona versões com gírias
    for _ in range(3):
        variacoes.append(gerar_variacao_giria(pergunta))
    
    # Adiciona versões com erros de digitação
    for _ in range(3):
        variacoes.append(gerar_variacao_erro_digitacao(pergunta))
    
    # Adiciona versões abreviadas
    variacoes.append(gerar_variacao_abreviada(pergunta))
    
    # Adiciona versões incompletas
    variacoes.append(gerar_variacao_incompleta(pergunta))
    
    # Adiciona versões informais
    variacoes.append(gerar_variacao_informal(pergunta))
    
    # Remove duplicatas mantendo ordem
    vistas = set()
    unicas = []
    for v in variacoes:
        if v not in vistas:
            vistas.add(v)
            unicas.append(v)
    
    return unicas

def gerar_corpus_robusto():
    """Gera corpus massivo com todas as variações."""
    print("Carregando corpus expandido...")
    
    linhas = []
    try:
        with open(CORPUS_EXPANDIDO, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    linhas.append(json.loads(linha))
    except FileNotFoundError:
        print("Corpus expandido não encontrado, começando do zero.")
        linhas = []
    
    print(f"Carregadas {len(linhas)} perguntas do corpus expandido")
    
    # Separa por intenção
    por_intencao = defaultdict(list)
    for item in linhas:
        por_intencao[item["intencao"]].append(item)
    
    # Gera variações para intenções de autonomia
    novas_perguntas = []
    
    for intencao, perguntas_base in PERGUNTAS_BASE.items():
        print(f"\nGerando variações para {intencao}...")
        
        # Adiciona as perguntas base originais
        for pergunta in perguntas_base:
            novas_perguntas.append({
                "pergunta": pergunta,
                "intencao": intencao,
                "origem": "base_robusta"
            })
        
        # Gera todas as variações
        for pergunta in perguntas_base:
            variacoes = gerar_todas_variacoes(pergunta)
            for variacao in variacoes:
                novas_perguntas.append({
                    "pergunta": variacao,
                    "intencao": intencao,
                    "origem": "variacao_robusta"
                })
        
        print(f"  Geradas {len(variacoes)} variações para {len(perguntas_base)} perguntas base")
    
    # Adiciona as perguntas existentes do corpus expandido
    for item in linhas:
        novas_perguntas.append(item)
    
    print(f"\nTotal de perguntas no corpus robusto: {len(novas_perguntas)}")
    
    # Distribuição por intenção
    distribuicao = defaultdict(int)
    for item in novas_perguntas:
        distribuicao[item["intencao"]] += 1
    
    print("\nDistribuição por intenção:")
    for intencao, contagem in sorted(distribuicao.items(), key=lambda x: x[1], reverse=True):
        print(f"  {intencao}: {contagem}")
    
    # Salva corpus robusto
    CORPUS_ROBUSTO.parent.mkdir(exist_ok=True)
    with open(CORPUS_ROBUSTO, "w", encoding="utf-8") as f:
        for item in novas_perguntas:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"\nSalvo: {CORPUS_ROBUSTO.name}")
    print(f"Tamanho: {CORPUS_ROBUSTO.stat().st_size / 1024:.0f} KB")

if __name__ == "__main__":
    gerar_corpus_robusto()