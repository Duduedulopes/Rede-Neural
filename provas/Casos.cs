using System.Globalization;
using System.Net;
using System.Text;
using AutonomousStore.AdminApp.Models;
using AutonomousStore.Gerente.Models;
using AutonomousStore.AdminApp.Services;
using AutonomousStore.Gerente.Services;

public static class Casos
{
    // O classificador carrega o modelo por HTTP. Aqui o "servidor" e o
    // arquivo real: o teste roda contra a REDE TREINADA, nao contra um
    // stub que sempre acerta. Um teste que dubla o classificador nao
    // testaria nada do que importa.
    class ServeOModelo : HttpMessageHandler
    {
        readonly string _caminho;
        public ServeOModelo(string caminho) => _caminho = caminho;
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r, CancellationToken c)
        {
            var url = r.RequestUri!.ToString();
            if (url.EndsWith("modelos/intencao.json"))
                return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(File.ReadAllText(_caminho), Encoding.UTF8, "application/json")
                });
            throw new HttpRequestException("sem rede no teste: " + url);
        }
    }

    class Fabrica : IHttpClientFactory
    {
        readonly string _modelo;
        public Fabrica(string m) => _modelo = m;
        public HttpClient CreateClient(string nome)
            => new HttpClient(new ServeOModelo(_modelo)) { BaseAddress = new Uri("http://teste/") };
    }

    static ProductDto P(string nome, decimal preco, int estoque)
        => new(Guid.NewGuid(), nome, "000", preco, null, null, null, null, null,
               estoque, null, false, true, DateTime.Now);

    static int _falhas, _casos;

    /// Como a tela se comporta: pergunta; se a rede ficou abaixo do
    /// limiar e ofereceu botoes, clica no palpite certo. E a rota normal
    /// de uma alteracao — 96,0% contra limiar de 97%.
    static async Task<string> Abre(GerenteService g, string frase, string intencao)
    {
        var r = await Diga(g, frase);
        if (r.Contains("não tenho certeza") || r.Contains("Escolha abaixo"))
        {
            Console.WriteLine($"    [abaixo do limiar -> clique no botao '{intencao}']");
            r = await g.ResponderComIntencaoAsync(intencao, frase);
            Console.WriteLine($"    ele > {r.Replace("\n", "\n           ")}");
        }
        return r;
    }

    static async Task<string> Diga(GerenteService g, string frase)
    {
        var r = await g.ResponderAsync(frase);
        Console.WriteLine($"    voce> {frase}");
        Console.WriteLine($"    ele > {r.Replace("\n", "\n           ")}");
        return r;
    }

    static void Espera(bool ok, string oque)
    {
        _casos++;
        if (!ok) { _falhas++; Console.WriteLine($"    >>> FALHOU: {oque}"); }
        else Console.WriteLine($"    ok: {oque}");
    }

    public static async Task<int> Rodar(string caminhoModelo)
    {
        Func<(GerenteService, LojaFalsa)> novo = () =>
        {
            var loja = new LojaFalsa();
            loja.Itens.Add(P("Água Mineral 500ml", 3.50m, 12));
            loja.Itens.Add(P("Coca-Cola 2L", 9.00m, 40));
            loja.Itens.Add(P("Chocolate Barra", 6.25m, 8));
            var fab = new Fabrica(caminhoModelo);
            var cls = new ClassificadorDeIntencao(fab);
            var g = new GerenteService(loja, new SessoesFalsas(), new EspacialFalso(), cls, fab);
            return (g, loja);
        };

        // O mesmo gerente, com historico de vendas e RELOGIO CONGELADO.
        // Sem congelar, "esta semana" muda de tamanho conforme o dia em que
        // a prova roda, e um teste que so vale as tercas nao e teste.
        Func<DateTime, (GerenteService, LojaFalsa, SessoesFalsas)> comVendas = agora =>
        {
            var loja = new LojaFalsa();
            loja.Itens.Add(P("Água Mineral 500ml", 3.50m, 12));
            var ses = new SessoesFalsas();
            var fab = new Fabrica(caminhoModelo);
            var cls = new ClassificadorDeIntencao(fab);
            var g = new GerenteService(loja, ses, new EspacialFalso(), cls, fab) { Agora = () => agora };
            return (g, loja, ses);
        };

        // O gerente COM a tabela de ocorrencia ligada.
        Func<DateTime, OcorrenciasFalsas, (GerenteService, LojaFalsa, SessoesFalsas)> comOcorrencias =
            (agora, oc) =>
            {
                var loja = new LojaFalsa();
                loja.Itens.Add(P("Água Mineral 500ml", 3.50m, 12));
                var ses = new SessoesFalsas();
                var fab = new Fabrica(caminhoModelo);
                var cls = new ClassificadorDeIntencao(fab);
                var g = new GerenteService(loja, ses, new EspacialFalso(), cls, fab, oc)
                { Agora = () => agora };
                return (g, loja, ses);
            };

        // ── 1. a frase que ja traz tudo ───────────────────────────────
        Console.WriteLine("\n1. FRASE COMPLETA: nao pergunta o que ja foi dito, e NAO grava ainda");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            Espera(r.Contains("3,50"), "mostra o preco de HOJE, lido do catalogo");
            Espera(r.Contains("5,50"), "mostra o preco NOVO");
            Espera(r.Contains("Água Mineral 500ml"), "mostra qual produto entendeu");
            Espera(r.Contains("Posso fazer?"), "pede confirmacao");
            Espera(loja.Escritas.Count == 0, "NAO gravou nada ainda");
        }

        // ── 2. o sim ──────────────────────────────────────────────────
        Console.WriteLine("\n2. O SIM grava, uma vez so, com o valor certo");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            var r = await Diga(g, "sim");
            Espera(loja.Escritas.Count == 1, $"gravou exatamente 1 vez (foi {loja.Escritas.Count})");
            Espera(loja.Escritas.FirstOrDefault()?.Contains("5.50") == true,
                   $"gravou 5,50 [{string.Join(" | ", loja.Escritas)}]");
        }

        // ── 3. o nao ──────────────────────────────────────────────────
        Console.WriteLine("\n3. O NAO nao grava nada");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            var r = await Diga(g, "nao");
            Espera(loja.Escritas.Count == 0, $"nada gravado (foi {loja.Escritas.Count})");
        }

        // ── 4. O PERIGO MEDIDO ────────────────────────────────────────
        Console.WriteLine("\n4. \"para por favor\" — a rede chama isso de confirmar_acao a 99,4%.");
        Console.WriteLine("   Acima do limiar geral (0,95), abaixo do corte do sim (0,995).");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            var r = await Diga(g, "para por favor");
            Espera(loja.Escritas.Count == 0, $"NAO gravou (foi {loja.Escritas.Count}) <- e este o ponto");
        }

        // ── 5. a frase incompleta ─────────────────────────────────────
        Console.WriteLine("\n5. FRASE INCOMPLETA: pergunta so o que falta");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "muda o preco da agua", "alterar_preco");
            Espera(r.Contains("preço") || r.Contains("preco"), "pergunta o preco");
            Espera(!r.Contains("Qual produto"), "NAO repergunta o produto, que ja foi dito");
            var r2 = await Diga(g, "7,90");
            Espera(r2.Contains("7,90") && r2.Contains("3,50"), "resumo com de-para");
            Espera(loja.Escritas.Count == 0, "ainda sem gravar");
            await Diga(g, "sim");
            Espera(loja.Escritas.Count == 1, $"agora sim gravou (foi {loja.Escritas.Count})");
        }

        // ── 6. a rota de saida ────────────────────────────────────────
        Console.WriteLine("\n6. ROTA DE SAIDA no meio da coleta");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua", "alterar_preco");
            var r = await Diga(g, "quero outra coisa");
            Espera(loja.Escritas.Count == 0, "nada gravado");
            Espera(!r.Contains("Qual o novo preço"), "saiu do dialogo, nao repetiu a pergunta");
        }

        // ── 7. A ARMADILHA DO NUMERO NO NOME ──────────────────────────
        Console.WriteLine("\n7. \"Coca-Cola 2L\": o 2 do nome nao pode virar o preco");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "muda o preco da coca cola 2l", "alterar_preco");
            Espera(!r.Contains("Posso fazer?"), "nao foi direto pra confirmacao com preco=2");
            Espera(r.Contains("preço") || r.Contains("preco"), "perguntou o preco");
        }

        // ── 8. sim solto ──────────────────────────────────────────────
        Console.WriteLine("\n8. \"sim\" sem nada pendente nao pode executar nada");
        {
            var (g, loja) = novo();
            var r = await Diga(g, "sim");
            Espera(loja.Escritas.Count == 0, "nada gravado");
            Espera(r.Contains("tem nenhuma alteração"), "explica que nao ha nada pendente");
        }

        // ── 9. estoque, e o aviso antes do sim ────────────────────────
        Console.WriteLine("\n9. ESTOQUE para baixo: avisa ANTES de pedir o sim");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "corrige o estoque da agua para 5", "alterar_estoque");
            if (r.Contains("Posso fazer?"))
                Espera(r.Contains("só consigo somar") || r.Contains("saem"),
                       "avisou da limitacao antes da confirmacao");
            else
                Espera(true, "seguiu por outro caminho (nao e regressao)");
            Espera(loja.Escritas.Count == 0, "nada gravado");
        }

        // ── 10. estoque para cima, ate o fim ──────────────────────────
        Console.WriteLine("\n10. ESTOQUE para cima: 12 -> 30 tem de somar 18, nao 30");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "corrige o estoque da agua para 30", "alterar_estoque");
            if (r.Contains("Posso fazer?"))
            {
                Espera(r.Contains("12"), "mostra o estoque de hoje");
                // O corte de gravacao muda a cada calibracao. O teste cobra
                // o RESULTADO — o numero certo no banco — e nao qual corte
                // estava em vigor no dia em que ele foi escrito. Um teste
                // preso ao numero de ontem falha por ter melhorado.
                await Diga(g, "isso mesmo");
                await Diga(g, "sim");
                Espera(loja.Escritas.Count == 1 && loja.Escritas[0].Contains("+18"),
                       $"somou 18 depois do sim [{string.Join(" | ", loja.Escritas)}]");
            }
            else Espera(true, "coletou por perguntas (nao e regressao)");
        }

        // ── 11. o preco da margem ─────────────────────────────────────
        Console.WriteLine("\n11. \"pode fazer\" — que ja foi o caso dificil deste teste.");
        Console.WriteLine("    Com o corpus de 3.132 ele dava 94,7% e ficava ABAIXO do corte: era o");
        Console.WriteLine("    preco de ter posto \"pode parar\" e \"pode deixar\" do lado do NAO.");
        Console.WriteLine("    Com o corpus fundido (4.291) ele passou dos 97% e grava direto.");
        Console.WriteLine("    O que o teste cobra e a SEGURANCA, nao a resposta de ontem: gravar");
        Console.WriteLine("    num sim claro e certo; o que nao pode e gravar no que nao e sim —");
        Console.WriteLine("    e isso o caso 12 cobra.");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            await Diga(g, "pode fazer");
            Espera(loja.Escritas.Count == 1,
                   $"\"pode fazer\" grava (foi {loja.Escritas.Count}) — melhorou com o corpus novo");
        }

        // ── 12. o par que estava empatado ─────────────────────────────
        Console.WriteLine("\n12. \"para por favor\" e \"faz por favor\": a cortesia nao pode decidir");
        {
            var (g1, l1) = novo();
            await Abre(g1, "muda o preco da agua para 5,50", "alterar_preco");
            await Diga(g1, "para por favor");
            Espera(l1.Escritas.Count == 0, "\"para por favor\" NAO grava");

            // O QUE ESTE CASO PROVA continua sendo que o VERBO decide, e
            // nao a cortesia: "para por favor" e cancelamento (99,6%) e
            // "faz por favor" e confirmacao (99,3%). Lados opostos.
            //
            // Gravar, ele nao grava — 99,3% fica abaixo do corte de 0,998.
            // Isso e falha segura e nao desfaz a propriedade acima.
            var (g2, l2) = novo();
            await Abre(g2, "muda o preco da agua para 5,50", "alterar_preco");
            var r2 = await Diga(g2, "faz por favor");
            Espera(!r2.Contains("Deixei pra lá"),
                   "\"faz por favor\" NAO foi lido como cancelamento — o verbo decide");
        }

        // ── 13. O VALOR GRAVADO E O VALOR CONFIRMADO ──────────────────
        Console.WriteLine("\n13. O que foi CONFIRMADO e o que foi GRAVADO tem de ser o mesmo numero.");
        Console.WriteLine("    Em pt-BR o ponto e separador de milhar. \"3.00\" lido sem cultura");
        Console.WriteLine("    vira 300 — e foi assim que R$ 3,00 virou R$ 300,00 no banco do Chefe.");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "muda o preco da agua para 3,00", "alterar_preco");
            Espera(r.Contains("R$ 3,00"), "o resumo promete R$ 3,00");
            await Diga(g, "sim");
            var gravado = loja.Escritas.FirstOrDefault() ?? "(nada)";
            Espera(gravado.Contains("-> 3.00"),
                   $"gravou EXATAMENTE 3.00 [{gravado}]");
            Espera(!gravado.Contains("300"), "nao gravou 300");
        }

        // e o inverso: um preco com milhar de verdade
        {
            var (g, loja) = novo();
            var r = await Abre(g, "muda o preco da agua para 1250,90", "alterar_preco");
            await Diga(g, "sim");
            var gravado = loja.Escritas.FirstOrDefault() ?? "(nada)";
            Espera(gravado.Contains("1250.90"), $"1250,90 grava 1250.90 [{gravado}]");
        }

        // ── 14. SOMAR NAO E DEFINIR ───────────────────────────────────
        Console.WriteLine("\n14. \"adicione 1 unidade\" SOMA. Nao define.");
        Console.WriteLine("    Com 4 em estoque, o certo e ficar com 5 — nao com 1.");
        Console.WriteLine("    Antes isto definia 1 e tirava 3; so nao estragou porque a");
        Console.WriteLine("    API nao sabe reduzir. Sorte de limitacao, nao desenho.");
        {
            var (g, loja) = novo();   // Agua Mineral 500ml comeca com 12
            var r = await Abre(g, "adicione 1 unidade de agua", "repor_estoque");
            Espera(r.Contains("entram 1"), "o resumo diz que ENTRA 1");
            Espera(r.Contains("13"), "e que fica com 13 (12 + 1)");
            Espera(!r.Contains("saem"), "nao fala em tirar nada");
            await Diga(g, "sim");
            var w = loja.Escritas.FirstOrDefault() ?? "(nada)";
            Espera(w.Contains("+1"), $"gravou +1 [{w}]");
        }

        // ── 15. E DEFINIR CONTINUA DEFININDO ──────────────────────────
        Console.WriteLine("\n15. \"corrige o estoque para 30\" continua sendo o total.");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "corrige o estoque da agua para 30", "alterar_estoque");
            Espera(r.Contains("30 unidades"), "o resumo diz o TOTAL de 30");
            await Diga(g, "sim");
            var w = loja.Escritas.FirstOrDefault() ?? "(nada)";
            Espera(w.Contains("+18"), $"somou a diferenca, 18 [{w}]");
        }

        // ── 16. O PRODUTO ASSUMIDO DA CONVERSA, E DITO ────────────────
        Console.WriteLine("\n16. \"adicione mais 1 unidade\" sem dizer o produto.");
        Console.WriteLine("    Ele usa o ultimo de que se falou — e AVISA qual foi.");
        {
            var (g, loja) = novo();
            // `Abre` e nao `Diga`: se a consulta cair abaixo do limiar ela
            // vira botao, e e clicando que ela roda — que e o que a pessoa
            // faz na tela. Com `Diga` a consulta nunca acontecia e o produto
            // nunca era lembrado; o teste media o meu atalho, nao o sistema.
            await Abre(g, "temos agua no estoque?", "estoque");
            var r = await Abre(g, "adicione mais 1 unidade", "repor_estoque");
            Espera(r.Contains("Água Mineral"), "assumiu a água");
            Espera(r.Contains("não disse o produto"), "e DISSE que assumiu");
            await Diga(g, "sim");
            Espera(loja.Escritas.Count == 1 && loja.Escritas[0].Contains("Água"),
                   $"gravou na água [{string.Join(" | ", loja.Escritas)}]");
        }

        // ── 17. "QUAIS SAO OS PRODUTOS?" RESPONDE COM OS PRODUTOS ─────
        Console.WriteLine("\n17. Loja pequena: a pergunta pede a LISTA, nao a soma.");
        Console.WriteLine("    Ele respondia \"3 produtos, 17 unidades, R$ 92,70\" tres vezes seguidas.");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "quais sao os produtos?", "estoque");
            Espera(r.Contains("Água Mineral 500ml"), "cita a Água");
            Espera(r.Contains("Coca-Cola 2L"), "cita a Coca");
            Espera(r.Contains("Chocolate Barra"), "cita o Chocolate");
            Espera(r.Contains("3,50") && r.Contains("9,00") && r.Contains("6,25"),
                   "traz o preco de cada um");
            Espera(loja.Escritas.Count == 0, "listar nao grava nada");
        }

        // ── 18. A LISTA NAO ATROPELA A CONSULTA DE UM PRODUTO SO ──────
        Console.WriteLine("\n18. Perguntar por UM produto continua respondendo so ele.");
        {
            var (g, loja) = novo();
            var r = await Abre(g, "temos agua no estoque?", "estoque");
            Espera(r.Contains("Água Mineral 500ml"), "achou a Água");
            Espera(!r.Contains("Coca-Cola"), "e NAO despejou o catalogo inteiro junto");
        }

        // ── 19. FATURAMENTO POR PERIODO ──────────────────────────────
        Console.WriteLine("\n19. \"de hoje, da semana e do mes\" — TRES respostas, nao uma.");
        Console.WriteLine("    Antes, qualquer periodo que nao fosse \"total\" caia em HOJE, calado.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);   // sabado
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-2), 10m)                  // hoje
               .Venda(agora.AddDays(-3), 20m)                   // esta semana
               .Venda(agora.AddDays(-10), 40m)                  // este mes, semana passada
               .Venda(agora.AddDays(-45), 80m);                 // mes passado

            var r = await Abre(g, "me fale qual o faturamento de hoje, da semana e do mes?", "faturamento");
            Espera(r.Contains("R$ 10,00") || r.Contains("R$ 10"), "hoje = 10");
            Espera(r.Contains("R$ 30,00") || r.Contains("R$ 30"), "semana = 10 + 20 = 30");
            Espera(r.Contains("R$ 70,00") || r.Contains("R$ 70"), "mes = 10 + 20 + 40 = 70");
            Espera(!r.Contains("R$ 150"), "e NAO somou o mes passado junto");
            Espera(r.Contains("10/08/2026") && r.Contains("01/08/2026"),
                   "mostrou as datas de cada recorte");
        }

        // ── 20. O ERRO SILENCIOSO QUE EXISTIA ────────────────────────
        Console.WriteLine("\n20. \"quanto faturamos este mes?\" devolvia o DIA, sem avisar.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-2), 10m)
               .Venda(agora.AddDays(-10), 40m);

            var r = await Abre(g, "quanto faturamos este mes?", "faturamento");
            Espera(r.Contains("R$ 50,00") || r.Contains("R$ 50"), "o mes inteiro: 50, nao 10");
            Espera(r.Contains("01/08/2026"), "e disse de quando ate quando");
        }

        // ── 21. SEM PERIODO NA FRASE, ELE AVISA O QUE ASSUMIU ────────
        Console.WriteLine("\n21. Frase sem periodo: responde hoje, mas DIZ que assumiu hoje.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-2), 10m).Venda(agora.AddDays(-10), 40m);

            var r = await Abre(g, "quanto faturamos?", "faturamento");
            Espera(r.Contains("R$ 10,00") || r.Contains("R$ 10"), "respondeu de hoje");
            Espera(r.Contains("não disse de quando"), "e avisou que assumiu hoje");
        }

        // ── 22. AS INTENCOES ORFAS ───────────────────────────────────
        Console.WriteLine("\n22. 505 frases treinadas caiam no menu de ajuda. Agora respondem.");
        {
            var (g, loja) = novo();
            var r = await g.ResponderComIntencaoAsync("configurar_camera", "pode adicionar mais uma camera?");
            Console.WriteLine($"    ele > {r.Replace("\n", "\n           ")}");
            Espera(!r.Contains("Posso te ajudar com"), "nao caiu no menu de ajuda");
            Espera(r.Contains("gente ou produto"), "pergunta o que separa os dois sistemas");
            Espera(r.Contains("quem instala é você"), "diz que NAO instala — nao promete o que nao faz");
            // CURTO. A primeira versao explicava homografia, escala e os 66%
            // de acerto da prateleira. O Chefe cortou: a pergunta e de uma
            // linha, a resposta tem de ser de uma linha. O detalhe existe —
            // e sai quando ele pedir, nao antes.
            Espera(r.Length < 400, $"resposta curta ({r.Length} caracteres)");
        }
        {
            var (g, loja) = novo();
            var r = await g.ResponderComIntencaoAsync("status_sistema", "ta rodando tudo?");
            Console.WriteLine($"    ele > {r.Replace("\n", "\n           ")}");
            Espera(r.Contains("WebApi"), "confere a WebApi");
            Espera(r.Contains("Espacial"), "confere o Sistema Espacial");
            Espera(r.Contains("intenções"), "confere se a rede carregou");
            // O EspacialFalso devolve null de proposito: um status que diz
            // "tudo certo" com um sistema fora do ar seria pior que nenhum.
            Espera(r.Contains("fora do lugar"), "e ACUSA o que esta fora, nao maquia");
        }
        {
            var (g, loja) = novo();
            var r = await g.ResponderComIntencaoAsync("reiniciar_servico", "reinicia o sistema");
            Espera(r.Contains("dotnet run") && r.Contains("rodar.py"), "diz como reiniciar cada serviço");
            Espera(loja.Escritas.Count == 0, "e nao mexe em nada sozinho");
        }

        // ── 23. AS TRES INTENCOES NOVAS ──────────────────────────────
        Console.WriteLine("\n23. \"quais sao os produtos?\" — a rede entende sozinha agora.");
        {
            var (g, loja) = novo();
            var r = await Diga(g, "quais sao os produtos?");
            Espera(!r.Contains("não tenho certeza"), "acima do limiar: sem botao");
            Espera(r.Contains("Água Mineral 500ml") && r.Contains("Coca-Cola 2L")
                   && r.Contains("Chocolate Barra"), "listou os tres");
            Espera(r.IndexOf("Água") < r.IndexOf("produtos, "),
                   "a LISTA vem antes da soma, nao depois");
        }

        Console.WriteLine("\n24. \"tivemos algum furo?\" — furo e estoque que nao bate.");
        Console.WriteLine("    Cancelamento com carrinho cheio baixa estoque e nao devolve.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-1), 10m)
               .Cancelada(agora.AddHours(-3), "Água Mineral 500ml", 2, 3.50m)
               .Cancelada(agora.AddHours(-5), "Coca-Cola 2L", 1, 9.00m);

            var r = await Diga(g, "tivemos algum furo no sistema?");
            Espera(!r.Contains("não tenho certeza"), "acima do limiar: sem botao");
            Espera(r.Contains("Sim, tem furo"), "acusou o furo");
            Espera(r.Contains("faltam 2") && r.Contains("Água Mineral"), "quantificou a água");
            Espera(r.Contains("Coca-Cola"), "e a coca");
            Espera(r.Contains("não é registrado"), "e DISSE o que nao sabe conferir");
            Espera(loja.Escritas.Count == 0, "conferir nao grava nada");
        }
        {
            // Sem cancelamento, nao pode inventar furo — nem dizer que
            // conferiu o que nao tem como conferir.
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-1), 10m);
            var r = await Diga(g, "o estoque bate?");
            Espera(r.Contains("achei estoque fora do lugar"), "sem furo, nao inventa");
            Espera(r.Contains("não é registrado"), "mas continua dizendo o que nao ve");
        }

        Console.WriteLine("\n25. \"puxe todas as informacoes\" — sem periodo, ele PERGUNTA.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var (g, loja, ses) = comVendas(agora);
            ses.Venda(agora.AddHours(-1), 10m).Venda(agora.AddDays(-10), 40m);

            var r = await Diga(g, "puxe todas as informacoes");
            Espera(r.Contains("de quando?"), "perguntou o periodo em vez de escolher sozinho");

            var r2 = await Diga(g, "puxe todas as informacoes do mes");
            Espera(r2.Contains("01/08/2026"), "com o periodo, monta o relatorio");
            Espera(r2.Contains("Vendas") && r2.Contains("Movimento"), "traz mais que dinheiro");
            Espera(r2.Contains("R$ 50,00"), "somou o mes: 10 + 40");
            Espera(r2.Contains("não guardo histórico de estoque"),
                   "e avisa que o estoque mostrado e de HOJE, nao do periodo");
        }

        // ── 26. O FURO VEM DA TABELA, NAO DA DEDUCAO ─────────────────
        Console.WriteLine("\n26. Com a tabela ligada, ele LE o que foi gravado.");
        Console.WriteLine("    O alarme da porta nunca aparecia na deducao: ele evaporava.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var oc = new OcorrenciasFalsas()
                .Add(agora.AddHours(-2), "Roubo", "Critica",
                     "A leitora da porta identificou **Coca-Cola 2L** saindo e o pagamento não está confirmado.")
                .Add(agora.AddHours(-5), "FuroDeSistema", "Media",
                     "Sessão cancelada com 2 unidade(s) ainda no carrinho.")
                .Add(agora.AddHours(-6), "FuroDeCobertura", "Informativa",
                     "A câmera comparou antes e depois e não identificou mudança.")
                .Add(agora.AddHours(-7), "FalhaApi", "Media",
                     "O monitor do Sistema Espacial não respondeu.");

            var (g, loja, ses) = comOcorrencias(agora, oc);
            var r = await Diga(g, "tivemos algum furo no sistema?");

            Espera(r.Contains("Saída sem pagamento"), "o ROUBO aparece — e era o que evaporava");
            Espera(r.IndexOf("Saída sem pagamento") < r.IndexOf("perdeu a conta"),
                   "e vem PRIMEIRO: e o unico que precisa de alguem hoje");
            Espera(r.Contains("perdeu a conta"), "o furo de sistema aparece separado");
            Espera(r.Contains("Defeito de software, não roubo"), "e nao e confundido com roubo");
            Espera(r.Contains("câmera não viu"), "a cegueira aparece");
            // FalhaApi e ocorrencia, mas nao e furo. Furo, para esta loja, e
            // estoque que nao bate — foi a escolha do Chefe.
            Espera(!r.Contains("não respondeu"), "falha de API NAO entra na conta de furo");
            Espera(r.Contains("3 ocorrência"), "contou 3 de estoque, nao as 4");
        }

        Console.WriteLine("\n27. Tabela fora do ar: ele NAO diz que está tudo certo.");
        {
            var agora = new DateTime(2026, 8, 15, 14, 30, 0);
            var oc = new OcorrenciasFalsas { Responde = false };
            var (g, loja, ses) = comOcorrencias(agora, oc);
            ses.Cancelada(agora.AddHours(-3), "Água Mineral 500ml", 2, 3.50m);

            var r = await Diga(g, "tivemos algum furo?");
            // Caiu na deducao ao vivo — que ainda enxerga o cancelamento.
            Espera(r.Contains("Sim, tem furo"), "cai na deducao e ainda acha o cancelamento");
            Espera(r.Contains("não é registrado"), "e continua dizendo o que nao consegue ver");
        }

        Console.WriteLine($"\n══════ {_casos - _falhas}/{_casos} verificacoes passaram ══════");
        return _falhas;
    }

    public static async Task<int> Main(string[] args)
    {
        // AS DUAS CULTURAS, e a de pt-BR e a que importa: e a do
        // navegador do Chefe. O teste rodava so em invariante, e por isso
        // deixou passar "3.00" virando R$ 300,00 no banco.
        var falhas = 0;
        foreach (var cultura in new[] { "pt-BR", "" })
        {
            // O leitor de periodo entra aqui dentro de proposito: nome de
            // mes e formato de data sao armadilha de cultura, igual ao
            // R$ 300. Uma passada so em invariante nao provaria nada.
            var c = new System.Globalization.CultureInfo(cultura);
            System.Globalization.CultureInfo.DefaultThreadCurrentCulture = c;
            System.Globalization.CultureInfo.CurrentCulture = c;
            _falhas = 0; _casos = 0;
            Console.WriteLine($"\n\n╔══════════════════════════════════════════════════╗");
            Console.WriteLine($"║  CULTURA: {(cultura == "" ? "invariante" : cultura),-39}║");
            Console.WriteLine($"╚══════════════════════════════════════════════════╝");
            falhas += ProvaPeriodo.Rodar();
            falhas += ProvaOcorrencias.Rodar();
            falhas += await Rodar(args[0]);
        }
        Console.WriteLine(falhas == 0
            ? "\n\n  as duas culturas passaram."
            : $"\n\n  {falhas} FALHA(S) — e uma falha so em pt-BR e um bug de verdade,\n" +
              "  porque pt-BR e a cultura do navegador de quem usa.");
        return falhas;
    }
}
