const API_BASE = `${window.location.protocol}//${window.location.hostname}:8001`;

const colors = {
  1: "#ef6a7a",
  2: "#35b8a0",
  3: "#5794f2",
  4: "#e6a348",
  5: "#a17be8",
  6: "#4f8cff",
  7: "#d47bd8",
  8: "#91a6bd",
};

const fileTab = document.getElementById("fileTab");
const textTab = document.getElementById("textTab");
const fileBox = document.getElementById("fileBox");
const textBox = document.getElementById("textBox");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const textInput = document.getElementById("textInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const fallbackBtn = document.getElementById("fallbackBtn");
const statusEl = document.getElementById("status");
const progressEl = document.querySelector(".progress");
const progressLabelEl = document.getElementById("progressLabel");
const progressPercentEl = document.getElementById("progressPercent");
const progressBarEl = document.getElementById("progressBar");
const graphEl = document.getElementById("graph");
const stageEl = document.querySelector(".stage");
const detailsEl = document.querySelector(".details");
const detailsResizeHandle = document.getElementById("detailsResizeHandle");
const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const emptyEl = document.getElementById("empty");
const relationshipsEl = document.getElementById("relationships");
const previewEl = document.getElementById("preview");
const nodeCountEl = document.getElementById("nodeCount");
const linkCountEl = document.getElementById("linkCount");
const pdfViewer = document.getElementById("pdfViewer");
const pdfViewerTitle = document.getElementById("pdfViewerTitle");
const pdfFrame = document.getElementById("pdfFrame");
const evidenceList = document.getElementById("evidenceList");
const closePdfViewer = document.getElementById("closePdfViewer");

let mode = "file";
let progressValue = 0;
let graphZoomControls = null;
let documentUrls = new Map();
let latestGraphData = null;

fileTab.addEventListener("click", () => setMode("file"));
textTab.addEventListener("click", () => setMode("text"));
fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files);
  if (!files.length) {
    fileName.textContent = "Choose PDF/TXT files";
  } else if (files.length === 1) {
    fileName.textContent = files[0].name;
  } else {
    fileName.textContent = `${files.length} files selected`;
  }
});
analyzeBtn.addEventListener("click", analyze);
fallbackBtn.addEventListener("click", () => {
  window.location.assign("/samples/index.html");
});
setupDetailsResize();

function setupDetailsResize() {
  let startY = 0;
  let startHeight = 0;

  function setDetailsHeight(height) {
    const stageHeight = stageEl.getBoundingClientRect().height;
    const maxHeight = Math.max(140, stageHeight - 220);
    const nextHeight = clamp(height, 120, maxHeight);
    stageEl.style.gridTemplateRows = `minmax(200px, 1fr) 9px ${nextHeight}px`;
    detailsResizeHandle.setAttribute("aria-valuenow", String(Math.round(nextHeight)));
  }

  detailsResizeHandle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    startY = event.clientY;
    startHeight = detailsEl.getBoundingClientRect().height;
    detailsResizeHandle.classList.add("dragging");
    detailsResizeHandle.setPointerCapture(event.pointerId);
  });

  detailsResizeHandle.addEventListener("pointermove", (event) => {
    if (!detailsResizeHandle.hasPointerCapture(event.pointerId)) return;
    setDetailsHeight(startHeight + startY - event.clientY);
  });

  function stopResize(event) {
    if (!detailsResizeHandle.hasPointerCapture(event.pointerId)) return;
    detailsResizeHandle.releasePointerCapture(event.pointerId);
    detailsResizeHandle.classList.remove("dragging");
  }

  detailsResizeHandle.addEventListener("pointerup", stopResize);
  detailsResizeHandle.addEventListener("pointercancel", stopResize);
  detailsResizeHandle.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();
    const delta = event.key === "ArrowUp" ? 24 : -24;
    setDetailsHeight(detailsEl.getBoundingClientRect().height + delta);
  });
}

function setMode(nextMode) {
  mode = nextMode;
  fileTab.classList.toggle("active", mode === "file");
  textTab.classList.toggle("active", mode === "text");
  fileBox.classList.toggle("hidden", mode !== "file");
  textBox.classList.toggle("hidden", mode !== "text");
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

async function analyze() {
  analyzeBtn.disabled = true;
  setStatus("Preparing analysis...");
  startProgress("Preparing request", 8);

  try {
    let response;
    if (mode === "file") {
      const files = Array.from(fileInput.files);
      if (!files.length) throw new Error("Choose one or more PDF/TXT files first.");
      for (const url of documentUrls.values()) URL.revokeObjectURL(url);
      documentUrls = new Map(
        files
          .filter((file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"))
          .map((file) => [file.name, URL.createObjectURL(file)]),
      );
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }
      setProgress("Uploading documents", 4);
      response = await fetch(`${API_BASE}/api/analyze-progress`, { method: "POST", body: formData });
    } else {
      const text = textInput.value.trim();
      if (!text) throw new Error("Enter text to analyze first.");
      setProgress("Sending text", 4);
      response = await fetch(`${API_BASE}/api/analyze-text-progress`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
    }

    if (!response.ok) throw new Error("Analysis request failed.");
    const data = await readProgressStream(response);
    setProgress("Rendering graph", 96);
    renderResult(data);
    setProgress("Complete", 100);
    setStatus(`Done: ${data.source || "extractor"}`);
  } catch (error) {
    setProgress("Failed", progressValue, true);
    setStatus(error.message || "Something went wrong.", true);
  } finally {
    progressEl.classList.remove("active-stream");
    analyzeBtn.disabled = false;
  }
}

function startProgress(label, value) {
  progressEl.classList.remove("active-stream", "error");
  setProgress(label, value);
}

function setProgress(label, value, isError = false) {
  progressValue = Math.max(0, Math.min(100, value));
  progressLabelEl.textContent = label;
  progressPercentEl.textContent = `${Math.round(progressValue)}%`;
  progressBarEl.style.width = `${progressValue}%`;
  progressEl.classList.toggle("error", isError);
}

async function readProgressStream(response) {
  if (!response.body) throw new Error("This browser cannot read progress updates.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      handleProgressEvent(event);
      if (event.event === "result") {
        result = event.data;
      }
    }
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer);
    handleProgressEvent(event);
    if (event.event === "result") {
      result = event.data;
    }
  }

  if (!result) throw new Error("Analysis finished without a result.");
  return result;
}

function handleProgressEvent(event) {
  if (event.event === "error") {
    throw new Error(event.message || "Analysis failed.");
  }

  if (event.event === "stream_start") {
    progressEl.classList.add("active-stream");
    setProgress(event.stage || "Ollama is generating output", 32);
    setStatus("Ollama started responding...");
    return;
  }

  if (event.event === "ollama_chunk") {
    progressEl.classList.add("active-stream");
    progressLabelEl.textContent = event.stage || `Receiving Ollama output: ${event.chunks} chunks`;
    progressPercentEl.textContent = `${event.chunks || 0} chunks`;
    setStatus("Receiving live Ollama output...");
    return;
  }

  if (event.event === "progress") {
    progressEl.classList.remove("active-stream");
    setProgress(event.stage || "Working", event.percent ?? progressValue);
  }
}

function renderResult(data) {
  latestGraphData = data;
  nodeCountEl.textContent = data.nodes.length;
  linkCountEl.textContent = data.links.length;
  previewEl.textContent = data.textPreview || "No preview available.";

  relationshipsEl.innerHTML = "";
  if (!data.links.length) {
    relationshipsEl.innerHTML = '<p class="muted">No relationships extracted.</p>';
  } else {
    for (const link of data.links) {
      const row = document.createElement("article");
      row.className = "relationship";
      row.innerHTML = `<b>${escapeHtml(link.source)}</b><span>${escapeHtml(link.label)}</span><b>${escapeHtml(link.target)}</b>`;
      relationshipsEl.appendChild(row);
    }
  }

  drawGraph(data);
}

function drawGraph(data) {
  graphEl.innerHTML = "";
  emptyEl.style.display = data.nodes.length ? "none" : "grid";

  const rect = graphEl.getBoundingClientRect();
  const width = Math.max(rect.width, 600);
  const height = Math.max(rect.height, 420);
  graphEl.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const nodes = data.nodes.map((node, index) => ({
    ...node,
    x: width / 2 + Math.cos(index) * 64,
    y: height / 2 + Math.sin(index) * 64,
    vx: 0,
    vy: 0,
  }));
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const links = data.links
    .map((link) => ({ ...link, sourceNode: nodeById.get(link.source), targetNode: nodeById.get(link.target) }))
    .filter((link) => link.sourceNode && link.targetNode);

  runStaticLayout(nodes, links, width, height);

const panState = { x: 0, y: 0, dragging: false, startX: 0, startY: 0, originX: 0, originY: 0 };
  const zoomState = { scale: 1 };
  const nodeDragState = {
    node: null,
    pointerId: null,
    offsetX: 0,
    offsetY: 0,
    startClientX: 0,
    startClientY: 0,
    moved: false,
  };
  const panSurface = svgEl("rect", {
    class: "pan-surface",
    x: "0",
    y: "0",
    width,
    height,
  });
  const viewportGroup = svgEl("g", { class: "graph-viewport" });
  const linkGroup = svgEl("g");
  const labelGroup = svgEl("g");
  const nodeGroup = svgEl("g");
  viewportGroup.append(linkGroup, labelGroup, nodeGroup);
  graphEl.append(panSurface, viewportGroup);

  const linkEls = links.map(() => {
    const line = svgEl("line", { class: "link" });
    linkGroup.appendChild(line);
    return line;
  });

  const labelEls = links.map((link) => {
    const text = svgEl("text", { class: "link-label" });
    text.textContent = link.label;
    labelGroup.appendChild(text);
    return text;
  });

  const nodeEls = nodes.map((node) => {
    const group = svgEl("g", { class: "node" });
    const hitWidth = Math.min(240, Math.max(48, node.id.length * 7));
    const hitArea = svgEl("rect", {
      class: "node-hit-area",
      x: String(-hitWidth / 2),
      y: "-16",
      width: String(hitWidth),
      height: "48",
      rx: "6",
      fill: "transparent",
    });
    const circle = svgEl("circle", {
      r: "8",
      fill: colors[node.group] || "#8c96a8",
      stroke: "#ffffff",
      "stroke-width": "1.5",
    });
    const label = svgEl("text", { y: "23", "text-anchor": "middle" });
    label.textContent = node.id;
    const title = svgEl("title");
    title.textContent = node.fileName && documentUrls.has(node.fileName)
      ? `${node.id} - click to open ${node.fileName}`
      : node.id;
    group.setAttribute("tabindex", "0");
    group.setAttribute("role", "button");
    group.setAttribute("aria-label", `Open evidence for ${node.id}`);
    group.append(title, hitArea, circle, label);
    group.addEventListener("pointerdown", (event) => startNodeDrag(event, node));
    group.addEventListener("click", () => {
      if (!nodeDragState.moved) activateNode(node);
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activateNode(node);
      }
    });
    nodeGroup.appendChild(group);
    return group;
  });

  function renderStaticGraph() {
    links.forEach((link, index) => {
      const a = link.sourceNode;
      const b = link.targetNode;
      linkEls[index].setAttribute("x1", a.x);
      linkEls[index].setAttribute("y1", a.y);
      linkEls[index].setAttribute("x2", b.x);
      linkEls[index].setAttribute("y2", b.y);
      labelEls[index].setAttribute("x", (a.x + b.x) / 2);
      labelEls[index].setAttribute("y", (a.y + b.y) / 2);
    });

    nodes.forEach((node, index) => {
      nodeEls[index].setAttribute("transform", `translate(${node.x}, ${node.y})`);
    });
  }

  function setPanTransform() {
    viewportGroup.setAttribute("transform", `translate(${panState.x}, ${panState.y}) scale(${zoomState.scale})`);
  }

  function getLocalPoint(event) {
    const point = graphEl.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const svgPoint = point.matrixTransform(graphEl.getScreenCTM().inverse());
    return {
      x: (svgPoint.x - panState.x) / zoomState.scale,
      y: (svgPoint.y - panState.y) / zoomState.scale,
    };
  }

  function zoomGraph(direction) {
    const nextScale = clamp(zoomState.scale * direction, 0.5, 2.5);
    if (nextScale === zoomState.scale) return;

    const centerX = width / 2;
    const centerY = height / 2;
    panState.x = centerX - ((centerX - panState.x) / zoomState.scale) * nextScale;
    panState.y = centerY - ((centerY - panState.y) / zoomState.scale) * nextScale;
    zoomState.scale = nextScale;
    setPanTransform();
  }

  function startNodeDrag(event, node) {
    if (event.button !== 0) return;
    event.stopPropagation();
    const point = getLocalPoint(event);
    nodeDragState.node = node;
    nodeDragState.pointerId = event.pointerId;
    nodeDragState.offsetX = point.x - node.x;
    nodeDragState.offsetY = point.y - node.y;
    nodeDragState.startClientX = event.clientX;
    nodeDragState.startClientY = event.clientY;
    nodeDragState.moved = false;
    graphEl.classList.add("dragging-node");
    graphEl.setPointerCapture(event.pointerId);
  }

  function moveNodeDrag(event) {
    if (!nodeDragState.node) return;
    if (
      Math.hypot(
        event.clientX - nodeDragState.startClientX,
        event.clientY - nodeDragState.startClientY,
      ) > 5
    ) {
      nodeDragState.moved = true;
    }
    const point = getLocalPoint(event);
    nodeDragState.node.x = point.x - nodeDragState.offsetX;
    nodeDragState.node.y = point.y - nodeDragState.offsetY;
    renderStaticGraph();
  }

  function endNodeDrag(event) {
    if (!nodeDragState.node || nodeDragState.pointerId !== event.pointerId) return;
    const selectedNode = nodeDragState.node;
    const shouldOpen = !nodeDragState.moved;
    nodeDragState.node = null;
    nodeDragState.pointerId = null;
    graphEl.classList.remove("dragging-node");
    if (graphEl.hasPointerCapture(event.pointerId)) {
      graphEl.releasePointerCapture(event.pointerId);
    }
    if (shouldOpen) activateNode(selectedNode);
  }

  let lastActivatedNode = null;
  let lastActivationTime = 0;

  function activateNode(node) {
    const now = performance.now();
    if (lastActivatedNode === node && now - lastActivationTime < 350) return;
    lastActivatedNode = node;
    lastActivationTime = now;
    openPdfReview(node);
  }

  function startPan(event) {
    if (!data.nodes.length || event.button !== 0) return;
    panState.dragging = true;
    panState.startX = event.clientX;
    panState.startY = event.clientY;
    panState.originX = panState.x;
    panState.originY = panState.y;
    graphEl.classList.add("dragging");
    graphEl.setPointerCapture(event.pointerId);
  }

  function movePan(event) {
    if (nodeDragState.node) {
      moveNodeDrag(event);
      return;
    }
    if (!panState.dragging) return;
    panState.x = panState.originX + event.clientX - panState.startX;
    panState.y = panState.originY + event.clientY - panState.startY;
    setPanTransform();
  }

  function endPan(event) {
    if (nodeDragState.node) {
      endNodeDrag(event);
      return;
    }
    if (!panState.dragging) return;
    panState.dragging = false;
    graphEl.classList.remove("dragging");
    if (graphEl.hasPointerCapture(event.pointerId)) {
      graphEl.releasePointerCapture(event.pointerId);
    }
  }

  graphEl.onpointerdown = startPan;
  graphEl.onpointermove = movePan;
  graphEl.onpointerup = endPan;
  graphEl.onpointercancel = endPan;
  graphZoomControls = {
    zoomIn: () => zoomGraph(1.2),
    zoomOut: () => zoomGraph(1 / 1.2),
  };

  renderStaticGraph();
}

zoomInBtn.addEventListener("click", () => {
  if (graphZoomControls) graphZoomControls.zoomIn();
});

zoomOutBtn.addEventListener("click", () => {
  if (graphZoomControls) graphZoomControls.zoomOut();
});

if (closePdfViewer && pdfViewer) {
  closePdfViewer.addEventListener("click", () => pdfViewer.close());
  pdfViewer.addEventListener("click", (event) => {
    if (event.target === pdfViewer) pdfViewer.close();
  });
}

function openPdfReview(node, requestedPage = null) {
  const filename = node.fileName || node.id;
  const pdfUrl = documentUrls.get(filename);
  if (!pdfUrl) return;
  if (!pdfViewer || !pdfViewerTitle || !pdfFrame || !evidenceList) {
    window.open(pdfUrl, "_blank", "noopener");
    return;
  }

  const highlights = Array.isArray(node.highlights) ? node.highlights : [];
  const firstPage = requestedPage || highlights[0]?.page || 1;
  pdfViewerTitle.textContent = filename;
  pdfFrame.src = `${pdfUrl}#page=${firstPage}&zoom=page-width`;
  evidenceList.replaceChildren();

  if (!highlights.length) {
    const message = document.createElement("p");
    message.className = "muted";
    message.textContent = "No verified text evidence was found for this node.";
    evidenceList.appendChild(message);
  } else {
    for (const highlight of highlights) {
      const pair = document.createElement("article");
      pair.className = "evidence-pair";

      const item = document.createElement("button");
      item.type = "button";
      item.className = "evidence-item";

      const meta = document.createElement("span");
      meta.className = "evidence-page";
      const page = document.createElement("span");
      page.textContent = `Page ${highlight.page}`;
      const related = document.createElement("span");
      related.textContent = filename;
      meta.append(page, related);

      const relationship = document.createElement("strong");
      relationship.textContent = highlight.relationship || "Relationship evidence";

      const snippet = document.createElement("p");
      appendHighlightedText(snippet, highlight.snippet || "", highlight.terms || []);
      item.append(meta, relationship, snippet);
      item.addEventListener("click", () => {
        pdfFrame.src = `${pdfUrl}#page=${highlight.page}&zoom=page-width`;
      });
      pair.appendChild(item);

      const relatedFilename = highlight.relatedFile;
      const relatedNode = latestGraphData?.nodes?.find(
        (candidate) => (candidate.fileName || candidate.id) === relatedFilename,
      );
      const matchingHighlight = relatedNode?.highlights?.find(
        (candidate) =>
          candidate.relatedFile === filename
          && candidate.relationship === highlight.relationship,
      );
      const relatedEvidence = highlight.relatedEvidence || matchingHighlight;

      if (relatedFilename && relatedNode && relatedEvidence) {
        const relatedButton = document.createElement("button");
        relatedButton.type = "button";
        relatedButton.className = "related-evidence";

        const relatedHeading = document.createElement("span");
        relatedHeading.className = "related-evidence-heading";
        relatedHeading.textContent = "Related file evidence — click to open";

        const relatedMeta = document.createElement("span");
        relatedMeta.className = "evidence-page";
        const relatedPage = document.createElement("span");
        relatedPage.textContent = `Page ${relatedEvidence.page || 1}`;
        const relatedName = document.createElement("span");
        relatedName.textContent = relatedFilename;
        relatedMeta.append(relatedPage, relatedName);

        const relatedSnippet = document.createElement("p");
        appendHighlightedText(
          relatedSnippet,
          relatedEvidence.snippet || "",
          relatedEvidence.terms || [],
        );
        relatedButton.append(relatedHeading, relatedMeta, relatedSnippet);
        relatedButton.addEventListener("click", () => {
          openPdfReview(relatedNode, relatedEvidence.page || 1);
        });
        pair.appendChild(relatedButton);
      }

      evidenceList.appendChild(pair);
    }
  }

  if (!pdfViewer.open) pdfViewer.showModal();
}

function appendHighlightedText(container, text, terms) {
  const candidates = [...new Set(
    terms
      .flatMap((term) => [String(term), ...String(term).split(/[\s_-]+/)])
      .map((term) => term.trim())
      .filter((term) => term.length >= 3),
  )].sort((left, right) => right.length - left.length);

  if (!candidates.length) {
    container.textContent = text;
    return;
  }

  const pattern = candidates
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|");
  const matcher = new RegExp(pattern, "gi");
  let cursor = 0;

  for (const match of text.matchAll(matcher)) {
    const index = match.index ?? 0;
    container.appendChild(document.createTextNode(text.slice(cursor, index)));
    const mark = document.createElement("mark");
    mark.textContent = match[0];
    container.appendChild(mark);
    cursor = index + match[0].length;
  }
  container.appendChild(document.createTextNode(text.slice(cursor)));
}

function runStaticLayout(nodes, links, width, height) {
  const linkDistance = nodes.length > 18 ? 92 : 76;
  const repulsion = nodes.length > 18 ? 260 : 170;
  const minX = Math.min(80, width / 2);
  const maxX = Math.max(width - 80, width / 2);
  const minY = Math.min(70, height / 2);
  const maxY = Math.max(height - 70, height / 2);

  for (let iteration = 0; iteration < 180; iteration += 1) {
    for (const node of nodes) {
      node.vx += (width / 2 - node.x) * 0.0008;
      node.vy += (height / 2 - node.y) * 0.0008;
    }

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x || 0.01;
        const dy = b.y - a.y || 0.01;
        const distSq = dx * dx + dy * dy;
        const force = Math.min(repulsion / distSq, 0.045);
        a.vx -= dx * force;
        a.vy -= dy * force;
        b.vx += dx * force;
        b.vy += dy * force;
      }
    }

    for (const link of links) {
      const a = link.sourceNode;
      const b = link.targetNode;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (distance - linkDistance) * 0.003;
      a.vx += dx * force;
      a.vy += dy * force;
      b.vx -= dx * force;
      b.vy -= dy * force;
    }

    nodes.forEach((node) => {
      node.vx *= 0.9;
      node.vy *= 0.9;
      node.x = clamp(node.x + node.vx, minX, maxX);
      node.y = clamp(node.y + node.vy, minY, maxY);
    });
  }
}

function svgEl(tag, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) {
    element.setAttribute(key, value);
  }
  return element;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
