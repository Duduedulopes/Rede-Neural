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
using AutonomousStore.AdminApp.Services;

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
    public Task<SessionDto?> GetCurrentOpenAsync() => Task.FromResult<SessionDto?>(null);
    public Task<List<SessionDto>> GetPendingEntryAsync() => Task.FromResult(new List<SessionDto>());
    public Task<(bool, string?)> ConfirmEntryAsync(string t) => Task.FromResult<(bool, string?)>((true, null));
    public Task<List<SessionDto>> GetHistoryAsync() => Task.FromResult(new List<SessionDto>());
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
