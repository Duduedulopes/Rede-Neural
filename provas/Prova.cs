// ══════════════════════════════════════════════════════════════════════
//  A CONVERSA INTEIRA, RODANDO DE VERDADE.
//
//  Compilar prova que o C# e valido. Nao prova que "sim" grava, que "nao"
//  nao grava, nem que o resumo mostra o preco certo — e essas tres sao
//  exatamente as afirmacoes que eu faria pro Eduardo sem ter conferido.
//
//  A `LojaFalsa` anota TODA escrita que recebe. Um caso que termina com
//  uma escrita a mais e um caso que gravou o que nao devia.
// ══════════════════════════════════════════════════════════════════════
using System.Globalization;
using System.Text.Json;
using AutonomousStore.AdminApp.Models;
using AutonomousStore.Gerente.Models;
using AutonomousStore.AdminApp.Services;
using AutonomousStore.Gerente.Services;
using AutonomousStore.Domain.Enums;

public class LojaFalsa : IProductApiService
{
    public List<ProductDto> Itens = new();
    public List<string> Escritas = new();

    public Task<List<ProductDto>> GetAllAsync() => Task.FromResult(Itens);
    public Task<List<ProductDto>> GetLowStockAsync() => Task.FromResult(new List<ProductDto>());

    public Task<(bool Success, ProductDto? Product, string? Error)> CreateAsync(CreateProductRequest r)
    {
        Escritas.Add($"CRIAR '{r.Name}' preco={r.Price} estoque={r.StockQuantity}");
        var p = new ProductDto(Guid.NewGuid(), r.Name, r.Barcode, r.Price, r.Description,
                               null, null, null, null, r.StockQuantity, null, false, true, DateTime.Now);
        Itens.Add(p);
        return Task.FromResult<(bool, ProductDto?, string?)>((true, p, null));
    }
    public Task<(bool Success, string? Error)> UpdatePriceAsync(Guid id, decimal preco)
    {
        var p = Itens.First(x => x.Id == id);
        Escritas.Add($"PRECO '{p.Name}' -> {preco.ToString(CultureInfo.InvariantCulture)}");
        return Task.FromResult<(bool, string?)>((true, null));
    }
    public Task<(bool Success, string? Error)> RestockAsync(Guid id, int q)
    {
        var p = Itens.First(x => x.Id == id);
        Escritas.Add($"ESTOQUE '{p.Name}' +{q}");
        return Task.FromResult<(bool, string?)>((true, null));
    }
    public Task<(bool, string?)> UpdateDetailsAsync(Guid i, string n, string? d, string? u)
        => Task.FromResult<(bool, string?)>((true, null));
    public Task<(bool, string?)> SetStockThresholdAsync(Guid i, int? t)
        => Task.FromResult<(bool, string?)>((true, null));
    public Task<(bool, string?)> AssignRfidTagAsync(Guid i, string? t)
        => Task.FromResult<(bool, string?)>((true, null));
}

public class SessoesFalsas : ISessionApiService
{
    public List<SessionDto> Historico = new();

    public Task<SessionDto?> GetCurrentOpenAsync() => Task.FromResult<SessionDto?>(null);
    public Task<List<SessionDto>> GetPendingEntryAsync() => Task.FromResult(new List<SessionDto>());
    public Task<(bool, string?)> ConfirmEntryAsync(string t) => Task.FromResult<(bool, string?)>((true, null));
    public Task<List<SessionDto>> GetHistoryAsync() => Task.FromResult(Historico);

    /// <summary>
    /// Uma sessao CANCELADA que ainda tinha produto no carrinho.
    /// </summary>
    /// <remarks>
    /// E o furo: o estoque baixou no `AddItem` e o `Cancel` da WebApi nao
    /// devolve. O produto esta na prateleira e o sistema conta a menos.
    /// </remarks>
    public SessoesFalsas Cancelada(DateTime quando, string produto, int qtd, decimal preco)
    {
        Historico.Add(new SessionDto(
            Guid.NewGuid(), Guid.NewGuid(), "qr", quando, SessionStatus.Cancelada,
            quando.AddMinutes(-10), quando, null, null, 0m,
            new List<SessionItemDto> { new(Guid.NewGuid(), produto, preco, qtd, preco * qtd) }));
        return this;
    }

    /// <summary>Uma venda paga em `quando`, no valor de `total`.</summary>
    public SessoesFalsas Venda(DateTime quando, decimal total, string produto = "Água Mineral 500ml", int qtd = 1)
    {
        var id = Guid.NewGuid();
        Historico.Add(new SessionDto(
            id, Guid.NewGuid(), "qr", quando, SessionStatus.Concluida,
            quando.AddMinutes(-5), quando, Guid.NewGuid(), quando, total,
            new List<SessionItemDto> { new(Guid.NewGuid(), produto, total / qtd, qtd, total) }));
        return this;
    }
}

/// <summary>
/// A API de ocorrencia, fingida — e ela sabe FALHAR.
/// </summary>
/// <remarks>
/// `Responde = false` devolve `null`, que e o caso de API fora do ar ou
/// migracao nao aplicada. E o caso que importa: um gerente que responde
/// "está tudo certo" quando nao conseguiu olhar e pior que um que nao
/// responde.
/// </remarks>
public class OcorrenciasFalsas : IOcorrenciaApiService
{
    public bool Responde = true;
    public List<OcorrenciaDto> Itens = new();

    public Task<List<OcorrenciaDto>?> BuscarAsync(
        DateTime? desde = null, DateTime? ate = null, string? tipo = null,
        string? severidadeMinima = null, string? estado = null,
        Guid? correlationId = null, int limite = 200)
    {
        if (!Responde) return Task.FromResult<List<OcorrenciaDto>?>(null);
        var filtradas = Itens
            .Where(o => desde is not { } d || o.QuandoUtc >= d)
            .Where(o => ate is not { } a || o.QuandoUtc < a)
            .Where(o => tipo is not { Length: > 0 } t || o.Tipo == t)
            .Where(o => estado is not { Length: > 0 } e || o.Estado == e)
            .Where(o => correlationId is not { } c || o.CorrelationId == c)
            .ToList();
        return Task.FromResult<List<OcorrenciaDto>?>(filtradas);
    }

    public Task<OcorrenciaDto?> PorIdAsync(Guid id)
        => Task.FromResult(Responde ? Itens.FirstOrDefault(o => o.Id == id) : null);

    public Task<OcorrenciaDto?> MarcarVistaAsync(Guid id) => Trocar(id, e => e with { Estado = "Vista" });

    public Task<OcorrenciaDto?> ResolverAsync(Guid id, string? nota)
        => Trocar(id, e => e with { Estado = "Resolvida", NotaDoAdmin = nota });

    public Task<OcorrenciaDto?> EnviarAoSuporteAsync(Guid id, string? descricaoDoAdmin)
        => Trocar(id, e => e with { Estado = "NoSuporte", NotaDoAdmin = descricaoDoAdmin });

    /// O servidor devolve a ocorrencia ATUALIZADA nesses POST, e a tela conta
    /// com isso para redesenhar. O duble tem de devolver tambem, senao o
    /// teste passaria por um caminho que nao existe de verdade.
    private Task<OcorrenciaDto?> Trocar(Guid id, Func<OcorrenciaDto, OcorrenciaDto> como)
    {
        if (!Responde) return Task.FromResult<OcorrenciaDto?>(null);
        var i = Itens.FindIndex(o => o.Id == id);
        if (i < 0) return Task.FromResult<OcorrenciaDto?>(null);
        Itens[i] = como(Itens[i]);
        return Task.FromResult<OcorrenciaDto?>(Itens[i]);
    }

    public Task<NaoVistasDto?> NaoVistasAsync()
        => Task.FromResult<NaoVistasDto?>(Responde
            ? new NaoVistasDto(Itens.Count(o => o.Estado == "Nova"),
                               Itens.Count(o => o.Severidade == "Critica"),
                               Itens.Count > 0 ? Itens.Max(o => o.QuandoUtc) : null)
            : null);

    public OcorrenciasFalsas Add(DateTime quando, string tipo, string severidade, string descricao)
    {
        Itens.Add(new OcorrenciaDto(
            Guid.NewGuid(), quando, "AutonomousStore", "SessionsController", "VerifyExit",
            tipo, severidade, descricao, null, null, null, null, null,
            "ApenasRegistrar", null, null, "Nova", Guid.NewGuid(), null, null, null, null));
        return this;
    }
}

public class EspacialFalso : IGerenteEspacialService
{
    public Task<EspacialResumoDto?> ObterAsync() => Task.FromResult<EspacialResumoDto?>(null);
}

public class FabricaFalsa : IHttpClientFactory
{
    // Nada aqui fala com a rede. O GravarPerguntaAsync usa isto e ja engole
    // a falha sozinho — que e o comportamento certo: nao gravar a pergunta
    // nao pode derrubar a resposta.
    public HttpClient CreateClient(string name)
        => new HttpClient(new SemRede()) { BaseAddress = new Uri("http://localhost:1/") };

    private class SemRede : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage r, CancellationToken c)
            => throw new HttpRequestException("sem rede no teste");
    }
}
