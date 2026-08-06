import json
import hashlib
import os
import re
import urllib.error
import urllib.request
from collections import OrderedDict
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Relationship Extraction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeTextRequest(BaseModel):
    text: str


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def ollama_options(num_predict: int | None = None) -> dict[str, Any]:
    options = {
        "temperature": 0.1,
        "num_ctx": env_int("OLLAMA_NUM_CTX", 4096),
        "num_predict": num_predict or env_int("OLLAMA_NUM_PREDICT", 800),
        "num_gpu": env_int("OLLAMA_NUM_GPU_LAYERS", 16),
    }
    return options


def text_fingerprint(text: str) -> str:
    visible_text = text.split("\nPDF metadata:", 1)[0].split("\nPDF links:", 1)[0]
    normalized = re.sub(r"\s+", " ", visible_text).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        parts = [
            f"\n[PDF page {index}]\n{page.extract_text() or ''}"
            for index, page in enumerate(reader.pages, start=1)
        ]
        urls: set[str] = set()
        for page in reader.pages:
            for annotation_ref in page.annotations or []:
                annotation = annotation_ref.get_object()
                action = annotation.get("/A")
                if action and action.get("/URI"):
                    urls.add(str(action["/URI"]))

        metadata = reader.metadata or {}
        metadata_text = " ".join(
            str(value) for value in metadata.values() if value
        )
        if metadata_text:
            parts.append(f"\nPDF metadata: {metadata_text}")
        if urls:
            parts.append("\nPDF links:\n" + "\n".join(sorted(urls)))
        return "\n".join(parts)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF text extraction failed: {exc}") from exc


def extract_text_from_upload(file: UploadFile, content: bytes) -> str:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    if filename.endswith(".pdf") or content_type == "application/pdf":
        return extract_text_from_pdf(content)

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("cp949")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and UTF-8/CP949 text files are supported in this MVP.",
            ) from exc


def clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    return cleaned[start : end + 1]


def parse_ollama_graph(
    response_text: str,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        return normalize_graph(json.loads(clean_json_text(response_text)))
    except (json.JSONDecodeError, ValueError):
        if not documents:
            raise

    links_marker = re.search(r'"links"\s*:\s*\[', response_text)
    if not links_marker:
        raise ValueError("Ollama returned incomplete JSON without a links array.")

    decoder = json.JSONDecoder()
    cursor = links_marker.end()
    recovered_links: list[dict[str, Any]] = []
    while cursor < len(response_text):
        while cursor < len(response_text) and response_text[cursor] in " \t\r\n,":
            cursor += 1
        if cursor >= len(response_text) or response_text[cursor] == "]":
            break
        try:
            value, end = decoder.raw_decode(response_text, cursor)
        except json.JSONDecodeError:
            break
        if isinstance(value, dict):
            recovered_links.append(value)
        cursor = end

    if not recovered_links:
        raise ValueError("Ollama JSON contained no complete recoverable links.")

    return normalize_graph(
        {
            "nodes": [
                {
                    "id": document["filename"],
                    "group": 6,
                    "fileName": document["filename"],
                }
                for document in documents
            ],
            "links": recovered_links,
        }
    )


def normalize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes: OrderedDict[str, dict[str, Any]] = OrderedDict()
    links: list[dict[str, str]] = []

    for node in graph.get("nodes", []):
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            continue
        group = node.get("group", 7)
        if isinstance(group, str):
            group = {
                "person": 1,
                "organization": 2,
                "location": 3,
                "amount": 4,
                "metric": 4,
                "date": 5,
                "event": 5,
                "concept": 7,
                "topic": 7,
                "claim": 7,
                "artifact": 8,
                "document": 8,
                "system": 8,
                "product": 8,
            }.get(group.lower(), 7)
        normalized_node = {"id": node_id, "group": int(group)}
        file_name = str(node.get("fileName", "")).strip()
        if file_name:
            normalized_node["fileName"] = file_name
        nodes[node_id] = normalized_node

    for link in graph.get("links", []):
        source = str(link.get("source", "")).strip()
        target = str(link.get("target", "")).strip()
        label = str(link.get("label", "related to")).strip() or "related to"
        if not source or not target or source == target:
            continue
        nodes.setdefault(source, {"id": source, "group": 7})
        nodes.setdefault(target, {"id": target, "group": 7})
        normalized_link: dict[str, Any] = {
            "source": source,
            "target": target,
            "label": label,
        }
        shared_entities = link.get("sharedEntities", [])
        if isinstance(shared_entities, list):
            normalized_link["sharedEntities"] = [
                str(entity).strip() for entity in shared_entities if str(entity).strip()
            ]
        relationship_type = str(link.get("relationshipType", "")).strip()
        if relationship_type:
            normalized_link["relationshipType"] = relationship_type
        try:
            normalized_link["confidence"] = float(link.get("confidence", 0))
        except (TypeError, ValueError):
            normalized_link["confidence"] = 0.0
        for evidence_key in ("sourceEvidence", "targetEvidence"):
            evidence = link.get(evidence_key)
            if isinstance(evidence, dict):
                quote = str(evidence.get("quote", "")).strip()
                if quote:
                    normalized_link[evidence_key] = {
                        "quote": quote,
                        "page": evidence.get("page"),
                    }
        rationale = str(link.get("rationale", "")).strip()
        if rationale:
            normalized_link["rationale"] = rationale
        evidence = link.get("evidence")
        if isinstance(evidence, dict):
            quote = str(evidence.get("quote", "")).strip()
            if quote:
                normalized_link["evidence"] = {
                    "quote": quote,
                    "page": evidence.get("page"),
                }
        links.append(normalized_link)

    return {"nodes": list(nodes.values()), "links": links}


def find_evidence_excerpt(text: str, terms: list[str]) -> dict[str, Any] | None:
    page_matches = list(re.finditer(r"\[PDF page (\d+)\]", text))
    sections: list[tuple[int, str]] = []
    if page_matches:
        for index, match in enumerate(page_matches):
            end = page_matches[index + 1].start() if index + 1 < len(page_matches) else len(text)
            sections.append((int(match.group(1)), text[match.end():end]))
    else:
        sections.append((1, text))

    for term in terms:
        compact_term = "".join(character for character in term.casefold() if character.isalpha())
        if len(compact_term) < 3:
            continue
        for page_number, page_text in sections:
            compact_chars = []
            source_indexes = []
            for source_index, character in enumerate(page_text):
                if character.isalpha():
                    compact_chars.append(character.casefold())
                    source_indexes.append(source_index)
            compact_text = "".join(compact_chars)
            compact_index = compact_text.find(compact_term)
            if compact_index == -1:
                continue

            source_start = source_indexes[compact_index]
            source_end_index = min(
                compact_index + len(compact_term) - 1,
                len(source_indexes) - 1,
            )
            source_end = source_indexes[source_end_index] + 1
            snippet_start = max(0, source_start - 110)
            snippet_end = min(len(page_text), source_end + 110)
            snippet = re.sub(r"\s+", " ", page_text[snippet_start:snippet_end]).strip()
            return {
                "page": page_number,
                "snippet": snippet,
                "terms": [term],
            }
    return None


def attach_document_sources(
    graph: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(documents) == 1:
        filename = documents[0]["filename"]
        document_text = documents[0]["text"]
        node_lookup = {node["id"]: node for node in graph["nodes"]}
        verified_links = []
        vague_labels = {
            "related to",
            "associated with",
            "mentioned with",
            "appears near",
        }

        for link in graph["links"]:
            evidence_quote = str(link.get("evidence", {}).get("quote", "")).strip()
            excerpt = find_evidence_excerpt(document_text, [evidence_quote])
            label = link["label"].strip().casefold()
            excerpt_key = (
                "".join(
                    character
                    for character in excerpt["snippet"].casefold()
                    if character.isalpha()
                )
                if excerpt
                else ""
            )
            source_key = "".join(
                character for character in link["source"].casefold() if character.isalpha()
            )
            target_key = "".join(
                character for character in link["target"].casefold() if character.isalpha()
            )
            if (
                float(link.get("confidence", 0)) < 0.65
                or label in vague_labels
                or not excerpt
                or source_key not in excerpt_key
                or target_key not in excerpt_key
            ):
                continue

            verified_links.append(link)
            for node_id in (link["source"], link["target"]):
                node = node_lookup.get(node_id)
                if node:
                    node.setdefault("highlights", []).append(
                        {
                            **excerpt,
                            "relationship": link["label"],
                            "relatedFile": filename,
                        }
                    )

        graph["links"] = verified_links
        for node in graph["nodes"]:
            node["fileName"] = filename
            if "highlights" not in node:
                excerpt = find_evidence_excerpt(document_text, [node["id"]])
            else:
                excerpt = None
            if excerpt:
                node["highlights"] = [
                    {
                        **excerpt,
                        "relationship": "entity occurrence",
                        "relatedFile": filename,
                    }
                ]
        return graph

    filenames = [document["filename"] for document in documents]
    filename_lookup = {name.casefold(): name for name in filenames}
    text_lookup = {
        document["filename"]: document["text"].casefold()
        for document in documents
    }
    nodes = [{"id": name, "group": 6, "fileName": name} for name in filenames]
    links: list[dict[str, Any]] = []
    weak_terms = {
        "ai", "media", "project", "event", "school", "summer", "document",
        "presentation", "program", "conference", "website", "platform",
        "assistant", "director", "manager", "staff", "team", "group",
        "\ud589\uc0ac", "\ubb38\uc11c", "\ud504\ub85c\uc81d\ud2b8", "\ubbf8\ub514\uc5b4",
        "\uc778\uacf5\uc9c0\ub2a5", "\uc138\ubbf8\ub098", "\ubc1c\ud45c",
    }

    def evidence_key(value: str) -> str:
        return "".join(character for character in value.casefold() if character.isalpha())

    allowed_relationship_types = {
        "same_entity",
        "same_organization",
        "same_event",
        "curriculum_sequence",
        "prerequisite",
        "companion_material",
        "continuation",
        "cooperation_request",
        "transaction",
    }

    for link in graph["links"]:
        source = filename_lookup.get(link["source"].casefold())
        target = filename_lookup.get(link["target"].casefold())
        if not source or not target or source == target:
            continue
        relationship_type = link.get("relationshipType", "").strip().casefold()
        confidence = float(link.get("confidence", 0))
        if relationship_type not in allowed_relationship_types or confidence < 0.78:
            continue

        verified_entities = []
        for entity in link.get("sharedEntities", []):
            normalized = entity.strip().casefold()
            compact = evidence_key(entity)
            if (
                len(normalized) >= 3
                and normalized not in weak_terms
                and not re.fullmatch(r"\d{1,4}(?:[./-]\d{1,2})*", normalized)
                and len(compact) >= 5
                and compact in evidence_key(text_lookup[source])
                and compact in evidence_key(text_lookup[target])
            ):
                verified_entities.append(entity.strip())

        source_evidence = link.get("sourceEvidence", {})
        target_evidence = link.get("targetEvidence", {})
        source_quote = str(source_evidence.get("quote", "")).strip()
        target_quote = str(target_evidence.get("quote", "")).strip()
        source_excerpt = find_evidence_excerpt(text_lookup[source], [source_quote])
        target_excerpt = find_evidence_excerpt(text_lookup[target], [target_quote])
        if verified_entities:
            source_excerpt = source_excerpt or find_evidence_excerpt(
                text_lookup[source],
                verified_entities,
            )
            target_excerpt = target_excerpt or find_evidence_excerpt(
                text_lookup[target],
                verified_entities,
            )
        semantic_relationship = relationship_type in {
            "curriculum_sequence",
            "prerequisite",
            "companion_material",
            "continuation",
        }
        identity_relationship = relationship_type in {
            "same_entity",
            "same_organization",
            "same_event",
        }
        source_words = re.findall(r"[A-Za-z\uac00-\ud7a3]{2,}", source_quote)
        target_words = re.findall(r"[A-Za-z\uac00-\ud7a3]{2,}", target_quote)
        detailed_semantic_evidence = (
            len(evidence_key(source_quote)) >= 35
            and len(evidence_key(target_quote)) >= 35
            and len(source_words) >= 6
            and len(target_words) >= 6
        )

        if (
            source_excerpt
            and target_excerpt
            and (not identity_relationship or bool(verified_entities))
            and (
                not semantic_relationship
                or detailed_semantic_evidence
                or bool(verified_entities)
            )
        ):
            links.append(
                {
                    "source": source,
                    "target": target,
                    "label": link["label"],
                    "relationshipType": relationship_type,
                    "sharedEntities": verified_entities,
                    "sourceEvidence": {
                        "quote": source_quote,
                        "page": source_excerpt["page"],
                    },
                    "targetEvidence": {
                        "quote": target_quote,
                        "page": target_excerpt["page"],
                    },
                    "rationale": link.get("rationale", ""),
                    "confidence": confidence,
                }
            )

    linked_pairs = {
        frozenset((link["source"], link["target"]))
        for link in links
    }
    equivalent_files: dict[str, set[str]] = {
        document["filename"]: {document["filename"]}
        for document in documents
    }
    for left in range(len(documents)):
        for right in range(left + 1, len(documents)):
            left_document = documents[left]
            right_document = documents[right]
            pair = frozenset((left_document["filename"], right_document["filename"]))
            same_bytes = bool(
                left_document.get("contentHash")
                and left_document["contentHash"] == right_document.get("contentHash")
            )
            same_text = bool(
                left_document.get("textHash")
                and left_document["textHash"] == right_document.get("textHash")
            )
            if same_bytes or same_text:
                left_name = left_document["filename"]
                right_name = right_document["filename"]
                merged = equivalent_files[left_name] | equivalent_files[right_name]
                for filename in merged:
                    equivalent_files[filename] = merged

            if (same_bytes or same_text) and pair not in linked_pairs:
                match_type = "file bytes" if same_bytes else "normalized document text"
                links.append(
                    {
                        "source": left_document["filename"],
                        "target": right_document["filename"],
                        "label": "identical document content",
                        "sharedEntities": [f"SHA-256 {match_type} match"],
                        "confidence": 1.0,
                    }
                )
                linked_pairs.add(pair)

    verified_links = [
        link for link in links if link["label"] != "identical document content"
    ]
    for link in verified_links:
        for source in equivalent_files[link["source"]]:
            for target in equivalent_files[link["target"]]:
                pair = frozenset((source, target))
                if source == target or pair in linked_pairs:
                    continue
                links.append(
                    {
                        **link,
                        "source": source,
                        "target": target,
                        "label": f"{link['label']} (via identical document)",
                    }
                )
                linked_pairs.add(pair)

    node_lookup = {node["id"]: node for node in nodes}
    document_lookup = {
        document["filename"]: document
        for document in documents
    }
    for link in links:
        for filename, related_filename in (
            (link["source"], link["target"]),
            (link["target"], link["source"]),
        ):
            document = document_lookup.get(filename)
            node = node_lookup.get(filename)
            if not document or not node:
                continue

            evidence_key_name = (
                "sourceEvidence"
                if filename == link["source"]
                else "targetEvidence"
            )
            evidence = link.get(evidence_key_name, {})
            evidence_terms = [str(evidence.get("quote", "")).strip()]

            excerpt = find_evidence_excerpt(document["text"], evidence_terms)
            if excerpt:
                related_document = document_lookup.get(related_filename)
                related_evidence_key = (
                    "targetEvidence"
                    if filename == link["source"]
                    else "sourceEvidence"
                )
                related_evidence = link.get(related_evidence_key, {})
                related_quote = str(related_evidence.get("quote", "")).strip()
                related_excerpt = (
                    find_evidence_excerpt(related_document["text"], [related_quote])
                    if related_document and related_quote
                    else None
                )
                node.setdefault("highlights", []).append(
                    {
                        **excerpt,
                        "relationship": link["label"],
                        "relatedFile": related_filename,
                        "relatedEvidence": (
                            {
                                **related_excerpt,
                                "fileName": related_filename,
                            }
                            if related_excerpt
                            else None
                        ),
                    }
                )

    return {"nodes": nodes, "links": links}


def fallback_extract_graph(text: str) -> dict[str, Any]:
    people = re.findall(r"\b(?:Mr\.|Ms\.|Dr\.|Senator|Minister|Mayor|CEO|Director)\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", text)
    companies = re.findall(
        r"\b[A-Z][A-Za-z0-9&.,'\- ]{2,}\s(?:Inc\.|LLC|Ltd\.|Corp\.|Corporation|Foundation|Group|Bank|Partners|Holdings)\b",
        text,
    )
    amounts = re.findall(r"(?:\$|USD\s?)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|k|M|B))?", text, flags=re.IGNORECASE)
    dates = re.findall(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b",
        text,
    )

    nodes: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for item in people[:12]:
        nodes[item] = {"id": item, "group": 1}
    for item in companies[:12]:
        nodes[item] = {"id": item, "group": 2}
    for item in amounts[:8]:
        nodes[item] = {"id": item, "group": 4}
    for item in dates[:8]:
        nodes[item] = {"id": item, "group": 5}

    ids = list(nodes.keys())
    links: list[dict[str, str]] = []
    relation_words = ["paid", "transferred", "donated", "met", "emailed", "contracted", "funded", "owned"]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        present = [entity for entity in ids if entity in sentence]
        if len(present) < 2:
            continue
        relation = next((word for word in relation_words if re.search(rf"\b{word}\b", sentence, re.I)), "mentioned with")
        for source, target in zip(present, present[1:]):
            links.append({"source": source, "target": target, "label": relation})
            if len(links) >= 30:
                return {"nodes": list(nodes.values()), "links": links}

    if not links and len(ids) >= 2:
        links = [{"source": ids[index], "target": ids[index + 1], "label": "appears near"} for index in range(min(len(ids) - 1, 12))]

    return {"nodes": list(nodes.values()), "links": links}


def fallback_document_graph(documents: list[dict[str, str]]) -> dict[str, Any]:
    nodes = [
        {"id": document["filename"], "group": 6, "fileName": document["filename"]}
        for document in documents
    ]
    return {"nodes": nodes, "links": []}


def add_explicit_document_links(
    graph: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    filenames = {document["filename"] for document in documents}
    document_lookup = {document["filename"]: document for document in documents}
    existing = {
        (link["source"], link["target"], link.get("relationshipType", ""))
        for link in graph.get("links", [])
    }
    keyword_types = (
        ("cooperation request", "cooperation_request"),
        ("prerequisite", "prerequisite"),
        ("companion material", "companion_material"),
        ("continuation", "continuation"),
    )

    for document in documents:
        source = document["filename"]
        sentences = [
            re.sub(r"\s+", " ", sentence).strip()
            for sentence in re.split(r"(?<=[.!?])\s+", document["text"])
            if sentence.strip()
        ]
        for sentence in sentences:
            lowered = sentence.casefold()
            relationship_type = next(
                (
                    value
                    for keyword, value in keyword_types
                    if keyword in lowered
                ),
                None,
            )
            if not relationship_type:
                continue
            for target in filenames:
                if target == source or target not in sentence:
                    continue
                key = (source, target, relationship_type)
                if key in existing:
                    continue

                target_text = document_lookup[target]["text"]
                shared_candidates = re.findall(
                    r"\b20\d{2}\s+[A-Z][A-Za-z ]{4,80}?"
                    r"(?:Hackathon|Conference|Summit|Workshop|Forum)\b",
                    document["text"],
                )
                shared_candidates += re.findall(
                    r"\b[A-Z][A-Za-z ]{4,80}?"
                    r"(?:Institute|Association|Organization|Center)\b",
                    document["text"],
                )
                shared_entity = next(
                    (
                        candidate.strip()
                        for candidate in shared_candidates
                        if candidate.strip() in target_text
                    ),
                    "",
                )
                if not shared_entity:
                    continue

                target_evidence = next(
                    (
                        re.sub(r"\s+", " ", target_sentence).strip()
                        for target_sentence in re.split(
                            r"(?<=[.!?])\s+",
                            target_text,
                        )
                        if shared_entity in target_sentence
                    ),
                    "",
                )
                if not target_evidence:
                    continue

                graph["links"].append(
                    {
                        "source": source,
                        "target": target,
                        "label": relationship_type.replace("_", " "),
                        "relationshipType": relationship_type,
                        "confidence": 0.99,
                        "sharedEntities": [shared_entity],
                        "sourceEvidence": {"page": 1, "quote": sentence},
                        "targetEvidence": {"page": 1, "quote": target_evidence},
                    }
                )
                existing.add(key)

    return graph


def build_ollama_prompt(text: str) -> str:
    document_limit = env_int("OLLAMA_DOCUMENT_CHAR_LIMIT", 9000)
    if len(text) > document_limit:
        head_length = int(document_limit * 0.8)
        text = (
            text[:head_length]
            + "\n[... middle omitted for faster analysis ...]\n"
            + text[-(document_limit - head_length):]
        )

    return f"""
You are a rigorous document analyst. Extract a coherent semantic knowledge graph from the document, regardless of whether it is an article, report, contract, tutorial, research paper, policy, or other document.
Return only valid JSON. Do not include markdown.

Schema:
{{
  "nodes": [
    {{"id": "specific entity or concept", "group": 1}}
  ],
  "links": [
    {{
      "source": "node id",
      "target": "node id",
      "label": "specific directed relationship",
      "confidence": 0.9,
      "evidence": {{
        "page": 2,
        "quote": "short exact quote copied from the document"
      }}
    }}
  ]
}}

Groups:
1 = person, 2 = organization, 3 = location, 4 = amount/metric,
5 = date/event, 7 = concept/topic/claim, 8 = artifact/document/system/product.

Rules:
- First identify the document's purpose and domain, then select the most meaningful nodes at a consistent level of detail.
- Use node ids that appear in the document text or are clear canonical forms of phrases that appear there.
- For articles and reports, capture actors, actions, claims, evidence, events, causes, effects, and outcomes.
- For tutorials and technical documents, capture concepts, prerequisites, components, procedures, inputs, outputs, and dependencies.
- For contracts and policies, capture parties, duties, permissions, restrictions, conditions, dates, and consequences.
- Merge aliases and repeated mentions into one canonical node. Do not create duplicate or overly broad nodes.
- Every link must express a concrete directed relationship supported by one exact quote from the document.
- The evidence quote and its immediate context must identify both the source and target nodes.
- Use precise labels such as "caused", "requires", "implements", "contradicts", "reported by", "funded", or "resulted in".
- Never use vague labels such as "related to", "associated with", "mentioned with", or "appears near".
- Mere co-occurrence in the same paragraph is not a relationship.
- Omit links below 0.65 confidence.
- Prefer 8-25 meaningful nodes and at most 45 strong links. A smaller coherent graph is better than a dense weak graph.

Document text:
{text}
"""


def build_documents_prompt(documents: list[dict[str, Any]]) -> str:
    if len(documents) == 1:
        return build_ollama_prompt(documents[0]["text"])

    sections = []
    total_limit = env_int("OLLAMA_MULTI_DOCUMENT_CHAR_LIMIT", 7000)
    per_document_limit = max(1000, min(3500, total_limit // len(documents)))
    for index, document in enumerate(documents, start=1):
        document_text = document["text"]
        if len(document_text) > per_document_limit:
            head_length = int(per_document_limit * 0.8)
            tail_length = per_document_limit - head_length
            document_text = (
                document_text[:head_length]
                + "\n[... middle omitted ...]\n"
                + document_text[-tail_length:]
            )
        sections.append(
            f"--- FILE {index}: {document['filename']} ---\n"
            f"{document_text}"
        )

    return f"""
You are a rigorous document relationship analyst comparing multiple documents.
First analyze each file independently. Then create a graph showing only relationships between the files.
Return only valid JSON. Do not include markdown.

Schema:
{{
  "nodes": [
    {{"id": "exact filename", "group": 6, "fileName": "exact filename"}}
  ],
  "links": [
    {{
      "source": "exact filename",
      "target": "exact filename",
      "label": "specific semantic relationship",
      "relationshipType": "companion_material",
      "confidence": 0.92,
      "sharedEntities": [],
      "sourceEvidence": {{
        "page": 2,
        "quote": "short exact quote copied from the source file"
      }},
      "targetEvidence": {{
        "page": 3,
        "quote": "short exact quote copied from the target file"
      }}
    }}
  ]
}}

Rules:
- Create exactly one node per file and use the exact filename as its id.
- Analyze the role, objectives, prerequisites, outputs, people, organizations, and events of every file before comparing pairs.
- Allowed relationshipType values only: same_entity, same_organization, same_event, curriculum_sequence, prerequisite, companion_material, continuation, cooperation_request, transaction.
- Use cooperation_request when one file explicitly requests participation or action for an event defined in another file.
- Use companion_material when one document teaches or demonstrates material that another document explicitly asks the learner to apply.
- Use curriculum_sequence or prerequisite only when the source content provides a concrete foundation or output needed by the target content.
- A numbered filename such as Part 1 or Part 2 is only a candidate-order hint. It is never evidence by itself.
- For every link, copy one short exact sourceEvidence quote from the source file and one short exact targetEvidence quote from the target file.
- Evidence quotes must be verbatim, contain no ellipses, and use at most 18 words.
- Never copy evidence from one file into the evidence field for the other file.
- The two evidence quotes may be different; together they must prove the semantic relationship described by the rationale.
- Set confidence below 0.78 or omit the link when the relationship is ambiguous.
- For same_entity, same_organization, and same_event, sharedEntities is required and must contain the exact distinctive person, organization, or event name genuinely present in both files.
- For other relationship types, sharedEntities is optional and should contain only distinctive proper names genuinely present in both files.
- Treat spaces, underscores, hyphens, and digits inside a URL username as formatting differences when matching a person.
- PDF metadata and URLs listed under "PDF links" are valid evidence for a person or organization.
- Generic topics or words such as AI, media, project, school, conference, a year, or a date are never enough to create a link.
- Similar subject matter alone is not a relationship.
- Compare every possible file pair before producing the final links.
- Prefer a small number of well-supported links over a dense graph of weak links.
- Important identity evidence may appear at the end of a file or inside PDF metadata and links.
- Do not create entity nodes in multi-file mode.
- Do not infer a relationship solely because the files were uploaded together.
- Include at most 8 of the strongest links.

Files:
{chr(10).join(sections)}
"""


def generate_with_ollama(prompt: str, num_predict: int | None = None) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    health_request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
    with urllib.request.urlopen(health_request, timeout=2):
        pass

    endpoint = f"{base_url}/api/generate"
    payload = json.dumps(
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
            "options": ollama_options(num_predict),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama API error {exc.code}: {detail}") from exc

    return response_data["response"]


def analyze_with_ollama(text: str) -> dict[str, Any]:
    response_text = generate_with_ollama(build_ollama_prompt(text))
    graph = json.loads(clean_json_text(response_text))
    return normalize_graph(graph)


def progress_line(event: str, **data: Any) -> str:
    return json.dumps({"event": event, **data}, ensure_ascii=False) + "\n"


def stream_analysis_events(
    text: str,
    start_percent: int = 8,
    documents: list[dict[str, str]] | None = None,
):
    if not text.strip():
        yield progress_line("error", message="The document did not contain readable text.")
        return

    yield progress_line("progress", stage="Validating input", percent=start_percent)

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))

    try:
        yield progress_line("progress", stage="Checking Ollama server", percent=start_percent + 8)
        health_request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(health_request, timeout=5):
            pass

        yield progress_line("progress", stage=f"Sending prompt to Ollama ({model_name})", percent=start_percent + 20)
        payload = json.dumps(
            {
                "model": model_name,
                "prompt": build_documents_prompt(documents) if documents else build_ollama_prompt(text),
                "stream": True,
                "format": "json",
                "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
                "options": ollama_options(
                    env_int("OLLAMA_MULTI_NUM_PREDICT", 1200)
                    if documents and len(documents) > 1
                    else None
                ),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        response_text = ""
        chunk_count = 0
        yield progress_line(
            "progress",
            stage="Ollama is analyzing document evidence",
            percent=start_percent + 24,
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            yield progress_line("stream_start", stage="Ollama response stream opened")
            for raw_line in response:
                if not raw_line.strip():
                    continue
                chunk = json.loads(raw_line.decode("utf-8"))
                piece = chunk.get("response", "")
                if piece:
                    response_text += piece
                    chunk_count += 1
                    if chunk_count == 1 or chunk_count % 20 == 0:
                        yield progress_line(
                            "ollama_chunk",
                            stage=f"Receiving Ollama output: {chunk_count} chunks",
                            chunks=chunk_count,
                        )
                if chunk.get("done"):
                    break

        yield progress_line("progress", stage="Parsing Ollama JSON", percent=82)
        graph = parse_ollama_graph(response_text, documents)
        if documents:
            graph = add_explicit_document_links(graph, documents)
            graph = attach_document_sources(graph, documents)
        result = {
            "source": f"ollama:{model_name}",
            "textPreview": text[:1200],
            **graph,
        }
    except Exception as exc:
        yield progress_line("progress", stage="Ollama failed; using fallback extractor", percent=82)
        if documents and len(documents) > 1:
            graph = attach_document_sources(
                add_explicit_document_links(
                    fallback_document_graph(documents),
                    documents,
                ),
                documents,
            )
        else:
            graph = normalize_graph(fallback_extract_graph(text))
            if documents:
                graph = attach_document_sources(graph, documents)
        result = {
            "source": f"fallback_after_ollama_error: {exc}",
            "textPreview": text[:1200],
            **graph,
        }

    yield progress_line("progress", stage="Graph data ready", percent=92)
    yield progress_line("result", data=result)


def analyze_text(text: str) -> dict[str, Any]:
    if not text.strip():
        raise HTTPException(status_code=400, detail="The document did not contain readable text.")

    try:
        graph = analyze_with_ollama(text)
        source = f"ollama:{os.getenv('OLLAMA_MODEL', 'llama3.2:3b')}"
    except Exception as exc:
        graph = fallback_extract_graph(text)
        source = f"fallback_after_ollama_error: {exc}"

    graph = normalize_graph(graph)
    return {"source": source, "textPreview": text[:1200], **graph}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one document.")

    documents: list[dict[str, Any]] = []
    for index, file in enumerate(files, start=1):
        content = await file.read()
        text = extract_text_from_upload(file, content)
        filename = file.filename or f"document-{index}"
        documents.append(
            {
                "filename": filename,
                "text": text,
                "contentHash": hashlib.sha256(content).hexdigest(),
                "textHash": text_fingerprint(text),
            }
        )

    combined_text = "\n".join(document["text"] for document in documents)
    try:
        graph = analyze_with_ollama(combined_text) if len(documents) == 1 else (
            add_explicit_document_links(
                parse_ollama_graph(
                    generate_with_ollama(
                        build_documents_prompt(documents),
                        env_int("OLLAMA_MULTI_NUM_PREDICT", 1200),
                    ),
                    documents,
                ),
                documents,
            )
        )
        source = f"ollama:{os.getenv('OLLAMA_MODEL', 'llama3.2:3b')}"
    except Exception as exc:
        graph = (
            add_explicit_document_links(
                fallback_document_graph(documents),
                documents,
            )
            if len(documents) > 1
            else normalize_graph(fallback_extract_graph(combined_text))
        )
        source = f"fallback_after_ollama_error: {exc}"
    graph = attach_document_sources(graph, documents)
    return {"source": source, "textPreview": combined_text[:1200], **graph}


@app.post("/api/analyze-text")
def analyze_raw_text(request: AnalyzeTextRequest) -> dict[str, Any]:
    return analyze_text(request.text)


@app.post("/api/analyze-progress")
async def analyze_documents_progress(files: list[UploadFile] = File(...)) -> StreamingResponse:
    initial_events: list[str] = []
    documents: list[dict[str, Any]] = []

    if not files:
        initial_events.append(progress_line("error", message="Please upload at least one document."))
    else:
        total_files = len(files)
        for index, file in enumerate(files, start=1):
            filename = file.filename or f"document-{index}"
            percent = 5 + int((index - 1) / total_files * 18)
            initial_events.append(progress_line("progress", stage=f"Reading file {index}/{total_files}: {filename}", percent=percent))
            content = await file.read()
            try:
                text = extract_text_from_upload(file, content)
            except HTTPException as exc:
                initial_events.append(progress_line("error", message=str(exc.detail)))
                break
            documents.append(
                {
                    "filename": filename,
                    "text": text,
                    "contentHash": hashlib.sha256(content).hexdigest(),
                    "textHash": text_fingerprint(text),
                }
            )

    def events():
        yield from initial_events
        if any(json.loads(event).get("event") == "error" for event in initial_events):
            return

        mode_label = "Preparing cross-file comparison" if len(documents) > 1 else "Preparing document analysis"
        yield progress_line("progress", stage=mode_label, percent=24)
        combined_text = "\n".join(document["text"] for document in documents)
        yield from stream_analysis_events(combined_text, start_percent=28, documents=documents)

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.post("/api/analyze-text-progress")
def analyze_raw_text_progress(request: AnalyzeTextRequest) -> StreamingResponse:
    return StreamingResponse(stream_analysis_events(request.text), media_type="application/x-ndjson")
