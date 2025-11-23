const MAX_RESULTS = 200;
const dom = {
  form: document.getElementById('search-form'),
  pattern: document.getElementById('regex-input'),
  button: document.getElementById('search-button'),
  status: document.getElementById('status'),
  hitCount: document.getElementById('hit-count'),
  list: document.getElementById('result-list'),
  note: document.getElementById('results-note'),
};

const state = {
  words: [],
  ready: false,
};

document.addEventListener('DOMContentLoaded', init);

async function init() {
  toggleSearch(false);
  setStatus('語彙リストを読み込んでいます…');
  try {
    state.words = await loadWordList();
    state.ready = true;
    setStatus(`語彙リストの読み込み完了 (${state.words.length.toLocaleString('ja-JP')} 語)`);
    toggleSearch(true);
    dom.pattern.focus();
  } catch (error) {
    setStatus(`語彙リストの読み込みに失敗しました: ${error.message}`, true);
  }

  dom.form.addEventListener('submit', (event) => {
    event.preventDefault();
    runSearch();
  });
}

function toggleSearch(enabled) {
  dom.pattern.disabled = !enabled;
  dom.button.disabled = !enabled;
}

async function loadWordList() {
  const response = await fetch('words.txt.gz');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const buffer = await response.arrayBuffer();
  const text = await decompressGzip(new Uint8Array(buffer));
  return text
    .split(/\r?\n/)
    .map((word) => word.trim())
    .filter(Boolean);
}

async function decompressGzip(bytes) {
  if (typeof DecompressionStream === 'function') {
    const ds = new DecompressionStream('gzip');
    const stream = new Blob([bytes]).stream().pipeThrough(ds);
    return await new Response(stream).text();
  }
  if (globalThis.fflate && typeof globalThis.fflate.decompressSync === 'function') {
    const decompressed = globalThis.fflate.decompressSync(bytes);
    return new TextDecoder('utf-8').decode(decompressed);
  }
  throw new Error('ブラウザが gzip 展開に対応していません。');
}

function runSearch() {
  if (!state.ready) {
    setStatus('語彙リストをまだ読み込み中です。', true);
    return;
  }

  const pattern = dom.pattern.value.trim();
  if (!pattern) {
    setStatus('正規表現を入力してください。', true);
    renderResults([], 0);
    return;
  }

  let regex;
  try {
    regex = new RegExp(pattern);
  } catch (error) {
    setStatus(`正規表現エラー: ${error.message}`, true);
    renderResults([], 0);
    return;
  }

  const preview = [];
  let total = 0;
  for (const word of state.words) {
    if (regex.test(word)) {
      total += 1;
      if (preview.length < MAX_RESULTS) {
        preview.push(word);
      }
    }
  }

  setStatus(`/${pattern}/ の検索結果`, false);
  renderResults(preview, total);
}

function setStatus(message, isError = false) {
  dom.status.textContent = message;
  dom.status.dataset.variant = isError ? 'error' : 'info';
}

function renderResults(items, total) {
  dom.hitCount.textContent = total.toLocaleString('ja-JP');
  dom.list.innerHTML = '';
  if (items.length) {
    for (const word of items) {
      const li = document.createElement('li');
      li.textContent = word;
      dom.list.appendChild(li);
    }
  }
  dom.note.textContent = getResultsNote(items.length, total);
}

function getResultsNote(shown, total) {
  if (!total) {
    return 'ヒットはありません。';
  }
  if (total <= shown) {
    return 'すべてのヒットを表示しています。';
  }
  return `先頭 ${shown} 件のみ表示しています (全 ${total.toLocaleString('ja-JP')} 件)。`;
}
