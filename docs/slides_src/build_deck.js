// Builds the Fraud Guard talk deck. Shapes named "a<N>_..." appear on click N
// (animations are injected afterwards by add_animations.py).
//
//   npm install && node build_deck.js base.pptx && python add_animations.py base.pptx ../Fraud_Guard_talk.pptx
const pptxgen = require("pptxgenjs");

const OUT = process.argv[2] || "base.pptx";
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Fraud Guard: How It Works";
pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };

// Designed on a 1920x1080 px canvas: 144 px per inch, 1 px = 0.5 pt.
const X = (px) => px / 144;
const PT = (px) => px / 2;

const COL = {
  bgLight: "F6F5F1", bgAlt: "ECEEF2", dark: "15202E", muted: "4A5568",
  blue: "2459C2", blueTint: "E3EBFA", orange: "C2560F", orangeTint: "FBE9DC",
  green: "2F7A4A", greenTint: "E3F1E6", red: "B23A3A", redTint: "F6D6D6",
  box: "FDFDFB", boxLine: "CBD2DC", card: "1F2C3D", cardLine: "2E3E54", pill: "2A3B52",
  pillText: "E6E9EF", lightBlue: "8FB4FF", lightOrange: "F2B27A", sub: "BFC8D6", cream: "F6F5F1",
  comment: "8A96A8",
};
const SANS = "Calibri";
const MONO = "Courier New";

function text(slide, runs, px, extra = {}) {
  slide.addText(runs, {
    x: X(px.x), y: X(px.y), w: X(px.w), h: X(px.h), isTextBox: true, margin: 0,
    fontFace: SANS, valign: "top", ...extra,
  });
}

function heading(slide, step, rest, subtitle) {
  text(slide, [
    { text: step, options: { color: COL.blue, bold: true } },
    { text: " · " + rest, options: { color: COL.dark, bold: true } },
  ], { x: 128, y: 120, w: 1664, h: 80 }, { fontSize: PT(56), objectName: "title" });
  text(slide, subtitle, { x: 128, y: 205, w: 1664, h: 50 }, { fontSize: PT(32), color: COL.muted, objectName: "subtitle" });
}

// Rounded box: optional step number, a title line, and detail text (string or colored runs).
function box(slide, name, px, o) {
  const runs = [];
  if (o.num) runs.push({ text: o.num + "  ", options: { color: o.numColor || COL.blue, bold: true, fontSize: PT(32) } });
  runs.push({
    text: o.title,
    options: {
      bold: true, fontSize: PT(o.titleSize || (o.titleMono ? 26 : 32)), color: o.titleColor || COL.dark,
      fontFace: o.titleMono ? MONO : SANS, breakLine: !!o.detail,
    },
  });
  for (const part of [].concat(o.detail || [])) {
    const d = typeof part === "string" ? { text: part } : part;
    runs.push({ text: d.text, options: { fontSize: PT(o.detailSize || 24), color: d.color || COL.muted, bold: !!d.bold,
      fontFace: d.mono ? MONO : SANS, breakLine: !!d.br } });
  }
  slide.addText(runs, {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.11,
    x: X(px.x), y: X(px.y), w: X(px.w), h: X(px.h),
    fill: { color: o.fill || COL.box }, line: { color: o.line || COL.boxLine, width: 1.5 },
    margin: o.margin ?? 10, valign: o.valign || "middle", align: o.align || "left", fontFace: SANS, paraSpaceAfter: 2,
    objectName: name,
  });
}

function arrow(slide, name, x1, y1, x2, y2, color, head = true) {
  slide.addShape(pres.shapes.LINE, {
    x: X(Math.min(x1, x2)), y: X(Math.min(y1, y2)), w: X(Math.abs(x2 - x1)), h: X(Math.abs(y2 - y1)),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width: 2.25, endArrowType: head ? "triangle" : undefined },
    objectName: name,
  });
}

// Across to the midpoint, vertical, then across to the target.
function elbow(slide, name, x1, y1, x2, y2, color) {
  const xm = Math.round((x1 + x2) / 2);
  arrow(slide, name + "_1", x1, y1, xm, y1, color, false);
  arrow(slide, name + "_2", xm, y1, xm, y2, color, false);
  arrow(slide, name + "_3", xm, y2, x2, y2, color, true);
}

function label(slide, name, t, px, color = COL.muted, size = 22) {
  text(slide, t, px, { fontSize: PT(size), color, objectName: name });
}

function codePanel(slide, name, px, header, lines, size = 22) {
  const NB = (str) => str.replace(/ /g, " ");
  const tone = { kw: COL.lightBlue, cm: COL.comment, st: COL.lightOrange };
  const runs = [{ text: header, options: { bold: true, color: COL.lightBlue, fontFace: MONO, fontSize: PT(26), breakLine: true } },
    { text: " ", options: { fontSize: PT(12), breakLine: true } }];
  lines.forEach((line, i) => line.forEach((seg, j) => {
    const [t, kind] = Array.isArray(seg) ? seg : [seg];
    runs.push({ text: NB(t), options: { color: tone[kind] || COL.pillText, fontFace: MONO, fontSize: PT(size),
      breakLine: j === line.length - 1 && i < lines.length - 1 } });
  }));
  slide.addText(runs, {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.11, x: X(px.x), y: X(px.y), w: X(px.w), h: X(px.h),
    fill: { color: COL.dark }, line: { color: COL.dark, width: 0.5 }, valign: "top", margin: 16, lineSpacingMultiple: 1.1,
    objectName: name,
  });
}

// ------------------------------------------------------------- 1 cover
{
  const s = pres.addSlide();
  s.background = { color: COL.dark };
  text(s, "LANGGRAPH · MULTI-AGENT · HUMAN IN THE LOOP", { x: 128, y: 128, w: 1664, h: 40 },
    { fontSize: PT(24), color: COL.lightBlue, charSpacing: 2, objectName: "eyebrow" });
  text(s, "Fraud Guard", { x: 128, y: 180, w: 1664, h: 120 }, { fontSize: PT(96), bold: true, color: COL.cream, objectName: "title" });
  text(s, "Pay for AI only where it matters: rules for the obvious, agents for the ambiguous, a person for the risky.",
    { x: 128, y: 320, w: 1400, h: 120 }, { fontSize: PT(40), color: COL.sub, objectName: "subtitle" });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(128), y: X(600), w: X(1664), h: X(220), rectRadius: 0.11,
    fill: { color: COL.card }, line: { color: COL.cardLine, width: 1 }, objectName: "card" });
  const stages = [
    ["a1_triage", "Triage", "rules, no LLM", COL.lightBlue],
    ["a2_investigate", "Investigate", "3 AI agents in parallel", COL.lightBlue],
    ["a3_review", "Human review", "pauses, survives restarts", COL.lightOrange],
    ["a4_remember", "Remember", "the account, next time", COL.lightOrange],
  ];
  const W = 340, GAP = 68;
  stages.forEach(([name, title, detail, accent], i) => {
    const x = 176 + i * (W + GAP);
    s.addText([
      { text: title, options: { bold: true, color: COL.cream, fontSize: PT(34), breakLine: true } },
      { text: detail, options: { color: accent, fontSize: PT(24) } },
    ], { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.15, x: X(x), y: X(650), w: X(W), h: X(120),
      fill: { color: COL.pill }, line: { color: COL.pill, width: 0.5 }, align: "center", valign: "middle",
      fontFace: SANS, margin: 6, objectName: name });
    if (i > 0) arrow(s, `a${i + 1}_arrow`, x - GAP + 12, 710, x - 12, 710, accent);
  });

  s.addNotes("Fraud Guard is a fraud-detection pipeline built with LangGraph. Click through the four stages: cheap rules triage every " +
    "transaction; only the ambiguous ones are investigated by three AI agents in parallel; when risk stays high a person decides, " +
    "and the pipeline can wait for them even across restarts; and the decision is remembered for the account's next transaction. " +
    "The whole point: spend LLM money only where rules can't decide, and keep a human accountable for the risky calls.");
}

// ------------------------------------------------------------- 2 problem
{
  const s = pres.addSlide();
  s.background = { color: COL.bgLight };
  heading(s, "The problem", "rules are rigid, LLMs everywhere are expensive",
    "Fraud Guard’s answer is tiered escalation: each transaction gets only as much effort as it needs.");

  const cards = [
    ["a1_rules", "Rules only", ["instant and free", { text: "", br: true }, { text: "but rigid: misses new fraud, blocks honest customers", color: COL.red }], COL.box, COL.boxLine],
    ["a2_llm", "An LLM on every transaction", ["understands context", { text: "", br: true }, { text: "but 3–4 LLM calls × millions of mostly obvious transactions", color: COL.red }], COL.box, COL.boxLine],
    ["a3_tiered", "Tiered (Fraud Guard)", [{ text: "rules settle the obvious, AI agents investigate the ambiguous, a person decides the risky", color: COL.dark }], COL.blueTint, COL.blue],
  ];
  cards.forEach(([name, title, detail, fill, line], i) => box(s, name, { x: 128 + i * 566, y: 290, w: 532, h: 280 },
    { title, detail, fill, line, valign: "top", margin: 18 }));

  label(s, "a4_caption", [{ text: "500 random synthetic transactions through triage ", options: { bold: true, color: COL.dark } },
    { text: "(notebook 01)", options: { color: COL.muted } }], { x: 128, y: 640, w: 1664, h: 40 }, COL.dark, 28);
  const total = 500, parts = [["approve", 428, "86%", COL.green], ["investigate", 44, "9%", COL.orange], ["decline", 28, "6%", COL.red]];
  let x = 128;
  parts.forEach(([key, n, pct, color]) => {
    const w = Math.round(1664 * n / total);
    s.addText(pct, { shape: pres.shapes.RECTANGLE, x: X(x), y: X(700), w: X(w), h: X(90), fill: { color },
      line: { color: COL.bgLight, width: 1 }, color: "FFFFFF", bold: true, fontSize: PT(30), align: "center", valign: "middle",
      fontFace: SANS, margin: 0, objectName: `a4_bar_${key}` });
    x += w;
  });
  label(s, "a4_legend", [
    { text: "■ auto-approved by rules   ", options: { color: COL.green, bold: true } },
    { text: "■ investigated by AI agents   ", options: { color: COL.orange, bold: true } },
    { text: "■ auto-declined by rules", options: { color: COL.red, bold: true } },
    { text: "   → only 9% pay for LLM calls", options: { color: COL.dark, bold: true } },
  ], { x: 128, y: 810, w: 1664, h: 40 }, COL.dark, 26);

  s.addNotes("Two obvious designs fail. Rules alone are instant and free but rigid. An LLM on every transaction understands context " +
    "but costs 3–4 calls each on millions of transactions, most of them obvious. Fraud Guard tiers the work. Last click: in notebook 01 " +
    "we pushed 500 random synthetic transactions through the rule engine: 86% approved and 6% declined instantly; only 9% reached " +
    "the AI agents. That is where the cost saving comes from.");
}

// ------------------------------------------------------------- 3 graph
{
  const s = pres.addSlide();
  s.background = { color: COL.bgLight };
  heading(s, "The graph", "one node, one job; edges are the business logic",
    "graph.py wires 10 nodes. Conditional edges route; parallel edges fan out; one node pauses for a person.");

  box(s, "a1_ingest", { x: 128, y: 510, w: 180, h: 100 }, { title: "ingest", titleMono: true, align: "center" });
  box(s, "a2_triage", { x: 360, y: 490, w: 240, h: 140 }, { title: "triage", titleMono: true, detail: "rules only, no LLM", fill: COL.orangeTint, line: COL.orange });
  arrow(s, "a2_arrow", 308, 560, 360, 560, COL.muted);

  box(s, "a3_approve", { x: 700, y: 280, w: 300, h: 90 }, { title: "auto_approve", titleMono: true, detail: "score < 0.30 → resolution", fill: COL.greenTint, line: COL.green });
  elbow(s, "a3_arrow", 600, 560, 700, 325, COL.green);
  box(s, "a4_decline", { x: 700, y: 760, w: 300, h: 90 }, { title: "auto_decline", titleMono: true, detail: "score ≥ 0.65 → resolution", fill: COL.redTint, line: COL.red });
  elbow(s, "a4_arrow", 600, 560, 700, 805, COL.red);

  [["a5_analyst", "transaction_analyst", 410], ["a5_identity", "identity_verifier", 510], ["a5_patterns", "pattern_detector", 610]].forEach(([name, title, y], i) => {
    box(s, name, { x: 700, y, w: 300, h: 80 }, { title, titleMono: true, titleSize: 21, fill: COL.blueTint, line: COL.blue });
    elbow(s, `a5_in${i}`, 600, 560, 700, y + 40, COL.blue);
    elbow(s, `a6_out${i}`, 1000, y + 40, 1080, 560, COL.blue);
  });
  label(s, "a5_label", "0.30–0.65: all three run in parallel", { x: 700, y: 700, w: 340, h: 40 }, COL.blue, 22);

  box(s, "a6_aggregator", { x: 1080, y: 490, w: 260, h: 140 }, { title: "aggregator", titleMono: true, detail: "one score + reasoning" });
  box(s, "a7_review", { x: 1440, y: 330, w: 352, h: 120 }, { title: "human_review", titleMono: true, detail: "pauses until a person decides", fill: COL.orangeTint, line: COL.orange });
  elbow(s, "a7_arrow", 1340, 560, 1440, 390, COL.orange);
  label(s, "a7_label", "≥ 0.5", { x: 1300, y: 455, w: 90, h: 34 }, COL.orange, 22);
  box(s, "a8_resolution", { x: 1440, y: 620, w: 352, h: 120 }, { title: "resolution", titleMono: true, detail: "final decision + account memory" });
  elbow(s, "a8_arrow", 1340, 560, 1440, 680, COL.muted);
  label(s, "a8_label", "< 0.5", { x: 1300, y: 625, w: 90, h: 34 }, COL.muted, 22);
  arrow(s, "a8_from_review", 1616, 450, 1616, 620, COL.orange);

  s.addNotes("Click through the graph. ingest records the transaction. triage scores it with plain Python rules. Below 0.30 it is " +
    "approved, at 0.65 or above declined, both instantly. In between, LangGraph fans out to three specialist agents that run in " +
    "parallel, each from a different angle, and fans back in at the aggregator, which turns three opinions into one score. At 0.5 or " +
    "above the graph pauses before human_review; otherwise it goes straight to resolution, which records the final decision and " +
    "writes it to the account's memory. Every box is a node with one job; every routing decision is a conditional edge.");
}

// ------------------------------------------------------------- 4 triage
{
  const s = pres.addSlide();
  s.background = { color: COL.bgAlt };
  heading(s, "Triage", "five warning signs and the account’s history",
    "nodes/triage.py adds points per signal, caps at 1.0, and routes on two thresholds. No LLM.");

  const signals = [
    ["Unusual amount", "+0.15 over the account’s max, +0.35 over 3×"],
    ["Unknown device", "+0.15"],
    ["Risky merchant", "merchant risk score × 0.2"],
    ["New wire beneficiary", "+0.15"],
    ["Impossible travel", "+0.55 if the country changed since the last transaction"],
    ["Account memory", "+0.15 per past escalation, +0.10 per decline (max +0.30)"],
  ];
  signals.forEach(([title, detail], i) => box(s, `a${i + 1}_signal`, { x: 128, y: 290 + i * 92, w: 720, h: 82 },
    { title, detail, titleSize: 28, detailSize: 24, fill: i === 5 ? COL.orangeTint : COL.box, line: i === 5 ? COL.orange : COL.boxLine }));

  const cx = 920, cw = 872, top = 290, bottom = 830;
  const zones = [[0, 0.30, COL.greenTint, "approve", COL.green], [0.30, 0.65, COL.orangeTint, "investigate", COL.orange], [0.65, 1.0, COL.redTint, "decline", COL.red]];
  zones.forEach(([a, b, fill, name, color]) => {
    s.addShape(pres.shapes.RECTANGLE, { x: X(cx + a * cw), y: X(top), w: X((b - a) * cw), h: X(bottom - top), fill: { color: fill },
      line: { color: fill, width: 0.5 }, objectName: `zone_${name}` });
    label(s, `zone_label_${name}`, name, { x: cx + a * cw + 12, y: top + 10, w: (b - a) * cw - 24, h: 34 }, color, 24);
  });
  [0, 0.30, 0.65, 1.0].forEach((v, i) => label(s, `tick_${i}`, v === 0 ? "0" : v.toFixed(2).replace(/0$/, ""),
    { x: cx + v * cw - (v === 1.0 ? 50 : v === 0 ? 0 : 25), y: bottom + 8, w: 50, h: 30 }, COL.muted, 22));
  [["clean_coffee", 0.01], ["borderline_restart_demo", 0.59], ["borderline_wire", 0.64], ["impossible_travel", 0.92]].forEach(([name, score], i) => {
    const y = 380 + i * 110;
    label(s, `a${i + 7}_name`, [{ text: name, options: { bold: true, color: COL.dark } }, { text: `  ${score.toFixed(2)}`, options: { color: COL.blue, bold: true } }],
      { x: cx + 12, y, w: cw - 24, h: 34 }, COL.dark, 24);
    s.addShape(pres.shapes.RECTANGLE, { x: X(cx), y: X(y + 40), w: X(Math.max(cw * score, 8)), h: X(44), fill: { color: COL.blue },
      line: { color: COL.blue, width: 0.5 }, objectName: `a${i + 7}_bar` });
  });

  s.addNotes("Clicks 1–6: the warning signs, one at a time. Triage is plain Python: points for each sign, capped at 1.0. Clicks 7–10: the four demo scenarios. The $6.50 coffee " +
    "scores 0.01: approved. The two wire transfers land in the middle band, 0.59 and 0.64: unusual amount, risky merchant, new " +
    "beneficiary, so they go to the agents. The US-to-Nigeria purchase ten minutes after a US one scores 0.92: impossible travel alone " +
    "adds 0.55, so it is declined with no LLM. The last signal is memory: an account with past escalations scores higher, and in " +
    "notebook 01 two escalations push the 0.59 wire to 0.89, an automatic decline.");
}

// ------------------------------------------------------------- 5 specialists
{
  const s = pres.addSlide();
  s.background = { color: COL.bgLight };
  heading(s, "The specialists", "three ReAct agents, three angles, one score",
    "Same factory (core/specialist_factory.py), different prompt and tools. They run in parallel.");

  const agents = [
    ["a1_analyst", "transaction_analyst", "Is the amount and merchant unusual for this account?",
      "account_history · merchant_risk_score · sanctions_check", "watchlist hit on “Silk Road Holdings Ltd” leads the finding"],
    ["a2_identity", "identity_verifier", "Are the device and location the real owner’s?",
      "device_fingerprint · geolocation", "geolocation is a live MCP server → ip-api.com"],
    ["a3_patterns", "pattern_detector", "Does it look like fraud we’ve seen before?",
      "account_history · similar_fraud_cases", "RAG: vector search over past fraud cases (Chroma)"],
  ];
  agents.forEach(([name, title, question, tools, highlight], i) => box(s, name, { x: 128 + i * 566, y: 280, w: 532, h: 370 }, {
    title, titleMono: true, titleSize: 28, valign: "top", margin: 18, fill: COL.blueTint, line: COL.blue,
    detail: [
      { text: question, color: COL.dark, br: true }, { text: " ", br: true },
      { text: "Tools: ", bold: true, color: COL.dark }, { text: tools, mono: true, br: true }, { text: " ", br: true },
      { text: highlight, color: COL.orange, bold: true },
    ],
  }));

  box(s, "a4_react", { x: 128, y: 690, w: 1060, h: 230 }, {
    title: "ReAct loop, inside each agent", valign: "top", margin: 18,
    detail: [
      { text: "the LLM reads the transaction → picks a tool → reads the result → picks again … → writes a 2–3 sentence finding", br: true },
      { text: " ", br: true },
      { text: "Adding a skill = adding one tool to a list. The graph doesn’t change.", color: COL.blue, bold: true },
    ],
  });
  box(s, "a5_aggregator", { x: 1252, y: 690, w: 540, h: 230 }, {
    title: "aggregator", titleMono: true, valign: "top", margin: 18, fill: COL.orangeTint, line: COL.orange,
    detail: [
      { text: "structured output, always parseable:", br: true },
      { text: "{composite_score, reasoning}", mono: true, color: COL.dark, br: true }, { text: " ", br: true },
      { text: "≥ 0.5 → a person reviews it", color: COL.orange, bold: true },
    ],
  });

  s.addNotes("Each specialist investigates one independent angle, which is why they can run in parallel. The transaction analyst checks " +
    "the amount against the account's history, the merchant's risk, and a sanctions watchlist; on the Silk Road wire it leads with the " +
    "watchlist hit. The identity verifier checks the device and calls a real MCP server for geolocation: the impossible-travel IP " +
    "really resolves to Nigeria. The pattern detector searches past fraud cases with embeddings. Each is a ReAct agent: the LLM keeps " +
    "choosing tools until it has enough, then writes a short finding. The aggregator turns three free-text findings into one number " +
    "using structured output, so the router can always compare it.");
}

// ------------------------------------------------------------- 6 human in the loop + memory
{
  const s = pres.addSlide();
  s.background = { color: COL.bgAlt };
  heading(s, "Human in the loop", "pause, survive a restart, resume, remember",
    "A checkpointer saves every step of one run; a store remembers the account across runs.");

  box(s, "a1_investigate", { x: 128, y: 300, w: 300, h: 110 }, { title: "investigate", titleMono: true, detail: "3 agents + aggregator" });
  box(s, "a2_paused", { x: 520, y: 300, w: 330, h: 110 }, { title: "paused", detail: "before human_review", fill: COL.orangeTint, line: COL.orange });
  arrow(s, "a2_arrow", 428, 355, 520, 355, COL.muted);
  box(s, "a3_reviewer", { x: 940, y: 300, w: 380, h: 110 }, { title: "a person decides", detail: "Approve · Decline · Escalate", fill: COL.orangeTint, line: COL.orange });
  arrow(s, "a3_arrow", 850, 355, 940, 355, COL.orange);
  box(s, "a4_resolution", { x: 1410, y: 300, w: 382, h: 110 }, { title: "resolution", titleMono: true, detail: "update_state → invoke(None)", fill: COL.blueTint, line: COL.blue });
  arrow(s, "a4_arrow", 1320, 355, 1410, 355, COL.blue);

  box(s, "a5_checkpoints", { x: 128, y: 500, w: 800, h: 170 }, {
    title: "checkpoints.sqlite · SqliteSaver", titleMono: true, titleSize: 26, valign: "top", margin: 16,
    detail: [{ text: "every step saved per thread_id. Kill the process mid-review, rebuild the graph from the file: the case is still waiting, findings and all.", color: COL.dark }],
  });
  arrow(s, "a5_arrow", 685, 410, 685, 500, COL.orange);
  box(s, "a6_store", { x: 992, y: 500, w: 800, h: 170 }, {
    title: "account_memory.sqlite · SqliteStore", titleMono: true, titleSize: 26, valign: "top", margin: 16,
    detail: [{ text: "each final decision saved per account. Next time, triage reads it back with get_store() and raises the score.", color: COL.dark }],
  });
  arrow(s, "a6_arrow", 1600, 410, 1600, 500, COL.blue);

  box(s, "a7_example", { x: 128, y: 730, w: 1664, h: 150 }, {
    title: "Same account, next transaction (notebook 04)", valign: "top", margin: 16, fill: COL.box,
    detail: [
      { text: "borderline_wire on a clean account: ", color: COL.dark }, { text: "0.64 → investigate", bold: true, color: COL.orange },
      { text: "      after one escalation on acct_2002: ", color: COL.dark }, { text: "0.79 → auto-declined, no LLM calls", bold: true, color: COL.red },
    ],
  });

  s.addNotes("Click 1–4: a risky case is investigated, the graph pauses before human_review, a person chooses approve, decline or " +
    "escalate, and the app writes that choice into the saved state and resumes the same thread. Click 5: every step is saved in SQLite " +
    "by the checkpointer. In notebook 04 we throw the graph object away, rebuild it from the file, and the case is still waiting with " +
    "all three findings. Click 6: separately, the store remembers decisions per account. Click 7: after one escalation on the account, " +
    "the next wire scores 0.79 instead of 0.64 and is declined automatically. Checkpointer = durability of one run; store = memory " +
    "across runs.");
}

// ------------------------------------------------------------- 7 code
{
  const s = pres.addSlide();
  s.background = { color: COL.bgLight };
  heading(s, "The code", "a graph builder and an agent factory",
    "Simplified excerpts. The real files add the routing maps, lazy agent creation and the audit trail.");

  codePanel(s, "a1_graph", { x: 128, y: 280, w: 816, h: 540 }, "graph.py", [
    ["builder = StateGraph(TransactionState)"],
    [["for", "kw"], " name ", ["in", "kw"], " NODE_NAMES:"],
    ["    builder.add_node(name, nodes[name])"],
    ["builder.add_edge(START, ", ['"ingest"', "st"], ")"],
    ["builder.add_edge(", ['"ingest"', "st"], ", ", ['"triage"', "st"], ")"],
    ["builder.add_conditional_edges(       ", ["# route", "cm"]],
    ["    ", ['"triage"', "st"], ", route_after_triage)"],
    [["for", "kw"], " agent ", ["in", "kw"], " SPECIALISTS:             ", ["# fan-in", "cm"]],
    ["    builder.add_edge(agent, ", ['"aggregator"', "st"], ")"],
    ["builder.add_conditional_edges("],
    ["    ", ['"aggregator"', "st"], ", route_after_aggregator)"],
    ["builder.add_edge(", ['"human_review"', "st"], ", ", ['"resolution"', "st"], ")"],
    [["return", "kw"], " builder.compile("],
    ["    checkpointer=checkpointer, store=store,"],
    ["    interrupt_before=[", ['"human_review"', "st"], "])  ", ["# pause", "cm"]],
  ]);
  codePanel(s, "a2_factory", { x: 976, y: 280, w: 816, h: 540 }, "core/specialist_factory.py", [
    [["def", "kw"], " make_specialist_node(name, key, tools, prompt):"],
    ["    ", ["def", "kw"], " node(state):"],
    ["        agent = create_react_agent("],
    ["            get_llm(temperature=0), tools,"],
    ["            prompt=prompt)                 ", ["# ReAct", "cm"]],
    ["        msgs = agent.invoke("],
    ["            {", ['"messages"', "st"], ": [(", ['"user"', "st"], ", task(state))]}"],
    ["        )[", ['"messages"', "st"], "]"],
    ["        ", ["return", "kw"], " {key: msgs[-1].content,  ", ["# finding", "cm"]],
    ["                ", ['"audit_log"', "st"], ": format_trace(msgs)}"],
    ["    ", ["return", "kw"], " node"],
    [" "],
    ["transaction_analyst_node = make_specialist_node("],
    ["    ", ['"transaction_analyst"', "st"], ", ", ['"analyst_findings"', "st"], ","],
    ["    [account_history, merchant_risk_score,"],
    ["     sanctions_check], SYSTEM_PROMPT)    ", ["# +1 skill", "cm"]],
  ]);

  const strip = (name, x, file, fn, setting) => s.addText([
    { text: file, options: { bold: true } }, { text: " · " + fn, options: { breakLine: true } }, { text: setting },
  ], {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.11, x: X(x), y: X(840), w: X(816), h: X(100),
    fill: { color: COL.blueTint }, line: { color: COL.blue, width: 1.5 }, fontFace: MONO, fontSize: PT(24),
    color: COL.dark, valign: "middle", margin: 10, objectName: name,
  });
  strip("a3_llm", 128, "core/llm.py", "get_llm()", "LLM_PROVIDER = gemini | openai");
  strip("a4_studio", 976, "langgraph.json", "graph.py:studio_graph", "uv run langgraph dev → LangGraph Studio");

  s.addNotes("Left: the whole pipeline is a StateGraph. Add the nodes, connect them with edges, add the two routers as conditional " +
    "edges, and compile with a checkpointer, a store, and interrupt_before human_review: that one argument is the pause. Right: all " +
    "three specialists come from one factory that wraps LangGraph's create_react_agent into a graph node, returning the agent's final " +
    "message as the finding plus an audit trail of its tool calls. Giving the analyst the sanctions skill was one more tool in a list. " +
    "Bottom: the model comes from get_llm, Gemini by default or OpenAI, and the same graph opens in LangGraph Studio.");
}

// ------------------------------------------------------------- 8 try it
{
  const s = pres.addSlide();
  s.background = { color: COL.dark };
  text(s, "TRY IT YOURSELF", { x: 128, y: 128, w: 1664, h: 40 }, { fontSize: PT(24), color: COL.lightBlue, charSpacing: 2, objectName: "eyebrow" });
  text(s, "Five notebooks, from LangGraph basics to production patterns", { x: 128, y: 180, w: 1664, h: 100 },
    { fontSize: PT(64), bold: true, color: COL.cream, objectName: "title" });
  text(s, "Each runs on its own, uses the project’s real code, and keeps its own databases. 00 and 01 need no API key.",
    { x: 128, y: 300, w: 1664, h: 60 }, { fontSize: PT(34), color: COL.sub, objectName: "subtitle" });

  const cards = [
    ["00", "Start here", "LangGraph basics on toy graphs"],
    ["01", "Triage rules", "signals, thresholds, memory"],
    ["02", "Specialists", "tools, RAG, live MCP, ReAct"],
    ["03", "Full graph", "parallel agents, pause, resume"],
    ["04", "Persistence", "restart mid-review, memory"],
  ];
  const W = 280, GAP = 66;
  cards.forEach(([num, title, detail], i) => {
    const x = 128 + i * (W + GAP);
    s.addText([
      { text: num, options: { fontFace: MONO, bold: true, color: i < 2 ? COL.lightBlue : COL.lightOrange, fontSize: PT(40), breakLine: true } },
      { text: title, options: { bold: true, color: COL.cream, fontSize: PT(32), breakLine: true } },
      { text: detail, options: { color: COL.sub, fontSize: PT(24) } },
    ], {
      shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.11, x: X(x), y: X(450), w: X(W), h: X(280),
      fill: { color: COL.card }, line: { color: COL.cardLine, width: 1.5 },
      valign: "top", margin: 14, fontFace: SANS, paraSpaceAfter: 6, objectName: `a${i + 1}_nb${num}`,
    });
    if (i < cards.length - 1) arrow(s, `a${i + 2}_arrow`, x + W + 12, 590, x + W + GAP - 12, 590, COL.lightBlue);
  });

  s.addText([
    { text: "github.com/iam-suraj-kumar/fintech-agent", options: { fontFace: MONO, bold: true, color: COL.cream, breakLine: true } },
    { text: "uv sync --dev  ·  GEMINI_API_KEY in .env  ·  uv run jupyter lab notebooks/", options: { color: COL.sub, fontFace: MONO } },
  ], { x: X(128), y: X(800), w: X(1664), h: X(110), fontSize: PT(28), fontFace: SANS, isTextBox: true, margin: 0, objectName: "a6_repo" });

  s.addNotes("The hands-on path. 00 teaches every LangGraph building block on toy graphs with no API key. 01 is the rule engine, also " +
    "with no key. 02 opens up the agents: tools, the fraud-case search, the live MCP server, ReAct step by step. 03 runs the whole graph, " +
    "pauses for review and resumes it. 04 kills the run mid-review and brings it back, and shows memory changing the next decision. " +
    "Setup: uv sync --dev, a free Gemini key in .env, then jupyter lab.");
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
