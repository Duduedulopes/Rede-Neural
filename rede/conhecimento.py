"""Camada de conhecimento sobre os sistemas Autonomous e SO-Espacial.

Este módulo fornece à rede neural:
- Conhecimento profundo sobre o sistema Smart Store (Autonomous)
- Conhecimento sobre o sistema de percepção espacial (SO-Espacial)
- Capacidade de explicar como os sistemas funcionam
- Capacidade de diagnosticar problemas
- Capacidade de sugerir soluções
- Contexto de integração entre sistemas
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class Sistema(Enum):
    """Enum dos sistemas que a rede neural coordena."""
    AUTONOMOUS = "autonomous"
    SO_ESPACIAL = "so_espacial"
    REDE_NEURAL = "rede_neural"
    INTEGRACAO = "integracao"


@dataclass
class ComponenteSistema:
    """Representa um componente de um sistema."""
    nome: str
    funcao: str
    estado: str
    importancia: str
    dependencias: List[str]
    problemas_conhecidos: List[str]


@dataclass
class ConhecimentoSistema:
    """Base de conhecimento sobre um sistema."""
    sistema: Sistema
    descricao: str
    componentes: List[ComponenteSistema]
    arquitetura: str
    tecnologias: List[str]
    pontos_fortes: List[str]
    pontos_fracos: List[str]
    metricas_importantes: Dict[str, str]
    problemas_comuns: List[Dict[str, str]]
    solucoes_recomendadas: List[Dict[str, str]]


class BaseConhecimentoAutonomous:
    """Base de conhecimento sobre o sistema Smart Store (Autonomous)."""
    
    @staticmethod
    def obter_conhecimento() -> ConhecimentoSistema:
        """Retorna conhecimento completo sobre o sistema Autonomous."""
        return ConhecimentoSistema(
            sistema=Sistema.AUTONOMOUS,
            descricao="""
            Sistema de loja autônoma em .NET 8 que gerencia vendas, estoque e clientes
            sem operador de caixa. Usa RFID para identificação de produtos e permite
            entrada autônoma por QR code.
            """,
            componentes=[
                ComponenteSistema(
                    nome="WebApi",
                    funcao="API REST que serve endpoints para comunicação",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["Domain", "Infrastructure", "SQL Server"],
                    problemas_conhecidos=["latência alta", "timeout em conexões"]
                ),
                ComponenteSistema(
                    nome="AdminApp",
                    funcao="Painel administrativo em Blazor WebAssembly",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["WebApi"],
                    problemas_conhecidos=["carregamento lento", "erro de autenticação"]
                ),
                ComponenteSistema(
                    nome="ClientApp",
                    funcao="App do cliente em Blazor WebAssembly",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["WebApi"],
                    problemas_conhecidos=["erro de login", "sessão expirada"]
                ),
                ComponenteSistema(
                    nome="ESP32",
                    funcao="Microcontrolador que lê tags RFID",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["WebApi", "Wi-Fi"],
                    problemas_conhecidos=["conexão Wi-Fi instável", "leitura de RFID falhando"]
                ),
                ComponenteSistema(
                    nome="SQL Server",
                    funcao="Banco de dados para persistência",
                    estado="operacional",
                    importancia="critica",
                    dependencias=[],
                    problemas_conhecidos=["conexão recusada", "timeout em queries"]
                )
            ],
            arquitetura="""
            Arquitetura em camadas: Domain → Application → Infrastructure → WebApi
            Clientes: AdminApp, ClientApp, EdgeDesktop
            Hardware: ESP32 com leitor RFID RC522
            """,
            tecnologias=[
                ".NET 8", "ASP.NET Core", "Entity Framework Core 8", "SQL Server",
                "Blazor WebAssembly", "WPF", "JWT", "Google Auth", ".NET nanoFramework"
            ],
            pontos_fortes=[
                "Arquitetura escalável em camadas",
                "Separação clara de responsabilidades",
                "Suporte a múltiplos clientes",
                "Hardware acessível para protótipo",
                "Documentação completa"
            ],
            pontos_fracos=[
                "Dependência de RFID 13.56 MHz com alcance curto",
                "Falta de detecção de fraudes avançada",
                "Integração com SO-Espacial ainda inicial",
                "Testes automatizados limitados"
            ],
            metricas_importantes={
                "fps_do_sistema": "Taxa de processamento do sistema",
                "tempo_resposta_api": "Tempo médio de resposta da API",
                "sucesso_leitura_rfid": "Taxa de sucesso de leitura de tags",
                "sessoes_ativas": "Número de sessões de compra ativas",
                "faturamento_hora": "Faturamento por hora"
            },
            problemas_comuns=[
                {
                    "problema": "Leitura RFID inconsistente",
                    "sintomas": "Tags não são lidas consistentemente",
                    "causas_provaveis": ["Problema com hardware RC522", "Interferência RF", "Distância muito grande"]
                },
                {
                    "problema": "Sessão expirada inesperadamente",
                    "sintomas": "Cliente perde sessão antes do checkout",
                    "causas_provaveis": ["Timeout muito curto", "Problema de rede", "Erro no token"]
                },
                {
                    "problema": "Estoque desincronizado",
                    "sintomas": "Estoque mostra valores incorretos",
                    "causas_provaveis": ["Race condition", "Erro em atualização", "Falha no cálculo"]
                }
            ],
            solucoes_recomendadas=[
                {
                    "problema": "Leitura RFID inconsistente",
                    "solucao": "Verificar conexão SPI, ajustar distância, testar com diferentes tags",
                    "prioridade": "alta"
                },
                {
                    "problema": "Sessão expirada inesperadamente",
                    "solucao": "Aumentar timeout, implementar refresh de token, melhorar tratamento de erros",
                    "prioridade": "media"
                },
                {
                    "problema": "Estoque desincronizado",
                    "solucao": "Implementar transações ACID, adicionar locks, melhorar logging",
                    "prioridade": "alta"
                }
            ]
        )


class BaseConhecimentoSOEspacial:
    """Base de conhecimento sobre o sistema SO-Espacial."""
    
    @staticmethod
    def obter_conhecimento() -> ConhecimentoSistema:
        """Retorna conhecimento completo sobre o sistema SO-Espacial."""
        return ConhecimentoSistema(
            sistema=Sistema.SO_ESPACIAL,
            descricao="""
            Sistema de percepção espacial multi-câmera em Python que cria um gêmeo digital
            da loja em tempo real. Usa visão computacional e geometria projetiva para
            rastrear pessoas e detectar gestos de retirada de produtos.
            """,
            componentes=[
                ComponenteSistema(
                    nome="Fonte de Câmeras",
                    funcao="Captura de vídeo de múltiplas câmeras",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["OpenCV", "hardware de câmera"],
                    problemas_conhecidos=["câmera caindo", "fps baixo", "conexão perdida"]
                ),
                ComponenteSistema(
                    nome="Detector YOLO",
                    funcao="Detecção de pessoas usando YOLO11-pose",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["Fonte de Câmeras", "Ultralytics"],
                    problemas_conhecidos=["inferência lenta", "falsos positivos", "memória alta"]
                ),
                ComponenteSistema(
                    nome="Motor Espacial",
                    funcao="Conversão de pixels para metros usando homografia",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["Detector YOLO", "calibração"],
                    problemas_conhecidos=["calibração imprecisa", "erro de coordenadas"]
                ),
                ComponenteSistema(
                    nome="Filtro de Kalman",
                    funcao="Rastreamento contínuo de pessoas",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["Motor Espacial"],
                    problemas_conhecidos=["perda de rastro", "troca de identidade"]
                ),
                ComponenteSistema(
                    nome="Classificador de Ação",
                    funcao="Classifica gestos em vocabulário fechado",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["Motor Espacial", "Filtro de Kalman"],
                    problemas_conhecidos=["classificação errada", "vocabulary limitado"]
                )
            ],
            arquitetura="""
            Pipeline: 3 Câmeras → Detector YOLO → Motor Espacial → Kalman → Classificador
            Arquitetura em threads independentes por câmera
            Fusão por voto (não média) de múltiplas câmeras
            """,
            tecnologias=[
                "Python 3.11+", "OpenCV", "YOLO11-pose", "MediaPipe", "NumPy",
                "homografia DLT", "filtro de Kalman", "metrologia de vista única"
            ],
            pontos_fortes=[
                "Geometria projetiva elegante (sem sensores caros)",
                "Fusão por voto (robusto a ruído)",
                "Vocabulário fechado (evita erros de renderização)",
                "Arquitetura em threads (escala bem)",
                "814 testes automatizados"
            ],
            pontos_fracos=[
                "Re-ID entre câmeras ainda não implementado",
                "Calibração manual para cada espaço",
                "Apenas 2 de 5 prateleiras confiáveis",
                "Performance depende de hardware"
            ],
            metricas_importantes={
                "fps_sistema": "Taxa de processamento do sistema",
                "fps_por_camera": "FPS individual de cada câmera",
                "precisao_posicao": "Erro em centímetros na posição",
                "taxa_sobrevivencia_rastro": "Porcentagem de rastros mantidos",
                "confiabilidade_prateleira": "Precisão de detecção de prateleira"
            },
            problemas_comuns=[
                {
                    "problema": "FPS baixo do sistema",
                    "sintomas": "Sistema processa menos de 10 fps",
                    "causas_provaveis": ["Câmera lenta limitando todas", "YOLO muito pesado", "CPU sobrecarregada"]
                },
                {
                    "problema": "Perda de rastro",
                    "sintomas": "Pessoa perde identidade durante movimento",
                    "causas_provaveis": ["Falha na fusão", "Oclusão prolongada", "Erro no Kalman"]
                },
                {
                    "problema": "Detecção de prateleira errada",
                    "sintomas": "Sistema identifica prateleira incorreta",
                    "causas_provaveis": ["Calibração imprecisa", "Altura da mão errada", "Fusão incorreta"]
                }
            ],
            solucoes_recomendadas=[
                {
                    "problema": "FPS baixo do sistema",
                    "solucao": "Usar câmeras mais rápidas, otimizar YOLO, aumentar poder de processamento",
                    "prioridade": "alta"
                },
                {
                    "problema": "Perda de rastro",
                    "solucao": "Implementar Re-ID, melhorar fusão, ajustar parâmetros do Kalman",
                    "prioridade": "media"
                },
                {
                    "problema": "Detecção de prateleira errada",
                    "solucao": "Recalibrar sistema, melhorar estimativa de altura, ajustar assinaturas de prateleira",
                    "prioridade": "alta"
                }
            ]
        )


class BaseConhecimentoIntegracao:
    """Base de conhecimento sobre a integração dos sistemas."""
    
    @staticmethod
    def obter_conhecimento() -> ConhecimentoSistema:
        """Retorna conhecimento sobre a integração dos sistemas."""
        return ConhecimentoSistema(
            sistema=Sistema.INTEGRACAO,
            descricao="""
            Integração entre Smart Store, SO-Espacial e Rede Neural para criar
            um ecossistema completo de varejo autônomo com gêmeo digital e
            gerente virtual inteligente.
            """,
            componentes=[
                ComponenteSistema(
                    nome="Monitor Espacial",
                    funcao="Servidor Python que expõe dados do SO-Espacial",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["SO-Espacial", "servidor HTTP"],
                    problemas_conhecidos=["latência", "formato de dados"]
                ),
                ComponenteSistema(
                    nome="Gerente Espacial",
                    funcao="Serviço C# que consome dados do monitor",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["Monitor Espacial", "AdminApp"],
                    problemas_conhecidos=["timeout", "erro de parsing"]
                ),
                ComponenteSistema(
                    nome="Gerente Virtual",
                    funcao="Rede neural que coordena os sistemas",
                    estado="operacional",
                    importancia="critica",
                    dependencias=["Autonomous", "SO-Espacial", "Classificador"],
                    problemas_conhecidos=["classificação errada", "baixa confiança"]
                ),
                ComponenteSistema(
                    nome="Classificador de Intenção",
                    funcao="Classifica perguntas em linguagem natural",
                    estado="operacional",
                    importancia="alta",
                    dependencias=["corpus treinado", "embeddings"],
                    problemas_conhecidos=["limiar baixo", "confusão entre intenções"]
                )
            ],
            arquitetura="""
            Arquitetura de integração:
            SO-Espacial → Monitor Espacial (HTTP) → Gerente Espacial (C#) → AdminApp
            AdminApp → Gerente Virtual (Rede Neural) → Classificador → Ação
            Autonomous API → Gerente Virtual → SO-Espacial dados
            """,
            tecnologias=[
                "HTTP/REST", "JSON", "Python", "C#", "NumPy", "Rede Neural",
                "WebSocket (planejado)", "gRPC (planejado)"
            ],
            pontos_fortes=[
                "Arquitetura modular e desacoplada",
                "Cada sistema opera independentemente",
                "Integração via API padronizada",
                "Gerente virtual com inteligência emocional",
                "Corpus treinado com dados reais"
            ],
            pontos_fracos=[
                "Integração ainda em fase inicial",
                "Falta de reconciliação automática entre sistemas",
                "Limiar de confiança ainda otimizando",
                "Falta de testes de integração completos"
            ],
            metricas_importantes={
                "latencia_integracao": "Tempo de resposta entre sistemas",
                "taxa_sucesso_reconciliacao": "Porcentagem de reconciliação bem-sucedida",
                "confianca_classificador": "Confiança média do classificador",
                "cobertura_intencoes": "Porcentagem de intenções bem classificadas"
            },
            problemas_comuns=[
                {
                    "problema": "Desincronização entre sistemas",
                    "sintomas": "Dados do SO-Espacial não batem com Autonomous",
                    "causas_provaveis": ["Latência alta", "Formato de dados diferente", "Erro de parsing"]
                },
                {
                    "problema": "Classificação incorreta de intenção",
                    "sintomas": "Gerente não entende a pergunta do usuário",
                    "causas_provaveis": ["Corpus insuficiente", "Limiar muito baixo", "Ambiguidade"]
                },
                {
                    "problema": "Reconciliação falha",
                    "sintomas": "Sistemas não concordam sobre o que aconteceu",
                    "causas_provaveis": ["Erro em um dos sistemas", "Janela temporal diferente", "Erro de fusão"]
                }
            ],
            solucoes_recomendadas=[
                {
                    "problema": "Desincronização entre sistemas",
                    "solucao": "Implementar sincronização por timestamp, adicionar buffer, melhorar formato de dados",
                    "prioridade": "alta"
                },
                {
                    "problema": "Classificação incorreta de intenção",
                    "solucao": "Expandir corpus, ajustar limiar, adicionar mais exemplos de borda",
                    "prioridade": "media"
                },
                {
                    "problema": "Reconciliação falha",
                    "solucao": "Implementar lógica de votação, ajustar janela temporal, adicionar logging detalhado",
                    "prioridade": "alta"
                }
            ]
        )


class GerenciadorConhecimento:
    """Gerenciador central de conhecimento dos sistemas."""
    
    def __init__(self):
        self.bases = {
            Sistema.AUTONOMOUS: BaseConhecimentoAutonomous.obter_conhecimento(),
            Sistema.SO_ESPACIAL: BaseConhecimentoSOEspacial.obter_conhecimento(),
            Sistema.INTEGRACAO: BaseConhecimentoIntegracao.obter_conhecimento()
        }
        self.cache_explicacoes = {}
    
    def obter_conhecimento(self, sistema: Sistema) -> ConhecimentoSistema:
        """Retorna conhecimento sobre um sistema específico."""
        return self.bases.get(sistema)
    
    def explicar_componente(self, sistema: Sistema, componente: str) -> str:
        """Explica um componente específico de um sistema."""
        conhecimento = self.obter_conhecimento(sistema)
        
        for comp in conhecimento.componentes:
            if comp.nome.lower() == componente.lower():
                return f"""
                {comp.nome}:
                Função: {comp.funcao}
                Estado: {comp.estado}
                Importância: {comp.importancia}
                Dependências: {', '.join(comp.dependencias)}
                Problemas conhecidos: {', '.join(comp.problemas_conhecidos)}
                """
        
        return f"Componente '{componente}' não encontrado no sistema {sistema.value}"
    
    def diagnosticar_problema(self, sistema: Sistema, sintoma: str) -> List[Dict]:
        """Diagnostica problemas baseados em sintomas."""
        conhecimento = self.obter_conhecimento(sistema)
        diagnosticos = []
        
        for problema in conhecimento.problemas_comuns:
            if sintoma.lower() in problema["sintomas"].lower():
                diagnosticos.append({
                    "problema": problema["problema"],
                    "causas": problema["causas_provaveis"],
                    "sistema": sistema.value
                })
        
        return diagnosticos
    
    def sugerir_solucao(self, sistema: Sistema, problema: str) -> Optional[Dict]:
        """Sugere solução para um problema específico."""
        conhecimento = self.obter_conhecimento(sistema)
        
        for solucao in conhecimento.solucoes_recomendadas:
            if problema.lower() in solucao["problema"].lower():
                return {
                    "solucao": solucao["solucao"],
                    "prioridade": solucao["prioridade"],
                    "sistema": sistema.value
                }
        
        return None
    
    def obter_metricas_importantes(self, sistema: Sistema) -> Dict[str, str]:
        """Retorna métricas importantes de um sistema."""
        conhecimento = self.obter_conhecimento(sistema)
        return conhecimento.metricas_importantes
    
    def comparar_sistemas(self) -> str:
        """Compara os três sistemas."""
        return f"""
        === COMPARACAO DE SISTEMAS ===
        
        AUTONOMOUS (Smart Store):
        - Tecnologias: {', '.join(self.bases[Sistema.AUTONOMOUS].tecnologias[:3])}...
        - Pontos fortes: {len(self.bases[Sistema.AUTONOMOUS].pontos_fortes)} principais
        - Pontos fracos: {len(self.bases[Sistema.AUTONOMOUS].pontos_fracos)} identificados
        
        SO-ESPACIAL:
        - Tecnologias: {', '.join(self.bases[Sistema.SO_ESPACIAL].tecnologias[:3])}...
        - Pontos fortes: {len(self.bases[Sistema.SO_ESPACIAL].pontos_fortes)} principais
        - Pontos fracos: {len(self.bases[Sistema.SO_ESPACIAL].pontos_fracos)} identificados
        
        INTEGRACAO:
        - Tecnologias: {', '.join(self.bases[Sistema.INTEGRACAO].tecnologias[:3])}...
        - Pontos fortes: {len(self.bases[Sistema.INTEGRACAO].pontos_fortes)} principais
        - Pontos fracos: {len(self.bases[Sistema.INTEGRACAO].pontos_fracos)} identificados
        """
    
    def responder_pergunta_conhecimento(self, pergunta: str) -> str:
        """Responde perguntas baseadas no conhecimento dos sistemas."""
        pergunta_lower = pergunta.lower()
        
        # Perguntas sobre funcionamento
        if "como funciona" in pergunta_lower or "funciona" in pergunta_lower:
            if "autonomous" in pergunta_lower or "smart store" in pergunta_lower:
                return self.bases[Sistema.AUTONOMOUS].descricao + "\n\n" + self.bases[Sistema.AUTONOMOUS].arquitetura
            elif "so espacial" in pergunta_lower or "camera" in pergunta_lower or "espacial" in pergunta_lower:
                return self.bases[Sistema.SO_ESPACIAL].descricao + "\n\n" + self.bases[Sistema.SO_ESPACIAL].arquitetura
            elif "integr" in pergunta_lower or "juntos" in pergunta_lower:
                return self.bases[Sistema.INTEGRACAO].descricao + "\n\n" + self.bases[Sistema.INTEGRACAO].arquitetura
        
        # Perguntas sobre problemas
        if "problema" in pergunta_lower or "erro" in pergunta_lower or "falha" in pergunta_lower:
            if "autonomous" in pergunta_lower:
                problemas = [p["problema"] for p in self.bases[Sistema.AUTONOMOUS].problemas_comuns]
                return f"Problemas comuns no Autonomous: {', '.join(problemas)}"
            elif "so espacial" in pergunta_lower or "camera" in pergunta_lower or "espacial" in pergunta_lower:
                problemas = [p["problema"] for p in self.bases[Sistema.SO_ESPACIAL].problemas_comuns]
                return f"Problemas comuns no SO-Espacial: {', '.join(problemas)}"
        
        # Perguntas sobre tecnologias
        if "tecnologia" in pergunta_lower or "usando" in pergunta_lower:
            if "autonomous" in pergunta_lower:
                return f"Autonomous usa: {', '.join(self.bases[Sistema.AUTONOMOUS].tecnologias)}"
            elif "so espacial" in pergunta_lower or "camera" in pergunta_lower or "espacial" in pergunta_lower:
                return f"SO-Espacial usa: {', '.join(self.bases[Sistema.SO_ESPACIAL].tecnologias)}"
        
        # Perguntas sobre comparacao
        if "comparar" in pergunta_lower or "diferenca" in pergunta_lower or "compare" in pergunta_lower:
            return self.comparar_sistemas()
        
        return "Nao tenho conhecimento especifico sobre essa pergunta. Posso ajudar com informacoes sobre Autonomous, SO-Espacial ou a integracao entre eles."
    
    def salvar_conhecimento(self, arquivo: str):
        """Salva o conhecimento em arquivo."""
        dados = {
            sistema.value: {
                "descricao": conhecimento.descricao,
                "arquitetura": conhecimento.arquitetura,
                "tecnologias": conhecimento.tecnologias,
                "pontos_fortes": conhecimento.pontos_fortes,
                "pontos_fracos": conhecimento.pontos_fracos,
                "metricas": conhecimento.metricas_importantes,
                "problemas": conhecimento.problemas_comuns,
                "solucoes": conhecimento.solucoes_recomendadas
            }
            for sistema, conhecimento in self.bases.items()
        }
        
        caminho = Path(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


def main():
    """Função principal para testar o sistema de conhecimento."""
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=== SISTEMA DE CONHECIMENTO DOS SISTEMAS ===\n")
    
    gerenciador = GerenciadorConhecimento()
    
    # Testes de perguntas
    perguntas_teste = [
        "Como funciona o sistema Autonomous?",
        "Quais são os problemas comuns no SO-Espacial?",
        "Quais tecnologias o Autonomous usa?",
        "Como funciona a integração entre os sistemas?",
        "Compare os três sistemas"
    ]
    
    for pergunta in perguntas_teste:
        resposta = gerenciador.responder_pergunta_conhecimento(pergunta)
        print(f"Pergunta: {pergunta}")
        print(f"Resposta: {resposta}")
        print("-" * 80)
    
    # Salvar conhecimento
    gerenciador.salvar_conhecimento("dados/conhecimento_sistemas.json")
    print("\nConhecimento salvo em dados/conhecimento_sistemas.json")


if __name__ == "__main__":
    main()