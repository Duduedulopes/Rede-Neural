// ══════════════════════════════════════════════════════════════════════
//  A AUDITORIA DE CONTRASTE, FEITA NA PÁGINA RENDERIZADA.
//
//  Medir a paleta no papel não basta: o que chega ao olho é a cor
//  DEPOIS de herança, opacidade, fundo translúcido e gradiente. "Produtos"
//  sumiu no escuro e a paleta estava toda aprovada — a conta certa é sobre
//  o pixel, não sobre o token.
//
//  Por isso isto roda no navegador e caminha o DOM: para cada texto,
//  descobre a cor efetiva e o fundo efetivo (subindo até achar quem pinta),
//  e mede.
// ══════════════════════════════════════════════════════════════════════
import { chromium } from "playwright";

const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
const achados = {};

for (const tema of ["claro", "escuro"]) {
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: 2 });
  await p.goto("file:///root/audit/pagina.html", { waitUntil: "networkidle" });
  await p.evaluate(t => document.documentElement.setAttribute("data-tema", t), tema);
  await p.waitForTimeout(400);

  achados[tema] = await p.evaluate(() => {
    const lum = ([r, g, b]) => {
      const f = u => { u /= 255; return u <= .04045 ? u / 12.92 : ((u + .055) / 1.055) ** 2.4; };
      return .2126 * f(r) + .7152 * f(g) + .0722 * f(b);
    };
    // O NAVEGADOR DEVOLVE `oklch(...)`, NAO `rgb(...)`.
    //
    // A primeira versao disto lia os numeros com uma regex e tratava
    // 0.955 / 0.006 / 285 como se fossem r/g/b. Resultado: 26 "falhas"
    // todas em 1:1, e nenhuma delas real. A regex parecia funcionar
    // porque devolvia numeros — mas eram os numeros errados.
    //
    // Quem sabe converter qualquer cor de CSS para sRGB e o proprio
    // navegador. Pintar num canvas e ler o pixel de volta nao tem como
    // divergir do que o olho recebe, que e exatamente o que se quer medir.
    const cv = document.createElement("canvas");
    cv.width = cv.height = 1;
    const cx = cv.getContext("2d", { willReadFrequently: true });
    const cache = new Map();
    const rgba = s => {
      if (cache.has(s)) return cache.get(s);
      cx.clearRect(0, 0, 1, 1);
      cx.fillStyle = "#000";
      cx.fillStyle = s;                    // se a cor for invalida, fica #000
      cx.globalCompositeOperation = "copy";
      cx.fillRect(0, 0, 1, 1);
      const d = cx.getImageData(0, 0, 1, 1).data;
      const a = d[3] / 255;
      // getImageData vem pre-multiplicado: desfaz para ter a cor original
      const v = a === 0 ? [0, 0, 0, 0]
                        : [d[0] / a, d[1] / a, d[2] / a, a].map((x, i) => i < 3 ? Math.min(255, x) : x);
      cache.set(s, v);
      return v;
    };
    // compõe uma cor translúcida sobre o que está atrás
    const sobre = (f, t) => f.slice(0, 3).map((c, i) => c * f[3] + t[i] * (1 - f[3]));

    // o fundo EFETIVO: sobe na árvore compondo cada camada translúcida
    const fundoDe = el => {
      let pilha = [];
      for (let n = el; n; n = n.parentElement) {
        const bg = rgba(getComputedStyle(n).backgroundColor);
        if (bg[3] > 0) pilha.push(bg);
        if (bg[3] === 1) break;
      }
      let base = [255, 255, 255];
      for (let i = pilha.length - 1; i >= 0; i--) base = sobre(pilha[i], base);
      return base;
    };

    const con = (a, b) => {
      const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
      return (x + .05) / (y + .05);
    };

    // FUNDO EM GRADIENTE: NÃO DÁ PARA MEDIR ASSIM, E MENTIR É PIOR.
    //
    // O avatar do operador aparecia como "branco sobre branco, 1:1" — ele
    // tem `background: var(--marca)`, um gradiente, e o walker só enxerga
    // `backgroundColor`, que ali é transparente. O número era inventado.
    //
    // Alarme falso repetido treina quem lê a ignorar a lista inteira.
    // Declarar que não sei medir é melhor do que produzir 1:1.
    // O <body> TAMBÉM TEM GRADIENTE, e ignorar tudo que está sobre ele
    // seria pular a página inteira — 15 de 16 textos, incluindo os menus
    // que sumiram. Um medidor que se cala em tudo não mede nada.
    //
    // Mas o gradiente do body tem uma cor sólida como última camada do
    // atalho `background`, e é ela que vira `backgroundColor`. Para o que
    // está por cima, essa sólida é uma base honesta.
    //
    // Então a regra é: pular só quando o gradiente for de um elemento
    // PRÓPRIO — o avatar com `var(--marca)` —, não quando for o fundo da
    // página.
    const temGradiente = el => {
      for (let n = el; n && n !== document.body && n !== document.documentElement; n = n.parentElement) {
        const c2 = getComputedStyle(n);
        if (c2.backgroundImage && c2.backgroundImage !== "none") return true;
        if (rgba(c2.backgroundColor)[3] === 1) return false;
      }
      return false;
    };

    const out = [], pulados = [];
    document.querySelectorAll("*").forEach(el => {
      const txt = [...el.childNodes]
        .filter(n => n.nodeType === 3 && n.textContent.trim())
        .map(n => n.textContent.trim()).join(" ");
      if (!txt) return;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;

      if (temGradiente(el)) { pulados.push(txt.slice(0, 30)); return; }
      const cor = sobre(rgba(cs.color), fundoDe(el));
      const c = con(cor, fundoDe(el));
      const tam = parseFloat(cs.fontSize);
      const grande = tam >= 24 || (tam >= 18.66 && +cs.fontWeight >= 700);
      const minimo = grande ? 3 : 4.5;
      if (c < minimo) out.push({
        txt: txt.slice(0, 40),
        alvo: el.className || el.tagName.toLowerCase(),
        c: +c.toFixed(2), minimo, tam: +tam.toFixed(1),
        cor: cs.color, fundo: `rgb(${fundoDe(el).map(Math.round)})`
      });
    });
    return { out, pulados };
  });
  await p.screenshot({ path: `/root/audit/${tema}.png`, fullPage: true });
  await p.close();
}

for (const [tema, r] of Object.entries(achados)) {
  const lista = r.out;
  console.log(`\n═══ ${tema.toUpperCase()} — ${lista.length} abaixo do mínimo ═══`);
  if (r.pulados.length)
    console.log(`  (${r.pulados.length} com fundo em gradiente, que este medidor não sabe medir: ${r.pulados.join(", ")})`);
  for (const f of lista)
    console.log(`  ${String(f.c).padStart(5)}:1 (min ${f.minimo})  ${f.alvo.slice(0,26).padEnd(26)} "${f.txt}"\n              ${f.cor} sobre ${f.fundo}`);
}
await b.close();
