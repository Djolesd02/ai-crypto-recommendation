const DATA_URL =
  "https://raw.githubusercontent.com/Djolesd02/ai-crypto-recommendation/data/data.json";
const REFRESH_MS = 15 * 60 * 1000;

const RISK_LABEL = { low: "Nizak", medium: "Srednji", high: "Visok" };

const fmtPrice = (p) => {
  if (!p) return "$0";
  return p >= 1 ? "$" + p.toFixed(2) : "$" + Number(p).toPrecision(3);
};
const fmtUsd = (n) =>
  n >= 1e6 ? "$" + (n / 1e6).toFixed(1) + "M"
  : n >= 1e3 ? "$" + (n / 1e3).toFixed(0) + "k"
  : "$" + Math.round(n || 0);
const chg = (v) => {
  const cls = v >= 0 ? "up" : "down";
  const sign = v >= 0 ? "+" : "";
  return `<span class="${cls}">${sign}${(v || 0).toFixed(1)}%</span>`;
};

function setStatus(text, state) {
  const el = document.getElementById("status");
  el.dataset.state = state;
  el.querySelector(".pulse-text").textContent = text;
}

function agoMinutes(generatedAt) {
  return Math.max(0, Math.round((Date.now() - generatedAt) / 60000));
}

function eqBars(c, delay) {
  const bands = [
    ["M", c.momentum], ["L", c.liquidity], ["B", c.safety], ["S", c.freshness],
  ];
  const cols = bands.map(([k, v], i) => {
    const h = Math.max(4, Math.min(100, v));
    const d = (delay + i * 0.05).toFixed(2);
    return `<div class="eq-col">
        <div class="eq-track"><i style="--h:${h}%;animation-delay:${d}s"></i></div>
        <span class="eq-k">${k}</span>
      </div>`;
  }).join("");
  return `<div class="eq" role="img"
      aria-label="Momentum ${c.momentum}, likvidnost ${c.liquidity}, bezbednost ${c.safety}, svežina ${c.freshness}">${cols}</div>`;
}

function card(c, index) {
  const delay = 0.05 + index * 0.06;
  const primary = c.rank === 1 ? " signal--primary" : "";
  const rugLink = c.rugcheck_url
    ? `<a href="${c.rugcheck_url}" target="_blank" rel="noopener">RugCheck</a>` : "";
  return `<article class="signal${primary}" style="animation-delay:${delay}s">
    <div class="rank">${String(c.rank).padStart(2, "0")}</div>
    <div class="id">
      <div class="sym">${c.symbol}</div>
      <div class="name">${c.name} · <span class="chain">${c.chain}</span></div>
    </div>
    <div class="stats">
      <span class="price">${fmtPrice(c.price_usd)}</span>
      <span><span class="lab">1h</span> ${chg(c.change_h1)}</span>
      <span><span class="lab">24h</span> ${chg(c.change_h24)}</span>
      <span><span class="lab">likv</span> ${fmtUsd(c.liquidity_usd)}</span>
      <span><span class="lab">vol</span> ${fmtUsd(c.volume_h24)}</span>
    </div>
    ${eqBars(c, delay)}
    <div class="score">
      <div class="score-cap">Signal</div>
      <div class="score-val">${c.total}</div>
      <div class="score-track"><i style="--w:${Math.min(100, c.total)}%"></i></div>
      <span class="risk ${c.risk_level}">${RISK_LABEL[c.risk_level] || c.risk_level}</span>
    </div>
    <div class="links">
      <a href="${c.dex_url}" target="_blank" rel="noopener">Grafikon</a>
      ${rugLink}
    </div>
  </article>`;
}

function render(payload) {
  const list = document.getElementById("list");
  const coins = payload.coins || [];
  document.getElementById("count").textContent = coins.length;
  if (!coins.length) {
    list.innerHTML = `<div class="notice"><strong>Nema signala trenutno.</strong>
      Radar nije uhvatio nijedan coin koji prolazi filtere. Pokušaj kasnije.</div>`;
    list.setAttribute("aria-busy", "false");
    return;
  }
  list.innerHTML = coins.map((c, i) => card(c, i)).join("");
  list.setAttribute("aria-busy", "false");
}

async function load() {
  try {
    const resp = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const payload = await resp.json();
    render(payload);
    const mins = agoMinutes(payload.generated_at);
    if (mins <= 20) setStatus(`Uživo · pre ${mins} min`, "fresh");
    else setStatus(`Signal star · pre ${mins} min`, "stale");
  } catch (e) {
    setStatus("Nema veze sa radarom", "error");
    const list = document.getElementById("list");
    if (!list.querySelector(".signal")) {
      list.innerHTML = `<div class="notice"><strong>Radar ne hvata signal.</strong>
        Ne mogu da dohvatim podatke — proveri da li skripta radi i da li je objavila data.json.</div>`;
      list.setAttribute("aria-busy", "false");
    }
  }
}

load();
setInterval(load, REFRESH_MS);
