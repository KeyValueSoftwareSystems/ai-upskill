"""A small web page for trying requests: paste a request, see the model calls, the poster, any answer and the images.

    uv run python -m launchkit.ui                  # opens http://localhost:8000
    uv run python -m launchkit.ui --port 8001 --no-open

It runs your approach_llm/app.py, the same code `ask` and the scoreboard run. Save a change to
app.py and your next request uses it; there's no need to restart.
"""
import argparse
import importlib
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .ask import run
from .poster import ROOT
from .scoreboard import APPROACHES, REQUESTS, load_handle

_loaded: dict[str, tuple[float | None, object]] = {}  # approach -> (file's mtime, handle)


def fresh_handle(approach: str):
    """The approach's handle(), reloaded only when its file has changed (so a graph keeps its memory)."""
    module = APPROACHES[approach]
    path = ROOT / (module.replace(".", "/") + ".py")
    mtime = path.stat().st_mtime if path.exists() else None
    if approach in _loaded and _loaded[approach][0] == mtime:
        return _loaded[approach][1]
    if module in sys.modules:
        importlib.reload(sys.modules[module])
    handle = load_handle(approach)
    _loaded[approach] = (mtime, handle)
    return handle


def handle_run(body: dict) -> dict:
    approach = body.get("approach", "llm")
    try:
        handle = fresh_handle(approach)
    except SyntaxError as e:
        return {"error": f"{e.filename and Path(e.filename).name} doesn't load: {e.msg} at line {e.lineno}. "
                         "Check the code you just pasted (indentation, whole function replaced)."}
    except (Exception, SystemExit) as e:
        return {"error": f"{APPROACHES[approach]} doesn't load: {e}"}
    return run(body.get("text", ""), handle=handle, conversation_id=body.get("conversation", "ui"),
               no_image=bool(body.get("no_image")))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, data: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            start = "graph" if (ROOT / "approach_graph" / "graph.py").is_file() else "llm"
            page = PAGE.replace("__REQUESTS__", json.dumps(REQUESTS)).replace("__APPROACH__", start)
            return self._send(200, "text/html; charset=utf-8", page.encode())
        # Images: only PNGs inside out/.
        path = (ROOT / self.path.lstrip("/").split("?")[0]).resolve()
        allowed = path.is_relative_to(ROOT / "out")
        if allowed and path.suffix == ".png" and path.is_file():
            return self._send(200, "image/png", path.read_bytes())
        self._send(404, "text/plain", b"not found")

    def do_POST(self):
        if self.path != "/run":
            return self._send(404, "text/plain", b"not found")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        print(f"→ {body.get('text', '')[:80]}", flush=True)
        self._send(200, "application/json", json.dumps(handle_run(body)).encode())

    def log_message(self, *args):  # keep the terminal quiet
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="don't open the browser")
    args = parser.parse_args()
    try:
        server = HTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        sys.exit(f"Port {args.port} is busy (another program, or the UI is already running). "
                 f"Try: uv run python -m launchkit.ui --port {args.port + 1}")
    url = f"http://localhost:{args.port}"
    print(f"LaunchKit UI running at {url}  (Ctrl+C to stop)", flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LaunchKit Playground</title>
<style>
  :root {
    --bg: #f6f4ef; --panel: #ffffff; --ink: #1c2430; --muted: #6b7380; --line: #e3e0d8;
    --accent: #1F3A5F; --accent-ink: #ffffff; --soft: #EFE6D8; --ok: #2f7d4f; --bad: #b3261e;
    --bad-bg: #fbeaea; --ok-bg: #e8f4ec; --code: #f3f1ec;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #12161c; --panel: #1a2029; --ink: #e6e9ee; --muted: #9aa3b0; --line: #2b3340;
      --accent: #A8D5BA; --accent-ink: #12161c; --soft: #232b36; --ok: #7fd1a0; --bad: #f2a19b;
      --bad-bg: #3a2023; --ok-bg: #1d3327; --code: #151a21;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { padding: 18px 24px 4px; }
  header h1 { margin: 0; font-size: 20px; }
  header p { margin: 2px 0 0; color: var(--muted); }
  main { display: grid; grid-template-columns: minmax(300px, 400px) 1fr; gap: 20px; padding: 16px 24px 40px;
         align-items: start; }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; padding: 12px 16px 32px; } header { padding: 16px 16px 0; } }
  .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
  form.panel { position: sticky; top: 16px; }
  @media (max-width: 860px) { form.panel { position: static; } }
  label.title { font-weight: 600; display: block; margin-bottom: 6px; }
  textarea { width: 100%; min-height: 130px; resize: vertical; padding: 10px; border-radius: 8px;
             border: 1px solid var(--line); background: var(--bg); color: var(--ink); font: inherit; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 4px; }
  .chip { border: 1px solid var(--line); background: var(--soft); color: var(--ink); border-radius: 999px;
          padding: 3px 10px; font-size: 13px; cursor: pointer; }
  .chip:hover { border-color: var(--accent); }
  .hint { color: var(--muted); font-size: 13px; }
  .opts { display: grid; gap: 8px; margin: 14px 0; }
  .opts label { display: flex; gap: 8px; align-items: center; }
  select { font: inherit; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--line);
           background: var(--bg); color: var(--ink); }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  button.primary { background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 8px;
                   padding: 9px 18px; font: inherit; font-weight: 600; cursor: pointer; }
  button.primary:disabled { opacity: .6; cursor: progress; }
  #results { display: grid; gap: 16px; min-width: 0; }
  .empty { color: var(--muted); text-align: center; padding: 48px 16px; }
  .card h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
             margin: 18px 0 8px; }
  .card h2:first-child { margin-top: 0; }
  .request { font-size: 16px; font-weight: 600; }
  .error { background: var(--bad-bg); color: var(--bad); border-radius: 8px; padding: 10px 12px; }
  .poster-wrap { display: grid; grid-template-columns: minmax(180px, 280px) 1fr; gap: 16px; align-items: start; }
  @media (max-width: 600px) { .poster-wrap { grid-template-columns: 1fr; } }
  .poster { position: relative; border-radius: 8px; overflow: hidden; aspect-ratio: 1; background: var(--soft); }
  .poster img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .poster .copy { position: absolute; inset: auto 0 0 0; padding: 14px; color: #fff;
                  background: linear-gradient(transparent, rgba(10, 20, 35, .82)); }
  .poster .h { font-weight: 700; font-size: 20px; line-height: 1.15; }
  .poster .s { font-size: 13px; opacity: .92; margin-top: 4px; }
  .caption { font-size: 12px; color: var(--muted); margin-top: 4px; }
  table { border-collapse: collapse; width: 100%; }
  td { padding: 6px 8px 6px 0; border-top: 1px solid var(--line); vertical-align: top; }
  td.f { color: var(--muted); white-space: nowrap; font-size: 13px; }
  .count { font-size: 12px; white-space: nowrap; color: var(--muted); }
  .count.over { color: var(--bad); font-weight: 600; }
  ul.rules { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  ul.rules li { padding: 6px 10px; border-radius: 6px; }
  li.ok { background: var(--ok-bg); color: var(--ok); }
  li.bad { background: var(--bad-bg); color: var(--bad); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; align-items: end; }
  .grid a { color: inherit; text-decoration: none; }
  .grid img { width: auto; max-width: 100%; height: auto; max-height: 200px; border-radius: 6px; display: block; }
  .size { font-weight: 600; font-size: 13px; margin-top: 4px; }
  details { border: 1px solid var(--line); border-radius: 8px; margin-top: 8px; background: var(--bg); }
  summary { cursor: pointer; padding: 8px 12px; font-weight: 600; }
  .msg { padding: 0 12px 10px; }
  .role { font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin: 8px 0 2px; }
  .role.reply { color: var(--accent); }
  pre { margin: 0; white-space: pre-wrap; word-break: break-word; background: var(--code); padding: 8px 10px;
        border-radius: 6px; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .note { font-size: 13px; color: var(--muted); font-style: italic; }
  .answer { background: var(--soft); border-radius: 8px; padding: 10px 12px; white-space: pre-wrap; }
  .caption.bad { color: var(--bad); font-weight: 600; }
</style>
</head>
<body>
<header>
  <h1>LaunchKit Playground</h1>
  <p>Send Maya's requests for Harbor. You'll see the model calls, the poster, any answer and the images your code makes.</p>
</header>
<main>
  <form class="panel" id="form">
    <label class="title" for="text">Request</label>
    <textarea id="text" placeholder="Tidal launch, a misty lakeshore at dawn. Can I get a concept, a storyboard, the words and a poster?"></textarea>
    <div class="chips" id="chips"></div>
    <div class="hint">Maya's four requests. Send R1 to R4 in order; reload the page to start over.</div>
    <div class="opts">
      <label><input type="checkbox" id="noimage"> Placeholder picture (no GPU, no image model)</label>
      <label>Approach
        <select id="approach"><option value="llm">one LLM call (approach_llm)</option>
        <option value="graph">LangGraph (approach_graph)</option></select></label>
    </div>
    <div class="row">
      <button class="primary" id="go" type="submit">Send</button>
      <span class="hint">or Ctrl+Enter</span>
    </div>
  </form>
  <section id="results"><div class="panel empty">Your results appear here.</div></section>
</main>
<script>
const REQUESTS = __REQUESTS__;
const $ = id => document.getElementById(id);
// One conversation per page load: the graph remembers Maya's poster by this id. Reload to start over.
const conversation = "ui-" + Math.random().toString(36).slice(2, 7);
let shown = false;  // true once Maya has seen a picture
$("approach").value = "__APPROACH__";

// Build DOM with textContent only: model output is never treated as HTML.
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v; else if (k === "text") el.textContent = v; else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid);
  return el;
}

for (const r of REQUESTS) {
  const chip = h("button", {type: "button", class: "chip", title: r.text}, `${r.id} · ${r.needs}`);
  chip.onclick = () => { $("text").value = r.text; $("text").focus(); };
  $("chips").append(chip);
}
$("text").addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("form").requestSubmit(); });

$("form").onsubmit = async e => {
  e.preventDefault();
  const text = $("text").value.trim();
  if (!text) return $("text").focus();
  $("go").disabled = true;
  $("go").textContent = $("noimage").checked ? "Calling the model…" : "Working… (a picture takes a few seconds on our GPU, about a minute through LiteLLM)";
  try {
    const res = await fetch("/run", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text, conversation, approach: $("approach").value, no_image: $("noimage").checked})});
    render(await res.json(), text);
  } catch (err) {
    render({request: text, error: "Couldn't reach the UI server. Is `uv run python -m launchkit.ui` still running?"}, text);
  } finally {
    $("go").disabled = false; $("go").textContent = "Send";
  }
};

function render(r, typed) {
  const card = h("div", {class: "panel card"});
  card.append(h("h2", {text: "Request"}),
              h("div", {class: "request", text: r.request || typed}));
  if (r.error) card.append(h("h2", {text: "No poster"}), h("div", {class: "error", text: r.error}));
  if (r.answer) card.append(h("h2", {text: "Answer"}), h("div", {class: "answer", text: r.answer}));
  const seenBefore = shown;
  if (r.images && r.images.length) shown = true;

  if (r.spec) {
    const field = name => r.spec.find(s => s.field === name).value;
    const wrap = h("div", {class: "poster-wrap"});
    if (r.images && r.images.length) {
      wrap.append(h("div", {},
        h("div", {class: "poster"}, h("img", {src: "/" + r.images[0].path, alt: "poster picture"}),
          h("div", {class: "copy"}, h("div", {class: "h", text: field("headline")}),
                                    h("div", {class: "s", text: field("subheadline")}))),
        h("div", {class: "caption", text: r.images[0].placeholder
          ? "Placeholder picture, drawn by code: no image model was called. Untick \u201cPlaceholder picture\u201d (and set LAUNCHKIT_IMAGE_PROVIDER back to gpu in .env, if it says placeholder) for a real one."
          : `Preview: the copy is laid over the picture by code, not drawn by the image model. ${r.images[0].resized_from ? "The earlier picture, resized by code." : `Picture by ${r.images[0].source || "the image model"}.`}`})));
    }
    const table = h("table");
    for (const s of r.spec) {
      const over = s.limit && s.words > s.limit;
      table.append(h("tr", {}, h("td", {class: "f", text: s.field}), h("td", {text: s.value}),
        h("td", {class: "count" + (over ? " over" : ""), text: s.limit ? `${s.words}/${s.limit} words` : ""})));
    }
    wrap.append(table);
    card.append(h("h2", {text: "Poster"}), wrap);

    const rules = h("ul", {class: "rules"});
    if (r.problems.length) for (const p of r.problems) rules.append(h("li", {class: "bad", text: "✗ " + p}));
    else rules.append(h("li", {class: "ok", text: "✓ all of Harbor's written rules followed"}));
    card.append(h("h2", {text: "Harbor's rules (checked here, whatever your code does)"}), rules);
  }

  if (r.images && r.images.length) {
    const grid = h("div", {class: "grid"});
    for (const img of r.images) {
      grid.append(h("a", {href: "/" + img.path, target: "_blank"},
        h("img", {src: "/" + img.path, alt: img.path, loading: "lazy"}),
        h("div", {class: "size", text: `${img.size[0]}×${img.size[1]}`}),
        img.resized_from ? h("div", {class: "caption", text: "resized by code"})
          : seenBefore ? h("div", {class: "caption bad", text: "new picture: the one she already saw was not reused"})
          : h("div", {class: "caption", text: img.placeholder ? "placeholder (no image model call)" : `made by ${img.source || "the image model"}`})));
    }
    card.append(h("h2", {text: `Images (${r.images.length})`}), grid);
    const made = r.images.find(i => i.prompt);
    if (made) card.append(h("details", {}, h("summary", {text: "Prompt sent to the image model"}),
                                     h("div", {class: "msg"}, h("pre", {text: made.prompt}))));
  }

  if (r.calls) {
    card.append(h("h2", {text: r.calls.length === 1 ? "The model call" : `Model calls (${r.calls.length})`}));
    if (!r.calls.length) card.append(h("div", {class: "note", text: "No model calls were made."}));
    r.calls.forEach((c, i) => {
      const body = h("div", {class: "msg"});
      if (c.repeated) body.append(h("div", {class: "note", text: `Everything from call ${i}, including its reply, then:`}));
      const earlier = c.messages.filter(m => m.role !== "system").slice(0, -1);
      const history = earlier.length ? h("div", {class: "msg"}) : null;
      for (const m of c.messages) {
        const content = String(m.content);
        if (earlier.includes(m)) { history.append(h("div", {class: "role", text: m.role}), h("pre", {text: content})); continue; }
        if (history && m === c.messages.find(x => x.role !== "system" && !earlier.includes(x))) {
          body.append(h("details", {}, h("summary", {text: `earlier in this conversation (${earlier.length} message${earlier.length === 1 ? "" : "s"}, sent again so the model remembers)`}), history));
        }
        if (m.role === "system") {
          body.append(h("details", {}, h("summary", {text: `system message (${content.split("\n").length} lines): Harbor's rules and the answer format`}),
                                        h("div", {class: "msg"}, h("pre", {text: content}))));
        } else {
          body.append(h("div", {class: "role", text: m.role}), h("pre", {text: content}));
        }
      }
      body.append(h("div", {class: "role reply", text: "← reply"}), h("pre", {text: c.reply}));
      card.append(h("details", {open: ""}, h("summary", {text: `Model call ${i + 1}`}), body));
    });
  }

  const results = $("results");
  results.querySelector(".empty")?.remove();
  results.prepend(card);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
