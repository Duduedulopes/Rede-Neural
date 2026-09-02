using System.Globalization;
using AutonomousStore.Gerente.Services.Agente;

/// Prova do leitor de periodo. Relogio congelado: sem isso, "ontem" muda de
/// significado a cada dia e a prova so vale na data em que foi escrita.
public static class ProvaPeriodo
{
    static int _falhas, _casos;

    // Sabado, 15 de agosto de 2026.
    static readonly DateTime Agora = new(2026, 8, 15, 14, 30, 0);

    static string D(DateTime d) => d.ToString("dd/MM/yyyy", CultureInfo.InvariantCulture);

    static void Um(string frase, string esperado)
    {
        _casos++;
        var achados = LeitorDePeriodo.Todos(frase, Agora);
        var deu = achados.Count == 0
            ? "(nada)"
            : string.Join(" + ", achados.Select(x => x.Tudo ? "TUDO" : $"{D(x.Inicio)}..{D(x.Fim.AddDays(-1))}"));

        if (deu == esperado)
        {
            Console.WriteLine($"  ok   {frase,-46} {deu}");
        }
        else
        {
            _falhas++;
            Console.WriteLine($"  FALHOU  {frase}");
            Console.WriteLine($"          esperado: {esperado}");
            Console.WriteLine($"          deu     : {deu}");
        }
    }

    static void Nome(string frase, string esperado)
    {
        _casos++;
        var a = LeitorDePeriodo.Ler(frase, Agora);
        var deu = a?.Nome ?? "(nada)";
        if (deu == esperado) Console.WriteLine($"  ok   nome de \"{frase}\" = {deu}");
        else { _falhas++; Console.WriteLine($"  FALHOU  nome de \"{frase}\": esperava \"{esperado}\", deu \"{deu}\""); }
    }

    public static int Rodar()
    {
        _falhas = 0; _casos = 0;
        Console.WriteLine($"\n  relogio congelado em {D(Agora.Date)} ({Agora.DayOfWeek})\n");

        // ── dias soltos ───────────────────────────────────────────────
        Um("quanto faturamos hoje?",            "15/08/2026..15/08/2026");
        Um("e ontem?",                          "14/08/2026..14/08/2026");
        // A ARMADILHA: "anteontem".Contains("ontem") e verdadeiro. Por token,
        // nao e — e este caso e o que prova a diferenca.
        Um("faturamento de anteontem",          "13/08/2026..13/08/2026");

        // ── semana (comeca na segunda) ────────────────────────────────
        Um("faturamento desta semana",          "10/08/2026..16/08/2026");
        Um("quanto foi na semana passada?",     "03/08/2026..09/08/2026");
        Um("faturamento semanal",               "10/08/2026..16/08/2026");

        // ── mes ───────────────────────────────────────────────────────
        Um("quanto faturamos este mes?",        "01/08/2026..31/08/2026");
        Um("o faturamento do mes passado",      "01/07/2026..31/07/2026");

        // ── ano ───────────────────────────────────────────────────────
        Um("faturamento deste ano",             "01/01/2026..31/12/2026");
        Um("e no ano passado?",                 "01/01/2025..31/12/2025");
        Um("faturamento de 2025",               "01/01/2025..31/12/2025");

        // ── mes por nome ──────────────────────────────────────────────
        Um("faturamento de agosto",             "01/08/2026..31/08/2026");
        Um("quanto vendemos em marco?",         "01/03/2026..31/03/2026");
        Um("faturamento de julho de 2025",      "01/07/2025..31/07/2025");
        // Dezembro ainda nao chegou em agosto de 2026: e o que JA aconteceu.
        Um("faturamento de dezembro",           "01/12/2025..31/12/2025");
        Um("quanto foi em ago?",                "01/08/2026..31/08/2026");

        // ── janelas ───────────────────────────────────────────────────
        Um("faturamento dos ultimos 7 dias",    "09/08/2026..15/08/2026");
        Um("nas ultimas 2 semanas",             "02/08/2026..15/08/2026");
        Um("nos ultimos 3 meses",               "16/05/2026..15/08/2026");

        // ── datas escritas ────────────────────────────────────────────
        Um("faturamento do dia 15/08",          "15/08/2026..15/08/2026");
        Um("quanto vendemos em 03/07/2025?",    "03/07/2025..03/07/2025");
        Um("faturamento do dia 12",             "12/08/2026..12/08/2026");
        // Dia que ainda nao chegou: e o do mes passado.
        Um("faturamento do dia 20",             "20/07/2026..20/07/2026");
        Um("faturamento do dia 3 de julho",     "03/07/2026..03/07/2026");

        // ── varios de uma vez: A PERGUNTA DO CHEFE ────────────────────
        Console.WriteLine();
        Um("me fale qual o faturamento de hoje, da semana e do mes?",
           "15/08/2026..15/08/2026 + 10/08/2026..16/08/2026 + 01/08/2026..31/08/2026");
        // "passada" e da semana, nao do mes — por isso "passado" so conta
        // colado na unidade.
        Um("faturamento da semana passada e deste mes",
           "03/08/2026..09/08/2026 + 01/08/2026..31/08/2026");
        Um("quanto foi ontem e hoje?",
           "14/08/2026..14/08/2026 + 15/08/2026..15/08/2026");

        // ── o que NAO deve virar periodo ──────────────────────────────
        Console.WriteLine();
        Um("quanto faturamos?",                 "(nada)");
        // "3.00" nao e dia 3 do mes 0: o ponto ficou fora da regex de data.
        Um("muda o preco da agua para 3.00",    "(nada)");
        // "dez" e o numero dez, nao dezembro.
        Um("vendemos dez aguas",                "(nada)");
        // O numero so vira janela depois de "ultimos".
        Um("vendemos 7 aguas",                  "(nada)");
        Um("faturamento total",                 "TUDO");

        // ── o nome que aparece na resposta ────────────────────────────
        Console.WriteLine();
        Nome("faturamento de hoje", "hoje");
        Nome("faturamento do mes passado", "no mês passado");
        Nome("faturamento de julho de 2025", "em julho de 2025");
        Nome("faturamento dos ultimos 7 dias", "nos últimos 7 dias");
        Nome("faturamento total", "no total");

        Console.WriteLine($"\n  ══════ {_casos - _falhas}/{_casos} do leitor de periodo ══════");
        return _falhas;
    }
}
