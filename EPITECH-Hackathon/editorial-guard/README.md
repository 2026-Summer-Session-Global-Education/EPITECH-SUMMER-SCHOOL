# Editorial Guard

A pre-publication risk linter for journalism. It reads a draft, flags spans that
match known editorial and legal risk patterns, explains why in plain language,
cites the standard behind each flag, and suggests a rewrite. It never edits your
text and never delivers a verdict. You accept, rewrite, or ignore. Like a linter,
not a judge.

This is topic #7 from the hackathon, built on a shared, task-agnostic engine so
the relationship-extraction tool (topic #4) can be added later as a second plugin
without touching the core.

## Quick start (no API key needed)

The app runs offline out of the box using built-in detectors, so you can test the
whole flow immediately.

```bash
cd editorial-guard
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000, then click Analyze. A sample draft is preloaded.

On macOS or Linux you can also just run `./run.sh`.

## Setting up the model from the UI

You no longer need to edit any file. Start the server, open http://localhost:8000,
and the Settings panel opens automatically on first run because no key is set.

1. Under API keys, choose the provider (Anthropic or Google Gemini), paste the
   matching API key, give it an optional label, and click Add key. The app detects
   the provider from the key prefix as a convenience, and immediately lists the
   models that key can access.
2. Add more keys, mixing providers if you like. One key is active at a time; click
   Use to switch. The provider and model list always follow the active key. When you
   activate a key whose provider differs, the model auto-switches to one that key can
   actually use.
3. Under Model, pick a model from the dropdown (or type an id) and click Save and
   test. It makes a real call and reports success, or the exact reason it failed.

Valid Anthropic ids include `claude-haiku-4-5` (the default), `claude-sonnet-5`, and
`claude-opus-4-8`. Gemini ids (for example `gemini-2.0-flash`) come straight from the
model list once a Gemini key is active, so you never have to guess them. The mode badge
(top right) always shows live or mock, and if a live call fails the app falls back to
mock and shows the reason above the marked-up text.

Adding a provider is a small change: implement one class in `app/core/providers.py`
and register it. Anthropic and Gemini ship in the box; OpenAI or others would follow
the same shape.

A `.env` file is optional. If `ANTHROPIC_API_KEY` is set there, it is seeded once on
first run as an Anthropic key, but the UI is the source of truth after that.

### Where keys are stored

Keys are stored locally in this app's SQLite database (`editorial_guard.db`) in plain
text, the same file that holds your history and standards. They are shown masked in the
UI and are never sent anywhere except to the Anthropic API. Keep that file private and
do not commit it (it is already in `.gitignore`). For anything beyond local use, put
the keys behind a real secret store.

## Uploading newsroom standards or country law

Open the Standards panel (top right) and upload one or more files as .txt or .pdf.
You can select several at once, and add or remove them over time. Unsupported files
are skipped with a message. What happens next depends on the mode:

- Live mode: the combined text is injected into the prompt. The AI prefers your
  standards over the built-in rules where they apply and cites the specific passage
  it relied on, so the proof points at your own rulebook.
- Mock mode (no key): directive lines that quote a term, for example
  `Avoid "collateral damage"`, are turned into flags on any occurrence of that term
  in the draft, citing the rule line.

Large bodies of text are truncated to a prompt budget (30k characters combined); the
panel warns you when you are over it. This is the natural place to adapt the tool to a
jurisdiction, for example by uploading French press-law guidance.

## How it works

The pipeline is one task-blind engine plus swappable analyzers.

Shared core (`app/core`):
- `ingest.py` splits text into chunks that keep their character offsets (provenance).
- `llm.py` calls the Anthropic API when a key is present, or reports not-live.
- `runner.py` drives an analyzer over the chunks and collects findings. It does not
  know which task it is running.
- `models.py` defines the shared `Finding` type: a claim, anchored to a span, backed
  by evidence.
- `store.py` logs analyses to SQLite (standard library, no external database).

The seam (`app/analyzers/base.py`):
- Every analyzer implements `system_prompt`, `user_prompt`, `parse`, `mock`, and
  `postprocess`. Adding a capability means writing one more analyzer.

Plugins:
- `legal_risk.py` is topic #7. Its `data/rules.json` holds the taxonomy and the
  paraphrased standards that back each flag.
- `relation.py` is topic #4, included in a lighter form to prove the seam is real.
  Try it: `POST /api/analyze` with `"analyzer": "relation"`.

Frontend (`web/`): dependency-free HTML, CSS, and JavaScript. No build step.

## API

- `GET /api/providers` lists supported providers (Anthropic, Gemini).
- `GET /api/health` reports mode, provider, active key label, model, and any error.
- `GET /api/keys`, `POST /api/keys`, `POST /api/keys/{id}/activate`, `DELETE /api/keys/{id}`
  manage API keys (each carries a provider; keys are masked in responses).
- `GET /api/models` lists models the active key can access.
- `POST /api/settings` body `{ "model": "..." }` sets and tests the model.
- `POST /api/analyze` body `{ "text": "...", "analyzer": "legal", "doc_id": "draft" }`.
- `GET /api/context`, `POST /api/context` (one or more files), `DELETE /api/context/{id}`
  manage uploaded standards.
- `GET /api/history` returns recent analyses.

## Tests

```bash
pip install -r requirements.txt
pytest
```

## A note on the standards

The citations in `data/rules.json` are paraphrased editorial principles, not
verbatim text from any style guide, and they are general rather than tied to one
country's law. Replace them with your newsroom's own standards, or tune them to a
specific jurisdiction (for example French press law), to make the tool sharper.
This tool flags risks to assist a human editor. It is not legal advice.
