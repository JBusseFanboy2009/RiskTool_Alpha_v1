let token = localStorage.getItem("token") || null;
const chartInstances = {};

const content = document.getElementById("content");
const authView = document.getElementById("authView");
const appView = document.getElementById("appView");

function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

function destroyAllCharts() {
  Object.keys(chartInstances).forEach(destroyChart);
}

function setSidebarActive(route) {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    const active = btn.dataset.route === route;
    btn.classList.toggle("bg-slate-800", active);
    btn.classList.toggle("text-white", active);
    btn.classList.toggle("font-semibold", active);
    btn.classList.toggle("text-slate-200", !active);
    btn.classList.toggle("hover:bg-slate-800", !active);
  });
}

function setAuthState() {
  if (token) {
    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    document.getElementById("logoutBtn").classList.remove("hidden");
    routeTo("dashboard");
  } else {
    authView.classList.remove("hidden");
    appView.classList.add("hidden");
    document.getElementById("logoutBtn").classList.add("hidden");
  }
}

function formatApiError(detail) {
  if (detail == null) return "API error";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return String(detail);
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = "API error";
    try {
      const body = await res.json();
      detail = formatApiError(body.detail);
    } catch (_) {
      detail = res.statusText || detail;
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function asNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatPercent(value, digits = 2) {
  return `${asNumber(value).toFixed(digits)}%`;
}

function formatRatio(value, digits = 2) {
  return asNumber(value).toFixed(digits);
}

function formatSignedPercent(value, digits = 2) {
  const n = asNumber(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

function dayChangeClass(value) {
  const n = asNumber(value);
  if (n > 0) return "text-emerald-600 font-medium";
  if (n < 0) return "text-red-600 font-medium";
  return "text-slate-600";
}

function riskColor(score) {
  const s = Math.max(0, Math.min(100, asNumber(score)));
  if (s < 33) return "#22c55e";
  if (s < 66) return "#eab308";
  return "#ef4444";
}

function correlationColor(value) {
  const v = Math.max(-1, Math.min(1, asNumber(value)));
  const t = (v + 1) / 2;
  const r = Math.round(239 * t + 34 * (1 - t));
  const g = Math.round(68 * t + 197 * (1 - t));
  const b = Math.round(68 * t + 94 * (1 - t));
  return `rgb(${r},${g},${b})`;
}

function riskSymbolsForm(endpoint, title, extraHtml = "") {
  return `
    <h2 class="text-2xl font-bold mb-4">${escapeHtml(title)}</h2>
    <div class="bg-white p-4 rounded shadow">
      <input id="symbolsInput" class="border rounded p-2 w-full mb-2" placeholder="Ticker komma-getrennt, z.B. AAPL,MSFT,SPY"/>
      <div class="flex gap-2 mb-3 flex-wrap">
        <button type="button" id="usePortfolioBtn" class="px-3 py-2 rounded bg-slate-700 text-white">Portfolio übernehmen</button>
        <button type="button" id="calcBtn" class="px-3 py-2 rounded bg-slate-900 text-white">Berechnen</button>
      </div>
      ${extraHtml}
      <div id="riskChartArea" class="mt-4"></div>
    </div>
  `;
}

function bindRiskSymbolsForm(onCalc) {
  document.getElementById("usePortfolioBtn").onclick = async () => {
    const symbols = await api("/risk/portfolio-symbols");
    const list = symbols && Array.isArray(symbols.symbols) ? symbols.symbols : [];
    document.getElementById("symbolsInput").value = list.join(",");
  };
  document.getElementById("calcBtn").onclick = onCalc;
}

function getSymbolsFromInput() {
  return document
    .getElementById("symbolsInput")
    .value.split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function renderBarChart(canvasId, labels, values, label, asPct = true) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  destroyChart(canvasId);
  chartInstances[canvasId] = new Chart(ctx.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: labels.map((_, i) => `hsl(${(i * 47) % 360} 55% 45%)`),
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => (asPct ? formatPercent(ctx.parsed.x * 100) : ctx.parsed.x.toFixed(4)),
          },
        },
      },
      scales: {
        x: {
          ticks: {
            callback: (v) => (asPct ? `${(v * 100).toFixed(1)}%` : v),
          },
        },
      },
    },
  });
}

function renderDonutChart(canvasId, labels, values, title) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  destroyChart(canvasId);
  chartInstances[canvasId] = new Chart(ctx.getContext("2d"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: labels.map((_, i) => `hsl(${(i * 53) % 360} 60% 50%)`) }],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "right" }, title: { display: !!title, text: title } },
    },
  });
}

function renderCorrelationHeatmap(containerId, matrix, labels) {
  const el = document.getElementById(containerId);
  if (!el || !labels.length) {
    el.innerHTML = '<p class="text-slate-500">Keine Korrelationsdaten.</p>';
    return;
  }
  const header = `<tr><th class="p-1 text-xs"></th>${labels.map((l) => `<th class="p-1 text-xs font-medium">${escapeHtml(l)}</th>`).join("")}</tr>`;
  const rows = labels
    .map((rowLabel) => {
      const cells = labels
        .map((colLabel) => {
          const v = asNumber(matrix[rowLabel]?.[colLabel], rowLabel === colLabel ? 1 : 0);
          return `<td class="p-1 text-center text-xs text-white font-medium" style="background:${correlationColor(v)}" title="${rowLabel} / ${colLabel}: ${v.toFixed(2)}">${v.toFixed(2)}</td>`;
        })
        .join("");
      return `<tr><th class="p-1 text-xs text-right font-medium">${escapeHtml(rowLabel)}</th>${cells}</tr>`;
    })
    .join("");
  el.innerHTML = `
    <p class="text-sm text-slate-600 mb-2">Grün/blau = geringe Korrelation, rot = hohe Korrelation</p>
    <div class="overflow-x-auto"><table class="border-collapse">${header}${rows}</table></div>
  `;
}

function renderGaugeChart(canvasId, score) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  destroyChart(canvasId);
  const s = Math.max(0, Math.min(100, asNumber(score)));
  const color = riskColor(s);
  chartInstances[canvasId] = new Chart(ctx.getContext("2d"), {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [s, 100 - s],
          backgroundColor: [color, "#e2e8f0"],
          borderWidth: 0,
          circumference: 180,
          rotation: 270,
        },
      ],
    },
    options: {
      responsive: true,
      cutout: "72%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

function chartBlock(id, height = 280) {
  return `<div class="mb-4"><canvas id="${id}" height="${height}"></canvas></div>`;
}

document.getElementById("registerBtn").onclick = async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  try {
    await api("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    document.getElementById("authMsg").textContent = "Registrierung erfolgreich. Bitte einloggen.";
  } catch (e) {
    document.getElementById("authMsg").textContent = e.message;
  }
};

document.getElementById("loginBtn").onclick = async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);
  try {
    const data = await api("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    token = data.access_token;
    localStorage.setItem("token", token);
    setAuthState();
  } catch (e) {
    document.getElementById("authMsg").textContent = e.message;
  }
};

document.getElementById("logoutBtn").onclick = () => {
  token = null;
  localStorage.removeItem("token");
  setAuthState();
};

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => routeTo(btn.dataset.route));
});

async function routeTo(route) {
  if (!token) return;
  destroyAllCharts();
  setSidebarActive(route);
  try {
    if (route === "dashboard") return await renderDashboard();
    if (route === "myshares") return await renderMyShares();
    if (route === "riskometer") return await renderRiskO();
    if (route === "volatility") return await renderVolatility();
    if (route === "correlation") return await renderCorrelation();
    if (route === "drawdown") return await renderDrawdown();
    if (route === "var") return await renderVarCvar();
    if (route === "stress") return await renderStress();
  } catch (e) {
    content.innerHTML = `<div class="bg-red-50 border border-red-200 text-red-800 p-4 rounded">${escapeHtml(e.message)}</div>`;
  }
}

async function renderDashboard() {
  const data = await api("/portfolio/overview");
  const slices = Array.isArray(data.slices) ? data.slices : [];
  const total = asNumber(data.total_value);
  content.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">Portfolio Overview</h2>
    <div class="bg-white p-4 rounded shadow max-w-3xl">
      <p class="mb-2">Gesamtwert: <strong>${total.toFixed(2)} EUR</strong></p>
      <canvas id="allocationChart"></canvas>
    </div>
  `;
  const ctx = document.getElementById("allocationChart").getContext("2d");
  chartInstances.allocationChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: slices.map((s) => s.ticker),
      datasets: [{ data: slices.map((s) => asNumber(s.value)) }],
    },
  });
}

async function renderMyShares() {
  const rows = await api("/positions");
  const list = Array.isArray(rows) ? rows : [];

  content.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">MyShares</h2>
    <div class="bg-white p-4 rounded shadow mb-6">
      <h3 class="font-semibold mb-2">Neue Position erfassen</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
        <input id="symbolInput" class="border rounded p-2" placeholder="Ticker (exakt, z. B. AAPL, SPY, VUSA.L, DAX.DE)"/>
        <input id="quantityInput" class="border rounded p-2" type="number" min="0.0001" step="0.0001" placeholder="Stückzahl"/>
        <input id="buyPriceInput" class="border rounded p-2" type="number" min="0.0001" step="0.0001" placeholder="Kaufkurs"/>
      </div>
      <div id="autocomplete" class="mt-2 text-sm"></div>
      <button id="addPositionBtn" class="mt-3 px-4 py-2 rounded bg-slate-900 text-white">Speichern</button>
    </div>
    <div class="bg-white p-4 rounded shadow overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left border-b">
            <th>Ticker</th><th>Stückzahl</th><th>Kaufkurs</th><th>Live</th><th>Tag %</th><th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          ${list.length === 0 ? `<tr><td colspan="6" class="py-4 text-slate-500">Keine Positionen vorhanden.</td></tr>` : list
            .map((r) => {
              const dc = asNumber(r.day_change_pct);
              return `
            <tr class="border-b hover:bg-slate-50" data-position-id="${r.id}">
              <td class="py-2 cursor-pointer view-cell">${escapeHtml(r.ticker)}</td>
              <td class="py-2 cursor-pointer view-cell">${asNumber(r.quantity)}</td>
              <td class="py-2 cursor-pointer view-cell">${asNumber(r.buy_price).toFixed(2)}</td>
              <td class="py-2 cursor-pointer view-cell">${asNumber(r.current_price).toFixed(2)}</td>
              <td class="py-2 cursor-pointer view-cell ${dayChangeClass(dc)}">${formatSignedPercent(dc)}</td>
              <td class="py-2 text-right whitespace-nowrap">
                <button type="button" class="view-btn px-2 py-1 rounded bg-slate-800 text-white text-xs mr-1" data-position-id="${r.id}">Ansehen</button>
                <button type="button" class="delete-btn px-2 py-1 rounded bg-red-600 text-white text-xs" data-position-id="${r.id}">Löschen</button>
              </td>
            </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;

  document.querySelectorAll(".view-btn, .view-cell").forEach((el) => {
    el.addEventListener("click", (e) => {
      const row = e.target.closest("tr[data-position-id]");
      if (!row) return;
      renderPositionDetail(Number(row.dataset.positionId));
    });
  });

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.positionId);
      if (!confirm("Position wirklich löschen?")) return;
      try {
        await api(`/positions/${id}`, { method: "DELETE" });
        await renderMyShares();
      } catch (err) {
        alert(err.message);
      }
    });
  });

  document.getElementById("symbolInput").addEventListener("input", async (e) => {
    const q = e.target.value;
    if (q.length < 2) return (document.getElementById("autocomplete").innerHTML = "");
    try {
      const suggestions = await api(`/market/search?q=${encodeURIComponent(q)}`);
      const items = Array.isArray(suggestions) ? suggestions : [];
      document.getElementById("autocomplete").innerHTML = items
        .map(
          (s) =>
            `<button type="button" class="px-2 py-1 mr-2 mb-1 rounded bg-slate-200" data-symbol="${escapeHtml(s.symbol)}">${escapeHtml(s.symbol)} - ${escapeHtml(s.shortname || "")}</button>`
        )
        .join("");
      document.querySelectorAll("#autocomplete button").forEach((b) => {
        b.onclick = () => {
          document.getElementById("symbolInput").value = b.dataset.symbol;
          document.getElementById("autocomplete").innerHTML = "";
        };
      });
    } catch (_) {
      document.getElementById("autocomplete").innerHTML = "";
    }
  });

  document.getElementById("addPositionBtn").onclick = async () => {
    try {
      await api("/positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: document.getElementById("symbolInput").value,
          quantity: Number(document.getElementById("quantityInput").value),
          buy_price: Number(document.getElementById("buyPriceInput").value),
        }),
      });
      await renderMyShares();
    } catch (e) {
      alert(e.message);
    }
  };
}

function renderStructureBlock(structure) {
  if (!structure || typeof structure !== "object") {
    return '<p class="text-slate-500">Keine Strukturdaten verfügbar.</p>';
  }
  const sector = escapeHtml(structure.sector || "Unknown");
  const industry = escapeHtml(structure.industry || "Unknown");
  const ratios = structure.valuation_ratios && typeof structure.valuation_ratios === "object" ? structure.valuation_ratios : {};
  const ratioRows = Object.entries(ratios)
    .map(([k, v]) => `<li>${escapeHtml(k)}: <strong>${formatRatio(v)}</strong></li>`)
    .join("");

  const listBlock = (title, obj, chartId, chartType) => {
    if (!obj || typeof obj !== "object" || Object.keys(obj).length === 0) return "";
    const entries = Object.entries(obj).sort((a, b) => asNumber(b[1]) - asNumber(a[1]));
    const rows = entries.map(([k, v]) => `<li>${escapeHtml(k)}: ${formatPercent(v)}</li>`).join("");
    const labels = entries.map(([k]) => k);
    const values = entries.map(([, v]) => asNumber(v));
    const canvas =
      chartType === "donut"
        ? chartBlock(chartId, 220)
        : chartBlock(chartId, Math.max(180, labels.length * 28));
    return `
      <div class="mt-4 border-t pt-4">
        <h4 class="font-medium mb-2">${escapeHtml(title)}</h4>
        <div class="grid md:grid-cols-2 gap-4">
          <ul class="text-sm list-disc ml-5">${rows}</ul>
          <div>${canvas}</div>
        </div>
      </div>`;
  };

  return `
    <p><span class="font-medium">Sektor:</span> ${sector}</p>
    <p><span class="font-medium">Branche:</span> ${industry}</p>
    ${ratioRows ? `<div class="mt-3"><h4 class="font-medium">Fundamentale Kennzahlen</h4><ul class="text-sm list-disc ml-5">${ratioRows}</ul></div>` : ""}
    ${listBlock("Sektorverteilung", structure.sectors, "structSectorsChart", "bar")}
    ${listBlock("Top Holdings", structure.top_holdings, "structHoldingsChart", "donut")}
    ${listBlock("Länder / Ratings", structure.countries, "structCountriesChart", "bar")}
  `;
}

function mountStructureCharts(structure) {
  if (!structure) return;
  const mount = (id, obj, type) => {
    if (!obj || !Object.keys(obj).length) return;
    const entries = Object.entries(obj).sort((a, b) => asNumber(b[1]) - asNumber(a[1]));
    const labels = entries.map(([k]) => k);
    const values = entries.map(([, v]) => asNumber(v));
    if (type === "donut") renderDonutChart(id, labels, values);
    else renderBarChart(id, labels, values, "Gewicht %", false);
  };
  mount("structSectorsChart", structure.sectors, "bar");
  mount("structHoldingsChart", structure.top_holdings, "donut");
  mount("structCountriesChart", structure.countries, "bar");
}

async function renderPositionDetail(positionId, period = "1y") {
  setSidebarActive("myshares");
  content.innerHTML = `<p class="text-slate-600">Lade Analyse …</p>`;

  let detail;
  try {
    detail = await api(`/positions/${positionId}/detail?period=${encodeURIComponent(period)}`);
  } catch (e) {
    content.innerHTML = `
      <button id="backBtn" class="mb-4 px-3 py-1 rounded bg-slate-800 text-white">Zurück</button>
      <div class="bg-red-50 border border-red-200 text-red-800 p-4 rounded">${escapeHtml(e.message)}</div>
    `;
    document.getElementById("backBtn").onclick = () => renderMyShares();
    return;
  }

  const ticker = detail.ticker || "—";
  const latestPrice = asNumber(detail.latest_price);
  const history = Array.isArray(detail.history) ? detail.history : [];
  const labels = history.map((p) => String(p.date ?? ""));
  const closes = history.map((p) => asNumber(p.close));

  content.innerHTML = `
    <button id="backBtn" class="mb-4 px-3 py-1 rounded bg-slate-800 text-white">Zurück</button>
    <h2 class="text-2xl font-bold mb-2">${escapeHtml(ticker)}</h2>
    <p class="mb-4">Live-Kurs: <strong>${latestPrice.toFixed(2)}</strong></p>
    <div class="mb-4 flex gap-2 flex-wrap">
      ${["1mo", "6mo", "1y", "3y"]
        .map(
          (p) =>
            `<button type="button" class="period-btn px-2 py-1 rounded ${p === period ? "bg-slate-800 text-white" : "bg-slate-200"}" data-period="${p}">${p.toUpperCase()}</button>`
        )
        .join("")}
    </div>
    <div class="bg-white p-4 rounded shadow mb-4">
      <canvas id="historyChart"></canvas>
      ${history.length === 0 ? '<p class="text-sm text-slate-500 mt-2">Kein Kursverlauf verfügbar.</p>' : ""}
    </div>
    <div class="bg-white p-4 rounded shadow">
      <h3 class="font-semibold mb-2">Struktur-Analyse</h3>
      ${renderStructureBlock(detail.structure)}
    </div>
  `;

  document.getElementById("backBtn").onclick = () => renderMyShares();
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.onclick = () => renderPositionDetail(positionId, btn.dataset.period);
  });

  if (history.length > 0) {
    const ctx = document.getElementById("historyChart").getContext("2d");
    chartInstances.historyChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{ label: ticker, data: closes, borderColor: "#0f172a", tension: 0.1 }],
      },
    });
  }
  mountStructureCharts(detail.structure);
}

async function renderRiskO() {
  content.innerHTML = `<p class="text-slate-600">Berechne Risiko-O-Meter …</p>`;

  let result;
  try {
    result = await api("/risk/risk-o-meter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: [] }),
    });
  } catch (e) {
    content.innerHTML = `
      <h2 class="text-2xl font-bold mb-4">Risiko-O-Meter</h2>
      <div class="bg-red-50 border border-red-200 text-red-800 p-4 rounded">${escapeHtml(e.message)}</div>
    `;
    return;
  }

  const payload = result && typeof result.result === "object" ? result.result : {};
  const score = asNumber(payload.score);
  const contributions = payload.contributions && typeof payload.contributions === "object" ? payload.contributions : {};
  const components = payload.components && typeof payload.components === "object" ? payload.components : {};
  const symbolCount = asNumber(payload.symbol_count, Object.keys(components).length);
  const color = riskColor(score);

  const rows = Object.entries(contributions)
    .sort((a, b) => asNumber(b[1]) - asNumber(a[1]))
    .map(([sym, pct]) => {
      const vol = asNumber(components[sym]) * 100;
      const barColor = riskColor(Math.min(100, vol));
      return `
        <div class="flex items-center gap-3 py-2 border-b border-slate-100">
          <span class="w-14 font-medium">${escapeHtml(sym)}</span>
          <div class="flex-1 h-2 bg-slate-100 rounded overflow-hidden">
            <div class="h-full rounded" style="width:${Math.min(100, asNumber(pct))}%;background:${barColor}"></div>
          </div>
          <span class="text-xs text-slate-600 w-24 text-right">${asNumber(pct).toFixed(1)}% Risiko</span>
          <span class="text-xs text-slate-500 w-20 text-right">${vol.toFixed(1)}% Vol</span>
        </div>`;
    })
    .join("");

  content.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">Risiko-O-Meter</h2>
    <div class="bg-white p-6 rounded shadow max-w-2xl">
      <div class="relative max-w-xs mx-auto mb-2">
        <canvas id="riskGauge"></canvas>
        <div class="absolute inset-0 flex flex-col items-center justify-end pb-6 pointer-events-none">
          <span class="text-4xl font-bold" style="color:${color}">${score.toFixed(0)}</span>
          <span class="text-sm text-slate-500">/ 100</span>
        </div>
      </div>
      <p class="text-center text-sm mb-4" style="color:${color}">${score < 33 ? "Risikoarm" : score < 66 ? "Moderat" : "Risikoreich"}</p>
      <p class="text-sm text-slate-600 mb-3 text-center">Basis: ${symbolCount} Position(en)</p>
      <h3 class="font-semibold text-sm mb-2">Beitrag je Position zum Gesamtrisiko</h3>
      ${rows || '<p class="text-slate-500">Keine Daten.</p>'}
    </div>
  `;
  renderGaugeChart("riskGauge", score);
}

async function renderVolatility() {
  content.innerHTML = riskSymbolsForm("volatility", "Volatilität (annualisiert)");
  bindRiskSymbolsForm(async () => {
    const response = await api("/risk/volatility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: getSymbolsFromInput(), confidence: 0.95 }),
    });
    const r = response.result || {};
    const labels = r.labels || Object.keys(r.annualized || {});
    const values = r.values || labels.map((k) => asNumber(r.annualized?.[k]));
    document.getElementById("riskChartArea").innerHTML = chartBlock("volChart");
    renderBarChart("volChart", labels, values.map((v) => v * 100), "Volatilität % p.a.", false);
  });
}

async function renderCorrelation() {
  content.innerHTML = riskSymbolsForm("correlation", "Korrelations-Heatmap");
  bindRiskSymbolsForm(async () => {
    const response = await api("/risk/correlation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: getSymbolsFromInput(), confidence: 0.95 }),
    });
    const r = response.result || {};
    document.getElementById("riskChartArea").innerHTML = '<div id="corrHeatmap"></div>';
    renderCorrelationHeatmap("corrHeatmap", r.matrix || {}, r.labels || []);
  });
}

async function renderDrawdown() {
  content.innerHTML = riskSymbolsForm("max-drawdown", "Maximum Drawdown");
  bindRiskSymbolsForm(async () => {
    const response = await api("/risk/max-drawdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: getSymbolsFromInput(), confidence: 0.95 }),
    });
    const r = response.result || {};
    const series = r.series || {};
    const summary = r.summary || {};
    const symbols = Object.keys(series);
    let html = symbols.map((s) => `<p class="text-sm mb-1"><strong>${escapeHtml(s)}</strong>: Max DD ${formatPercent(asNumber(summary[s]) * 100)}</p>`).join("");
    html += symbols.map((s) => chartBlock(`dd_${s}`, 200)).join("");
    document.getElementById("riskChartArea").innerHTML = html;
    symbols.forEach((sym) => {
      const s = series[sym];
      const ctx = document.getElementById(`dd_${sym}`);
      if (!ctx) return;
      destroyChart(`dd_${sym}`);
      chartInstances[`dd_${sym}`] = new Chart(ctx.getContext("2d"), {
        type: "line",
        data: {
          labels: s.dates || [],
          datasets: [
            {
              label: `${sym} Drawdown`,
              data: (s.values || []).map((v) => v * 100),
              borderColor: "#dc2626",
              backgroundColor: "rgba(220,38,38,0.1)",
              fill: true,
              tension: 0.1,
            },
          ],
        },
        options: {
          plugins: { title: { display: true, text: sym } },
          scales: { y: { ticks: { callback: (v) => `${v}%` } } },
        },
      });
    });
  });
}

async function renderVarCvar() {
  const confHtml = `<label class="text-sm block mb-2">Konfidenz: <input id="confInput" type="number" min="0.8" max="0.99" step="0.01" value="0.95" class="border rounded p-1 w-20 ml-1"/></label>`;
  content.innerHTML = riskSymbolsForm("var-cvar", "VaR & CVaR", confHtml);
  bindRiskSymbolsForm(async () => {
    const conf = asNumber(document.getElementById("confInput")?.value, 0.95);
    const response = await api("/risk/var-cvar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: getSymbolsFromInput(), confidence: conf }),
    });
    const result = response.result || {};
    let html = "";
    Object.entries(result).forEach(([sym, data]) => {
      html += `
        <div class="mb-6 border-t pt-4">
          <h3 class="font-semibold">${escapeHtml(sym)}</h3>
          <p class="text-sm">VaR (${(conf * 100).toFixed(0)}%): <strong class="text-red-600">${formatPercent(asNumber(data.var) * 100)}</strong>
          · CVaR: <strong class="text-red-700">${formatPercent(asNumber(data.cvar) * 100)}</strong></p>
          ${chartBlock(`var_${sym}`, 200)}
        </div>`;
    });
    document.getElementById("riskChartArea").innerHTML = html || '<p class="text-slate-500">Keine Daten.</p>';
    Object.entries(result).forEach(([sym, data]) => {
      const hist = data.histogram;
      if (!hist?.counts?.length) return;
      const ctx = document.getElementById(`var_${sym}`);
      if (!ctx) return;
      const mid = hist.edges.slice(0, -1).map((e, i) => ((e + hist.edges[i + 1]) / 2) * 100);
      destroyChart(`var_${sym}`);
      chartInstances[`var_${sym}`] = new Chart(ctx.getContext("2d"), {
        type: "bar",
        data: {
          labels: mid.map((v) => v.toFixed(2)),
          datasets: [{ label: "Rendite-Histogramm %", data: hist.counts, backgroundColor: "#64748b" }],
        },
        options: {
          plugins: {
            annotation: undefined,
            title: { display: true, text: "Historische Verteilung der Tagesrenditen" },
          },
        },
      });
    });
  });
}

async function renderStress() {
  let scenarios = [];
  try {
    const data = await api("/risk/stress-scenarios");
    scenarios = data.scenarios || [];
  } catch (_) {
    scenarios = [
      { id: "tech_crash", label: "Tech-Sektor Crash", description: "", default_shock: -0.15 },
      { id: "market_wide", label: "Breiter Marktcrash", description: "", default_shock: -0.25 },
    ];
  }

  const scenarioOptions = scenarios
    .map((s) => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.label)}</option>`)
    .join("");

  content.innerHTML = `
    <h2 class="text-2xl font-bold mb-4">Stress Testing</h2>
    <div class="bg-white p-4 rounded shadow max-w-3xl">
      <input id="stressSymbols" class="border rounded p-2 w-full mb-3" placeholder="Ticker komma-getrennt (leer = Portfolio)"/>
      <div class="grid md:grid-cols-2 gap-3 mb-3">
        <label class="text-sm block">
          Szenario
          <select id="stressScenario" class="border rounded p-2 w-full mt-1">${scenarioOptions}</select>
        </label>
        <label class="text-sm block">
          Schock-Intensität (×)
          <input id="stressIntensity" type="range" min="0.5" max="2" step="0.1" value="1" class="w-full mt-2"/>
          <span id="stressIntensityVal" class="text-slate-600">1.0×</span>
        </label>
      </div>
      <label class="text-sm block mb-3">
        Globaler Schock (optional, nur Marktcrash / Override) %
        <input id="stressGlobal" type="number" min="-90" max="0" step="1" placeholder="z.B. -25" class="border rounded p-2 w-full mt-1"/>
      </label>
      <p id="stressDesc" class="text-sm text-slate-600 mb-3"></p>
      <div class="flex gap-2 mb-3">
        <button type="button" id="portfolioFillStress" class="px-3 py-2 rounded bg-slate-700 text-white">Portfolio übernehmen</button>
        <button type="button" id="startStress" class="px-3 py-2 rounded bg-slate-900 text-white">Simulation starten</button>
      </div>
      <div id="spinner" class="hidden flex items-center gap-2 mb-3">
        <div class="animate-spin h-5 w-5 border-2 border-slate-500 border-t-transparent rounded-full"></div>
        <span>Simulation läuft …</span>
      </div>
      <div id="stressResults"></div>
    </div>
  `;

  const updateDesc = () => {
    const sel = document.getElementById("stressScenario");
    const s = scenarios.find((x) => x.id === sel.value);
    document.getElementById("stressDesc").textContent = s?.description || "";
  };
  document.getElementById("stressScenario").onchange = updateDesc;
  document.getElementById("stressIntensity").oninput = (e) => {
    document.getElementById("stressIntensityVal").textContent = `${asNumber(e.target.value).toFixed(1)}×`;
  };
  updateDesc();

  document.getElementById("portfolioFillStress").onclick = async () => {
    const symbols = await api("/risk/portfolio-symbols");
    const list = symbols?.symbols || [];
    document.getElementById("stressSymbols").value = list.join(",");
  };

  document.getElementById("startStress").onclick = async () => {
    document.getElementById("spinner").classList.remove("hidden");
    document.getElementById("stressResults").innerHTML = "";
    destroyChart("stressChart");
    try {
      const symbols = document
        .getElementById("stressSymbols")
        .value.split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const globalRaw = document.getElementById("stressGlobal").value;
      const global_shock = globalRaw !== "" ? asNumber(globalRaw) / 100 : null;
      const response = await api("/risk/stress-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbols,
          scenario: document.getElementById("stressScenario").value,
          shock_intensity: asNumber(document.getElementById("stressIntensity").value, 1),
          global_shock,
        }),
      });
      const r = response.result || {};
      const sim = r.simulation || {};
      const entries = Object.entries(sim).sort((a, b) => asNumber(a[1].shocked_return) - asNumber(b[1].shocked_return));

      let table = `
        <p class="mb-2"><strong>${escapeHtml(r.scenario_label || r.scenario)}</strong></p>
        <p class="text-sm mb-3">Portfolio: ${formatSignedPercent(asNumber(r.portfolio_base_return) * 100)} →
          <span class="${dayChangeClass(r.portfolio_shocked_return)}">${formatSignedPercent(asNumber(r.portfolio_shocked_return) * 100)}</span> (gestresst)</p>
        <table class="w-full text-sm mb-4">
          <thead><tr class="border-b text-left"><th>Ticker</th><th>Sektor</th><th>Schock</th><th>Basis</th><th>Gestresst</th></tr></thead>
          <tbody>
            ${entries
              .map(([sym, d]) => `
              <tr class="border-b">
                <td class="py-1">${escapeHtml(sym)}</td>
                <td class="py-1 text-slate-600">${escapeHtml(d.sector || "—")}</td>
                <td class="py-1">${formatSignedPercent(asNumber(d.applied_shock) * 100)}</td>
                <td class="py-1">${formatSignedPercent(asNumber(d.base_return) * 100)}</td>
                <td class="py-1 ${dayChangeClass(d.shocked_return)}">${formatSignedPercent(asNumber(d.shocked_return) * 100)}</td>
              </tr>`)
              .join("")}
          </tbody>
        </table>
        ${chartBlock("stressChart", 240)}
      `;
      document.getElementById("stressResults").innerHTML = table;

      const labels = entries.map(([s]) => s);
      const base = entries.map(([, d]) => asNumber(d.base_return) * 100);
      const shocked = entries.map(([, d]) => asNumber(d.shocked_return) * 100);
      const ctx = document.getElementById("stressChart");
      if (ctx) {
        chartInstances.stressChart = new Chart(ctx.getContext("2d"), {
          type: "bar",
          data: {
            labels,
            datasets: [
              { label: "Basis %", data: base, backgroundColor: "#94a3b8" },
              { label: "Gestresst %", data: shocked, backgroundColor: "#ef4444" },
            ],
          },
          options: { responsive: true },
        });
      }
    } catch (e) {
      document.getElementById("stressResults").innerHTML = `<p class="text-red-600">${escapeHtml(e.message)}</p>`;
    } finally {
      document.getElementById("spinner").classList.add("hidden");
    }
  };
}

setAuthState();
