const symbols = ["AAPL", "GOOG", "NVDA"];
const colors = { AAPL: "#48c8a5", GOOG: "#8298ff", NVDA: "#ffbd66" };
const chart = new Chart(document.getElementById("history-chart"), {
  type: "line",
  data: { labels: [], datasets: symbols.map((symbol) => ({
    label: symbol, data: [], borderColor: colors[symbol], backgroundColor: colors[symbol],
    borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25, spanGaps: true
  })) },
  options: {
    responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
    plugins: { legend: { display: false }, tooltip: { backgroundColor: "#09111f", borderColor: "#35445c", borderWidth: 1 } },
    scales: {
      x: { grid: { color: "#26344a" }, ticks: { color: "#8191a8", maxTicksLimit: 9, maxRotation: 0, font: { size: 10 } }, border: { display: false } },
      y: { grid: { color: "#26344a" }, ticks: { color: "#8191a8", maxTicksLimit: 6, font: { size: 10 }, callback: (value) => "$" + Number(value).toFixed(0) }, border: { display: false } }
    }
  }
});

function label(row) {
  const fetched = new Date(row.fetchedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `D${row.cycle + 1} ${row.marketTime} · ${fetched}`;
}

async function refresh() {
  try {
    const [latestResponse, historyResponse] = await Promise.all([
      fetch("/api/quotes/latest", { cache: "no-store" }),
      fetch("/api/quotes/history", { cache: "no-store" })
    ]);
    if (!latestResponse.ok || !historyResponse.ok) throw new Error("API request failed");
    const latest = await latestResponse.json();
    const history = await historyResponse.json();
    for (const quote of latest) {
      const card = document.querySelector(`[data-symbol="${quote.symbol}"] strong`);
      if (card) card.textContent = "$" + Number(quote.price).toFixed(2);
    }
    const groups = new Map();
    for (const row of history) {
      const key = row.fetchedAt;
      if (!groups.has(key)) groups.set(key, new Map());
      groups.get(key).set(row.symbol, row);
    }
    const observations = [...groups.values()];
    chart.data.labels = observations.map((group) => label(group.values().next().value));
    chart.data.datasets.forEach((dataset) => {
      dataset.data = observations.map((group) => group.has(dataset.label) ? Number(group.get(dataset.label).price) : null);
    });
    chart.update("none");
    if (latest.length) {
      const current = latest[0];
      document.getElementById("session-label").textContent = `Day ${current.cycle + 1} · ${current.marketTime} ET`;
    }
    document.getElementById("updated").textContent = latest.length
      ? `Last stored ${new Date(latest[0].fetchedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
      : "Waiting for first stored quotes";
  } catch (error) {
    document.getElementById("updated").textContent = "API unavailable · showing last loaded quotes";
  } finally {
    window.setTimeout(refresh, 60_000);
  }
}

refresh();
