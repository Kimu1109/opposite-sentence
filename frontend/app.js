// 対義文ジェネレーターの画面。POST /api/invert を呼んで結果とトレースを出す。

const METHOD_LABEL = {
  csv: "辞書",
  wordnet: "WordNet",
  vector: "ベクトル",
  negate: "否定化",
  keep: "素通し",
};
const MAX_SEED = 2 ** 31 - 1;

const $ = (id) => document.getElementById(id);
const form = $("form");
const textEl = $("text");
const againBtn = $("again");

let last = null; // 直前に送った { text, mode }

function currentMode() {
  return form.querySelector('input[name="mode"]:checked').value;
}

function randomSeed() {
  return Math.floor(Math.random() * MAX_SEED);
}

function updateCount() {
  $("count").textContent = textEl.value.length;
}

async function run(text, mode, seed) {
  $("status").textContent = "";
  $("go").disabled = true;
  againBtn.disabled = true;
  try {
    const res = await fetch("/api/invert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode, seed }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ? JSON.stringify(body.detail) : `HTTP ${res.status}`);
    }
    const data = await res.json();
    last = { text, mode };
    render(data);
    updateUrl(text, mode, data.seed);
  } catch (e) {
    $("status").textContent = `エラー: ${e.message}`;
  } finally {
    $("go").disabled = false;
    againBtn.disabled = last === null;
  }
}

function tooltip(t) {
  const lines = [`元の語: ${t.surface}（${t.lemma}・${t.pos}）`, `方式: ${METHOD_LABEL[t.method]}`];
  if (t.score !== null) lines.push(`スコア: ${t.score.toFixed(3)}`);
  return lines.join("\n");
}

function render(data) {
  const result = $("result");
  result.replaceChildren();
  for (const t of data.tokens) {
    if (t.method === "keep") {
      result.append(t.replaced);
      continue;
    }
    const span = document.createElement("span");
    span.className = `w m-${t.method}`;
    span.textContent = t.replaced;
    span.title = tooltip(t);
    result.append(span);
  }

  const tbody = $("trace");
  tbody.replaceChildren();
  for (const t of data.tokens) {
    if (!t.surface.trim()) continue;
    const tr = document.createElement("tr");
    if (t.method !== "keep") tr.className = "changed";
    const cells = [
      t.surface,
      t.lemma,
      t.pos,
      t.replaced,
      METHOD_LABEL[t.method],
      t.score === null ? "–" : t.score.toFixed(3),
    ];
    cells.forEach((c, i) => {
      const td = document.createElement("td");
      td.textContent = c;
      if (i === 4 && t.method !== "keep") {
        td.innerHTML = "";
        const chip = document.createElement("span");
        chip.className = `chip m-${t.method}`;
        chip.textContent = c;
        td.append(chip);
      }
      if (i === 5) td.className = "num";
      tr.append(td);
    });
    tbody.append(tr);
  }

  $("seed").textContent = `シード ${data.seed}`;
  $("output").hidden = false;
}

function shareUrl(text, mode, seed) {
  const params = new URLSearchParams({ text, mode, seed: String(seed) });
  return `${location.pathname}?${params}`;
}

function updateUrl(text, mode, seed) {
  const url = shareUrl(text, mode, seed);
  history.replaceState(null, "", url);
  $("share").href = url;
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = textEl.value.trim();
  if (!text) {
    $("status").textContent = "文を入れてください";
    return;
  }
  run(text, currentMode(), randomSeed());
});

againBtn.addEventListener("click", () => {
  if (last) run(last.text, last.mode, randomSeed());
});

textEl.addEventListener("input", updateCount);

async function showHealth() {
  try {
    const h = await (await fetch("/api/health")).json();
    const yes = (b) => (b ? "あり" : "なし");
    $("health").textContent =
      `辞書 ${h.antonym_pairs}組 · WordNet ${yes(h.wordnet_loaded)} · ベクトル ${yes(h.vectors_loaded)}`;
  } catch {
    $("health").textContent = "サーバーの状態を取得できませんでした";
  }
}

// URLの ?text=&mode=&seed= から結果を再現する
function restoreFromUrl() {
  const p = new URLSearchParams(location.search);
  const text = p.get("text");
  if (!text) return;
  textEl.value = text;
  const mode = p.get("mode");
  const radio = form.querySelector(`input[name="mode"][value="${CSS.escape(mode || "")}"]`);
  if (radio) radio.checked = true;
  const seed = Number.parseInt(p.get("seed"), 10);
  run(text, currentMode(), Number.isInteger(seed) && seed >= 0 && seed <= MAX_SEED ? seed : randomSeed());
}

updateCount();
showHealth();
restoreFromUrl();
