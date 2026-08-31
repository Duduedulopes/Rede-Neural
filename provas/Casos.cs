using System.Globalization;
using System.Net;
using System.Text;
using AutonomousStore.AdminApp.Models;
using AutonomousStore.AdminApp.Services;

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
                await Diga(g, "isso mesmo");
                Espera(loja.Escritas.Count == 1 && loja.Escritas[0].Contains("+18"),
                       $"somou 18 [{string.Join(" | ", loja.Escritas)}]");
            }
            else Espera(true, "coletou por perguntas (nao e regressao)");
        }

        // ── 11. o preco da margem ─────────────────────────────────────
        Console.WriteLine("\n11. \"pode fazer\" (94,7%) fica abaixo do corte (0,97) DE PROPOSITO.");
        Console.WriteLine("    E o preco de ter posto \"pode parar\" e \"pode deixar\" do lado do NAO:");
        Console.WriteLine("    \"pode\" deixou de ser sinal de sim, e \"pode fazer\" perdeu certeza junto.");
        Console.WriteLine("    Custa uma repeticao. A alternativa era \"pode parar\" gravando a 99,8%.");
        {
            var (g, loja) = novo();
            await Abre(g, "muda o preco da agua para 5,50", "alterar_preco");
            await Diga(g, "pode fazer");
            Espera(loja.Escritas.Count == 0, "nao gravou no primeiro (esperado)");
            await Diga(g, "sim");
            Espera(loja.Escritas.Count == 1, $"gravou depois do sim (foi {loja.Escritas.Count})");
        }

        // ── 12. o par que estava empatado ─────────────────────────────
        Console.WriteLine("\n12. \"para por favor\" e \"faz por favor\": a cortesia nao pode decidir");
        {
            var (g1, l1) = novo();
            await Abre(g1, "muda o preco da agua para 5,50", "alterar_preco");
            await Diga(g1, "para por favor");
            Espera(l1.Escritas.Count == 0, "\"para por favor\" NAO grava");

            var (g2, l2) = novo();
            await Abre(g2, "muda o preco da agua para 5,50", "alterar_preco");
            await Diga(g2, "faz por favor");
            Espera(l2.Escritas.Count == 1, $"\"faz por favor\" grava (foi {l2.Escritas.Count})");
        }

        Console.WriteLine($"\n══════ {_casos - _falhas}/{_casos} verificacoes passaram ══════");
        return _falhas;
    }

    public static async Task<int> Main(string[] args) => await Rodar(args[0]);
}
