#!/usr/bin/env python3
"""
Web interface for last-x-days research skill.
Run: python3 scripts/webapp.py
Then open http://localhost:5000
"""

import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, Response, render_template_string, request, stream_with_context

SCRIPT_DIR = Path(__file__).parent.resolve()
MAIN_SCRIPT = SCRIPT_DIR / "last30days.py"
PYTHON = sys.executable

# SSL cert fix for macOS Python 3.9
try:
    import certifi
    SSL_CERT_FILE = certifi.where()
except ImportError:
    SSL_CERT_FILE = None

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>last-x-days · Research</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #22263a;
      --border: #2e3248;
      --accent: #6c8fff;
      --accent2: #a78bfa;
      --green: #4ade80;
      --red: #f87171;
      --yellow: #fbbf24;
      --text: #e2e8f0;
      --muted: #64748b;
      --radius: 12px;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px;
    }

    header {
      text-align: center;
      margin-bottom: 40px;
    }

    header h1 {
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.5px;
    }

    header p {
      color: var(--muted);
      margin-top: 6px;
      font-size: 0.95rem;
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 28px;
      width: 100%;
      max-width: 760px;
    }

    .form-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .field label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .field.grow { flex: 1; min-width: 200px; }

    input[type="text"], input[type="number"], select {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      font-size: 0.95rem;
      padding: 10px 14px;
      outline: none;
      transition: border-color 0.15s;
    }

    input[type="text"]:focus, input[type="number"]:focus, select:focus {
      border-color: var(--accent);
    }

    input[type="number"] { width: 90px; }

    select { cursor: pointer; }

    .btn {
      align-self: flex-end;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      border: none;
      border-radius: 8px;
      color: #fff;
      cursor: pointer;
      font-size: 0.95rem;
      font-weight: 600;
      padding: 10px 28px;
      transition: opacity 0.15s, transform 0.1s;
      white-space: nowrap;
    }

    .btn:hover { opacity: 0.88; }
    .btn:active { transform: scale(0.97); }
    .btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* status bar */
    #status-bar {
      display: none;
      align-items: center;
      gap: 10px;
      margin-top: 20px;
      padding: 10px 14px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 0.85rem;
      color: var(--muted);
    }

    #status-bar.visible { display: flex; }

    .spinner {
      width: 14px; height: 14px;
      border: 2px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      flex-shrink: 0;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    /* results */
    #results-wrap {
      width: 100%;
      max-width: 760px;
      margin-top: 24px;
    }

    #results {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 32px;
      display: none;
    }

    #results.visible { display: block; }

    /* markdown styles */
    #results h2 {
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }

    #results h3 {
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--accent2);
      margin: 28px 0 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 0.8rem;
    }

    #results p {
      line-height: 1.7;
      color: var(--text);
      margin-bottom: 10px;
      font-size: 0.92rem;
    }

    /* result cards */
    .result-item {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px 18px;
      margin-bottom: 12px;
      transition: border-color 0.15s;
    }

    .result-item:hover { border-color: var(--accent); }

    .result-item .meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }

    .result-item .handle {
      font-weight: 600;
      color: var(--accent);
      font-size: 0.88rem;
    }

    .result-item .score {
      background: var(--border);
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 0.75rem;
      color: var(--muted);
    }

    .result-item .score.high { background: rgba(74,222,128,0.15); color: var(--green); }
    .result-item .score.mid  { background: rgba(251,191,36,0.15);  color: var(--yellow); }
    .result-item .score.low  { background: rgba(248,113,113,0.15); color: var(--red); }

    .result-item .date { font-size: 0.78rem; color: var(--muted); }
    .result-item .engagement { font-size: 0.78rem; color: var(--muted); }

    .result-item .body {
      font-size: 0.9rem;
      line-height: 1.6;
      color: #c8d3e0;
      margin-bottom: 8px;
    }

    .result-item a {
      font-size: 0.8rem;
      color: var(--accent);
      text-decoration: none;
      word-break: break-all;
    }

    .result-item a:hover { text-decoration: underline; }

    .result-item .insight {
      font-size: 0.82rem;
      color: var(--muted);
      font-style: italic;
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid var(--border);
    }

    /* error & empty states */
    .error-block {
      background: rgba(248,113,113,0.08);
      border: 1px solid rgba(248,113,113,0.3);
      border-radius: 8px;
      padding: 12px 16px;
      color: var(--red);
      font-size: 0.88rem;
      margin-bottom: 12px;
    }

    .section-empty {
      color: var(--muted);
      font-style: italic;
      font-size: 0.88rem;
      padding: 10px 0;
    }

    /* coverage badge */
    .coverage {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(108,143,255,0.1);
      border: 1px solid rgba(108,143,255,0.25);
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 0.8rem;
      color: var(--accent);
      margin-top: 24px;
    }

    /* sources footer */
    .sources-footer {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 0.78rem;
      color: var(--muted);
    }

    .sources-footer strong { color: var(--text); }

    /* raw markdown fallback */
    #raw-output {
      display: none;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 0.82rem;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
      color: #c8d3e0;
      margin-top: 8px;
      max-height: 600px;
      overflow-y: auto;
    }

    #raw-output.visible { display: block; }

    .toggle-raw {
      background: none;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--muted);
      cursor: pointer;
      font-size: 0.78rem;
      padding: 4px 10px;
      margin-top: 12px;
      transition: border-color 0.15s, color 0.15s;
    }
    .toggle-raw:hover { border-color: var(--accent); color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1>last-x-days</h1>
    <p>Deep research across Reddit · X · YouTube · HN · TikTok · Web</p>
  </header>

  <div class="card">
    <form id="research-form">
      <div class="form-row">
        <div class="field grow">
          <label for="query">Topic / Query</label>
          <input type="text" id="query" name="query" placeholder="e.g. Claude Code, React vs Svelte..." required autocomplete="off" />
        </div>
        <div class="field">
          <label for="days">Days back</label>
          <input type="number" id="days" name="days" value="30" min="1" max="365" />
        </div>
        <div class="field">
          <label for="depth">Depth</label>
          <select id="depth" name="depth">
            <option value="">Default</option>
            <option value="quick">Quick (~60s)</option>
            <option value="deep">Deep (~5min)</option>
          </select>
        </div>
        <button class="btn" type="submit" id="submit-btn">Research</button>
      </div>
    </form>

    <div id="status-bar">
      <div class="spinner"></div>
      <span id="status-text">Starting research…</span>
    </div>
  </div>

  <div id="results-wrap">
    <div id="results"></div>
    <button class="toggle-raw" id="toggle-raw" style="display:none">Show raw output</button>
    <pre id="raw-output"></pre>
  </div>

  <script>
    const form = document.getElementById('research-form');
    const submitBtn = document.getElementById('submit-btn');
    const statusBar = document.getElementById('status-bar');
    const statusText = document.getElementById('status-text');
    const resultsDiv = document.getElementById('results');
    const rawOutput = document.getElementById('raw-output');
    const toggleRaw = document.getElementById('toggle-raw');

    // Status line patterns
    const STATUS_RE = /[⏳✓✗]\s+.+/;

    let rawLines = [];
    let currentReader = null;

    toggleRaw.addEventListener('click', () => {
      const showing = rawOutput.classList.toggle('visible');
      toggleRaw.textContent = showing ? 'Hide raw output' : 'Show raw output';
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (currentReader) { try { currentReader.cancel(); } catch(_) {} }

      const query = document.getElementById('query').value.trim();
      const days  = document.getElementById('days').value;
      const depth = document.getElementById('depth').value;
      if (!query) return;

      // Reset UI
      rawLines = [];
      rawOutput.textContent = '';
      rawOutput.classList.remove('visible');
      toggleRaw.style.display = 'none';
      resultsDiv.innerHTML = '';
      resultsDiv.classList.remove('visible');
      statusBar.classList.add('visible');
      statusText.textContent = 'Starting research…';
      submitBtn.disabled = true;

      const params = new URLSearchParams({ query, days });
      if (depth) params.set('depth', depth);

      try {
        const resp = await fetch('/research?' + params.toString());
        if (!resp.ok) throw new Error('Server error ' + resp.status);

        const reader = resp.body.getReader();
        currentReader = reader;
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // consume complete lines
          let nl;
          while ((nl = buffer.indexOf('\\n')) !== -1) {
            const line = buffer.slice(0, nl);
            buffer = buffer.slice(nl + 1);
            handleLine(line);
          }
        }
        // flush
        if (buffer) handleLine(buffer);

        finalize();
      } catch (err) {
        statusText.textContent = 'Error: ' + err.message;
        submitBtn.disabled = false;
      }
    });

    function handleLine(line) {
      rawLines.push(line);
      rawOutput.textContent = rawLines.join('\\n');

      // Strip ANSI codes for status display
      const clean = line.replace(/\\x1b\\[[0-9;]*m/g, '').replace(/[⏳✓✗]/g, '').trim();

      // Detect progress lines
      if (/[⏳✓✗]/.test(line) || /^\[/.test(clean)) {
        const stripped = line.replace(/\\x1b\\[[0-9;]*m/g, '').trim();
        if (stripped) statusText.textContent = stripped;
      }
    }

    function finalize() {
      submitBtn.disabled = false;
      statusBar.classList.remove('visible');
      toggleRaw.style.display = 'inline-block';

      const raw = rawLines.join('\\n');
      // Find the markdown section (starts at ## Research Results)
      const mdStart = raw.indexOf('## Research Results');
      if (mdStart === -1) {
        // Show raw if no structured output
        rawOutput.classList.add('visible');
        toggleRaw.style.display = 'none';
        return;
      }

      const md = raw.slice(mdStart);
      renderMarkdown(md);
    }

    function renderMarkdown(md) {
      resultsDiv.classList.add('visible');

      // Parse sections manually for richer rendering
      const lines = md.split('\\n');
      let html = '';
      let currentSection = '';
      let inItem = false;
      let itemLines = [];

      function flushItem() {
        if (itemLines.length === 0) return;
        html += renderItem(itemLines.join('\\n'));
        itemLines = [];
        inItem = false;
      }

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // H2 — main title
        if (line.startsWith('## ')) {
          flushItem();
          html += `<h2>${escHtml(line.slice(3))}</h2>`;
          continue;
        }

        // H3 — section headers
        if (line.startsWith('### ')) {
          flushItem();
          currentSection = line.slice(4).toLowerCase();
          html += `<h3>${escHtml(line.slice(4))}</h3>`;
          continue;
        }

        // Bold meta lines (date range, mode)
        if (line.startsWith('**Date Range:**') || line.startsWith('**Mode:**')) {
          flushItem();
          html += `<p>${marked.parseInline(line)}</p>`;
          continue;
        }

        // Coverage badge
        if (line.startsWith('**🔍 Research Coverage')) {
          flushItem();
          const pct = line.match(/(\\d+%)/)?.[1] || '';
          html += `<div class="coverage">📊 ${escHtml(line.replace(/\*\*/g, ''))}</div>`;
          continue;
        }

        // Sources footer
        if (line.startsWith('**Sources:**')) {
          flushItem();
          html += `<div class="sources-footer"><strong>Sources</strong><br>`;
          let j = i + 1;
          while (j < lines.length && (lines[j].startsWith('  ✅') || lines[j].startsWith('  ❌') || lines[j].startsWith('  ⚡'))) {
            html += escHtml(lines[j]) + '<br>';
            j++;
          }
          html += '</div>';
          i = j - 1;
          continue;
        }

        // Warning / info blocks
        if (line.startsWith('**⚠️') || line.startsWith('**🌐')) {
          flushItem();
          html += `<div class="error-block">${marked.parseInline(line)}</div>`;
          continue;
        }

        // Empty state lines
        if (line.startsWith('*No relevant')) {
          flushItem();
          html += `<p class="section-empty">${escHtml(line.replace(/\\*/g,''))}</p>`;
          continue;
        }

        // ERROR lines
        if (line.startsWith('**ERROR:**')) {
          flushItem();
          html += `<div class="error-block">${escHtml(line.replace(/\*\*/g,''))}</div>`;
          continue;
        }

        // Item starter: bold ID like **X3** or **R1** or **HN5**
        if (/^\*\*[A-Z]+\d+\*\*/.test(line)) {
          flushItem();
          inItem = true;
          itemLines = [line];
          continue;
        }

        if (inItem) {
          // Blank line = end of item
          if (line.trim() === '') {
            flushItem();
          } else {
            itemLines.push(line);
          }
          continue;
        }

        // Generic paragraph
        if (line.trim()) {
          html += `<p>${marked.parseInline(line)}</p>`;
        }
      }

      flushItem();
      resultsDiv.innerHTML = html;
    }

    function renderItem(text) {
      const lines = text.split('\\n').filter(l => l.trim());
      if (!lines.length) return '';

      // Parse header line: **ID** (score:N) @handle (date) [metrics]
      const header = lines[0];
      const idMatch    = header.match(/^\*\*([A-Z]+\d+)\*\*/);
      const scoreMatch = header.match(/score:(\d+)/);
      const handleMatch = header.match(/@([\w.]+)/);
      const dateMatch  = header.match(/\((\d{4}-\d{2}-\d{2}[^)]*)\)/);
      const metricsMatch = header.match(/\[([^\]]+)\]/);

      const id      = idMatch?.[1] ?? '';
      const score   = parseInt(scoreMatch?.[1] ?? '0');
      const handle  = handleMatch?.[1] ?? '';
      const date    = dateMatch?.[1] ?? '';
      const metrics = metricsMatch?.[1] ?? '';

      // Remaining lines
      let body = '', url = '', insight = '';
      for (let i = 1; i < lines.length; i++) {
        const l = lines[i].trim();
        if (l.startsWith('http')) url = l;
        else if (l.startsWith('*') && l.endsWith('*')) insight = l.replace(/\\*/g,'');
        else if (l.startsWith('💬') || l.startsWith('Insights:')) insight += ' ' + l;
        else if (l && !l.startsWith('**')) body = body ? body + ' ' + l : l;
      }

      const scoreClass = score >= 85 ? 'high' : score >= 70 ? 'mid' : 'low';
      const prefix = id.replace(/\d+$/,'');
      const sourceIcon = {
        'X': '𝕏', 'R': '📖', 'YT': '▶', 'HN': '🔶',
        'TK': '🎵', 'IG': '📸', 'BS': '🦋', 'PM': '📈', 'WEB': '🌐'
      }[prefix] || '•';

      return `
        <div class="result-item">
          <div class="meta">
            <span class="handle">${sourceIcon} ${handle ? '@' + escHtml(handle) : escHtml(id)}</span>
            ${score ? `<span class="score ${scoreClass}">score ${score}</span>` : ''}
            ${date ? `<span class="date">${escHtml(date)}</span>` : ''}
            ${metrics ? `<span class="engagement">${escHtml(metrics)}</span>` : ''}
          </div>
          ${body ? `<div class="body">${escHtml(body.slice(0,300))}${body.length>300?'…':''}</div>` : ''}
          ${url ? `<a href="${escHtml(url)}" target="_blank" rel="noopener">${escHtml(url)}</a>` : ''}
          ${insight ? `<div class="insight">${escHtml(insight.slice(0,200))}</div>` : ''}
        </div>`;
    }

    function escHtml(s) {
      return String(s)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/research")
def research():
    query = request.args.get("query", "").strip()
    days = request.args.get("days", "30").strip()
    depth = request.args.get("depth", "").strip()

    if not query:
        return Response("Missing query", status=400)

    try:
        days_int = max(1, min(365, int(days)))
    except ValueError:
        days_int = 30

    cmd = [PYTHON, str(MAIN_SCRIPT), query, "--emit=compact", f"--days={days_int}"]
    if depth == "quick":
        cmd.append("--quick")
    elif depth == "deep":
        cmd.append("--deep")

    env = os.environ.copy()
    if SSL_CERT_FILE:
        env["SSL_CERT_FILE"] = SSL_CERT_FILE

    def generate():
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
            bufsize=1,
        )
        try:
            for line in proc.stdout:
                # Skip noisy lines
                if any(skip in line for skip in ["[safari]", "Permission denied", "binarycookies"]):
                    continue
                yield line
        finally:
            proc.wait()

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  last-x-days web UI → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
