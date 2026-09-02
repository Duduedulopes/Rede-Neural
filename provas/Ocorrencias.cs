using System.Text.Json;
using AutonomousStore.Domain.Entities;
using AutonomousStore.Domain.Enums;

/// Prova da POLITICA de ocorrencia: o que e de cada tipo, com que gravidade,
/// e o que o sistema propoe fazer. Nao e teste de banco — e teste da
/// decisao, que e a parte que erra caro.
public static class ProvaOcorrencias
{
    static int _falhas, _casos;

    static void Espera(bool ok, string oque)
    {
        _casos++;
        if (!ok) { _falhas++; Console.WriteLine($"    >>> FALHOU: {oque}"); }
        else Console.WriteLine($"    ok: {oque}");
    }

    static readonly DateTime Agora = new(2026, 8, 15, 14, 30, 0, DateTimeKind.Utc);

    public static int Rodar()
    {
        _falhas = 0; _casos = 0;

        // ── 1. A TRAVA DA AUTONOMIA ──────────────────────────────────
        Console.WriteLine("\n1. Ninguem corrige sozinho na v1 — e a trava fica no dominio.");
        {
            var recusou = false;
            try
            {
                _ = new Ocorrencia(Agora, "AutonomousStore", "X", "Y",
                                   TipoDeOcorrencia.ErroDados, Severidade.Baixa, "teste",
                                   AcaoRecomendada.CorrigirAutomaticamente);
            }
            catch (ArgumentException) { recusou = true; }

            Espera(recusou, "o construtor RECUSA CorrigirAutomaticamente");
            // A trava e no dominio de proposito: se dependesse da boa vontade
            // de quem escreve cada detector, bastaria um esquecimento.
        }

        // ── 2. HORA SEMPRE EM UTC ────────────────────────────────────
        Console.WriteLine("\n2. Hora local vira UTC na entrada. Guardar local é guardar preço sem moeda.");
        {
            var local = new DateTime(2026, 8, 15, 14, 30, 0, DateTimeKind.Local);
            var o = new Ocorrencia(local, "AutonomousStore", "X", "Y",
                                   TipoDeOcorrencia.ErroDados, Severidade.Baixa, "teste",
                                   AcaoRecomendada.ApenasRegistrar);
            Espera(o.QuandoUtc.Kind == DateTimeKind.Utc, "converteu para UTC");
        }

        // ── 3. O ESTADO SO ANDA PARA A FRENTE ────────────────────────
        Console.WriteLine("\n3. Resolvida nao volta a ser \"vista\".");
        {
            var o = new Ocorrencia(Agora, "AutonomousStore", "X", "Y",
                                   TipoDeOcorrencia.ErroDados, Severidade.Baixa, "teste",
                                   AcaoRecomendada.ApenasRegistrar);
            Espera(o.Estado == EstadoDaOcorrencia.Nova, "nasce Nova");

            o.MarcarVista();
            Espera(o.Estado == EstadoDaOcorrencia.Vista, "vira Vista");

            o.Resolver("eduardo", "conferi na prateleira");
            Espera(o.Estado == EstadoDaOcorrencia.Resolvida, "vira Resolvida");
            Espera(o.ResolvidaPor == "eduardo", "guarda quem resolveu");

            o.MarcarVista();
            Espera(o.Estado == EstadoDaOcorrencia.Resolvida,
                   "e MarcarVista de novo nao rebaixa — senao o sino ressuscitaria o resolvido");
        }

        // ── 4. CAUSA-RAIZ NAO ENTRA POR DETECTOR ─────────────────────
        Console.WriteLine("\n4. CausaProvavel e palpite; CausaRaiz e confirmacao. Nao se misturam.");
        {
            var o = Deteccoes.SessaoCanceladaComItem(
                Guid.NewGuid(), Agora, new[] { ("Água Mineral 500ml", 2, 7.00m) });

            Espera(o.CausaProvavel is { Length: > 0 }, "o detector preenche CausaProvavel");
            Espera(o.CausaProvavel!.Contains("Inferência"), "e ela se declara inferencia");
            Espera(o.CausaRaiz is null, "e NAO preenche CausaRaiz");
            Espera(!o.Descricao.Contains("Inferência"),
                   "a Descricao fica so com fato observado");

            o.ConfirmarCausaRaiz("Cancel não chamava IncreaseStockAsync.");
            Espera(o.CausaRaiz is { Length: > 0 }, "CausaRaiz so entra por confirmacao explicita");
        }

        // ── 5. FURO DE SISTEMA: A GRAVIDADE SEGUE O DINHEIRO ─────────
        Console.WriteLine("\n5. Cancelamento com carrinho: quanto maior o valor, mais grave.");
        {
            var barato = Deteccoes.SessaoCanceladaComItem(
                Guid.NewGuid(), Agora, new[] { ("Água Mineral 500ml", 2, 7.00m) });
            var caro = Deteccoes.SessaoCanceladaComItem(
                Guid.NewGuid(), Agora, new[] { ("Coca-Cola 2L", 10, 90.00m) });

            Espera(barato.Tipo == TipoDeOcorrencia.FuroDeSistema, "R$ 7 e furo de SISTEMA");
            Espera(barato.Severidade == Severidade.Media, "R$ 7 e Media");
            Espera(caro.Severidade == Severidade.Alta, "R$ 90 e Alta");
            Espera(barato.Recomendacao == AcaoRecomendada.SugerirCorrecao, "sugere correcao");

            // A LINHA QUE MAIS IMPORTA NESTE ARQUIVO. Acusar cliente por bug
            // nosso seria o pior erro que este sistema poderia cometer.
            Espera(!barato.Descricao.Contains("roubo", StringComparison.OrdinalIgnoreCase),
                   "e NAO chama de roubo o que e defeito de software");
        }

        // ── 6. ROUBO: FRIO, SEM CONCLUSAO SOBRE PESSOA ───────────────
        Console.WriteLine("\n6. Roubo e a unica que acusa alguem — por isso o registro e frio.");
        {
            var sessao = Guid.NewGuid();
            var o = Deteccoes.SaidaSemPagamento("TAG-99", "Coca-Cola 2L", sessao, "Aberta", Agora);

            Espera(o.Tipo == TipoDeOcorrencia.Roubo, "e Roubo");
            Espera(o.Severidade == Severidade.Critica, "e Critica — acende o sino em vermelho");
            Espera(o.Recomendacao == AcaoRecomendada.BloquearOperacao, "manda bloquear");
            Espera(o.CorrelationId == sessao, "amarra na sessao, para o suporte ver o rastro");

            var dados = JsonDocument.Parse(o.DadosEnvolvidosJson!).RootElement;
            Espera(dados.GetProperty("tagRfid").GetString() == "TAG-99", "guarda a tag lida");

            // O sistema nao viu ninguem: viu uma TAG. Palavra sobre pessoa
            // aqui viraria acusacao que o dado nao sustenta.
            foreach (var p in new[] { "cliente", "ladrão", "pessoa", "furtou", "roubou" })
                Espera(!o.Descricao.Contains(p, StringComparison.OrdinalIgnoreCase),
                       $"a descricao nao diz \"{p}\"");
        }

        // ── 7. TAG DESCONHECIDA NAO E ROUBO ──────────────────────────
        Console.WriteLine("\n7. Tag sem produto: provavelmente cadastro faltando, nao crime.");
        {
            var o = Deteccoes.TagDesconhecidaNaPorta("TAG-XYZ", Agora);
            Espera(o.Tipo == TipoDeOcorrencia.ErroDados,
                   "e ErroDados, nao Roubo — chamar tudo de roubo ensina a ignorar a palavra");
            Espera(o.CausaProvavel!.Contains("As duas são possíveis"),
                   "e diz que as duas leituras cabem, em vez de escolher uma");
        }

        // ── 8. CAMERA CEGA E INFORMATIVA ─────────────────────────────
        Console.WriteLine("\n8. Camera que nao viu nada: registra, nao alarma.");
        {
            var o = Deteccoes.CameraNaoViuMudanca(Guid.NewGuid(), Agora);
            Espera(o.Tipo == TipoDeOcorrencia.FuroDeCobertura, "e furo de cobertura");
            Espera(o.Severidade == Severidade.Informativa,
                   "Informativa: pode nao ter saido nada mesmo. O valor esta na soma");
            Espera(o.Recomendacao == AcaoRecomendada.ApenasRegistrar, "so registra");
        }

        // ── 9. A CHAVE QUE IMPEDE CEM LINHAS IGUAIS ──────────────────
        Console.WriteLine("\n9. A mesma sessao cancelada, varrida duas vezes, e UM fato.");
        {
            var sessao = Guid.NewGuid();
            var itens = new[] { ("Água Mineral 500ml", 2, 7.00m) };
            var a = Deteccoes.SessaoCanceladaComItem(sessao, Agora, itens);
            var b = Deteccoes.SessaoCanceladaComItem(sessao, Agora.AddHours(3), itens);

            Espera(a.Chave == b.Chave,
                   "mesma chave mesmo em varreduras diferentes — o repositorio deduplica");
            Espera(a.Chave!.Contains(sessao.ToString()), "a chave carrega o id da sessao");

            // Duas excecoes iguais em momentos diferentes sao DOIS fatos: a
            // segunda pode ser o sinal de que virou rotina. Deduplicar aqui
            // esconderia frequencia, que e metade da informacao.
            var e1 = Deteccoes.ErroDeExecucao("/api/x", "GET", new InvalidOperationException("boom"), Guid.NewGuid(), Agora);
            Espera(e1.Chave is null, "excecao NAO tem chave: frequencia e informacao");
        }

        // ── 10. A PILHA VAI TRUNCADA ─────────────────────────────────
        Console.WriteLine("\n10. Pilha gigante nao enche a coluna sozinha.");
        {
            Exception capturada;
            try { throw new InvalidOperationException("boom"); }
            catch (Exception e) { capturada = e; }

            var o = Deteccoes.ErroDeExecucao("/api/produtos", "POST", capturada, Guid.NewGuid(), Agora);
            Espera(o.Tipo == TipoDeOcorrencia.ErroExecucao, "e ErroExecucao");
            Espera(o.Descricao.Contains("InvalidOperationException") && o.Descricao.Contains("boom"),
                   "a descricao traz tipo e mensagem");
            Espera(o.Operacao == "POST /api/produtos", "e a operacao diz o verbo e a rota");

            var dados = JsonDocument.Parse(o.DadosEnvolvidosJson!).RootElement;
            var pilha = dados.GetProperty("pilha").GetString() ?? "";
            Espera(pilha.Length <= 4100, $"pilha limitada ({pilha.Length} caracteres)");
        }

        // ── 11. OCORRENCIA SEM DESCRICAO NAO SERVE ───────────────────
        Console.WriteLine("\n11. Campo obrigatorio e obrigatorio mesmo.");
        {
            foreach (var (campo, acao) in new (string, Action)[]
            {
                ("sistema", () => new Ocorrencia(Agora, "", "M", "O", TipoDeOcorrencia.ErroDados, Severidade.Baixa, "d", AcaoRecomendada.ApenasRegistrar)),
                ("modulo",  () => new Ocorrencia(Agora, "S", "", "O", TipoDeOcorrencia.ErroDados, Severidade.Baixa, "d", AcaoRecomendada.ApenasRegistrar)),
                ("operacao",() => new Ocorrencia(Agora, "S", "M", "", TipoDeOcorrencia.ErroDados, Severidade.Baixa, "d", AcaoRecomendada.ApenasRegistrar)),
                ("descricao",() => new Ocorrencia(Agora, "S", "M", "O", TipoDeOcorrencia.ErroDados, Severidade.Baixa, "", AcaoRecomendada.ApenasRegistrar)),
            })
            {
                var recusou = false;
                try { acao(); } catch (ArgumentException) { recusou = true; }
                Espera(recusou, $"recusa sem {campo}");
            }
        }

        Console.WriteLine($"\n  ══════ {_casos - _falhas}/{_casos} de ocorrencias ══════");
        return _falhas;
    }
}
