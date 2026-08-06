from pathlib import Path

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from build_demo_pdfs import DOCUMENTS, ROOT


SAMPLES_DIR = ROOT / "samples"
QA_DIR = ROOT / ".agents" / "sample_pdf_qa"
QA_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Malgun", FONT_DIR / "malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBold", FONT_DIR / "malgunbd.ttf"))

INK = colors.HexColor("#142130")
BLUE = colors.HexColor("#2E74B5")
DARK_BLUE = colors.HexColor("#1F4D78")
MUTED = colors.HexColor("#5C6773")


STYLES = {
    "kicker": ParagraphStyle(
        "Kicker",
        fontName="MalgunBold",
        fontSize=9,
        leading=11,
        textColor=BLUE,
        spaceAfter=3,
    ),
    "title": ParagraphStyle(
        "Title",
        fontName="MalgunBold",
        fontSize=23,
        leading=30,
        textColor=INK,
        spaceAfter=4,
    ),
    "subtitle": ParagraphStyle(
        "Subtitle",
        fontName="Malgun",
        fontSize=11.5,
        leading=15,
        textColor=MUTED,
        spaceAfter=8,
    ),
    "meta": ParagraphStyle(
        "Meta",
        fontName="Malgun",
        fontSize=10.5,
        leading=14,
        textColor=INK,
        spaceAfter=2,
    ),
    "h1": ParagraphStyle(
        "Heading1",
        fontName="MalgunBold",
        fontSize=16,
        leading=21,
        textColor=BLUE,
        spaceBefore=12,
        spaceAfter=6,
    ),
    "body": ParagraphStyle(
        "Body",
        fontName="Malgun",
        fontSize=11,
        leading=16,
        textColor=INK,
        spaceAfter=7,
        wordWrap="CJK",
    ),
    "note": ParagraphStyle(
        "Note",
        fontName="Malgun",
        fontSize=9,
        leading=13,
        textColor=MUTED,
        spaceBefore=8,
    ),
    "header_left": ParagraphStyle(
        "HeaderLeft",
        fontName="MalgunBold",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_LEFT,
    ),
    "header_right": ParagraphStyle(
        "HeaderRight",
        fontName="Malgun",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_RIGHT,
    ),
    "footer": ParagraphStyle(
        "Footer",
        fontName="Malgun",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_CENTER,
    ),
}


def page_furniture(canvas, doc):
    canvas.saveState()
    width, height = LETTER
    canvas.setFont("MalgunBold", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.9 * inch, height - 0.45 * inch, "RELATIONSHIP GRAPH DEMO")
    canvas.setFont("Malgun", 8)
    canvas.drawRightString(
        width - 0.9 * inch,
        height - 0.45 * inch,
        "SYNTHETIC SAMPLE",
    )
    canvas.drawCentredString(
        width / 2,
        0.42 * inch,
        "Synthetic demonstration document - not affiliated with a real organization or event",
    )
    canvas.restoreState()


def build_pdf(spec):
    output = SAMPLES_DIR / f"{spec['filename']}.pdf"
    document = SimpleDocTemplate(
        str(output),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.68 * inch,
        title=spec["title"],
        author="Relationship Graph Demo",
        subject="Synthetic relationship extraction sample",
    )
    story = [
        Paragraph(spec["kicker"].upper(), STYLES["kicker"]),
        Paragraph(spec["title"], STYLES["title"]),
        Paragraph(spec["subtitle"], STYLES["subtitle"]),
        HRFlowable(width="100%", thickness=1.2, color=BLUE, spaceAfter=10),
    ]
    for label, value in spec["meta"]:
        story.append(
            Paragraph(
                f'<font name="MalgunBold" color="#1F4D78">{label}:</font> {value}',
                STYLES["meta"],
            )
        )
    for heading, paragraphs in spec["sections"]:
        block = [Paragraph(heading, STYLES["h1"])]
        block.extend(Paragraph(text, STYLES["body"]) for text in paragraphs)
        story.append(KeepTogether(block))
    story.extend(
        [
            Spacer(1, 4),
            Paragraph(
                "Demo note: The title, organization, event name, and sentence-level evidence in this file are designed for relationship graph demonstrations.",
                STYLES["note"],
            ),
        ]
    )
    document.build(story, onFirstPage=page_furniture, onLaterPages=page_furniture)
    return output


def render_for_qa(pdf_path):
    pdf = fitz.open(pdf_path)
    if len(pdf) != 1:
        raise RuntimeError(f"{pdf_path.name}: expected one page, got {len(pdf)}")
    page = pdf[0]
    image_path = QA_DIR / f"{pdf_path.stem}.png"
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(image_path)
    extracted = "".join(item[4] for item in page.get_text("blocks"))
    if len(extracted.strip()) < 250:
        raise RuntimeError(f"{pdf_path.name}: suspiciously little extractable text")
    return image_path


if __name__ == "__main__":
    for document_spec in DOCUMENTS:
        pdf_path = build_pdf(document_spec)
        png_path = render_for_qa(pdf_path)
        print(f"{pdf_path}\t{png_path}")
