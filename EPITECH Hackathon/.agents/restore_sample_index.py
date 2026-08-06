from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(
    "C:/Users/qkdqk/.codex/attachments/"
    "ea5fdef8-a3ac-49b0-85ba-28bb64fb9e6f/pasted-text.txt"
)
TARGET = ROOT / "samples" / "index.html"

html = SOURCE.read_text(encoding="utf-8")

html = html.replace(
    "grid-template-rows: minmax(360px, 1fr) 220px;",
    "grid-template-rows: minmax(240px, 1fr) 9px 220px;",
    1,
)
html = html.replace(
    ".graph-wrap {",
    """.details-resize-handle {
  position: relative;
  z-index: 3;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  cursor: row-resize;
  touch-action: none;
}

.details-resize-handle::after {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 42px;
  height: 3px;
  border-radius: 999px;
  background: var(--border-strong);
  content: "";
  transform: translate(-50%, -50%);
}

.details-resize-handle:hover::after,
.details-resize-handle:focus-visible::after,
.details-resize-handle.dragging::after {
  background: var(--accent);
}

.graph-wrap {""",
    1,
)
html = html.replace(
    ".stage { grid-template-rows: 520px auto; }",
    ".stage { grid-template-rows: 520px 9px auto; }",
    1,
)
html = html.replace(
    ".stage { grid-template-rows: minmax(320px, 1fr) 190px; }",
    ".stage { grid-template-rows: minmax(260px, 1fr) 9px 190px; }",
    1,
)

details_marker = '        <section class="details">'
resize_handle = """        <div
          id="detailsResizeHandle"
          class="details-resize-handle"
          role="separator"
          aria-label="Resize relationship details panel"
          aria-orientation="horizontal"
          tabindex="0"
        ></div>

"""
if details_marker not in html:
    raise RuntimeError("Could not find the details panel insertion point.")
html = html.replace(details_marker, resize_handle + details_marker, 1)

resize_script = """
(() => {
  const stage = document.querySelector(".stage");
  const details = document.querySelector(".details");
  const handle = document.getElementById("detailsResizeHandle");
  let startY = 0;
  let startHeight = 0;

  function setDetailsHeight(height) {
    const stageHeight = stage.getBoundingClientRect().height;
    const maxHeight = Math.max(140, stageHeight - 220);
    const nextHeight = Math.max(120, Math.min(maxHeight, height));
    stage.style.gridTemplateRows = `minmax(200px, 1fr) 9px ${nextHeight}px`;
    handle.setAttribute("aria-valuenow", String(Math.round(nextHeight)));
  }

  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    startY = event.clientY;
    startHeight = details.getBoundingClientRect().height;
    handle.classList.add("dragging");
    handle.setPointerCapture(event.pointerId);
  });

  handle.addEventListener("pointermove", (event) => {
    if (!handle.hasPointerCapture(event.pointerId)) return;
    setDetailsHeight(startHeight + startY - event.clientY);
  });

  function stopResize(event) {
    if (!handle.hasPointerCapture(event.pointerId)) return;
    handle.releasePointerCapture(event.pointerId);
    handle.classList.remove("dragging");
  }

  handle.addEventListener("pointerup", stopResize);
  handle.addEventListener("pointercancel", stopResize);
  handle.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();
    const delta = event.key === "ArrowUp" ? 24 : -24;
    setDetailsHeight(details.getBoundingClientRect().height + delta);
  });
})();
"""

last_script = html.rfind("</script>")
if last_script == -1:
    raise RuntimeError("Could not find the final script tag.")
html = html[:last_script] + resize_script + html[last_script:]

TARGET.write_text(html, encoding="utf-8")
print(TARGET)
