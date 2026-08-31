"""Gerador de corpus inteligente - rede neural com empatia e contexto.

Este programa expande o corpus com:
- Perguntas emocionais (frustração, urgência, satisfação, preocupação)
- Perguntas complexas que exigem entendimento de contexto
- Perguntas que mostram estados mentais do usuário
- Perguntas que exigem respostas empáticas
- Perguntas sobre problemas e soluções
- Perguntas que misturam múltiplas intenções
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# Estados emocionais e seus marcadores
ESTADOS_EMOCIONAIS = {
    "frustracao": {
        "prefixos": ["me da um desespero", "tá chato", "pq não funciona", "cansado disso", "que raiva", "irritado"],
        "sufixos": ["por favor", "me ajuda", "já faz tempo", "de novo", "pra ontem"],
        "interjeicoes": ["ah", "eita", "droga", "caraca", "nossa"]
    },
    "urgencia": {
        "prefixos": ["corre", "rápido", "agora", "emergência", "urgentissimo", "jahora"],
        "sufixos": ["por favor", "se puder", "obrigado", "valeu", "brigado"],
        "interjeicoes": ["socorro", "ai", "meu deus", "ajuda", "fogo"]
    },
    "satisfacao": {
        "prefixos": ["muito bom", "excelente", "perfeito", "gostei", "show", "maravilha"],
        "sufixos": ["valeu", "obrigado", "brigadão", "top", "legal"],
        "interjeicoes": ["oba", "yay", "uau", "que legal", "massa"]
    },
    "preocupacao": {
        "prefixos": ["tenho medo", "preocupado", "será que", "e se", "to preocupado", "tensão"],
        "sufixos": ["não sei", "espero que não", "talvez", "será", "a gente vê"],
        "interjeicoes": ["hmm", " será", "eita", "nossa", "ai"]
    },
    "curiosidade": {
        "prefixos": ["quero saber", "como funciona", "me explica", "tenho dúvida", "curioso"],
        "sufixos": ["?", "??", "???", "alguém sabe", "tem como"],
        "interjeicoes": ["hein", "opa", "e", "o", "hum"]
    }
}

# Intenções expandidas com variações emocionais
INTENCOES_EMOCIONAIS = {
    "pessoas_na_loja": {
        "neutral": ["quantas pessoas estão na loja", "tem cliente", "movimento hoje"],
        "frustracao": ["não consigo ver quantas pessoas tem", "por que não mostra quantos clientes", "tá difícil saber quem está na loja"],
        "urgencia": ["preciso saber quantos agorajá", "rápido quantos clientes tem", "emergência quantas pessoas"],
        "satisfacao": ["que legal consigo ver o movimento", "ótimo sei quantos clientes tem", "show monitoramento perfeito"],
        "preocupacao": ["será que tem muita gente", "e se tiver mais pessoas do que deveria", "tenho medo de lotação"]
    },
    "estoque": {
        "neutral": ["quantos produtos temos", "qual o estoque", "me mostra o inventário"],
        "frustracao": ["não acho o estoque", "pq não mostra direito", "cansado de procurar produto"],
        "urgencia": ["preciso do estoque já", "rápido quantos itens tem", "urgente preciso saber"],
        "satisfacao": ["bom estoque atualizado", "ótimo consigo ver tudo", "maravilha inventário show"],
        "preocupacao": ["será que vai faltar", "e se acabar o produto", "tenho medo de ruptura"]
    },
    "faturamento": {
        "neutral": ["quanto faturamos hoje", "qual a receita", "vendas do dia"],
        "frustracao": ["não consigo ver faturamento", "pq não mostra quanto vendi", "chato não saber resultado"],
        "urgencia": ["preciso do faturamento já", "rápido quanto vendi", "urgente preciso saber caixa"],
        "satisfacao": ["que bom vendi bem", "ótimo faturamento alto", "show dia lucrativo"],
        "preocupacao": ["será que vendi pouco", "e se o faturamento estiver baixo", "tenho medo de prejuízo"]
    },
    "ajuda": {
        "neutral": ["me ajuda", "o que você faz", "quais comandos"],
        "frustracao": ["não consigo usar", "pq tão difícil", "cansado de tentar"],
        "urgencia": ["preciso de ajuda já", "rápido me ensina", "urgente preciso saber usar"],
        "satisfacao": ["que bom você ajuda", "ótimo suporte", "maravilha fácil usar"],
        "preocupacao": ["será que consigo usar", "e se eu não entender", "tenho medo de errar"]
    },
    "status_sistema": {
        "neutral": ["como está o sistema", "tudo funcionando", "status geral"],
        "frustracao": ["sistema caindo", "pq não funciona", "chato ficar reiniciando"],
        "urgencia": ["sistema em emergência", "rápido está tudo ok", "urgente preciso saber status"],
        "satisfacao": ["sistema perfeito", "ótimo funcionando bem", "show estabilidade"],
        "preocupacao": ["será que vai cair", "e se der problema", "tenho medo de falha"]
    }
}

# Perguntas complexas que exigem contexto
PERGUNTAS_COMPLEXAS = {
    "contexto_temporal": [
        "quantas pessoas tiveram na loja nas últimas 2 horas",
        "o faturamento de hoje comparado com ontem",
        "estoque que diminuiu mais esta semana",
        "câmeras que tiveram problemas hoje à tarde",
        "horário com mais movimento hoje"
    ],
    "comparacao": [
        "tem mais gente agora do que ontem neste horário",
        "o faturamento está melhor que a média",
        "estoque maior do que mês passado",
        "câmeras melhor que semana passada",
        "comparação de vendas hoje vs ontem"
    ],
    "causa_efeito": [
        "por que o faturamento caiu",
        "o que causou problema nas câmeras",
        "por que o estoque baixou tanto",
        "motivo de ter pouca gente",
        "razão do sistema lento"
    ],
    "predicao": [
        "vai ter movimento depois",
        "estoque vai acabar em quanto tempo",
        "faturamento será maior que ontem",
        "câmeras vão aguentar o pico",
        "previsão de vendas hoje"
    ],
    "solucao_problema": [
        "como resolver problema de câmera",
        "o que fazer se estoque acabar",
        "como aumentar faturamento",
        "solução para pouca gente",
        "ajuda com sistema lento"
    ]
}

# Marcadores de empatia e personalidade
MARCADORES_EMPATIA = {
    "saudacao_personalizada": [
        "bom dia chefe", "ola chefe", "bom dia Eduardo", "ola tudo bem",
        "ei chefe", "opa tudo bom", "e ai Eduardo", "fala ai"
    ],
    "agradecimento": [
        "obrigado", "valeu", "brigado", "agradeço", "muito obrigado",
        "brigadão", "valeu mesmo", "obrigadão", "grato", "thanks"
    ],
    "desculpa": [
        "desculpa", "perdão", "me desculpa", "foi mal", "sinto muito",
        "me perdoa", "desculpe", "mal aí", "errei"
    ],
    "elogio": [
        "você é incrível", "muito bom", "excelente", "ótimo trabalho",
        "perfeito", "maravilha", "fantástico", "sensacional", "show"
    ],
    "solidariedade": [
        "tudo bem com você", "como você está", "precisa de algo",
        "posso ajudar", "está difícil", "vamos resolver juntos"
    ]
}

def gerar_variacoes_emocionais(intencao, base_emocional):
    """Gera variações de uma intenção com diferentes estados emocionais."""
    variacoes = []
    
    for estado, padroes in ESTADOS_EMOCIONAIS.items():
        if estado in base_emocional:
            frases = base_emocional[estado]
            for frase in frases:
                # Adicionar prefixos emocionais
                for prefixo in padroes["prefixos"]:
                    variacoes.append(f"{prefixo}, {frase}")
                
                # Adicionar sufixos emocionais
                for sufixo in padroes["sufixos"]:
                    variacoes.append(f"{frase}, {sufixo}")
                
                # Adicionar interjeições
                for interjeicao in padroes["interjeicoes"]:
                    variacoes.append(f"{interjeicao}! {frase}")
    
    return variacoes

def gerar_perguntas_com_empatia():
    """Gera perguntas que mostram estados mentais e exigem resposta empática."""
    perguntas_empaticas = []
    
    # Perguntas que mostram frustração e pedem ajuda
    frustracao = [
        "estou perdido não sei como resolver",
        "tá difícil me ajuda por favor",
        "não entendo nada disso",
        "tenta explicar de outro jeito",
        "deixa eu tentar entender",
        "sinto que não consigo usar direito",
        "me ensina de novo",
        "acho que estou fazendo errado"
    ]
    
    # Perguntas que mostram preocupação
    preocupacao = [
        "tem certeza que vai funcionar",
        "e se der errado",
        "será que é seguro",
        "não quero cometer erro",
        "tenho medo de estragar algo",
        "preciso de certeza antes",
        "pode me garantir que está certo"
    ]
    
    # Perguntas que mostram satisfação e gratidão
    gratidao = [
        "agradeço pela ajuda",
        "você me salvou hoje",
        "que bom que funciona",
        "melhorou muito agora",
        "tá muito melhor obrigado",
        "agora entendi valeu",
        "perfeito funcionou de primeira"
    ]
    
    # Perguntas que mostram urgência real
    urgencia_real = [
        "cliente esperando preciso resolver já",
        "loja aberta e sistema não funciona",
        "preciso de resposta urgente por favor",
        "não posso esperar muito tempo",
        "emergência no sistema me ajuda",
        "tem gente na fila já precisa disso"
    ]
    
    perguntas_empaticas.extend(frustracao)
    perguntas_empaticas.extend(preocupacao)
    perguntas_empaticas.extend(gratidao)
    perguntas_empaticas.extend(urgencia_real)
    
    return perguntas_empaticas

def gerar_perguntas_contextuais():
    """Gera perguntas que exigem entendimento de contexto dos sistemas."""
    perguntas_contextuais = []
    
    # Perguntas que conectam os sistemas
    integracao = [
        "a rede neural está conversando com o so espacial",
        "como a smart store está se comunicando com as câmeras",
        "o gerente está entendendo as câmeras",
        "a loja autônoma está integrada com a percepção",
        "os sistemas estão se falando direito",
        "a rede neural está processando os dados das câmeras",
        "o monitor espacial está mandando dados para a rede"
    ]
    
    # Perguntas sobre diagnóstico de problemas
    diagnostico = [
        "qual câmera está com problema",
        "por que o rastreamento falhou",
        "qual produto causou erro no estoque",
        "onde está o gargalo do sistema",
        "qual parte do sistema está lenta",
        "encontrei um bug onde reporto",
        "o que causou a falha de comunicação"
    ]
    
    # Perguntas sobre otimização
    otimizacao = [
        "como melhorar o rastreamento",
        "a câmera pode ficar mais rápida",
        "posso aumentar a precisão",
        "como fazer a rede aprender mais",
        "melhorias possíveis no sistema",
        "otimizar performance da rede",
        "deixar câmeras mais eficientes"
    ]
    
    perguntas_contextuais.extend(integracao)
    perguntas_contextuais.extend(diagnostico)
    perguntas_contextuais.extend(otimizacao)
    
    return perguntas_contextuais

def gerar_corpus_expandido():
    """Gera corpus expandido com inteligência emocional e contextual."""
    corpus_expandido = []
    
    # 1. Expandir intenções existentes com variações emocionais
    for intencao, base_emocional in INTENCOES_EMOCIONAIS.items():
        variacoes = gerar_variacoes_emocionais(intencao, base_emocional)
        for variacao in variacoes:
            corpus_expandido.append({
                "pergunta": variacao,
                "intencao": intencao,
                "origem": "expansao_emocional",
                "estado_emocional": detectar_estado(variacao)
            })
    
    # 2. Adicionar perguntas empáticas
    perguntas_empaticas = gerar_perguntas_com_empatia()
    for pergunta in perguntas_empaticas:
        intencao = classificar_intencao_empatica(pergunta)
        corpus_expandido.append({
            "pergunta": pergunta,
            "intencao": intencao,
            "origem": "empatia",
            "estado_emocional": detectar_estado(pergunta)
        })
    
    # 3. Adicionar perguntas contextuais complexas
    perguntas_contextuais = gerar_perguntas_contextuais()
    for pergunta in perguntas_contextuais:
        intencao = classificar_intencao_contextual(pergunta)
        corpus_expandido.append({
            "pergunta": pergunta,
            "intencao": intencao,
            "origem": "contexto_complexo",
            "estado_emocional": detectar_estado(pergunta)
        })
    
    # 4. Adicionar perguntas com marcadores de empatia
    for intencao, frases in INTENCOES_EMOCIONAIS.items():
        for frase in frases["neutral"]:
            for marcador in MARCADORES_EMPATIA["saudacao_personalizada"]:
                corpus_expandido.append({
                    "pergunta": f"{marcador}, {frase}",
                    "intencao": intencao,
                    "origem": "personalidade",
                    "estado_emocional": "neutro_personalizado"
                })
    
    return corpus_expandido

def detectar_estado(texto):
    """Detecta o estado emocional baseado em marcadores linguísticos."""
    texto_lower = texto.lower()
    
    for estado, padroes in ESTADOS_EMOCIONAIS.items():
        for tipo, marcadores in padroes.items():
            for marcador in marcadores:
                if marcador.lower() in texto_lower:
                    return estado
    
    return "neutro"

def classificar_intencao_empatica(pergunta):
    """Classifica intenções de perguntas empáticas."""
    pergunta_lower = pergunta.lower()
    
    if any(p in pergunta_lower for p in ["perdão", "desculpa", "erro", "errado"]):
        return "desculpa_correcao"
    elif any(p in pergunta_lower for p in ["obrigado", "valeu", "grato", "brigado"]):
        return "agradecimento"
    elif any(p in pergunta_lower for p in ["medo", "receio", "preocupado", "tenso"]):
        return "preocupacao"
    elif any(p in pergunta_lower for p in ["urgente", "rápido", "emergência", "fila"]):
        return "urgencia"
    elif any(p in pergunta_lower for p in ["ensina", "explica", "entender", "como"]):
        return "aprendizado"
    else:
        return "ajuda"

def classificar_intencao_contextual(pergunta):
    """Classifica intenções de perguntas contextuais complexas."""
    pergunta_lower = pergunta.lower()
    
    if any(p in pergunta_lower for p in ["integr", "comunic", "convers", "sistema"]):
        return "integracao_sistemas"
    elif any(p in pergunta_lower for p in ["problema", "erro", "falha", "bug"]):
        return "diagnostico_problema"
    elif any(p in pergunta_lower for p in ["melhor", "otimizar", "aumentar", "performance"]):
        return "otimizacao"
    elif any(p in pergunta_lower for p in ["câmera", "rastreamento", "percepção"]):
        return "cameras"
    elif any(p in pergunta_lower for p in ["rede neural", "gerente", "aprender"]):
        return "status_sistema"
    else:
        return "duvida_sistema"

def salvar_corpus(corpus, arquivo_saida):
    """Salva o corpus expandido em formato JSONL."""
    caminho = Path(arquivo_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    
    with open(caminho, 'w', encoding='utf-8') as f:
        for item in corpus:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"Corpus salvo em {caminho}")
    print(f"Total de exemplos: {len(corpus)}")

def carregar_corpus_existente(arquivo):
    """Carrega corpus existente para análise."""
    corpus_existente = []
    caminho = Path(arquivo)
    
    if caminho.exists():
        with open(caminho, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.strip():
                    corpus_existente.append(json.loads(linha))
    
    return corpus_existente

def mesclar_corpus(corpus_novo, corpus_existente):
    """Mescla corpus novo com existente, removendo duplicatas."""
    perguntas_existentes = {item["pergunta"] for item in corpus_existente}
    
    corpus_mesclado = corpus_existente.copy()
    for item in corpus_novo:
        if item["pergunta"] not in perguntas_existentes:
            corpus_mesclado.append(item)
    
    return corpus_mesclado

def analisar_distribuicao(corpus):
    """Analisa a distribuição de intenções e estados emocionais."""
    intencoes = defaultdict(int)
    estados = defaultdict(int)
    origens = defaultdict(int)
    
    for item in corpus:
        intencoes[item["intencao"]] += 1
        estados[item.get("estado_emocional", "neutro")] += 1
        origens[item.get("origem", "desconhecido")] += 1
    
    print("\n=== DISTRIBUIÇÃO DE INTENÇÕES ===")
    for intencao, count in sorted(intencoes.items(), key=lambda x: x[1], reverse=True):
        print(f"{intencao}: {count}")
    
    print("\n=== DISTRIBUIÇÃO DE ESTADOS EMOCIONAIS ===")
    for estado, count in sorted(estados.items(), key=lambda x: x[1], reverse=True):
        print(f"{estado}: {count}")
    
    print("\n=== DISTRIBUIÇÃO DE ORIGENS ===")
    for origem, count in sorted(origens.items(), key=lambda x: x[1], reverse=True):
        print(f"{origem}: {count}")

def main():
    """Função principal de geração de corpus inteligente."""
    print("=== GERADOR DE CORPUS INTELIGENTE ===")
    print("Gerando corpus com empatia, contexto e inteligência emocional...\n")
    
    # Carregar corpus existente
    arquivo_existente = "dados/perguntas.jsonl"
    corpus_existente = carregar_corpus_existente(arquivo_existente)
    print(f"Corpus existente: {len(corpus_existente)} exemplos")
    
    # Gerar corpus expandido
    corpus_expandido = gerar_corpus_expandido()
    print(f"Corpus expandido gerado: {len(corpus_expandido)} exemplos")
    
    # Mesclar com corpus existente
    corpus_final = mesclar_corpus(corpus_expandido, corpus_existente)
    print(f"Corpus final após mesclagem: {len(corpus_final)} exemplos")
    
    # Analisar distribuição
    analisar_distribuicao(corpus_final)
    
    # Salvar corpus final
    arquivo_saida = "dados/perguntas_inteligente.jsonl"
    salvar_corpus(corpus_final, arquivo_saida)
    
    print(f"\nCorpus inteligente gerado com sucesso!")
    print(f"Novos exemplos adicionados: {len(corpus_expandido)}")
    print(f"Total final: {len(corpus_final)}")

if __name__ == "__main__":
    main()