// Screenshots every docs/*.html page in light and dark at 1440 and 390 px into
// screenshots/docs/, and reports horizontal overflow and console errors.
// Run: node docs/assets/screenshot-docs.mjs [page ...]
import { chromium } from "playwright";
import { readdirSync, mkdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const docs = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = resolve(docs, "..", "screenshots", "docs");
mkdirSync(outDir, { recursive: true });
const only = process.argv.slice(2);
const pages = readdirSync(docs).filter((f) => f.endsWith(".html")).map((f) => f.slice(0, -5)).filter((p) => !only.length || only.includes(p));

const browser = await chromium.launch();
const problems = [];
for (const width of [1440, 390]) {
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 }, deviceScaleFactor: 1 });
    await ctx.addInitScript((t) => localStorage.setItem("keel-docs-theme", t), theme);
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    for (const p of pages) {
      errors.length = 0;
      await page.goto(pathToFileURL(join(docs, `${p}.html`)).href);
      const r = await page.evaluate(() => {
        const vw = document.documentElement.clientWidth;
        const wide = [];
        for (const el of document.querySelectorAll("main *")) {
          const b = el.getBoundingClientRect();
          if (b.right > vw + 1 && !el.closest(".table-wrap,.fig-scroll,pre")) wide.push(`${el.tagName.toLowerCase()}.${el.className}`.slice(0, 60));
        }
        return { sw: document.documentElement.scrollWidth, vw, theme: document.documentElement.dataset.theme, wide: wide.slice(0, 5) };
      });
      if (r.sw > r.vw || r.wide.length) problems.push(`${p} ${theme} ${width}: scrollWidth ${r.sw} > ${r.vw} ${r.wide.join(", ")}`);
      if (r.theme !== theme) problems.push(`${p}: theme ${r.theme} != ${theme}`);
      if (errors.length) problems.push(`${p} ${theme} ${width}: ${errors.join(" | ")}`);
      await page.screenshot({ path: join(outDir, `${p}-${theme}-${width}.png`), fullPage: true });
    }
    await ctx.close();
  }
}
await browser.close();
console.log(`${pages.length * 4} screenshots in ${outDir}`);
for (const p of problems) console.log(`PROBLEM ${p}`);
