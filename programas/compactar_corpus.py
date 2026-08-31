"""Compacta o corpus removendo redundância semântica.

O corpus atual tem 593 perguntas com muitas variações quase idênticas.
Isso ocupa espaço desnecessário no modelo e não adiciona valor.

ESTRATÉGIA DE COMPACTAÇÃO:

1. Agrupar perguntas semelhantes usando similaridade de trigramas
2. Manter apenas as mais representativas de cada grupo
3. Criar um sistema de geração automática de variações
4. Expandir para incluir os novos sistemas (Sistema Espacial SO, Cliente, API)

"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rede.texto import normalizar, pedacos

RAIZ = Path(__file__).resolve().parents[1]
CORPUS = RAIZ / "dados" / "perguntas.jsonl"
CORPUS_COMPACTADO = RAIZ / "dados" / "perguntas_compactado.jsonl"
CORPUS_EXPANDIDO = RAIZ / "dados" / "perguntas_expandido.jsonl"


def similaridade_trigramas(p1, p2):
    """Similaridade baseada em trigramas compartilhados."""
    pecas1 = set(pedacos(p1))
    pecas2 = set(pedacos(p2))
    
    if not pecas1 or not pecas2:
        return 0.0
    
    intersecao = pecas1 & pecas2
    uniao = pecas1 | pecas2
    
    return len(intersecao) / len(uniao) if uniao else 0.0


def agrupar_similares(perguntas, limiar=0.7):
    """Agrupa perguntas semelhantes."""
    grupos = []
    usadas = set()
    
    for i, p1 in enumerate(perguntas):
        if i in usadas:
            continue
        
        grupo = [i]
        for j, p2 in enumerate(perguntas):
            if j in usadas or i == j:
                continue
            
            if similaridade_trigramas(p1["pergunta"], p2["pergunta"]) >= limiar:
                grupo.append(j)
                usadas.add(j)
        
        grupos.append(grupo)
        usadas.add(i)
    
    return grupos


def selecionar_representante(grupo, perguntas):
    """Seleciona a pergunta mais representativa do grupo."""
    if len(grupo) == 1:
        return perguntas[grupo[0]]
    
    # Escolhe a mais média em comprimento
    comprimentos = [len(perguntas[i]["pergunta"]) for i in grupo]
    idx_medio = comprimentos.index(min(comprimentos, key=lambda x: abs(x - sum(comprimentos)/len(comprimentos))))
    
    return perguntas[grupo[idx_medio]]


def compactar_corpus():
    """Compacta o corpus removendo redundâncias."""
    print("Carregando corpus atual...")
    with open(CORPUS, encoding="utf-8") as f:
        perguntas = [json.loads(l) for l in f]
    
    print(f"Total: {len(perguntas)} perguntas")
    
    # Agrupar por intenção primeiro
    por_intencao = defaultdict(list)
    for i, p in enumerate(perguntas):
        por_intencao[p["intencao"]].append((i, p))
    
    compactado = []
    removidas = 0
    
    for intencao, itens in por_intencao.items():
        print(f"\nProcessando {intencao}: {len(itens)} perguntas")
        
        # Agrupar similares dentro da mesma intenção
        indices = [i for i, _ in itens]
        perguntas_intencao = [p for _, p in itens]
        
        grupos = agrupar_similares(perguntas_intencao, limiar=0.6)
        
        print(f"  Reduziu de {len(itens)} para {len(grupos)} grupos")
        
        for grupo in grupos:
            representante = selecionar_representante(grupo, perguntas_intencao)
            compactado.append(representante)
            removidas += len(grupo) - 1
    
    print(f"\nRemovidas: {removidas} perguntas redundantes")
    print(f"Compactado: {len(compactado)} perguntas ({100*len(compactado)/len(perguntas):.1f}% do original)")
    
    # Salvar compactado
    CORPUS_COMPACTADO.parent.mkdir(exist_ok=True)
    with open(CORPUS_COMPACTADO, "w", encoding="utf-8") as f:
        for p in compactado:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    
    print(f"Salvo: {CORPUS_COMPACTADO.name}")
    
    return compactado


def gerar_novas_intencoes():
    """Gera novas intenções para melhorar integração Autonomous + SO Espacial."""
    
    novas = [
        # Integração mais profunda entre os sistemas
        {"pergunta": "coordenação entre sistemas", "intencao": "integracao_sistemas", "origem": "gerente"},
        {"pergunta": "os sistemas estão sincronizados", "intencao": "integracao_sistemas", "origem": "gerente"},
        {"pergunta": "comunicação entre loja e espacial", "intencao": "integracao_sistemas", "origem": "gerente"},
        
        # Análises combinadas dos dois sistemas
        {"pergunta": "pessoas vs carrinhos", "intencao": "analise_combinada", "origem": "gerente"},
        {"pergunta": "conflito entre rastros e sessões", "intencao": "analise_combinada", "origem": "gerente"},
        {"pergunta": "pessoas sem sessão", "intencao": "analise_combinada", "origem": "gerente"},
        
        # Cliente (Mobile App)
        {"pergunta": "meu carrinho", "intencao": "meu_carrinho", "origem": "cliente"},
        {"pergunta": "minhas compras", "intencao": "meu_carrinho", "origem": "cliente"},
        {"pergunta": "o que estou comprando", "intencao": "meu_carrinho", "origem": "cliente"},
        
        {"pergunta": "pagar agora", "intencao": "pagamento", "origem": "cliente"},
        {"pergunta": "finalizar compra", "intencao": "pagamento", "origem": "cliente"},
        {"pergunta": "checkout", "intencao": "pagamento", "origem": "cliente"},
        
        {"pergunta": "entrar na loja", "intencao": "entrada_loja", "origem": "cliente"},
        {"pergunta": "abrir portão", "intencao": "entrada_loja", "origem": "cliente"},
        {"pergunta": "liberar acesso", "intencao": "entrada_loja", "origem": "cliente"},
        
        # API (Integração técnica)
        {"pergunta": "status da api", "intencao": "status_api", "origem": "api"},
        {"pergunta": "api funcionando", "intencao": "status_api", "origem": "api"},
        {"pergunta": "endpoint disponível", "intencao": "status_api", "origem": "api"},
        
        {"pergunta": "logs do sistema", "intencao": "logs_sistema", "origem": "api"},
        {"pergunta": "ver logs", "intencao": "logs_sistema", "origem": "api"},
        {"pergunta": "erro no sistema", "intencao": "logs_sistema", "origem": "api"},
        
        # ===== NOVAS INTENÇÕES DE AUTONOMIA =====
        
        # Operações de escrita - adicionar
        {"pergunta": "adiciona um produto novo", "intencao": "adicionar_produto", "origem": "agente"},
        {"pergunta": "criar novo produto", "intencao": "adicionar_produto", "origem": "agente"},
        {"pergunta": "cadastrar produto", "intencao": "adicionar_produto", "origem": "agente"},
        {"pergunta": "novo item no estoque", "intencao": "adicionar_produto", "origem": "agente"},
        
        # Operações de escrita - alterar
        {"pergunta": "alterar preço do produto", "intencao": "alterar_preco", "origem": "agente"},
        {"pergunta": "mudar valor", "intencao": "alterar_preco", "origem": "agente"},
        {"pergunta": "atualizar preço", "intencao": "alterar_preco", "origem": "agente"},
        {"pergunta": "modificar preço", "intencao": "alterar_preco", "origem": "agente"},
        
        {"pergunta": "alterar estoque", "intencao": "alterar_estoque", "origem": "agente"},
        {"pergunta": "atualizar quantidade", "intencao": "alterar_estoque", "origem": "agente"},
        {"pergunta": "corrigir estoque", "intencao": "alterar_estoque", "origem": "agente"},
        {"pergunta": "mudar quantidade", "intencao": "alterar_estoque", "origem": "agente"},
        
        # Operações de escrita - remover
        {"pergunta": "remover produto", "intencao": "remover_produto", "origem": "agente"},
        {"pergunta": "apagar item", "intencao": "remover_produto", "origem": "agente"},
        {"pergunta": "excluir produto", "intencao": "remover_produto", "origem": "agente"},
        {"pergunta": "deletar produto", "intencao": "remover_produto", "origem": "agente"},
        
        # Operações de configuração - câmeras
        {"pergunta": "adicionar câmera", "intencao": "configurar_camera", "origem": "agente"},
        {"pergunta": "nova câmera", "intencao": "configurar_camera", "origem": "agente"},
        {"pergunta": "configurar câmera", "intencao": "configurar_camera", "origem": "agente"},
        {"pergunta": "instalar câmera", "intencao": "configurar_camera", "origem": "agente"},
        
        # Operações de configuração - sistema
        {"pergunta": "configurar sistema", "intencao": "configurar_sistema", "origem": "agente"},
        {"pergunta": "alterar configuração", "intencao": "configurar_sistema", "origem": "agente"},
        {"pergunta": "mudar settings", "intencao": "configurar_sistema", "origem": "agente"},
        {"pergunta": "ajustar configuração", "intencao": "configurar_sistema", "origem": "agente"},
        
        # Operações de sistema
        {"pergunta": "reiniciar serviço", "intencao": "reiniciar_servico", "origem": "agente"},
        {"pergunta": "reiniciar sistema", "intencao": "reiniciar_servico", "origem": "agente"},
        {"pergunta": "restart no serviço", "intencao": "reiniciar_servico", "origem": "agente"},
        
        # Confirmação e aprovação
        {"pergunta": "confirmar operação", "intencao": "confirmar_acao", "origem": "agente"},
        {"pergunta": "pode prosseguir", "intencao": "confirmar_acao", "origem": "agente"},
        {"pergunta": "está certo", "intencao": "confirmar_acao", "origem": "agente"},
        {"pergunta": "aprovar", "intencao": "confirmar_acao", "origem": "agente"},
        
        # Cancelamento
        {"pergunta": "cancelar operação", "intencao": "cancelar_operacao", "origem": "agente"},
        {"pergunta": "não fazer", "intencao": "cancelar_operacao", "origem": "agente"},
        {"pergunta": "desistir", "intencao": "cancelar_operacao", "origem": "agente"},
        {"pergunta": "parar", "intencao": "cancelar_operacao", "origem": "agente"},
        
        # Escolha de solução
        {"pergunta": "tentar primeira solução", "intencao": "escolher_solucao", "origem": "agente"},
        {"pergunta": "usar solução 1", "intencao": "escolher_solucao", "origem": "agente"},
        {"pergunta": "tentar correção automática", "intencao": "escolher_solucao", "origem": "agente"},
    ]
    
    return novas


def expandir_corpus(compactado):
    """Expande o corpus com novas intenções."""
    novas = gerar_novas_intencoes()
    
    expandido = compactado + novas
    
    print(f"\nAdicionadas {len(novas)} novas intenções")
    print(f"Total expandido: {len(expandido)} perguntas")
    
    # Salvar expandido
    CORPUS_EXPANDIDO.parent.mkdir(exist_ok=True)
    with open(CORPUS_EXPANDIDO, "w", encoding="utf-8") as f:
        for p in expandido:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    
    print(f"Salvo: {CORPUS_EXPANDIDO.name}")
    
    return expandido


def main():
    print("=== COMPACTAÇÃO E EXPANSÃO DO CORPUS ===\n")
    
    # Compactar
    compactado = compactar_corpus()
    
    # Expandir
    expandido = expandir_corpus(compactado)
    
    print("\n=== ESTATÍSTICAS FINAIS ===")
    print(f"Original:     593 perguntas")
    print(f"Compactado:   {len(compactado)} perguntas ({100*len(compactado)/593:.1f}%)")
    print(f"Expandido:     {len(expandido)} perguntas ({100*len(expandido)/593:.1f}%)")
    print(f"Economia:     {593 - len(compactado)} perguntas removidas")
    print(f"Novas funcs:  {len(expandido) - len(compactado)} intenções adicionadas")


if __name__ == "__main__":
    main()