"""Sistema de detecção emocional avançado para a rede neural.

Este módulo permite que a rede neural:
- Detecte o estado emocional do usuário
- Adapte respostas com base no contexto emocional
- Responda com empatia e personalidade
- Mantenha contexto de conversação
- Aprenda com interações passadas
"""

import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class EstadoEmocional:
    """Representa o estado emocional detectado."""
    
    ESTADOS = [
        "neutro", "feliz", "triste", "frustrado", "preocupado",
        "urgente", "satisfeito", "curioso", "irritado", "agradecido"
    ]
    
    INTENSIDADES = ["baixa", "media", "alta"]
    
    def __init__(self, estado: str = "neutro", intensidade: str = "media"):
        self.estado = estado if estado in self.ESTADOS else "neutro"
        self.intensidade = intensidade if intensidade in self.INTENSIDADES else "media"
        self.confianca = 0.5
    
    def __repr__(self):
        return f"EstadoEmocional({self.estado}, {self.intensidade}, conf={self.confianca:.2f})"
    
    def para_dict(self):
        return {
            "estado": self.estado,
            "intensidade": self.intensidade,
            "confianca": self.confianca
        }


class DetectorEmocional:
    """Detector de estado emocional baseado em análise linguística."""
    
    # Marcadores linguísticos para cada estado emocional
    MARCADORES = {
        "feliz": {
            "palavras": ["feliz", "alegre", "contente", "ótimo", "maravilha", "show", "legal", "bom", "gostei", "perfeito"],
            "emojis": ["😊", "😄", "🎉", "⭐", "✨"],
            "pontuacao": ["!!!", "!!", "!"],
            "interjeicoes": ["oba", "yay", "uau", "massa", "top"]
        },
        "triste": {
            "palavras": ["triste", "deprimido", "mal", "ruim", "péssimo", "chato", "cansado", "exausto"],
            "emojis": ["😢", "😞", "😔", "😣"],
            "pontuacao": ["...", ".."],
            "interjeicoes": ["ah", "eita", "nossa"]
        },
        "frustrado": {
            "palavras": ["frustrado", "chateado", "irritado", "cansado", "difícil", "impossível", "não funciona", "erro"],
            "emojis": ["😤", "😡", "😠", "😑"],
            "pontuacao": ["!?", "?!", "?!!"],
            "interjeicoes": ["droga", "caraca", "nossa", "eita"]
        },
        "preocupado": {
            "palavras": ["preocupado", "medo", "receio", "tenso", "ansioso", "inseguro", "será", "e se"],
            "emojis": ["😰", "😟", "😨", "🤔"],
            "pontuacao": ["??", "???", "??"],
            "interjeicoes": ["hmm", "será", "eita"]
        },
        "urgente": {
            "palavras": ["urgente", "rápido", "já", "agora", "emergência", "imediato", "pressa", "corre"],
            "emojis": ["🚨", "⚡", "🔥", "❗"],
            "pontuacao": ["!!!", "!!", "!"],
            "interjeicoes": ["socorro", "ajuda", "fogo", "ai"]
        },
        "satisfeito": {
            "palavras": ["satisfeito", "resolvido", "funcionou", "consegui", "ótimo", "bom", "legal"],
            "emojis": ["😌", "😊", "👍", "✅"],
            "pontuacao": ["!!", "!"],
            "interjeicoes": ["oba", "uau", "show"]
        },
        "curioso": {
            "palavras": ["curioso", "interessado", "quero saber", "como", "por que", "explica", "entender"],
            "emojis": ["🤔", "🧐", "❓", "💡"],
            "pontuacao": ["??", "?"],
            "interjeicoes": ["hein", "opa", "hum"]
        },
        "irritado": {
            "palavras": ["irritado", "raiva", "ódio", "incômodo", "chato", "enfadado", "impaciente"],
            "emojis": ["😤", "😡", "😠", "🤬"],
            "pontuacao": ["!!!", "!!", "!"],
            "interjeicoes": ["droga", "caraca", "nossa"]
        },
        "agradecido": {
            "palavras": ["obrigado", "valeu", "grato", "agradeço", "brigado", "thanks", "graças"],
            "emojis": ["🙏", "😊", "❤️", "✨"],
            "pontuacao": ["!!", "!"],
            "interjeicoes": ["valeu", "obrigado", "brigadão"]
        }
    }
    
    def __init__(self):
        self.historico_emocoes = deque(maxlen=10)
        self.contagem_palavras = defaultdict(int)
    
    def detectar(self, texto: str) -> EstadoEmocional:
        """Detecta o estado emocional do texto."""
        texto_lower = texto.lower()
        pontuacoes = []
        
        # Contar pontuações
        for p in ["!!!", "!!", "!", "???", "??", "?", "...", ".."]:
            if p in texto:
                pontuacoes.append(p)
        
        # Calcular pontuação para cada estado
        pontuacao_estados = defaultdict(float)
        for estado, marcadores in self.MARCADORES.items():
            # Pontuação por palavras
            for palavra in marcadores["palavras"]:
                if palavra in texto_lower:
                    pontuacao_estados[estado] += 2.0
            
            # Pontuação por emojis
            for emoji in marcadores["emojis"]:
                if emoji in texto:
                    pontuacao_estados[estado] += 1.5
            
            # Pontuação por pontuação
            for pont in marcadores["pontuacao"]:
                if pont in pontuacoes:
                    pontuacao_estados[estado] += 1.0
            
            # Pontuação por interjeições
            for interjeicao in marcadores["interjeicoes"]:
                if interjeicao in texto_lower:
                    pontuacao_estados[estado] += 1.2
        
        # Determinar estado dominante
        if pontuacao_estados:
            estado_vencedor = max(pontuacao_estados.items(), key=lambda x: x[1])
            estado = estado_vencedor[0]
            pontuacao = estado_vencedor[1]
            
            # Calcular intensidade baseada na pontuação
            if pontuacao >= 4.0:
                intensidade = "alta"
            elif pontuacao >= 2.0:
                intensidade = "media"
            else:
                intensidade = "baixa"
            
            # Calcular confiança normalizada
            confianca = min(pontuacao / 5.0, 1.0)
        else:
            estado = "neutro"
            intensidade = "media"
            confianca = 0.3
        
        estado_emocional = EstadoEmocional(estado, intensidade)
        estado_emocional.confianca = confianca
        
        # Adicionar ao histórico
        self.historico_emocoes.append(estado_emocional)
        
        return estado_emocional
    
    def tendencia_emocional(self) -> Optional[str]:
        """Detecta tendência emocional baseada no histórico."""
        if len(self.historico_emocoes) < 3:
            return None
        
        estados_recentes = [e.estado for e in list(self.historico_emocoes)[-5:]]
        contagem = defaultdict(int)
        for estado in estados_recentes:
            contagem[estado] += 1
        
        estado_dominante = max(contagem.items(), key=lambda x: x[1])
        if estado_dominante[1] >= 3:
            return estado_dominante[0]
        
        return None


class SistemaEmpatia:
    """Sistema de empatia e resposta contextual."""
    
    # Respostas empáticas baseadas em estado emocional
    RESPOSTAS_EMPATICAS = {
        "feliz": [
            "Fico feliz que você esteja bem! Como posso ajudar?",
            "Que ótimo que as coisas estão indo bem!",
            "Adoro seu entusiasmo! Em que posso ser útil?",
            "Sua energia positiva é contagiante!"
        ],
        "triste": [
            "Sinto muito que você esteja se sentindo assim. Como posso ajudar?",
            "Lamento que as coisas não estejam bem. Estou aqui para ajudar.",
            "Compreendo sua situação. Vamos resolver isso juntos.",
            "Estou aqui para você. Me diga como posso ajudar."
        ],
        "frustrado": [
            "Entendo sua frustração. Vamos resolver isso passo a passo.",
            "Compreendo que está chato. Deixe-me ajudar você.",
            "Vamos resolver esse problema juntos. Paciência que dá certo.",
            "Entendo sua irritação. Vamos encontrar uma solução."
        ],
        "preocupado": [
            "Compreendo sua preocupação. Vamos verificar juntos.",
            "Entendo seu receio. Vamos analisar a situação com calma.",
            "Não se preocupe, vamos resolver isso juntos.",
            "Sua preocupação é válida. Vamos checar tudo com cuidado."
        ],
        "urgente": [
            "Entendo a urgência. Vou trabalhar nisso imediatamente.",
            "Vou priorizar isso para você agora mesmo.",
            "Compreendo a emergência. Já estou verificando.",
            "Vou resolver isso o mais rápido possível."
        ],
        "satisfeito": [
            "Fico feliz que tenha funcionado! Mais alguma coisa?",
            "Excelente! Em que mais posso ajudar?",
            "Ótimo resultado! Continue assim!",
            "Que bom que resolveu! Posso ajudar em mais algo?"
        ],
        "curioso": [
            "Adoro sua curiosidade! Vou explicar detalhadamente.",
            "Excelente pergunta! Vou te mostrar como funciona.",
            "Sua dúvida é interessante! Vamos explorar isso juntos.",
            "Vou te dar uma explicação completa sobre isso."
        ],
        "irritado": [
            "Compreendo sua irritação. Vamos resolver isso com calma.",
            "Entendo que está irritado. Vamos focar na solução.",
            "Vou trabalhar para resolver isso o mais rápido possível.",
            "Compreendo seu aborrecimento. Vamos resolver juntos."
        ],
        "agradecido": [
            "De nada! Estou sempre aqui para ajudar.",
            "Fico feliz em poder ajudar! Precisa de mais algo?",
            "Por nada! É um prazer ajudar você.",
            "Obrigado a você! Me avise se precisar de mais algo."
        ],
        "neutro": [
            "Entendi. Como posso ajudar você?",
            "Compreendo. Vamos resolver isso.",
            "Entendi sua solicitação. Vou verificar.",
            "Entendido. Em que mais posso ajudar?"
        ]
    }
    
    def __init__(self):
        self.contexto_conversa = deque(maxlen=20)
        self.historico_interacoes = []
    
    def resposta_empatica(self, estado_emocional: EstadoEmocional, 
                          contexto: Optional[str] = None) -> str:
        """Gera resposta empática baseada no estado emocional."""
        respostas_possiveis = self.RESPOSTAS_EMPATICAS.get(
            estado_emocional.estado, 
            self.RESPOSTAS_EMPATICAS["neutro"]
        )
        
        # Selecionar resposta aleatória
        resposta = np.random.choice(respostas_possiveis)
        
        # Adicionar contexto se disponível
        if contexto:
            resposta = f"{resposta} {contexto}"
        
        return resposta
    
    def adicionar_contexto(self, usuario: str, sistema: str, 
                          estado: EstadoEmocional):
        """Adiciona interação ao contexto da conversa."""
        self.contexto_conversa.append({
            "usuario": usuario,
            "sistema": sistema,
            "estado": estado.para_dict(),
            "timestamp": np.datetime64('now')
        })
    
    def historia_relevante(self, palavras_chave: List[str]) -> List[Dict]:
        """Busca histórico relevante baseado em palavras-chave."""
        relevantes = []
        for interacao in self.contexto_conversa:
            if any(palavra in interacao["usuario"].lower() 
                   for palavra in palavras_chave):
                relevantes.append(interacao)
        return relevantes
    
    def salvar_historico(self, arquivo: str):
        """Salva histórico de interações em arquivo."""
        caminho = Path(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(list(self.contexto_conversa), f, 
                     ensure_ascii=False, indent=2, default=str)
    
    def carregar_historico(self, arquivo: str):
        """Carrega histórico de interações de arquivo."""
        caminho = Path(arquivo)
        if caminho.exists():
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                self.contexto_conversa = deque(dados, maxlen=20)


class PersonalidadeAdaptativa:
    """Sistema de personalidade adaptativa que evolui com interações."""
    
    def __init__(self):
        self.tom_padrao = "profissional"
        self.nivel_formalidade = 0.7  # 0.0 = informal, 1.0 = muito formal
        self.nivel_empatia = 0.8      # 0.0 = frio, 1.0 = muito empático
        self.humor = 0.5              # 0.0 = sério, 1.0 = bem-humorado
        self.proatividade = 0.6       # 0.0 = reativo, 1.0 = proativo
        
        self.interacoes_totais = 0
        self.interacoes_positivas = 0
        self.interacoes_negativas = 0
    
    def adaptar_personalidade(self, feedback: str, 
                            estado_usuario: EstadoEmocional):
        """Adapta personalidade baseada em feedback e estado do usuário."""
        self.interacoes_totais += 1
        
        # Ajustar nível de empatia baseado no estado do usuário
        if estado_usuario.estado in ["triste", "preocupado", "frustrado"]:
            self.nivel_empatia = min(1.0, self.nivel_empatia + 0.1)
        elif estado_usuario.estado in ["feliz", "satisfeito"]:
            self.nivel_empatia = max(0.5, self.nivel_empatia - 0.05)
        
        # Ajustar formalidade baseado no feedback
        feedback_lower = feedback.lower()
        if any(p in feedback_lower for p in ["formal", "sério", "profissional"]):
            self.nivel_formalidade = min(1.0, self.nivel_formalidade + 0.1)
        elif any(p in feedback_lower for p in ["informal", "relaxado", "amigo"]):
            self.nivel_formalidade = max(0.3, self.nivel_formalidade - 0.1)
        
        # Ajustar humor baseado em feedback positivo/negativo
        if any(p in feedback_lower for p in ["bom", "ótimo", "legal", "obrigado"]):
            self.interacoes_positivas += 1
            self.humor = min(1.0, self.humor + 0.05)
        elif any(p in feedback_lower for p in ["ruim", "chato", "frustrante"]):
            self.interacoes_negativas += 1
            self.humor = max(0.3, self.humor - 0.05)
    
    def gerar_saudacao(self, estado_usuario: EstadoEmocional) -> str:
        """Gera saudação personalizada baseada no estado do usuário."""
        saudacoes = {
            "feliz": ["Bom dia!", "Olá!", "Oi! Tudo bem?", "E aí!"],
            "triste": ["Bom dia... Espero que seu dia melhore.", "Olá. Como você está?"],
            "frustrado": ["Bom dia. Entendo que está difícil. Vamos resolver.", "Olá. Vamos trabalhar nisso juntos."],
            "preocupado": ["Bom dia. Tudo bem? Estou aqui para ajudar.", "Olá. Vamos verificar isso com calma."],
            "urgente": ["Olá! Já estou verificando.", "Bom dia! Vou resolver isso agora."],
            "satisfeito": ["Bom dia! Que bom que está tudo bem!", "Olá! Continue assim!"],
            "curioso": ["Bom dia! Adoro sua curiosidade!", "Olá! Vamos explorar isso juntos."],
            "irritado": ["Bom dia. Vamos resolver isso com calma.", "Olá. Vou trabalhar nisso imediatamente."],
            "agradecido": ["Bom dia! Fico feliz em ajudar!", "Olá! É um prazer ajudar você."],
            "neutro": ["Bom dia!", "Olá!", "Oi!", "Bom dia. Como posso ajudar?"]
        }
        
        opcoes = saudacoes.get(estado_usuario.estado, saudacoes["neutro"])
        return np.random.choice(opcoes)
    
    def ajustar_tom_resposta(self, resposta_base: str, 
                            estado_usuario: EstadoEmocional) -> str:
        """Ajusta o tom da resposta baseado na personalidade e estado do usuário."""
        # Adicionar elementos de personalidade
        if self.humor > 0.7 and estado_usuario.estado in ["feliz", "satisfeito"]:
            return f"{resposta_base} 😊"
        
        if self.nivel_empatia > 0.8 and estado_usuario.estado in ["triste", "preocupado"]:
            return f"{resposta_base} Estou aqui para você."
        
        if self.proatividade > 0.7:
            return f"{resposta_base} Posso ajudar em mais algo?"
        
        return resposta_base
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas da personalidade."""
        return {
            "interacoes_totais": self.interacoes_totais,
            "interacoes_positivas": self.interacoes_positivas,
            "interacoes_negativas": self.interacoes_negativas,
            "nivel_formalidade": self.nivel_formalidade,
            "nivel_empatia": self.nivel_empatia,
            "humor": self.humor,
            "proatividade": self.proatividade
        }


class SistemaInteligenciaEmocional:
    """Sistema integrado de inteligência emocional."""
    
    def __init__(self):
        self.detector = DetectorEmocional()
        self.sistema_empatia = SistemaEmpatia()
        self.personalidade = PersonalidadeAdaptativa()
    
    def processar_entrada(self, texto: str, contexto: Optional[str] = None) -> Dict:
        """Processa entrada do usuário com inteligência emocional."""
        # Detectar estado emocional
        estado = self.detector.detectar(texto)
        
        # Gerar resposta empática
        resposta_empatica = self.sistema_empatia.resposta_empatica(estado, contexto)
        
        # Ajustar resposta com personalidade
        resposta_final = self.personalidade.ajustar_tom_resposta(
            resposta_empatica, estado
        )
        
        # Adicionar ao contexto
        self.sistema_empatia.adicionar_contexto(texto, resposta_final, estado)
        
        return {
            "texto_original": texto,
            "estado_emocional": estado.para_dict(),
            "resposta_empatica": resposta_empatica,
            "resposta_final": resposta_final,
            "tendencia_emocional": self.detector.tendencia_emocional(),
            "personalidade": self.personalidade.obter_estatisticas()
        }
    
    def treinar_personalidade(self, conversas: List[Dict]):
        """Treina a personalidade com base em conversas passadas."""
        for conversa in conversas:
            usuario = conversa.get("usuario", "")
            feedback = conversa.get("feedback", "")
            estado = EstadoEmocional(**conversa.get("estado", {"estado": "neutro", "intensidade": "media"}))
            
            self.personalidade.adaptar_personalidade(feedback, estado)
    
    def salvar_estado(self, arquivo: str):
        """Salva o estado do sistema em arquivo."""
        estado = {
            "personalidade": self.personalidade.obter_estatisticas(),
            "contexto": list(self.sistema_empatia.contexto_conversa),
            "historico_emocoes": [
                e.para_dict() for e in self.detector.historico_emocoes
            ]
        }
        
        caminho = Path(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=2, default=str)
    
    def carregar_estado(self, arquivo: str):
        """Carrega o estado do sistema de arquivo."""
        caminho = Path(arquivo)
        if caminho.exists():
            with open(caminho, 'r', encoding='utf-8') as f:
                estado = json.load(f)
                
                # Restaurar personalidade
                stats = estado.get("personalidade", {})
                self.personalidade.nivel_formalidade = stats.get("nivel_formalidade", 0.7)
                self.personalidade.nivel_empatia = stats.get("nivel_empatia", 0.8)
                self.personalidade.humor = stats.get("humor", 0.5)
                self.personalidade.proatividade = stats.get("proatividade", 0.6)
                self.personalidade.interacoes_totais = stats.get("interacoes_totais", 0)
                self.personalidade.interacoes_positivas = stats.get("interacoes_positivas", 0)
                self.personalidade.interacoes_negativas = stats.get("interacoes_negativas", 0)
                
                # Restaurar contexto
                self.sistema_empatia.contexto_conversa = deque(
                    estado.get("contexto", []), maxlen=20
                )
                
                # Restaurar histórico emocional
                self.detector.historico_emocoes = deque(
                    [EstadoEmocional(**e) for e in estado.get("historico_emocoes", [])],
                    maxlen=10
                )


def main():
    """Função principal para testar o sistema de inteligência emocional."""
    print("=== SISTEMA DE INTELIGÊNCIA EMOCIONAL ===\n")
    
    sistema = SistemaInteligenciaEmocional()
    
    # Testes de detecção emocional
    testes = [
        "Estou muito feliz com o resultado!",
        "Isso é muito frustrante, não funciona!",
        "Preciso de ajuda urgente por favor!",
        "Estou preocupado com o sistema",
        "Obrigado pela ajuda, funcionou perfeito!",
        "Como funciona esse sistema? Fiquei curioso.",
        "Me desculpa, acho que fiz errado.",
        "Bom dia chefe, tudo bem?"
    ]
    
    for teste in testes:
        resultado = sistema.processar_entrada(teste)
        print(f"Usuário: {teste}")
        print(f"Estado: {resultado['estado_emocional']['estado']} ({resultado['estado_emocional']['intensidade']})")
        print(f"Resposta: {resultado['resposta_final']}")
        print("-" * 50)
    
    # Salvar estado
    sistema.salvar_estado("dados/estado_emocional.json")
    print("\nEstado salvo em dados/estado_emocional.json")


if __name__ == "__main__":
    main()