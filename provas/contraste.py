# -*- coding: utf-8 -*-
"""
A PALETA ESCURA, CONFERIDA EM VEZ DE OLHADA.

Escolher cor escura "no olho" falha de um jeito especifico: no monitor do
autor, de noite, tudo parece legivel. O mesmo cinza sobre grafite some numa
sala clara — e quem le nao tem como saber se o problema e a tela ou a cor.

WCAG AA pede 4,5:1 para texto normal e 3:1 para texto grande e para a
borda de um controle. Aqui cada par que vai existir na tela e medido, e o
que nao passa aparece marcado.

Uma armadilha propria do modo escuro: as cores da MARCA foram escolhidas
para brilhar sobre branco. Sobre grafite elas escurecem relativamente e
perdem contraste — violeta 0,60 sobre fundo 0,20 da menos que sobre 1,00.
Por isso a paleta escura nao e "a mesma com o fundo invertido": as cores
de marca sobem de luminancia.
"""
from coloraide import Color

def rel_lum(c):
    r, g, b = Color(c).convert("srgb")[:3]
    def f(u):
        u = max(0.0, min(1.0, u))
        return u/12.92 if u <= 0.04045 else ((u+0.055)/1.055) ** 2.4
    return 0.2126*f(r) + 0.7152*f(g) + 0.0722*f(b)

def contraste(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# ── A PALETA ESCURA (grafite, nao preto — escolha do Eduardo) ──────────
E = {
  # GRAFITE, e nao preto: 0,205 saia em #16161d, que e quase preto. Varri a
  # faixa e 0,26 / 0,32 e o par mais escuro que ainda separa o cartao do
  # fundo (1,22:1) sem virar carvao.
  "bg-void":       "oklch(0.260 0.012 285)",   # o fundo da pagina  #23232a
  "surface-solid": "oklch(0.320 0.014 285)",   # cartao             #32323a
  "surface-alto":  "oklch(0.375 0.016 285)",   # cartao sobre cartao
  "line":          "oklch(0.440 0.018 285)",
  "ink":           "oklch(0.955 0.006 285)",
  "ink-2":         "oklch(0.800 0.012 285)",
  "ink-3":         "oklch(0.705 0.016 285)",
  # marca, mais clara do que no tema claro para sobreviver ao fundo escuro
  "ciano":         "oklch(0.800 0.120 195)",
  "violeta":       "oklch(0.740 0.150 295)",
  "rosa":          "oklch(0.760 0.160 345)",
  "acao-azul":     "oklch(0.760 0.120 205)",
  "acao-violeta":  "oklch(0.740 0.150 295)",
  # Tingimento e superficie ELEVADA, entao tem de ser mais claro que o
  # cartao (0,32) — nao mais escuro. Em 0,31 eles ficavam abaixo do cartao
  # e o "destaque" lia como buraco.
  "tint-ciano":    "oklch(0.375 0.055 195)",
  "tint-violeta":  "oklch(0.375 0.060 295)",
  "tint-rosa":     "oklch(0.375 0.060 345)",
  # texto sobre o tingimento
  "texto-ciano":   "oklch(0.880 0.080 197)",
  "texto-violeta": "oklch(0.870 0.080 295)",
  "texto-rosa":    "oklch(0.880 0.085 348)",
  "danger":        "oklch(0.720 0.150 25)",
}

PARES = [
  ("texto normal sobre o fundo",        "ink",          "bg-void",       4.5),
  ("texto normal sobre cartao",         "ink",          "surface-solid", 4.5),
  ("texto normal sobre cartao alto",    "ink",          "surface-alto",  4.5),
  ("texto secundario sobre cartao",     "ink-2",        "surface-solid", 4.5),
  ("texto apagado sobre cartao",        "ink-3",        "surface-solid", 4.5),
  ("texto apagado sobre o fundo",       "ink-3",        "bg-void",       4.5),
  ("ciano sobre cartao",                "ciano",        "surface-solid", 3.0),
  ("violeta sobre cartao",              "violeta",      "surface-solid", 3.0),
  ("rosa sobre cartao",                 "rosa",         "surface-solid", 3.0),
  ("acao-azul sobre cartao",            "acao-azul",    "surface-solid", 3.0),
  ("texto no tingimento ciano",         "texto-ciano",  "tint-ciano",    4.5),
  ("texto no tingimento violeta",       "texto-violeta","tint-violeta",  4.5),
  ("texto no tingimento rosa",          "texto-rosa",   "tint-rosa",     4.5),
  ("erro sobre cartao",                 "danger",       "surface-solid", 4.5),
  ("borda sobre cartao",                "line",         "surface-solid", 1.4),
  ("tingimento acima do cartao",        "tint-violeta", "surface-solid", 1.1),
  ("cartao contra o fundo",             "surface-solid","bg-void",       1.2),
]

print("  PALETA ESCURA — contraste medido\n")
print(f"  {'par':<34} {'medido':>8}  {'minimo':>7}")
ruins = []
for rot, a, b, minimo in PARES:
    c = contraste(E[a], E[b])
    ok = c >= minimo
    if not ok: ruins.append((rot, a, b, c, minimo))
    print(f"  {'  ' if ok else '!!'}{rot:<32} {c:7.2f}:1 {minimo:6.1f}:1")

print("\n  em hex, para conferir no navegador:")
for k, v in E.items():
    print(f"     --{k:<15} {Color(v).convert('srgb').to_string(hex=True)}")

if ruins:
    print(f"\n  {len(ruins)} par(es) abaixo do minimo:")
    for rot, a, b, c, m in ruins:
        print(f"     {rot}: {c:.2f} < {m}   ({a} sobre {b})")
    raise SystemExit(1)
print("\n  todos os pares passam.")
