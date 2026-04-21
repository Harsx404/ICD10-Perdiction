"""PDF report generator using ReportLab.

Produces a polished clinical summary PDF from a ClinicalAnalysisResponse.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from html import escape
from typing import Any


_SOAP_SECTION_LABELS = ("Subjective:", "Objective:", "Assessment:", "Plan:")


def _safe_text(value: Any) -> str:
    return escape(str(value or ""))


def _truncate_text(value: Any, limit: int = 180) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _percent(value: Any) -> int:
    try:
        pct = round(float(value) * 100)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(pct)))


def _format_report_text(report_text: Any) -> str:
    lines: list[str] = []
    for raw_line in str(report_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        formatted = _safe_text(line)
        for label in _SOAP_SECTION_LABELS:
            prefix = label[:-1].lower()
            if line.lower().startswith(prefix):
                remainder = line[len(label):].strip() if line.lower().startswith(label.lower()) else line[len(prefix):].lstrip(": ").strip()
                formatted = f"<b>{_safe_text(label)}</b> {_safe_text(remainder)}".strip()
                break
        lines.append(formatted)

    return "<br/><br/>".join(lines)


def _format_entity_items(items: Any) -> str:
    if not items:
        return "None detected"
    if isinstance(items, list):
        return ", ".join(str(item) for item in items if str(item).strip()) or "None detected"
    return str(items)


def _confidence_hex(pct: int) -> str:
    if pct >= 80:
        return "#15803d"
    if pct >= 50:
        return "#b45309"
    return "#b91c1c"


def _severity_palette(severity: str) -> tuple[str, str]:
    normalized = str(severity or "low").lower()
    if normalized == "high":
        return "#fef2f2", "#b91c1c"
    if normalized == "moderate":
        return "#fffbeb", "#b45309"
    return "#f0fdf4", "#15803d"


def generate_pdf(response_dict: dict[str, Any], note_text: str = "") -> bytes:
    """Return PDF bytes for the given analysis response dict."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    brand_hex = "#4f46e5"
    brand_dark_hex = "#312e81"
    brand_light_hex = "#eef2ff"
    ink_hex = "#0f172a"
    muted_hex = "#64748b"
    border_hex = "#dbe3f0"
    panel_hex = "#f8fafc"
    red_hex = "#b91c1c"
    amber_hex = "#b45309"

    BRAND = colors.HexColor(brand_hex)
    BRAND_DARK = colors.HexColor(brand_dark_hex)
    BRAND_LIGHT = colors.HexColor(brand_light_hex)
    INK = colors.HexColor(ink_hex)
    MUTED = colors.HexColor(muted_hex)
    BORDER = colors.HexColor(border_hex)
    PANEL = colors.HexColor(panel_hex)
    RED = colors.HexColor(red_hex)
    AMBER = colors.HexColor(amber_hex)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Clinical Analysis Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=24,
        textColor=BRAND_DARK,
        spaceAfter=0,
    )
    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=MUTED,
    )
    meta_style = ParagraphStyle(
        "meta",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_RIGHT,
        textColor=MUTED,
    )
    mode_style = ParagraphStyle(
        "mode",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    metric_style = ParagraphStyle(
        "metric",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=INK,
    )
    section_style = ParagraphStyle(
        "section",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=BRAND_DARK,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=9.25,
        leading=14,
        textColor=INK,
    )
    compact_style = ParagraphStyle(
        "compact",
        parent=body_style,
        fontSize=8.4,
        leading=11,
        textColor=MUTED,
    )
    table_header_style = ParagraphStyle(
        "table-header",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.white,
    )
    table_body_style = ParagraphStyle(
        "table-body",
        parent=body_style,
        fontSize=8.7,
        leading=12,
    )
    code_style = ParagraphStyle(
        "code",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=10,
        leading=12,
        textColor=BRAND_DARK,
    )
    report_style = ParagraphStyle(
        "report",
        parent=body_style,
        fontSize=9.5,
        leading=15,
        textColor=INK,
    )
    centered_warning_style = ParagraphStyle(
        "warning",
        parent=styles["Normal"],
        fontSize=8.8,
        leading=12,
        alignment=TA_CENTER,
        textColor=RED,
    )

    full_width = doc.width
    story: list[Any] = []

    mode = str(response_dict.get("mode", "full") or "full").upper()
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
    mode_bg = AMBER if mode == "DEGRADED" else BRAND

    primary = response_dict.get("primary_icd_code") or None
    icd_codes = response_dict.get("icd_codes") or []
    diagnosis = response_dict.get("diagnosis") or []
    risks = response_dict.get("risks") or []
    entities = response_dict.get("entities") or {}
    notes = response_dict.get("validation_notes") or []

    header = Table(
        [
            [
                Paragraph("Clinical Analysis Report", title_style),
                Paragraph(mode, mode_style),
            ],
            [
                Paragraph(
                    "Structured ICD coding, diagnosis ranking, risk review, and SOAP report summary.",
                    subtitle_style,
                ),
                Paragraph(f"Generated<br/>{_safe_text(generated_at)}", meta_style),
            ],
        ],
        colWidths=[full_width - (42 * mm), 42 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), mode_bg),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 8))

    input_summary = f"{len(note_text.strip())} chars" if note_text.strip() else "Image-only"
    primary_label = primary.get("code", "None") if primary else "None"
    summary_cells = [
        Paragraph(
            f'<font size="7" color="{muted_hex}"><b>PRIMARY CODE</b></font><br/>'
            f'<font size="13" color="{ink_hex}"><b>{_safe_text(primary_label)}</b></font>',
            metric_style,
        ),
        Paragraph(
            f'<font size="7" color="{muted_hex}"><b>ICD CODES</b></font><br/>'
            f'<font size="13" color="{ink_hex}"><b>{len(icd_codes)}</b></font>',
            metric_style,
        ),
        Paragraph(
            f'<font size="7" color="{muted_hex}"><b>DIAGNOSES</b></font><br/>'
            f'<font size="13" color="{ink_hex}"><b>{len(diagnosis)}</b></font>',
            metric_style,
        ),
        Paragraph(
            f'<font size="7" color="{muted_hex}"><b>INPUT</b></font><br/>'
            f'<font size="13" color="{ink_hex}"><b>{_safe_text(input_summary)}</b></font>',
            metric_style,
        ),
    ]
    summary = Table([summary_cells], colWidths=[full_width / 4.0] * 4)
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.75, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary)

    def add_section_heading(title: str) -> None:
        story.append(Spacer(1, 10))
        story.append(Paragraph(title, section_style))
        story.append(HRFlowable(width="100%", thickness=0.7, color=BORDER, spaceBefore=1, spaceAfter=5))

    if primary:
        add_section_heading("Primary Diagnosis Code")
        primary_pct = _percent(primary.get("confidence", 0))
        primary_conf_hex = _confidence_hex(primary_pct)
        primary_rationale = primary.get("rationale") or "Selected as the best matching final code."
        primary_card = Table(
            [
                [
                    Paragraph(
                        f'<font size="7" color="{muted_hex}"><b>PRIMARY ICD CODE</b></font><br/>'
                        f'<font size="22" color="{brand_dark_hex}"><b>{_safe_text(primary.get("code", ""))}</b></font><br/>'
                        f'<font size="9" color="{primary_conf_hex}"><b>{primary_pct}% confidence</b></font>',
                        ParagraphStyle(
                            "primary-left",
                            parent=body_style,
                            leading=14,
                        ),
                    ),
                    Paragraph(
                        f'<font size="12" color="{ink_hex}"><b>{_safe_text(primary.get("description", ""))}</b></font><br/>'
                        f'<font size="8.7" color="{muted_hex}">{_safe_text(primary_rationale)}</font>',
                        ParagraphStyle(
                            "primary-right",
                            parent=body_style,
                            leading=14,
                        ),
                    ),
                ]
            ],
            colWidths=[42 * mm, full_width - (42 * mm)],
        )
        primary_card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), BRAND_LIGHT),
                    ("BACKGROUND", (1, 0), (1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER),
                    ("LINEAFTER", (0, 0), (0, 0), 0.75, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(primary_card)

    display_codes = [
        code for code in icd_codes if not primary or code.get("code") != primary.get("code")
    ]
    if not primary:
        display_codes = icd_codes

    if display_codes:
        add_section_heading("ICD-10 Codes" if not primary else "Additional ICD-10 Codes")
        code_rows = [
            [
                Paragraph("Code", table_header_style),
                Paragraph("Description", table_header_style),
                Paragraph("Confidence", table_header_style),
            ]
        ]
        for code in display_codes:
            code_rows.append(
                [
                    Paragraph(_safe_text(code.get("code", "")), code_style),
                    Paragraph(_safe_text(code.get("description", "")), table_body_style),
                    Paragraph(f"{_percent(code.get('confidence', 0))}%", table_body_style),
                ]
            )
        code_table = Table(code_rows, colWidths=[28 * mm, full_width - (52 * mm), 24 * mm], repeatRows=1)
        code_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(code_table)

    if diagnosis:
        add_section_heading("Differential Diagnosis")
        diagnosis_rows = [
            [
                Paragraph("Diagnosis", table_header_style),
                Paragraph("Probability", table_header_style),
                Paragraph("Rationale", table_header_style),
            ]
        ]
        for item in diagnosis:
            diagnosis_rows.append(
                [
                    Paragraph(_safe_text(item.get("label", "")), table_body_style),
                    Paragraph(f"{_percent(item.get('probability', 0))}%", table_body_style),
                    Paragraph(_safe_text(_truncate_text(item.get("rationale", ""))), compact_style),
                ]
            )
        diagnosis_table = Table(
            diagnosis_rows,
            colWidths=[46 * mm, 24 * mm, full_width - (70 * mm)],
            repeatRows=1,
        )
        diagnosis_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(diagnosis_table)

    add_section_heading("Extracted Clinical Entities")
    entity_rows = []
    for label, key in (
        ("Diseases", "diseases"),
        ("Symptoms", "symptoms"),
        ("Severity", "severity"),
        ("Complications", "complications"),
        ("Negations", "negations"),
    ):
        entity_rows.append(
            [
                Paragraph(f"<b>{label}</b>", compact_style),
                Paragraph(_safe_text(_format_entity_items(entities.get(key))), body_style),
            ]
        )
    entities_table = Table(entity_rows, colWidths=[34 * mm, full_width - (34 * mm)])
    entities_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(entities_table)

    add_section_heading("Risk Signals")
    if risks:
        for risk in risks:
            severity = str(risk.get("severity", "low")).lower()
            bg_hex, accent_hex = _severity_palette(severity)
            risk_card = Table(
                [
                    [
                        Paragraph(
                            f'<font color="{accent_hex}"><b>{_safe_text(severity.upper())} RISK</b></font> '
                            f'<font color="{ink_hex}"><b>{_safe_text(risk.get("label", ""))}</b></font><br/>'
                            f'<font color="{ink_hex}">{_safe_text(risk.get("rationale", ""))}</font>',
                            body_style,
                        )
                    ]
                ],
                colWidths=[full_width],
            )
            risk_card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_hex)),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(bg_hex)),
                        ("LINEBEFORE", (0, 0), (0, 0), 4, colors.HexColor(accent_hex)),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(risk_card)
            story.append(Spacer(1, 4))
    else:
        empty_risk = Table(
            [[Paragraph("No elevated risk signals identified.", body_style)]],
            colWidths=[full_width],
        )
        empty_risk.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#bbf7d0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(empty_risk)

    report_text = str(response_dict.get("report", "") or "").strip()
    if report_text:
        add_section_heading("Clinical Report (SOAP)")
        report_panel = Table(
            [[Paragraph(_format_report_text(report_text), report_style)]],
            colWidths=[full_width],
        )
        report_panel.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(report_panel)

    if notes:
        add_section_heading("Validation Notes")
        note_rows = [
            [Paragraph(f'<font color="{amber_hex}"><b>Note:</b></font> {_safe_text(note)}', compact_style)]
            for note in notes
        ]
        notes_table = Table(note_rows, colWidths=[full_width])
        notes_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fed7aa")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fed7aa")),
                    ("LINEBEFORE", (0, 0), (0, -1), 4, AMBER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(notes_table)

    story.append(Spacer(1, 12))
    footer = Table(
        [
            [
                Paragraph(
                    "This report is AI-generated and must be reviewed by a qualified clinician before clinical use.",
                    centered_warning_style,
                )
            ]
        ],
        colWidths=[full_width],
    )
    footer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fecaca")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(footer)

    doc.build(story)
    buf.seek(0)
    return buf.read()
