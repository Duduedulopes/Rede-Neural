# Rede Neural

**Gerente virtual inteligente para loja autônoma — integração natural entre sistemas**

Classificação de intenção × sistema de permissões × personalidade adaptativa

Eduardo Lopes, 2026 — MIT, ver [`LICENSE`](LICENSE)

---

## O problema

O sistema da loja autônoma sabe **o quê** foi levado por RFID, mas não sabe **quem** levou** nem como o gesto foi executado.

O sistema SO-Espacial sabe **como** o gesto foi executado por câmeras, mas não tem acesso ao **conteúdo** dos produtos nem ao sistema de vendas.

As duas leituras do mesmo gesto ainda não se falam: cada sistema opera sozinho, e a reconciliação entre elas é a próxima decisão de arquitetura, não um trabalho de encanamento pendente.

## A solução

**Um gerente virtual que entende a pergunta certa.**

Uma rede neural escrita do zero em NumPy que:
- Classifica intenção em linguagem natural imperfeita
- Infere contexto a partir dos dados disponíveis
- Sistema de permissões para ações de modificação
- Personalidade adaptativa com detecção emocional
- Loop de feedback inteligente e correção de erros
- Integra os sistemas Smart Store e SO-Espacial

> "O que é mais difícil na ciência de dados é qual é a pergunta certa"

---

## Arquitetura

```
   USUÁRIO           INTENÇÃO            AGENTE               SISTEMAS
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐
│  pergunta    │   │  classificador│   │  permissões  │   │  Smart Store│
│  natural     │──▶│  embeddings  │──▶│  personalidade│──▶│  API + RFID │
│  imperfeita  │   │  softmax     │   │  feedback     │   │  (NET 8)    │
└──────────────┘   └──────────────┘   └──────────────┘   └─────────────┘
                     corpus de         inferência de       SO-Espacial
                     31 intenções      contexto            (Python)
```

**Três camadas de segurança:**

1. **Classificação de intenção** — rede neural com embeddings de trigramas
2. **Sistema de permissões** — níveis de risco e confirmação explícita
3. **Personalidade adaptativa** — tom de voz apropriado ao contexto

---

## Pilha tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ (treino), C# (execução) |
| Rede neural | NumPy (from scratch) |
| Classificação | Embeddings de trigramas, camada oculta, softmax |
| Treinamento | Descida do gradiente estocástica, validação cruzada |
| Corpus | 592 frases, 31 intenções |
| Interface | Monitor em tempo real, chat Blazor |
| Testes | pytest |

---

## Estrutura

```
Rede-Neural/
├─ rede/              A BIBLIOTECA — nenhum arquivo aqui tem main()
│   ├─ classificador.py    classificador de intenção
│   ├─ texto.py            normalização e trigramas
│   ├─ embutimento.py      embedding table
│   ├─ previsor.py         prévio de tokens
│   ├─ retropropagacao.py  gradiente
│   ├─ treino.py           SGD e minilotes
│   └─ rede.py             rede neural completa
├─ programas/         O QUE SE EXECUTA — nenhum e importado
│   ├─ treinar_intencao.py
│   ├─ treinar_gerente.py
│   ├─ compactar_corpus.py
│   ├─ gerar_corpus_robusto.py
│   ├─ calibrar_limiar.py
│   └─ gerar_conferencia.py
├─ dados/             perguntas.jsonl, correcoes.jsonl
├─ modelos/           intencao.json, pesos treinados
├─ monitor/           servidor de monitoramento em tempo real
├─ testes/            pytest
├─ caderno/           anotacoes, uma por dia
└─ provas/            casos de teste em C#
```

**Duas regras:** um arquivo é **biblioteca ou programa, nunca os dois**; e
nenhum caminho fica cravado no código.

---

## Estado atual

**Gerente virtual funcional com classificação de intenção.**

O caminho crítico opera de ponta a ponta: usuário faz pergunta em linguagem natural, rede neural classifica intenção, sistema de permissões avalia risco, personalidade gera resposta apropriada, e ação é confirmada antes de executar.

### O que foi medido, não estimado

| | antes | depois | o que era |
|---|---|---|---|
| intenções | 14 | **31** | expansão para operações administrativas |
| frases | 593 | **592** | compactação de corpus sem perda de significado |
| acurácia | 60.8% | **50.1%** | muitas novas intenções com poucos exemplos |
| peças de texto | 608 | **996** | expansão do vocabulário |

### O que ainda não funciona, dito com número

Ser honesto aqui vale mais que parecer pronto:

- **Acurácia de 50.1% ainda baixa para operações críticas.** Precisa de mais exemplos balanceados.
- **Corpus robusto ainda não gerado.** Script de variações com erros precisa ser executado.
- **Sistema de confirmação multi-etapas não testado.** Fluxo completo ainda não validado.
- **Integração com SO-Espacial ainda é leitura apenas.** Ações de configuração não executam automaticamente.

---

## Roteiro

Cada degrau funciona e demonstra sozinho. Nada depende de terminar tudo.

- [x] **0 · Esqueleto da rede** — camadas, ativação, custo, retropropagação
- [x] **1 · Classificador de intenção** — embeddings, softmax, 31 intenções
- [x] **2 · Sistema de permissões** — níveis de risco, confirmação explícita
- [x] **3 · Personalidade adaptativa** — tom de voz, detecção emocional
- [x] **4 · Loop de feedback** — correção de erros, aprendizado
- [x] **5 · Monitor em tempo real** — servidor local, painel web
- [~] **6 · Corpus robusto** — variações com erros, gírias, abreviações
- [ ] **7 · Acurácia operacional** — retreino com corpus balanceado
- [ ] **8 · Integração completa** — leitura e escrita em ambos sistemas
- [ ] **9 · Deploy em produção** — ambiente de loja real

---

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
python programas\treinar_intencao.py
pytest
```

Para o monitor em tempo real:

```powershell
python programas\ao_vivo.py
```

---

## Projetos relacionados

Este projeto é **o gerente virtual inteligente** que coordena os dois sistemas:

- **[LOJA-AUT-NOMA-PRO](https://github.com/Duduedulopes/LOJA-AUT-NOMA-PRO)** — a loja autônoma em .NET 8 — API, apps Blazor, firmware ESP32. Este sistema usa RFID para identificar itens e contar o que sai do portal, mas não sabe quem pegou nem de qual prateleira.

- **[SO-Espacial](https://github.com/Duduedulopes/SO-Espacial)** — a percepção espacial por câmeras — o gêmeo digital da loja. Este é um projeto separado em Python que usa visão computacional e geometria projetiva para entender gestos e movimentos.

As duas leituras do mesmo gesto ainda não se falam: cada sistema opera sozinho, e a reconciliação entre elas é a próxima decisão de arquitetura, não um trabalho de encanamento pendente.

**Site do projeto:** https://smart-store.contato-dudulopes.workers.dev
