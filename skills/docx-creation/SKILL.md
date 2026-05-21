---
name: docx-creation
description: Create Microsoft Word (.docx) deliverables for Harry Potter's Crew responding to the Hogwarts RFP. Use whenever a deliverable needs to land as an editable .docx — proposals, executive summaries, statements of work, contracts. Enforces the firm's Gryffindor-themed branding (deep red + gold), Harry Potter's Crew → Hogwarts header/footer attribution, and well-structured layouts with embedded visualisations to keep the client deck visually compelling.
---

# DOCX Creation — Harry Potter's Crew house style

Use this when a downstream consumer (Hogwarts procurement, the headmaster's office, the Board of Governors) needs an editable Word document. Every `.docx` produced from this skill must look unmistakably like it came from **Harry Potter's Crew** and was authored **for Hogwarts**.

## Non-negotiable firm guidelines

These three rules are mandatory. Do not ship a document that violates them.

1. **Attribution everywhere.** The firm name "Harry Potter's Crew" and the client "Hogwarts" must appear in the document header, footer, and cover page. Footers must read: `Harry Potter's Crew  ·  Prepared for Hogwarts  ·  Confidential  ·  Page X of Y`.
2. **Gryffindor palette.** Use deep red (`#7F0909`) and gold (`#FFC500`) as the primary accent colours, with a darker red (`#3C0000`) for headings and an off-white (`#FFF8E7`) for table-row banding. Black for body text. No other accent colours.
3. **Structured and visual.** Every deliverable must include a cover page, table of contents, clearly numbered sections, at least one summary table, and at least one chart/visualisation. A wall of prose is not acceptable for this client.

## Dependencies

```bash
pip install python-docx matplotlib
```

`matplotlib` is required for the chart visualisations described below — `python-docx` alone cannot draw charts, so we generate them as PNGs and embed them.

## Brand constants — copy this block verbatim

```python
from docx.shared import RGBColor, Pt, Inches

FIRM_NAME   = "Harry Potter's Crew"
CLIENT_NAME = "Hogwarts"

# Gryffindor palette
GRYFFINDOR_RED      = RGBColor(0x7F, 0x09, 0x09)   # primary accent
GRYFFINDOR_GOLD     = RGBColor(0xFF, 0xC5, 0x00)   # secondary accent / dividers
GRYFFINDOR_DARK_RED = RGBColor(0x3C, 0x00, 0x00)   # headings
GRYFFINDOR_CREAM    = RGBColor(0xFF, 0xF8, 0xE7)   # table-row banding
BODY_BLACK          = RGBColor(0x10, 0x10, 0x10)

# Matplotlib equivalents (hex strings) for charts
CHART_PALETTE = ["#7F0909", "#FFC500", "#3C0000", "#B8860B", "#FFF8E7"]
```

## Document scaffold — every deliverable starts here

```python
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def new_branded_doc(title: str, subtitle: str) -> Document:
    doc = Document()
    _apply_base_styles(doc)
    _add_cover_page(doc, title, subtitle)
    _add_header(doc)
    _add_footer(doc)
    return doc
```

### Base styles (Gryffindor heading colours)

```python
def _apply_base_styles(doc):
    styles = doc.styles
    body = styles["Normal"].font
    body.name = "Calibri"
    body.size = Pt(11)
    body.color.rgb = BODY_BLACK

    for level, size in [(0, 28), (1, 20), (2, 14), (3, 12)]:
        h = styles[f"Heading {level}" if level else "Title"].font
        h.name = "Cambria"
        h.size = Pt(size)
        h.color.rgb = GRYFFINDOR_DARK_RED
        h.bold = True
```

### Cover page

```python
def _add_cover_page(doc, title: str, subtitle: str):
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"{FIRM_NAME}\nfor\n{CLIENT_NAME}")
    run.font.size = Pt(22)
    run.font.color.rgb = GRYFFINDOR_RED
    run.bold = True

    doc.add_paragraph()  # spacer
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run(title)
    title_run.font.size = Pt(28)
    title_run.font.color.rgb = GRYFFINDOR_DARK_RED
    title_run.bold = True

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run(subtitle)
    sub_run.font.size = Pt(14)
    sub_run.font.color.rgb = GRYFFINDOR_GOLD
    sub_run.italic = True

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
```

### Header — firm + client on every page

```python
def _add_header(doc):
    header_p = doc.sections[0].header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header_p.add_run(f"{FIRM_NAME}  →  {CLIENT_NAME}")
    run.font.size = Pt(9)
    run.font.color.rgb = GRYFFINDOR_RED
    run.bold = True
```

### Footer — mandatory wording + auto page numbers

```python
def _add_footer(doc):
    footer_p = doc.sections[0].footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    prefix = footer_p.add_run(
        f"{FIRM_NAME}  ·  Prepared for {CLIENT_NAME}  ·  Confidential  ·  Page "
    )
    prefix.font.size = Pt(9)
    prefix.font.color.rgb = GRYFFINDOR_DARK_RED

    # PAGE field
    _add_field(footer_p, "PAGE")
    of_run = footer_p.add_run(" of ")
    of_run.font.size = Pt(9)
    of_run.font.color.rgb = GRYFFINDOR_DARK_RED
    # NUMPAGES field
    _add_field(footer_p, "NUMPAGES")


def _add_field(paragraph, field_code: str):
    """Insert a Word field (e.g. PAGE, NUMPAGES) into a paragraph."""
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.text = f" {field_code} "
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin); run._r.append(instr); run._r.append(fld_end)
    run.font.size = Pt(9)
    run.font.color.rgb = GRYFFINDOR_DARK_RED
```

## Structure — required section order

Every deliverable should follow this skeleton, in order:

1. **Cover page** — firm → client, document title, subtitle (handled by `new_branded_doc`)
2. **Table of contents** — `doc.add_paragraph("Table of Contents", style="Heading 1")` followed by a TOC field (Word will populate on open)
3. **Executive Summary** — one page max, ends with a 3-bullet "Why Harry Potter's Crew" call-out
4. **Understanding of Hogwarts' needs** — restate the RFP in our words; cite specific requirements
5. **Proposed approach** — numbered sub-sections; include the *approach diagram* (chart) here
6. **Commercials** — pricing table (banded rows, see below) + a *cost breakdown* chart
7. **Timeline / milestones** — Gantt-style horizontal bar chart
8. **Why Harry Potter's Crew** — credentials, past wins
9. **Appendix** — assumptions, risks, glossary

## Branded tables

Use cream banding on alternating rows and a deep-red header row:

```python
def add_branded_table(doc, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 2"  # closest built-in; we override colours below

    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = GRYFFINDOR_GOLD
        _shade_cell(cell, "7F0909")  # red header

    # Body rows with cream banding
    for r_idx, row in enumerate(rows):
        row_cells = table.add_row().cells
        for c_idx, value in enumerate(row):
            row_cells[c_idx].text = str(value)
            if r_idx % 2 == 0:
                _shade_cell(row_cells[c_idx], "FFF8E7")  # cream
    return table


def _shade_cell(cell, hex_fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)
```

## Visualisations — required, not optional

Generate charts with `matplotlib` using the Gryffindor palette, save as PNG, then embed:

```python
import matplotlib.pyplot as plt
from pathlib import Path

def render_chart(fig, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    return out_path

def cost_breakdown_chart(labels, values, out_path):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=CHART_PALETTE[:len(labels)],
           edgecolor="#3C0000", linewidth=1.2)
    ax.set_title("Cost breakdown", color="#3C0000", fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#7F0909")
    ax.tick_params(colors="#3C0000")
    return render_chart(fig, out_path)

def embed_image(doc, png_path: Path, caption: str, width_inches: float = 5.5):
    doc.add_picture(str(png_path), width=Inches(width_inches))
    last = doc.paragraphs[-1]
    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = cap.add_run(f"Figure — {caption}")
    cap_run.italic = True
    cap_run.font.size = Pt(9)
    cap_run.font.color.rgb = GRYFFINDOR_DARK_RED
```

**Required charts per deliverable:**

- An **approach diagram** in §5 (flow or pillars — even a simple horizontal bar of workstreams counts)
- A **cost breakdown** in §6 (use `cost_breakdown_chart` above)
- A **timeline** in §7 (`ax.barh` with milestones on the y-axis)

If real numbers are unavailable, use clearly-labelled placeholders (e.g. "Illustrative — to be confirmed with Hogwarts finance office") rather than skipping the visual.

## Putting it together

```python
from pathlib import Path

doc = new_branded_doc(
    title="Modernising the Hogwarts Records Platform",
    subtitle="A proposal from Harry Potter's Crew",
)

doc.add_heading("Executive Summary", level=1)
doc.add_paragraph(
    "Hogwarts' RFP calls for a unified records platform replacing the "
    "current parchment-and-quill archive by the start of next term. "
    "Harry Potter's Crew proposes ..."
)

doc.add_heading("Commercials", level=1)
add_branded_table(
    doc,
    headers=["Workstream", "Effort (days)", "Fee (galleons)"],
    rows=[
        ["Discovery", "10", "12,000"],
        ["Build", "60", "84,000"],
        ["Rollout", "20", "26,000"],
    ],
)
chart_path = cost_breakdown_chart(
    labels=["Discovery", "Build", "Rollout"],
    values=[12000, 84000, 26000],
    out_path=Path("deliverables/hogwarts/figures/cost-breakdown.png"),
)
embed_image(doc, chart_path, caption="Cost breakdown by workstream")

doc.save("deliverables/hogwarts/hogwarts-proposal-v1.docx")
```

## Output conventions for this repo

- Save deliverables to `deliverables/hogwarts/<doc-type>-v<n>.docx`
- Save chart PNGs to `deliverables/hogwarts/figures/<chart-name>.png` (kept alongside the doc so they can be regenerated)
- Filename pattern: `hogwarts-proposal-v1.docx`, `hogwarts-sow-v2.docx` — lowercase, kebab-case, version suffix
- After saving, re-open with `Document(path)` and assert: (a) the footer text contains both "Harry Potter's Crew" and "Hogwarts", (b) at least one inline image is present, (c) at least one table exists. Empty/branding-less docs are the most common failure mode.

## How to format your output

When asked for a .docx deliverable, return:

1. The absolute path to the saved file
2. A one-line summary: section count, table count, chart count, approx page count
3. Confirmation that branding checks passed (firm + client in footer, ≥1 chart, ≥1 table)
4. Any assumptions you baked in that the requester should verify (pricing numbers, dates, names)

Do **not** paste the document contents back into chat unless explicitly asked — the file is the deliverable.
