STYLE_BLOCK = (
    "<style>"
    '.fg-diagram text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }'
    '.fg-diagram .th { font-size: 14px; font-weight: 600; }'
    '.fg-diagram .ts { font-size: 12px; font-weight: 400; }'
    '.fg-diagram .tlabel { font-size: 12px; font-weight: 600; }'
    '.fg-diagram .arr { stroke: #5F5E5A; stroke-width: 1.5; fill: none; }'
    '.fg-diagram .arr-dashed { stroke: #5F5E5A; stroke-width: 1.5; fill: none; stroke-dasharray: 5 4; }'
    '.fg-diagram .container { fill: none; stroke: #B4B2A9; stroke-width: 1; stroke-dasharray: 6 5; }'
    '.fg-diagram .junction { fill: #5F5E5A; }'
    "</style>"
)

ARROW_DEFS = (
    "<defs>"
    '<marker id="fg-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    '<path d="M2 1L8 5L2 9" fill="none" stroke="#5F5E5A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    "</marker>"
    "</defs>"
)

# ramp = (fill_50, stroke_600, title_800, subtitle_600)
RAMPS = {
    "gray": ("#F1EFE8", "#5F5E5A", "#2C2C2A", "#5F5E5A"),
    "blue": ("#E6F1FB", "#185FA5", "#0C447C", "#185FA5"),
    "teal": ("#E1F5EE", "#0F6E56", "#085041", "#0F6E56"),
    "purple": ("#EEEDFE", "#534AB7", "#3C3489", "#534AB7"),
    "amber": ("#FAEEDA", "#854F0B", "#633806", "#854F0B"),
    "green": ("#EAF3DE", "#3B6D11", "#27500A", "#3B6D11"),
    "red": ("#FCEBEB", "#A32D2D", "#791F1F", "#A32D2D"),
}


def _box(x, y, w, h, title, subtitle, ramp, rx=8):
    fill, stroke, title_c, sub_c = RAMPS[ramp]
    cx = x + w / 2
    if subtitle:
        title_y = y + h / 2 - 9
        sub_y = y + h / 2 + 10
        text = (
            f'<text class="th" x="{cx}" y="{title_y}" text-anchor="middle" '
            f'dominant-baseline="central" fill="{title_c}">{title}</text>'
            f'<text class="ts" x="{cx}" y="{sub_y}" text-anchor="middle" '
            f'dominant-baseline="central" fill="{sub_c}">{subtitle}</text>'
        )
    else:
        cy = y + h / 2
        text = (
            f'<text class="th" x="{cx}" y="{cy}" text-anchor="middle" '
            f'dominant-baseline="central" fill="{title_c}">{title}</text>'
        )
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="0.5"/>{text}'
    )


def _line(x1, y1, x2, y2, dashed=False):
    cls = "arr-dashed" if dashed else "arr"
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" marker-end="url(#fg-arrow)"/>'


def _lpath(points, dashed=False):
    d = "M " + " L ".join(f"{x} {y}" for x, y in points)
    cls = "arr-dashed" if dashed else "arr"
    return f'<path d="{d}" class="{cls}" marker-end="url(#fg-arrow)"/>'


def _svg(view_box, title, desc, body_parts):
    # No blank lines anywhere in this string: Streamlit's markdown renderer
    # (CommonMark HTML-block rules) ends a raw-HTML block at the first blank
    # line and reinterprets everything after it as markdown text, silently
    # truncating the diagram. Joining with a single "\n" avoids that.
    lines = [
        f'<svg width="100%" viewBox="{view_box}" role="img" class="fg-diagram" xmlns="http://www.w3.org/2000/svg">',
        f"<title>{title}</title>",
        f"<desc>{desc}</desc>",
        ARROW_DEFS,
        *body_parts,
        "</svg>",
    ]
    return "\n".join(lines)


FLOW_DIAGRAM_SVG = _svg(
    "0 0 1300 920",
    "Fraud Guard execution flow",
    "Ingest to triage, then either auto-approve, auto-decline, or a parallel investigation by "
    "three specialist agents that feed an aggregator, which routes to human review or straight "
    "to resolution.",
    [
        _box(560, 40, 180, 44, "Ingest", None, "gray"),
        _line(650, 84, 650, 150),
        _box(530, 150, 240, 56, "Triage", "Deterministic risk score", "blue"),
        _line(650, 206, 650, 250),
        '<circle cx="650" cy="250" r="3" class="junction"/>',
        _lpath([(650, 250), (155, 250), (155, 300)]),
        _lpath([(650, 250), (1145, 250), (1145, 300)]),
        _line(650, 250, 650, 280),
        _box(60, 300, 190, 56, "Auto-approve", "Score &lt; 0.30", "green"),
        _box(1050, 300, 190, 56, "Auto-decline", "Score &ge; 0.65", "red"),
        '<rect x="300" y="280" width="700" height="110" rx="10" class="container"/>',
        '<text class="tlabel" x="316" y="298" fill="#5F5E5A">Parallel investigation &middot; score 0.30&ndash;0.65</text>',
        '<circle cx="650" cy="280" r="3" class="junction"/>',
        _lpath([(650, 280), (420, 306)]),
        _line(650, 280, 650, 306),
        _lpath([(650, 280), (880, 306)]),
        _box(320, 306, 200, 56, "Transaction Analyst", "Amount &amp; merchant risk", "teal"),
        _box(550, 306, 200, 56, "Identity Verifier", "Device &amp; live geolocation", "teal"),
        _box(780, 306, 200, 56, "Pattern Detector", "History &amp; fraud-case RAG", "teal"),
        _lpath([(420, 362), (650, 460)]),
        _line(650, 362, 650, 460),
        _lpath([(880, 362), (650, 460)]),
        _box(530, 460, 240, 56, "Aggregator", "Composite score &amp; rationale", "purple"),
        _line(650, 516, 650, 590),
        _lpath([(750, 516), (870, 516), (870, 732), (810, 732)], dashed=True),
        '<text class="ts" x="878" y="508" fill="#5F5E5A">score &lt; 0.5</text>',
        _box(530, 590, 240, 56, "Human Review", "Interrupt &mdash; awaits reviewer", "amber"),
        _line(650, 646, 650, 720),
        _lpath([(155, 356), (155, 748), (490, 748)]),
        _lpath([(1145, 356), (1145, 765), (810, 765)]),
        _box(490, 720, 320, 56, "Resolution", "Final decision + audit log", "gray"),
        _line(650, 776, 650, 840),
        _box(590, 840, 120, 40, "End", None, "gray", rx=20),
    ],
)

ARCHITECTURE_DIAGRAM_SVG = _svg(
    "0 0 1300 620",
    "Fraud Guard component architecture",
    "Streamlit UI drives a LangGraph orchestration layer containing triage, three specialist "
    "agents, and an aggregator/resolution stage. The orchestration layer depends on a "
    "persistence layer (checkpointer and memory store) and an external dependencies layer "
    "(OpenAI, an MCP geolocation server, a Chroma vector store, and in-process mock APIs).",
    [
        _box(560, 40, 180, 44, "Streamlit UI", None, "gray"),
        _line(650, 84, 650, 150),
        '<rect x="60" y="150" width="1180" height="140" rx="10" class="container"/>',
        '<text class="tlabel" x="80" y="170" fill="#5F5E5A">LangGraph orchestration (the graph)</text>',
        _box(100, 200, 320, 56, "Deterministic Triage", "Rule-based scoring", "blue"),
        _box(490, 200, 320, 56, "Specialist Agents", "3 parallel ReAct agents", "teal"),
        _box(880, 200, 320, 56, "Aggregator + Resolution", "Synthesis &amp; final decision", "purple"),
        _line(650, 290, 650, 320),
        '<circle cx="650" cy="320" r="3" class="junction"/>',
        _lpath([(650, 320), (340, 360)]),
        _lpath([(650, 320), (960, 360)]),
        '<rect x="60" y="360" width="560" height="210" rx="10" class="container"/>',
        '<text class="tlabel" x="80" y="380" fill="#5F5E5A">Persistence</text>',
        _box(100, 410, 480, 56, "Checkpointer", "SqliteSaver &middot; checkpoints.sqlite", "gray"),
        _box(100, 490, 480, 56, "Memory Store", "SqliteStore &middot; account_memory.sqlite", "gray"),
        '<rect x="680" y="360" width="560" height="210" rx="10" class="container"/>',
        '<text class="tlabel" x="700" y="380" fill="#5F5E5A">External dependencies</text>',
        _box(700, 410, 250, 56, "OpenAI API", "LLM calls for reasoning", "teal"),
        _box(970, 410, 250, 56, "MCP Geolocation Server", "Live call to ip-api.com", "teal"),
        _box(700, 486, 250, 56, "Chroma Vector Store", "RAG over fraud cases", "teal"),
        _box(970, 486, 250, 56, "Mock APIs", "Synthetic account &amp; device data", "gray"),
    ],
)
