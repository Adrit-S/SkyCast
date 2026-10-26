const SERIES = { persistence: "--s1", climatology: "--s2", linear: "--s3", gbm: "--s4" };
const NS = "http://www.w3.org/2000/svg";
const tip = document.getElementById("tip");
const state = { bt: "tmax", sk: "tmax" };
let DATA = null;

const fmtDay = (iso, opts) => new Date(iso + "T12:00:00").toLocaleDateString("en-US", opts);
const signed = (n) => (n > 0 ? "+" : n < 0 ? "−" : "±") + Math.abs(Math.round(n));

function el(tag, attrs = {}, parent) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

function niceTicks(min, max, count = 5) {
  const step0 = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0);
  const ticks = [];
  for (let v = Math.floor(min / step) * step; v <= max + 1e-9; v += step) ticks.push(+v.toFixed(6));
  return ticks;
}

function showTip(evt, html) {
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 14, r = tip.getBoundingClientRect();
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - pad;
  if (y + r.height > innerHeight - 8) y = evt.clientY - r.height - pad;
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}
const hideTip = () => (tip.hidden = true);

/* ---------- forecast cards ---------- */
function renderCards(fc) {
  document.getElementById("loc").textContent = fc.location;
  document.getElementById("issued").textContent =
    `Based on observations through ${fmtDay(fc.issued_from, { weekday: "long", month: "short", day: "numeric" })}.`;
  const box = document.getElementById("cards");
  box.innerHTML = "";
  for (const d of fc.days) {
    const pct = Math.round(d.rain * 100);
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="day">${fmtDay(d.date, { weekday: "long" })}</div>
      <div class="date">${fmtDay(d.date, { month: "short", day: "numeric" })} · ${d.horizon}-day lead</div>
      <div class="temps"><span class="hi">${Math.round(d.tmax)}°</span><span class="lo">${Math.round(d.tmin)}°</span></div>
      <div class="vs">High ${signed(d.tmax - d.normal.tmax)}° vs normal ${Math.round(d.normal.tmax)}°</div>
      <div class="rain">
        <div class="rain-row"><span>Chance of rain</span><strong>${pct}%</strong></div>
        <div class="meter" role="img" aria-label="${pct}% chance of rain"><span style="width:${pct}%"></span></div>
        <div class="badge">Normal for the date: ${Math.round(d.normal.rain * 100)}%</div>
      </div>`;
    box.appendChild(card);
  }
}

/* ---------- backtest line chart ---------- */
function renderBacktest() {
  const bt = DATA.backtest[state.bt];
  const box = document.getElementById("bt-chart");
  const W = Math.max(320, box.clientWidth - 16), H = 280;
  const m = { t: 12, r: 14, b: 28, l: 36 };
  const n = bt.dates.length;
  const vals = [...bt.actual, ...bt.skycast];
  const ticks = niceTicks(Math.min(...vals), Math.max(...vals));
  const y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const x = (i) => m.l + (i / (n - 1)) * (W - m.l - m.r);
  const y = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b);

  const mae = bt.actual.reduce((s, a, i) => s + Math.abs(a - bt.skycast[i]), 0) / n;
  document.getElementById("bt-caption").textContent =
    `SkyCast's next-day ${state.bt === "tmax" ? "high" : "low"} vs what actually happened, last ${n} test days. Average miss: ${mae.toFixed(1)}°F.`;

  box.innerHTML = "";
  const legend = document.createElement("div");
  legend.className = "legend";
  legend.style.padding = "0 8px";
  legend.innerHTML = `<span><i class="line" style="background:var(--s1)"></i>Actual</span><span><i class="line" style="background:var(--s2)"></i>SkyCast (1 day ahead)</span>`;
  box.appendChild(legend);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Line chart of predicted versus actual temperature" }, box);

  for (const t of ticks) {
    el("line", { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), class: "grid" }, svg);
    el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end" }, svg).textContent = t + "°";
  }
  let lastMonth = "";
  bt.dates.forEach((d, i) => {
    const mo = d.slice(0, 7);
    if (mo !== lastMonth && d.slice(8) <= "07") {
      el("text", { x: x(i), y: H - 8, "text-anchor": "start" }, svg).textContent = fmtDay(d, { month: "short" });
      lastMonth = mo;
    }
  });

  const path = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  el("path", { d: path(bt.actual), fill: "none", style: "stroke:var(--s1)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
  el("path", { d: path(bt.skycast), fill: "none", style: "stroke:var(--s2)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);

  const cross = el("line", { y1: m.t, y2: H - m.b, style: "stroke:var(--text-3)", "stroke-width": 1, visibility: "hidden" }, svg);
  const dots = ["--s1", "--s2"].map((c) => el("circle", { r: 4, style: `fill:var(${c});stroke:var(--surface)`, "stroke-width": 2, visibility: "hidden" }, svg));
  const hit = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);

  hit.addEventListener("pointermove", (evt) => {
    const r = svg.getBoundingClientRect();
    const px = ((evt.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(n - 1, Math.round(((px - m.l) / (W - m.l - m.r)) * (n - 1))));
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
    [bt.actual[i], bt.skycast[i]].forEach((v, k) => {
      dots[k].setAttribute("cx", x(i)); dots[k].setAttribute("cy", y(v)); dots[k].setAttribute("visibility", "visible");
    });
    const diff = bt.skycast[i] - bt.actual[i];
    showTip(evt, `<div class="t">${fmtDay(bt.dates[i], { weekday: "short", month: "short", day: "numeric", year: "numeric" })}</div>
      <div class="r"><i style="background:var(--s1)"></i>Actual <strong>${bt.actual[i].toFixed(0)}°F</strong></div>
      <div class="r"><i style="background:var(--s2)"></i>SkyCast <strong>${bt.skycast[i].toFixed(0)}°F</strong></div>
      <div class="t">Missed by ${Math.abs(diff).toFixed(1)}°</div>`);
  });
  hit.addEventListener("pointerleave", () => {
    hideTip();
    cross.setAttribute("visibility", "hidden");
    dots.forEach((d) => d.setAttribute("visibility", "hidden"));
  });
}

/* ---------- skill grouped columns ---------- */
function renderSkill() {
  const met = DATA.metrics;
  const t = met.targets[state.sk];
  const horizons = Object.keys(t);
  const models = Object.keys(SERIES);

  document.getElementById("sk-legend").innerHTML = models
    .map((k) => `<span><i style="background:var(${SERIES[k]})"></i>${met.models[k]}</span>`).join("");

  const box = document.getElementById("sk-chart");
  const W = Math.max(320, box.clientWidth - 16), H = 240;
  const m = { t: 12, r: 8, b: 28, l: 36 };
  const max = Math.max(...horizons.flatMap((h) => models.map((k) => t[h][k].mae)));
  const ticks = niceTicks(0, max, 4);
  const top = ticks[ticks.length - 1];
  const y = (v) => H - m.b - (v / top) * (H - m.t - m.b);
  const band = (W - m.l - m.r) / horizons.length;
  const bw = Math.min(24, (band * 0.6) / models.length - 2);
  const groupW = models.length * bw + (models.length - 1) * 2;

  box.innerHTML = "";
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Column chart of forecast error by model and lead time" }, box);
  for (const tk of ticks) {
    el("line", { x1: m.l, x2: W - m.r, y1: y(tk), y2: y(tk), class: "grid" }, svg);
    el("text", { x: m.l - 6, y: y(tk) + 4, "text-anchor": "end" }, svg).textContent = tk + "°";
  }
  horizons.forEach((h, hi) => {
    const gx = m.l + hi * band + (band - groupW) / 2;
    el("text", { x: m.l + hi * band + band / 2, y: H - 8, "text-anchor": "middle", class: "label" }, svg)
      .textContent = `${h.slice(1)} day${h === "h1" ? "" : "s"} ahead`;
    models.forEach((k, mi) => {
      const v = t[h][k].mae, bx = gx + mi * (bw + 2), by = y(v), bh = y(0) - by, r = Math.min(4, bh);
      const d = `M${bx},${y(0)}V${by + r}Q${bx},${by} ${bx + r},${by}H${bx + bw - r}Q${bx + bw},${by} ${bx + bw},${by + r}V${y(0)}Z`;
      el("path", { d, style: `fill:var(${SERIES[k]})` }, svg);
      const hit = el("rect", { x: bx - 1, y: m.t, width: bw + 2, height: H - m.t - m.b, fill: "transparent" }, svg);
      hit.addEventListener("pointermove", (evt) => showTip(evt,
        `<div class="t">${h.slice(1)} day${h === "h1" ? "" : "s"} ahead</div>
         <div class="r"><i style="background:var(${SERIES[k]})"></i>${met.models[k]} <strong>${v.toFixed(2)}°F</strong></div>`));
      hit.addEventListener("pointerleave", hideTip);
    });
  });

  const table = document.getElementById("sk-table");
  table.innerHTML = `<thead><tr><th>Model</th>${horizons.map((h) => `<th>${h.slice(1)}-day</th>`).join("")}</tr></thead><tbody>${models
    .map((k) => `<tr><td>${met.models[k]}</td>${horizons.map((h) => {
      const best = Math.min(...models.map((mm) => t[h][mm].mae)) === t[h][k].mae;
      return `<td class="${best ? "best" : ""}">${t[h][k].mae.toFixed(2)}°</td>`;
    }).join("")}</tr>`).join("")}</tbody>`;
}

function renderRain() {
  const met = DATA.metrics, t = met.targets.rain, horizons = Object.keys(t);
  const models = ["persistence", "linear", "gbm"];
  document.getElementById("rn-table").innerHTML =
    `<thead><tr><th>Model</th>${horizons.map((h) => `<th>${h.slice(1)}-day</th>`).join("")}</tr></thead><tbody>${models
      .map((k) => `<tr><td>${met.models[k]}</td>${horizons.map((h) => {
        const s = t[h][k].brier_skill, best = t[h].best === k;
        return `<td class="${best ? "best" : ""}">${s >= 0 ? "+" : "−"}${Math.abs(s).toFixed(2)}</td>`;
      }).join("")}</tr>`).join("")}</tbody>`;
  document.getElementById("test-start").textContent = met.test_start.slice(0, 4);
}

function wireToggles(attr, key, render) {
  document.querySelectorAll(`[data-${attr}]`).forEach((btn) =>
    btn.addEventListener("click", () => {
      state[key] = btn.dataset[attr];
      document.querySelectorAll(`[data-${attr}]`).forEach((b) => b.setAttribute("aria-pressed", b === btn));
      render();
    }));
}

async function main() {
  const get = (f) => fetch(`data/${f}.json`, { cache: "no-store" }).then((r) => r.json());
  try {
    const [forecast, metrics, backtest] = await Promise.all([get("forecast"), get("metrics"), get("backtest")]);
    DATA = { forecast, metrics, backtest };
  } catch (e) {
    document.getElementById("cards").innerHTML =
      `<p class="muted">Couldn't load forecast data. If you opened this file directly, serve it instead: <code>python3 -m http.server -d docs</code></p>`;
    return;
  }
  renderCards(DATA.forecast);
  renderBacktest();
  renderSkill();
  renderRain();
  wireToggles("bt", "bt", renderBacktest);
  wireToggles("sk", "sk", renderSkill);
  let rt;
  addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { renderBacktest(); renderSkill(); }, 150); });
}
main();
