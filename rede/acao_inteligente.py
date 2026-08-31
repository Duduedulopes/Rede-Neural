"""Sistema de ação inteligente com verificação de contexto.

Este módulo permite que a rede neural:
- Execute ações com verificação de contexto
- Valide parâmetros antes de executar
- Peça confirmação para ações de alto risco
- Mantenha histórico de ações executadas
- Reaja a feedback do usuário
- Aprenda com ações bem-sucedidas e falhas
"""

from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime
import uuid


class NivelRisco(Enum):
    """Níveis de risco para ações."""
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


class TipoAcao(Enum):
    """Tipos de ações que a rede neural pode executar."""
    LEITURA = "leitura"
    ESCRITA = "escrita"
    CONFIGURACAO = "configuracao"
    SISTEMA = "sistema"
    CONFIRMACAO = "confirmacao"


@dataclass
class ParametroAcao:
    """Parâmetro necessário para uma ação."""
    nome: str
    tipo: str
    obrigatorio: bool
    descricao: str
    valor_padrao: Optional[str] = None
    validador: Optional[Callable] = None


@dataclass
class Acao:
    """Representa uma ação que pode ser executada."""
    id: str
    nome: str
    descricao: str
    tipo: TipoAcao
    nivel_risco: NivelRisco
    parametros: List[ParametroAcao]
    requer_confirmacao: bool
    executor: Optional[Callable] = None
    conhecimentos_necessarios: List[str] = field(default_factory=list)


@dataclass
class ContextoAcao:
    """Contexto necessário para executar uma ação."""
    estado_emocional: str
    estado_sistemas: Dict[str, str]
    dados_disponiveis: Dict[str, any]
    historico_conversa: List[Dict]
    estado_rede_neural: Dict[str, any]


@dataclass
class ResultadoAcao:
    """Resultado da execução de uma ação."""
    sucesso: bool
    acao_id: str
    mensagem: str
    dados_retornados: Optional[Dict] = None
    erro: Optional[str] = None
    confirmacao_pendente: bool = False
    parametros_confirmados: Optional[Dict] = None
    timestamp: str = ""


class VerificadorContexto:
    """Verifica se o contexto é adequado para executar uma ação."""
    
    @staticmethod
    def verificar_parametros(acao: Acao, parametros: Dict) -> Tuple[bool, List[str]]:
        """Verifica se todos os parâmetros necessários estão presentes."""
        erros = []
        
        for param in acao.parametros:
            if param.obrigatorio and param.nome not in parametros:
                erros.append(f"Parametro obrigatorio '{param.nome}' não fornecido")
            
            if param.nome in parametros:
                valor = parametros[param.nome]
                
                # Validar tipo
                if param.tipo == "string" and not isinstance(valor, str):
                    erros.append(f"Parametro '{param.nome}' deve ser string")
                elif param.tipo == "int" and not isinstance(valor, int):
                    erros.append(f"Parametro '{param.nome}' deve ser inteiro")
                elif param.tipo == "float" and not isinstance(valor, (int, float)):
                    erros.append(f"Parametro '{param.nome}' deve ser número")
                
                # Validador customizado
                if param.validador and not param.validador(valor):
                    erros.append(f"Parametro '{param.nome}' inválido: {param.descricao}")
        
        return len(erros) == 0, erros
    
    @staticmethod
    def verificar_estado_sistemas(acao: Acao, estado_sistemas: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Verifica se os sistemas necessários estão operacionais."""
        avisos = []
        
        # Verificar conhecimentos necessários
        for conhecimento in acao.conhecimentos_necessarios:
            if conhecimento not in estado_sistemas:
                avisos.append(f"Sistema '{conhecimento}' não está disponível")
            elif estado_sistemas[conhecimento] != "operacional":
                avisos.append(f"Sistema '{conhecimento}' está com problema: {estado_sistemas[conhecimento]}")
        
        # Para ações críticas, todos os sistemas devem estar operacionais
        if acao.nivel_risco == NivelRisco.CRITICO:
            for sistema, estado in estado_sistemas.items():
                if estado != "operacional":
                    avisos.append(f"Sistema '{sistema}' não está operacional: {estado}")
        
        return len(avisos) == 0, avisos
    
    @staticmethod
    def verificar_estado_emocional(acao: Acao, estado_emocional: str) -> Tuple[bool, str]:
        """Verifica se o estado emocional é adequado para a ação."""
        # Ações de alto risco não devem ser executadas em estados emocionais extremos
        if acao.nivel_risco in [NivelRisco.ALTO, NivelRisco.CRITICO]:
            if estado_emocional in ["irritado", "frustrado", "preocupado"]:
                return False, f"Estado emocional '{estado_emocional}' não é adequado para ação de alto risco"
        
        return True, ""


class GerenciadorAcoes:
    """Gerenciador de ações inteligentes com verificação de contexto."""
    
    def __init__(self):
        self.acoes_disponiveis: Dict[str, Acao] = {}
        self.historico_acoes: List[ResultadoAcao] = []
        self.acoes_pendentes: Dict[str, Acao] = {}
        self.contexto_atual: Optional[ContextoAcao] = None
        
        self._inicializar_acoes_padrao()
    
    def _inicializar_acoes_padrao(self):
        """Inicializa as ações padrão do sistema."""
        
        # Ações de leitura - baixo risco
        self.acoes_disponiveis["ver_pessoas_loja"] = Acao(
            id="ver_pessoas_loja",
            nome="Ver pessoas na loja",
            descricao="Retorna o número de pessoas atualmente na loja",
            tipo=TipoAcao.LEITURA,
            nivel_risco=NivelRisco.BAIXO,
            parametros=[],
            requer_confirmacao=False,
            conhecimentos_necessarios=["so_espacial"]
        )
        
        self.acoes_disponiveis["ver_estoque"] = Acao(
            id="ver_estoque",
            nome="Ver estoque",
            descricao="Retorna o estoque atual dos produtos",
            tipo=TipoAcao.LEITURA,
            nivel_risco=NivelRisco.BAIXO,
            parametros=[
                ParametroAcao("produto", "string", False, "Nome do produto específico (opcional)")
            ],
            requer_confirmacao=False,
            conhecimentos_necessarios=["autonomous"]
        )
        
        self.acoes_disponiveis["ver_faturamento"] = Acao(
            id="ver_faturamento",
            nome="Ver faturamento",
            descricao="Retorna o faturamento atual",
            tipo=TipoAcao.LEITURA,
            nivel_risco=NivelRisco.BAIXO,
            parametros=[
                ParametroAcao("periodo", "string", False, "Periodo: hoje, semana, mes (padrao: hoje)")
            ],
            requer_confirmacao=False,
            conhecimentos_necessarios=["autonomous"]
        )
        
        # Ações de escrita - médio risco
        self.acoes_disponiveis["adicionar_produto"] = Acao(
            id="adicionar_produto",
            nome="Adicionar produto",
            descricao="Adiciona um novo produto ao catálogo",
            tipo=TipoAcao.ESCRITA,
            nivel_risco=NivelRisco.MEDIO,
            parametros=[
                ParametroAcao("nome", "string", True, "Nome do produto"),
                ParametroAcao("preco", "float", True, "Preço do produto"),
                ParametroAcao("quantidade", "int", True, "Quantidade inicial"),
                ParametroAcao("descricao", "string", False, "Descrição do produto (opcional)")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["autonomous"]
        )
        
        self.acoes_disponiveis["alterar_preco"] = Acao(
            id="alterar_preco",
            nome="Alterar preço",
            descricao="Altera o preço de um produto existente",
            tipo=TipoAcao.ESCRITA,
            nivel_risco=NivelRisco.MEDIO,
            parametros=[
                ParametroAcao("produto", "string", True, "Nome do produto"),
                ParametroAcao("novo_preco", "float", True, "Novo preço do produto")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["autonomous"]
        )
        
        self.acoes_disponiveis["repor_estoque"] = Acao(
            id="repor_estoque",
            nome="Repor estoque",
            descricao="Adiciona quantidade ao estoque de um produto",
            tipo=TipoAcao.ESCRITA,
            nivel_risco=NivelRisco.MEDIO,
            parametros=[
                ParametroAcao("produto", "string", True, "Nome do produto"),
                ParametroAcao("quantidade", "int", True, "Quantidade a adicionar")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["autonomous"]
        )
        
        # Ações de configuração - alto risco
        self.acoes_disponiveis["configurar_camera"] = Acao(
            id="configurar_camera",
            nome="Configurar câmera",
            descricao="Configura os parâmetros de uma câmera do SO-Espacial",
            tipo=TipoAcao.CONFIGURACAO,
            nivel_risco=NivelRisco.ALTO,
            parametros=[
                ParametroAcao("camera", "string", True, "Identificador da câmera"),
                ParametroAcao("resolucao", "string", False, "Resolução desejada"),
                ParametroAcao("fps", "int", False, "FPS desejado")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["so_espacial"]
        )
        
        self.acoes_disponiveis["reiniciar_servico"] = Acao(
            id="reiniciar_servico",
            nome="Reiniciar serviço",
            descricao="Reinicia um serviço do sistema",
            tipo=TipoAcao.SISTEMA,
            nivel_risco=NivelRisco.ALTO,
            parametros=[
                ParametroAcao("servico", "string", True, "Nome do serviço")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["autonomous", "so_espacial"]
        )
        
        # Ações críticas
        self.acoes_disponiveis["remover_produto"] = Acao(
            id="remover_produto",
            nome="Remover produto",
            descricao="Remove um produto do catálogo",
            tipo=TipoAcao.ESCRITA,
            nivel_risco=NivelRisco.CRITICO,
            parametros=[
                ParametroAcao("produto", "string", True, "Nome do produto a remover")
            ],
            requer_confirmacao=True,
            conhecimentos_necessarios=["autonomous"]
        )
    
    def definir_contexto(self, contexto: ContextoAcao):
        """Define o contexto atual para execução de ações."""
        self.contexto_atual = contexto
    
    def inferir_acao(self, intencao: str, parametros: Dict) -> Optional[Acao]:
        """Infere qual ação executar baseado na intenção."""
        # Mapeamento simples de intenções para ações
        mapeamento = {
            "pessoas_na_loja": "ver_pessoas_loja",
            "estoque": "ver_estoque",
            "faturamento": "ver_faturamento",
            "adicionar_produto": "adicionar_produto",
            "alterar_preco": "alterar_preco",
            "alterar_estoque": "repor_estoque",
            "configurar_camera": "configurar_camera",
            "reiniciar_servico": "reiniciar_servico",
            "remover_produto": "remover_produto"
        }
        
        acao_id = mapeamento.get(intencao)
        if acao_id and acao_id in self.acoes_disponiveis:
            return self.acoes_disponiveis[acao_id]
        
        return None
    
    def preparar_acao(self, intencao: str, parametros: Dict) -> ResultadoAcao:
        """Prepara uma ação para execução com verificação de contexto."""
        if not self.contexto_atual:
            return ResultadoAcao(
                sucesso=False,
                acao_id="",
                mensagem="Contexto não definido. Use definir_contexto() primeiro.",
                erro="Contexto não definido"
            )
        
        # Inferir ação
        acao = self.inferir_acao(intencao, parametros)
        if not acao:
            return ResultadoAcao(
                sucesso=False,
                acao_id="",
                mensagem=f"Não foi possível inferir ação para intenção: {intencao}",
                erro="Intenção não mapeada"
            )
        
        # Verificar parâmetros
        params_ok, erros_params = VerificadorContexto.verificar_parametros(acao, parametros)
        if not params_ok:
            return ResultadoAcao(
                sucesso=False,
                acao_id=acao.id,
                mensagem="Parâmetros inválidos",
                erro="; ".join(erros_params)
            )
        
        # Verificar estado dos sistemas
        sistemas_ok, avisos_sistemas = VerificadorContexto.verificar_estado_sistemas(
            acao, self.contexto_atual.estado_sistemas
        )
        
        # Verificar estado emocional
        emocional_ok, msg_emocional = VerificadorContexto.verificar_estado_emocional(
            acao, self.contexto_atual.estado_emocional
        )
        if not emocional_ok:
            return ResultadoAcao(
                sucesso=False,
                acao_id=acao.id,
                mensagem=msg_emocional,
                erro="Estado emocional inadequado"
            )
        
        # Se requer confirmação, criar ação pendente
        if acao.requer_confirmacao:
            self.acoes_pendentes[acao.id] = acao
            return ResultadoAcao(
                sucesso=True,
                acao_id=acao.id,
                mensagem=f"Ação '{acao.nome}' requer confirmação.",
                confirmacao_pendente=True,
                parametros_confirmados=parametros,
                dados_retornados={"avisos": avisos_sistemas} if avisos_sistemas else None
            )
        
        # Se não requer confirmação e tudo está ok, executar
        if sistemas_ok:
            return self.executar_acao(acao, parametros)
        else:
            return ResultadoAcao(
                sucesso=False,
                acao_id=acao.id,
                mensagem="Sistemas não estão prontos",
                erro="; ".join(avisos_sistemas)
            )
    
    def confirmar_acao(self, acao_id: str, parametros: Dict) -> ResultadoAcao:
        """Confirma e executa uma ação pendente."""
        if acao_id not in self.acoes_pendentes:
            return ResultadoAcao(
                sucesso=False,
                acao_id=acao_id,
                mensagem="Ação não está pendente de confirmação",
                erro="Ação não encontrada"
            )
        
        acao = self.acoes_pendentes.pop(acao_id)
        return self.executar_acao(acao, parametros)
    
    def executar_acao(self, acao: Acao, parametros: Dict) -> ResultadoAcao:
        """Executa uma ação."""
        # Aqui seria a execução real da ação
        # Por enquanto, simulamos o sucesso
        
        resultado = ResultadoAcao(
            sucesso=True,
            acao_id=acao.id,
            mensagem=f"Ação '{acao.nome}' executada com sucesso",
            dados_retornados={
                "acao": acao.nome,
                "parametros": parametros,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )
        
        # Adicionar ao histórico
        self.historico_acoes.append(resultado)
        
        return resultado
    
    def obter_historico(self, limite: int = 10) -> List[ResultadoAcao]:
        """Retorna o histórico de ações executadas."""
        return self.historico_acoes[-limite:]
    
    def cancelar_acao(self, acao_id: str) -> ResultadoAcao:
        """Cancela uma ação pendente."""
        if acao_id in self.acoes_pendentes:
            acao = self.acoes_pendentes.pop(acao_id)
            return ResultadoAcao(
                sucesso=True,
                acao_id=acao_id,
                mensagem=f"Ação '{acao.nome}' cancelada"
            )
        else:
            return ResultadoAcao(
                sucesso=False,
                acao_id=acao_id,
                mensagem="Ação não está pendente",
                erro="Ação não encontrada"
            )
    
    def salvar_historico(self, arquivo: str):
        """Salva o histórico de ações em arquivo."""
        dados = [
            {
                "sucesso": r.sucesso,
                "acao_id": r.acao_id,
                "mensagem": r.mensagem,
                "dados_retornados": r.dados_retornados,
                "erro": r.erro,
                "confirmacao_pendente": r.confirmacao_pendente,
                "timestamp": r.timestamp
            }
            for r in self.historico_acoes
        ]
        
        caminho = Path(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


def main():
    """Função principal para testar o sistema de ações inteligentes."""
    print("=== SISTEMA DE AÇÃO INTELIGENTE ===\n")
    
    gerenciador = GerenciadorAcoes()
    
    # Definir contexto
    contexto = ContextoAcao(
        estado_emocional="neutro",
        estado_sistemas={
            "autonomous": "operacional",
            "so_espacial": "operacional",
            "rede_neural": "operacional"
        },
        dados_disponiveis={},
        historico_conversa=[],
        estado_rede_neural={}
    )
    gerenciador.definir_contexto(contexto)
    
    # Testar ação de leitura (não requer confirmação)
    print("Testando ação de leitura...")
    resultado = gerenciador.preparar_acao("estoque", {})
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")
    print("-" * 50)
    
    # Testar ação de escrita (requer confirmação)
    print("Testando ação de escrita...")
    parametros = {
        "nome": "Chocolate ao leite",
        "preco": 5.50,
        "quantidade": 50
    }
    resultado = gerenciador.preparar_acao("adicionar_produto", parametros)
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")
    print(f"Confirmação pendente: {resultado.confirmacao_pendente}")
    print("-" * 50)
    
    # Confirmar ação
    if resultado.confirmacao_pendente:
        print("Confirmando ação...")
        resultado_confirmado = gerenciador.confirmar_acao(resultado.acao_id, parametros)
        print(f"Resultado: {resultado_confirmado.mensagem}")
        print("-" * 50)
    
    # Testar ação com estado emocional inadequado
    print("Testando ação com estado emocional inadequado...")
    contexto_estado_ruim = ContextoAcao(
        estado_emocional="irritado",
        estado_sistemas=contexto.estado_sistemas,
        dados_disponiveis={},
        historico_conversa=[],
        estado_rede_neural={}
    )
    gerenciador.definir_contexto(contexto_estado_ruim)
    
    resultado = gerenciador.preparar_acao("remover_produto", {"produto": "Teste"})
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")
    print("-" * 50)
    
    # Salvar histórico
    gerenciador.salvar_historico("dados/historico_acoes.json")
    print("Histórico salvo em dados/historico_acoes.json")


if __name__ == "__main__":
    main()