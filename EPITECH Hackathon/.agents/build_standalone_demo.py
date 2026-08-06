import base64
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import main  # noqa: E402


def data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:application/pdf;base64,{encoded}"


pdf_paths = sorted((ROOT / "samples").glob("*.pdf"))
documents = []
embedded_documents = []
for path in pdf_paths:
    content = path.read_bytes()
    text = main.extract_text_from_pdf(content)
    documents.append(
        {
            "filename": path.name,
            "text": text,
            "contentHash": "",
            "textHash": main.text_fingerprint(text),
        }
    )
    embedded_documents.append([path.name, data_url(path)])

graph = main.add_explicit_document_links(
    main.fallback_document_graph(documents),
    documents,
)
graph = main.attach_document_sources(graph, documents)
result = {
    "source": "standalone:precomputed-demo",
    "textPreview": "Precomputed demonstration graph. Ollama is not required.",
    **graph,
}

index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
app = re.sub(r"</script", r"<\\/script", app, flags=re.IGNORECASE)

index_html = re.sub(
    r'<link rel="stylesheet" href="[^"]+"\s*/>',
    f"<style>{styles}</style>",
    index_html,
)
index_html = re.sub(
    r'<script src="[^"]+"></script>',
    "",
    index_html,
)

graph_json = json.dumps(result, ensure_ascii=True)
documents_json = json.dumps(embedded_documents, ensure_ascii=True)
bootstrap = f"""
<script>{app}</script>
<script>
documentUrls = new Map({documents_json});
latestGraphData = {graph_json};
renderResult(latestGraphData);
setProgress("Saved result", 100);
setStatus("Standalone result - Ollama and backend are not required.");
analyzeBtn.hidden = true;
fallbackBtn.hidden = true;
document.querySelector(".tabs").hidden = true;
document.querySelector("#fileBox").hidden = true;
document.querySelector("#textBox").hidden = true;
document.querySelector(".progress").hidden = true;
document.querySelector(".sub").textContent =
  "Portable relationship graph with embedded source documents.";
</script>
"""
standalone = index_html.replace("</body>", f"{bootstrap}</body>")
output = ROOT / "samples" / "index.html"
output.write_text(standalone, encoding="utf-8")

if len(result["links"]) != 5:
    raise RuntimeError(f"Expected 5 demo links, got {len(result['links'])}")
if len(embedded_documents) != 6:
    raise RuntimeError(f"Expected 6 embedded PDFs, got {len(embedded_documents)}")
print(output)
print(f"nodes={len(result['nodes'])} links={len(result['links'])} pdfs={len(embedded_documents)}")
