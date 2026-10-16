// Entra ID self-service deck. node build.js <out.pptx>
// Shapes named "a<N>_..." appear on click N (animate.py adds the click-to-reveal timing afterwards).
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const path = require("path");
const fa = require("react-icons/fa");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");

const OUT = process.argv[2] || "deck.pptx";
const IMG = path.join(__dirname, "img");

// BMO-like blue on white; red only for problems/failures, green only for "done".
const HEX = { blue: "0079C1", navy: "003A70", sky: "E8F3FB", mid: "5FA8DC", red: "D7282F", green: "2E8540", amber: "C98300", slate: "5B6770", ink: "1F2933", line: "D5E3EF" };
const THEME = {
  name: "Entra Self-Service Blue",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.ink, lt1: "FFFFFF", dk2: HEX.navy, lt2: HEX.sky,
    accent1: HEX.blue, accent2: HEX.mid, accent3: HEX.red, accent4: HEX.green, accent5: HEX.amber, accent6: HEX.slate,
    hlink: HEX.blue, folHlink: HEX.navy,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Entra ID app registrations in minutes";
pres.subject = "Self-service Entra ID app registrations on Power Apps, Power Automate and SharePoint";
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, M = 0.6;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "Title",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: 6.4, h: 1.9, fontSize: 40, bold: true, color: C.text2, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.05, w: 6.2, h: 1.2, fontSize: 18, color: C.accent6, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.5, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 0.8, fontSize: 30, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "Entra ID Self-Service  |  Power Apps · Power Automate · SharePoint", options: { x: M, y: H - 0.42, w: 8, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.42, w: 0.6, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
});
pres.defineSlideMaster({
  title: "Closing",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.6, w: W - 2 * M, h: 1.3, fontSize: 48, bold: true, color: C.text2, align: "center", valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 3.95, w: W - 2 * M, h: 0.8, fontSize: 18, color: C.accent6, align: "center", valign: "top", margin: 0 }, text: "" } },
  ],
});

// ---------------------------------------------------------------- helpers
const iconCache = {};
async function icon(name, color = "FFFFFF") {
  const k = name + color;
  if (!iconCache[k]) {
    const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(fa[name], { color: "#" + color, size: 256 }));
    const buf = await sharp(Buffer.from(svg)).resize(256, 256, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer();
    iconCache[k] = "image/png;base64," + buf.toString("base64");
  }
  return iconCache[k];
}
const shadow = () => ({ type: "outer", color: "7F9DB9", blur: 6, offset: 2, angle: 90, opacity: 0.25 });

async function circleIcon(s, x, y, d, iconName, name, fill = C.accent1) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + "_circle" });
  s.addImage({ data: await icon(iconName), x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: name + "_icon", altText: "" });
}
function card(s, x, y, w, h, name, fill = C.background2) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, shadow: shadow(), objectName: name });
}
function text(s, t, x, y, w, h, opts = {}) {
  s.addText(t, { x, y, w, h, isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top", ...opts });
}
function picture(s, file, x, y, w, h, name, alt) {
  // fit inside the box, keep aspect ratio, centred
  const sizes = require(path.join(IMG, "sizes.json"));
  const [iw, ih] = sizes[file];
  let pw = w, ph = (w * ih) / iw;
  if (ph > h) { ph = h; pw = (h * iw) / ih; }
  s.addImage({ path: path.join(IMG, file), x: x + (w - pw) / 2, y: y + (h - ph) / 2, w: pw, h: ph, objectName: name, altText: alt });
}
function screenshot(s, x, y, w, h, label, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.accent2, width: 1.25, dashType: "dash" }, objectName: name + "_frame" });
  s.addShape(pres.shapes.RECTANGLE, { x: x + 0.12, y: y + 0.12, w: w - 0.24, h: 0.22, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: name + "_bar" });
  text(s, [{ text: "Screenshot", options: { bold: true, breakLine: true } }, { text: label }], x + 0.15, y + 0.5, w - 0.3, h - 0.65,
    { fontSize: 11, color: C.accent6, align: "center", valign: "middle", objectName: name + "_label" });
}
function arrow(s, x1, y1, x2, y2, name, color = C.accent2) {
  s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width: 2, endArrowType: "triangle" }, objectName: name });
}
function content(section, title) {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

// ---------------------------------------------------------------- slides
async function build() {
  // 1 Title -----------------------------------------------------------------
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "Title", sectionTitle: "Opening" });
  text(s, "ENTRA ID AUTOMATION", M, 1.45, 6, 0.4, { fontSize: 14, bold: true, color: C.accent1, charSpacing: 3 });
  s.addText("App registrations in minutes, not days", { placeholder: "title" });
  s.addText("Self-service Entra ID app registrations built on Power Apps, Power Automate and SharePoint", { placeholder: "body" });
  text(s, "Presenter name  ·  Team  ·  Date", M, 6.35, 6, 0.35, { fontSize: 14, color: C.accent6 });
  card(s, 7.35, 0.9, 5.4, 5.7, "title_panel", C.background2);
  const glance = [["FaMobileAlt", "Ask", "The team fills in a form in the Power App"], ["FaLock", "Lock", "The request is saved and locked"],
    ["FaUserCheck", "Approve", "Manager, then the Entra ID team"], ["FaRobot", "Create", "A flow builds it in Entra ID through Graph"],
    ["FaTags", "Stamp", "Owner, appCatID and request ID as tags"]];
  for (let i = 0; i < glance.length; i++) {
    const y = 1.2 + i * 1.05;
    await circleIcon(s, 7.75, y, 0.7, glance[i][0], `glance${i}`);
    text(s, glance[i][1], 8.7, y + 0.02, 3.8, 0.35, { fontSize: 17, bold: true, color: C.text2 });
    text(s, glance[i][2], 8.7, y + 0.37, 3.8, 0.35, { fontSize: 13, color: C.text1 });
    if (i < glance.length - 1) s.addShape(pres.shapes.LINE, { x: 8.1, y: y + 0.72, w: 0, h: 0.31, line: { color: C.accent2, width: 1.5 }, objectName: `glance_line${i}` });
  }
  s.addNotes("Open with the outcome: a team asks for an app registration in a form, two people approve, and a flow creates it in Entra ID in minutes. Everything runs on Microsoft 365 services we already license. See the speaker notes document for the full talk track.");

  // 2 Agenda ----------------------------------------------------------------
  s = content("Opening", "What we'll cover");
  const agenda = [
    ["FaExclamationTriangle", "The problem today"], ["FaHandshake", "Working with the M365 team"], ["FaBalanceScale", "Options and why the Power stack"],
    ["FaProjectDiagram", "How the solution works"], ["FaLayerGroup", "What it delivers"], ["FaChartLine", "Benefits and savings"],
    ["FaTags", "Tags and ownership"], ["FaRoute", "Future path"], ["FaUsers", "How we work together"],
  ];
  for (let i = 0; i < agenda.length; i++) {
    const col = Math.floor(i / 3), row = i % 3;
    const x = M + col * 4.1, y = 1.55 + row * 1.65;
    card(s, x, y, 3.8, 1.35, `agenda${i}_card`, C.background2);
    await circleIcon(s, x + 0.25, y + 0.3, 0.75, agenda[i][0], `agenda${i}`);
    text(s, String(i + 1).padStart(2, "0"), x + 1.2, y + 0.25, 0.8, 0.35, { fontSize: 14, bold: true, color: C.accent1 });
    text(s, agenda[i][1], x + 1.2, y + 0.58, 2.45, 0.6, { fontSize: 16, bold: true, color: C.text2 });
  }
  s.addNotes("Nine short sections. The first half explains why and how; the second half covers the benefits, the ownership model, what comes next, and how we want to work with your team.");

  // 3 Problem ---------------------------------------------------------------
  pres.addSection({ title: "Why" });
  s = content("Why", "Today an app registration is a 10-day ticket");
  const pains = [
    ["FaHourglassHalf", "10 working days", "average time from request to a usable app registration"],
    ["FaUserClock", "1 person-day", "of Entra ID team effort for every request"],
    ["FaComments", "Back-and-forth", "requirements gathered over email and tickets, often several rounds"],
    ["FaEyeSlash", "No visibility", "project teams can't see Entra ID, so mistakes and rework slip in"],
  ];
  for (let i = 0; i < pains.length; i++) {
    const x = M + i * 3.07, y = 1.6;
    const n = `a${i + 1}_pain${i}`;
    card(s, x, y, 2.85, 3.6, n + "_card");
    await circleIcon(s, x + 0.3, y + 0.35, 0.8, pains[i][0], n, C.accent3);
    text(s, pains[i][1], x + 0.3, y + 1.4, 2.4, 0.6, { fontSize: 24, bold: true, color: C.text2, objectName: n + "_stat" });
    text(s, pains[i][2], x + 0.3, y + 2.05, 2.35, 1.3, { fontSize: 14, color: C.text1, objectName: n + "_text" });
  }
  text(s, [{ text: "Result: ", options: { bold: true, color: C.accent3 } },
    { text: "projects wait, teams work around the process (one app reused for many purposes), and names, owners and settings differ every time." }],
    M, 5.55, W - 2 * M, 0.8, { fontSize: 16, objectName: "a5_result" });
  s.addNotes("Walk the four cards left to right (one per click). Use real examples of a project that waited, an app reused for several purposes, or a misconfigured redirect URI. The last line is the consequence: delay plus inconsistency.");

  // 4 Collaboration with M365 ----------------------------------------------
  pres.addSection({ title: "How" });
  s = content("How", "Built with the M365 team, on services we already license");
  const m365 = [
    ["FaMobileAlt", "Power Apps", "The request form and tracker. Standard connectors only, so users need nothing beyond Microsoft 365."],
    ["FaCogs", "Power Automate", "Approvals in Outlook and Teams, and the flows that create everything in Entra ID through Microsoft Graph."],
    ["FaListAlt", "SharePoint", "The request list (the audit trail), the catalog of apps and groups, and the settings. Item-level security."],
  ];
  for (let i = 0; i < m365.length; i++) {
    const x = M + i * 4.1, y = 1.5, n = `a${i + 1}_m365${i}`;
    card(s, x, y, 3.8, 2.85, n + "_card");
    await circleIcon(s, x + 0.3, y + 0.3, 0.8, m365[i][0], n);
    text(s, m365[i][1], x + 1.3, y + 0.42, 2.3, 0.55, { fontSize: 20, bold: true, color: C.text2, objectName: n + "_title" });
    text(s, m365[i][2], x + 0.3, y + 1.3, 3.25, 1.45, { fontSize: 14, objectName: n + "_text" });
  }
  text(s, "What we needed from the M365 team", M, 4.65, 8, 0.4, { fontSize: 18, bold: true, color: C.accent1, objectName: "a4_askhead" });
  const asks = [
    ["A Power Platform environment with Dataverse", "used by Approvals and the solution import"],
    ["Connectors allowed in the DLP policy", "SharePoint, Approvals, Outlook, Office 365 Users, HTTP with Entra ID"],
    ["One Power Automate Premium licence", "for the flow account only, not for users"],
    ["A SharePoint site", "for the request, catalog and settings lists"],
  ];
  for (let i = 0; i < asks.length; i++) {
    const x = M + (i % 2) * 6.15, y = 5.15 + Math.floor(i / 2) * 0.72, n = `a4_ask${i}`;
    s.addImage({ data: await icon("FaCheckCircle", HEX.blue), x, y: y + 0.04, w: 0.3, h: 0.3, objectName: n + "_icon", altText: "" });
    text(s, [{ text: asks[i][0], options: { bold: true, breakLine: true } }, { text: asks[i][1], options: { color: C.accent6 } }], x + 0.45, y, 5.6, 0.68, { fontSize: 14, objectName: n + "_text" });
  }
  s.addNotes("Stress that this is a partnership with the M365 team: we enable Power Apps, Power Automate and SharePoint capabilities that are already licensed, and keep the footprint small. Four concrete asks.");

  // 5 Options ---------------------------------------------------------------
  s = content("How", "Three ways to build it: why we chose the Power stack");
  const crit = ["Familiar to M365 users", "Easy to extend flows", "Keeps data in M365", "Low maintenance (no servers)", "Approvals built in", "Running cost"];
  const opts = [
    ["CI/CD pipelines", "Azure DevOps / GitHub", [1, 2, 1, 2, 2, 3]],
    ["Function App + web portal", "Azure, custom code", [1, 3, 2, 1, 1, 2]],
    ["Power Apps + Automate + SharePoint", "Microsoft 365, low-code", [3, 3, 3, 3, 3, 3]],
  ];
  const dots = (n) => "●".repeat(n) + "○".repeat(3 - n);
  const rows = [[{ text: "", options: { fill: { color: C.background1 } } }].concat(opts.map((o, i) => ({
    text: [{ text: o[0], options: { bold: true, breakLine: true } }, { text: o[1], options: { fontSize: 11, color: i === 2 ? C.background1 : C.accent6 } }],
    options: { fill: { color: i === 2 ? C.accent1 : C.background2 }, color: i === 2 ? C.background1 : C.text2, align: "center", valign: "middle" },
  })))];
  crit.forEach((c, r) => rows.push([{ text: c, options: { bold: true, color: C.text2, fill: { color: C.background1 } } }]
    .concat(opts.map((o, i) => ({ text: dots(o[2][r]), options: { align: "center", color: i === 2 ? C.accent1 : C.accent6, fontSize: 18, fill: { color: i === 2 ? C.background2 : C.background1 } } })))));
  s.addTable(rows, { x: M, y: 1.4, w: 8.3, colW: [2.6, 1.9, 1.9, 1.9], rowH: [0.75, 0.52, 0.52, 0.52, 0.52, 0.52, 0.52], fontSize: 14, border: { type: "solid", pt: 0.75, color: HEX.line }, valign: "middle", objectName: "options_table" });
  card(s, 9.25, 1.4, 3.48, 4.65, "a1_decision_card", C.accent1);
  s.addImage({ data: await icon("FaCheckCircle"), x: 9.55, y: 1.7, w: 0.6, h: 0.6, objectName: "a1_decision_icon", altText: "" });
  text(s, "Decision", 10.3, 1.78, 2.2, 0.45, { fontSize: 20, bold: true, color: C.background1, objectName: "a1_decision_head" });
  text(s, [
    { text: "Power Apps + Power Automate + SharePoint", options: { bold: true, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 8 } },
    { text: "People already know it, flows extend without developers, data stays in M365, nothing to host or patch, and approvals come built in.", options: {} },
  ], 9.55, 2.5, 2.95, 3.4, { fontSize: 15, color: C.background1, objectName: "a1_decision_text" });
  text(s, "Rating: ●●● strong · ●●○ partial · ●○○ weak", M, 5.85, 8.3, 0.3, { fontSize: 11, color: C.accent6, objectName: "options_key" });
  s.addNotes("Compare the three options against the six criteria. Pipelines and a Function App are both viable, but they need developer skills to extend, they keep data outside M365 or need custom storage, and approvals have to be built. Click to reveal the decision.");

  // 6 High-level flow (editable shapes) ------------------------------------
  s = content("How", "How it works: five steps from request to Entra ID");
  const steps = [
    ["FaMobileAlt", "Ask", "Requester fills in the Power App form"],
    ["FaLock", "Lock", "Request saved in SharePoint and locked"],
    ["FaUserCheck", "Manager approves", "Outlook / Teams approval card"],
    ["FaShieldAlt", "Entra team approves", "Second approval, self-approval blocked"],
    ["FaRobot", "Create", "Flow calls Microsoft Graph as the platform app"],
  ];
  const bw = 2.1, gap = 0.38, by = 1.5;
  for (let i = 0; i < steps.length; i++) {
    const x = M + i * (bw + gap), n = `a${i + 1}_step${i}`;
    card(s, x, by, bw, 3.05, n + "_card");
    await circleIcon(s, x + (bw - 0.85) / 2, by + 0.3, 0.85, steps[i][0], n);
    text(s, steps[i][1], x + 0.15, by + 1.28, bw - 0.3, 0.7, { fontSize: 17, bold: true, color: C.text2, align: "center", valign: "middle", objectName: n + "_title" });
    text(s, steps[i][2], x + 0.15, by + 2.05, bw - 0.3, 0.9, { fontSize: 13, align: "center", objectName: n + "_text" });
    if (i < steps.length - 1) arrow(s, x + bw + 0.05, by + 1.37, x + bw + gap - 0.05, by + 1.37, `a${i + 2}_arrow${i}`);
  }
  card(s, M, 4.85, W - 2 * M, 1.45, "a6_result_card", C.background2);
  await circleIcon(s, M + 0.3, 5.15, 0.85, "FaCheckDouble", "a6_result", C.accent4);
  text(s, [{ text: "Result in minutes: ", options: { bold: true, color: C.text2 } },
    { text: "app registration, Application ID URI and scopes, app roles with their groups, enterprise app, tags and notes. The requester sees every step in My requests and by email." }],
    M + 1.45, 5.05, W - 2 * M - 1.7, 1.1, { fontSize: 15, valign: "middle", objectName: "a6_result_text" });
  text(s, "Editable: every box and arrow on this slide is a PowerPoint shape.", M, 6.5, 8, 0.3, { fontSize: 10, color: C.accent6, objectName: "edit_hint" });
  s.addNotes("One click per step. Emphasise that nothing happens in Entra ID until two people approve, and that the request is locked first so what is approved is exactly what gets built.");

  // 7 Request vs execution --------------------------------------------------
  s = content("How", "Requests and execution are kept apart");
  const zones = [
    ["a1", "Request side", "Runs as the requester", C.background2, C.text2, [
      ["FaUser", "Uses their own sign-in and standard licence"], ["FaListAlt", "Can only create and read their own requests"], ["FaBan", "Needs no Entra ID rights at all"]]],
    ["a2", "Approval gate", "Lock, then two approvals", C.background2, C.text2, [
      ["FaLock", "Request locked: requester can no longer edit"], ["FaCamera", "Snapshot of exactly what is approved"], ["FaUserCheck", "Manager, then Entra ID team"]]],
    ["a3", "Execution side", "Runs as the platform", C.accent1, C.background1, [
      ["FaRobot", "Flow account, separate from people"], ["FaCertificate", "App identity with a certificate, no secrets"], ["FaKey", "Only identity with Graph write permissions"]]],
  ];
  for (let i = 0; i < zones.length; i++) {
    const [p, head, sub, fill, fg, items] = zones[i];
    const x = M + i * 4.1, y = 1.45, n = `${p}_zone${i}`;
    card(s, x, y, 3.8, 3.75, n + "_card", fill);
    text(s, head, x + 0.3, y + 0.25, 3.2, 0.45, { fontSize: 20, bold: true, color: fg, objectName: n + "_head" });
    text(s, sub, x + 0.3, y + 0.7, 3.2, 0.35, { fontSize: 13, color: i === 2 ? C.background1 : C.accent6, objectName: n + "_sub" });
    for (let j = 0; j < items.length; j++) {
      s.addImage({ data: await icon(items[j][0], i === 2 ? "FFFFFF" : HEX.blue), x: x + 0.3, y: y + 1.3 + j * 0.78, w: 0.36, h: 0.36, objectName: `${n}_i${j}`, altText: "" });
      text(s, items[j][1], x + 0.85, y + 1.25 + j * 0.78, 2.75, 0.7, { fontSize: 14, color: fg, objectName: `${n}_t${j}` });
    }
    if (i < 2) arrow(s, x + 3.82, y + 1.9, x + 4.08, y + 1.9, `${zones[i + 1][0]}_arrow${i}`);
  }
  text(s, "Guards the execution flow checks before it changes anything", M, 5.45, 9, 0.4, { fontSize: 16, bold: true, color: C.accent1, objectName: "a4_guards_head" });
  text(s, [
    { text: "Requester is the item's built-in Created By (can't be faked)  ·  ", options: {} },
    { text: "Last edit made by the flow account  ·  ", options: {} },
    { text: "Both decisions Approved  ·  ", options: {} },
    { text: "Owner tag names the requester or their group", options: {} },
  ], M, 5.85, W - 2 * M, 0.7, { fontSize: 14, objectName: "a4_guards_text" });
  s.addNotes("Explain the separation: people never get Entra ID rights; the only identity that can change Entra ID is the platform app, and only the execution flow uses it. A site owner editing the list by hand cannot trigger it.");

  // 8 Core flow screenshots -------------------------------------------------
  pres.addSection({ title: "What" });
  s = content("What", "Core flow: register an application in one request");
  const wiz = [["1", "Basics", "Name convention, appCatID, environment, optional owning group"], ["2", "Expose an API", "Application ID URI, scopes, token claims"],
    ["3", "App roles", "User / Admin roles, each held by a group"], ["4", "Enterprise app", "Assignment required, account types, tags"], ["5", "Review + submit", "Summary, then manager and Entra approvals"]];
  for (let i = 0; i < wiz.length; i++) {
    const x = M + i * 2.45, n = `a${i + 1}_wiz${i}`;
    screenshot(s, x, 1.45, 2.25, 2.65, wiz[i][1] + " step", n);
    s.addShape(pres.shapes.OVAL, { x: x, y: 4.3, w: 0.45, h: 0.45, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: n + "_num" });
    text(s, wiz[i][0], x, 4.3, 0.45, 0.45, { fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", objectName: n + "_numtext" });
    text(s, wiz[i][1], x + 0.6, 4.33, 1.65, 0.4, { fontSize: 15, bold: true, color: C.text2, objectName: n + "_title" });
    text(s, wiz[i][2], x, 4.85, 2.25, 1.1, { fontSize: 13, objectName: n + "_text" });
  }
  text(s, "Replace each frame with a screenshot of the matching wizard step (Insert > Pictures, then send the frame to back or delete it).", M, 6.3, W - 2 * M, 0.35, { fontSize: 11, color: C.accent6, objectName: "shot_hint" });
  s.addNotes("Walk through the five wizard steps (one per click). Only Basics is required; the display name prefix is built from appCatID, environment and BoR short name and cannot be edited. Swap the frames for real screenshots before presenting.");

  // 9 What one request delivers --------------------------------------------
  s = content("What", "What one request delivers");
  const deliver = [
    ["FaSignature", "Standard name", "APPCAT-ENV-BOR-name, prefix enforced"], ["FaLink", "Application ID URI", "api://{appId} or custom"],
    ["FaKey", "Scopes", "e.g. access_as_user for delegated access"], ["FaUserShield", "App roles", "User / Admin or custom roles"],
    ["FaUsers", "Role assignments", "Existing groups hold each role"], ["FaBuilding", "Enterprise app", "Created for the app, assignment required"],
    ["FaIdBadge", "Token claims & URIs", "Optional claims, groups claim, redirect URIs"], ["FaTags", "Tags & notes", "Owner, appCatID, request ID, audit"],
  ];
  for (let i = 0; i < deliver.length; i++) {
    const col = i % 4, row = Math.floor(i / 4), x = M + col * 3.07, y = 1.5 + row * 2.45, n = `a${row + 1}_del${i}`;
    card(s, x, y, 2.85, 2.15, n + "_card");
    await circleIcon(s, x + 0.3, y + 0.3, 0.7, deliver[i][0], n);
    text(s, deliver[i][1], x + 0.3, y + 1.1, 2.4, 0.4, { fontSize: 16, bold: true, color: C.text2, objectName: n + "_title" });
    text(s, deliver[i][2], x + 0.3, y + 1.5, 2.4, 0.6, { fontSize: 13, objectName: n + "_text" });
  }
  s.addNotes("Manually these are eight separate tasks in the Entra admin center, each a chance for a mistake. Here they come from one form, validated, and created in the right order with retries while Entra replicates.");

  // 10 Complete picture -----------------------------------------------------
  s = content("What", "The complete picture");
  picture(s, "components.png", M, 1.3, W - 2 * M, 5.55, "components_diagram", "Components: people, Power Platform environment, SharePoint, flows, Microsoft Graph and Entra ID");
  s.addNotes("People on the left, the Power Platform environment in the middle (app, SharePoint lists, flows), Entra ID on the right. Point out that only the platform app registration holds Graph permissions. Editable source: diagrams/entra-powerplatform.drawio, page 2.");

  // 11 Other flows ----------------------------------------------------------
  s = content("What", "Beyond new apps: the other flows");
  const flows = [
    ["a1", "FaUserCheck", "ER-01 Approvals", "Locks the request, manager then Entra ID team"], ["a1", "FaRobot", "ER-02 Execute", "Creates and changes apps through Graph, logs every step"],
    ["a1", "FaSyncAlt", "ER-03 Catalog sync", "Hourly refresh of who can pick which apps and groups"], ["a2", "FaUserPlus", "ER-04 Add existing group", "Members make their group selectable, no approval"],
    ["a2", "FaSearch", "ER-05 Find app", "Search by app ID; only the owner can continue"], ["a2", "FaExchangeAlt", "ER-06 Owning group", "Hand an app from a person to a group"],
    ["a3", "FaRedo", "ER-07 Requeue", "Entra team re-runs approved requests"], ["a3", "FaEdit", "Change requests", "Expose an API, app roles, role assignments, enterprise app"],
  ];
  for (let i = 0; i < flows.length; i++) {
    const col = i % 2, row = Math.floor(i / 2), x = M + col * 6.15, y = 1.4 + row * 1.25, n = `${flows[i][0]}_flow${i}`;
    card(s, x, y, 5.9, 1.05, n + "_card");
    await circleIcon(s, x + 0.2, y + 0.17, 0.7, flows[i][1], n);
    text(s, flows[i][2], x + 1.1, y + 0.15, 4.6, 0.4, { fontSize: 16, bold: true, color: C.text2, objectName: n + "_title" });
    text(s, flows[i][3], x + 1.1, y + 0.53, 4.6, 0.45, { fontSize: 13, objectName: n + "_text" });
  }
  s.addNotes("Three groups (one per click): the core pipeline (approvals, execution, catalog), the self-service helpers that need no approval (add group, find app, owning group), and operations (requeue, change requests).");

  // 12 Before / after -------------------------------------------------------
  pres.addSection({ title: "Benefits" });
  s = content("Benefits", "From a 10-day ticket to a same-day request");
  const ba = [
    ["Lead time", "~10 working days", "Same day: approval time plus minutes of flow time"],
    ["Entra ID team effort", "≥ 1 person-day per request", "About 5 minutes to review and approve"],
    ["Requirements", "Back-and-forth over email and tickets", "One validated form, captured once"],
    ["Visibility", "Project teams can't see Entra ID", "My requests: status, approvals, step-by-step notes"],
    ["Consistency", "Every engineer builds it differently", "Same names, tags and settings every time"],
  ];
  text(s, "Manual today", M + 2.95, 1.42, 4.3, 0.4, { fontSize: 16, bold: true, color: C.accent3 });
  text(s, "With self-service", M + 7.55, 1.42, 4.5, 0.4, { fontSize: 16, bold: true, color: C.accent4 });
  for (let i = 0; i < ba.length; i++) {
    const y = 1.95 + i * 0.9, n = `a${i + 1}_ba${i}`;
    card(s, M, y, W - 2 * M, 0.75, n + "_card", i % 2 ? C.background1 : C.background2);
    text(s, ba[i][0], M + 0.25, y, 2.6, 0.75, { fontSize: 15, bold: true, color: C.text2, valign: "middle", objectName: n + "_k" });
    s.addImage({ data: await icon("FaTimesCircle", HEX.red), x: M + 2.95, y: y + 0.22, w: 0.3, h: 0.3, objectName: n + "_x", altText: "" });
    text(s, ba[i][1], M + 3.4, y, 4.0, 0.75, { fontSize: 14, valign: "middle", objectName: n + "_before" });
    s.addImage({ data: await icon("FaCheckCircle", HEX.green), x: M + 7.55, y: y + 0.22, w: 0.3, h: 0.3, objectName: n + "_v", altText: "" });
    text(s, ba[i][2], M + 8.0, y, 4.05, 0.75, { fontSize: 14, valign: "middle", objectName: n + "_after" });
  }
  s.addNotes("One row per click. Each row is a pain point from slide 3 and how the platform answers it.");

  // 13 Savings --------------------------------------------------------------
  s = content("Benefits", "What it saves");
  const stats = [["~9", "working days", "shorter lead time per request"], ["~7.9 h", "per request", "Entra ID team effort saved"], ["1", "Premium licence", "the only extra running cost"]];
  for (let i = 0; i < stats.length; i++) {
    const y = 1.5 + i * 1.65, n = `a${i + 1}_stat${i}`;
    card(s, M, y, 4.6, 1.4, n + "_card");
    text(s, stats[i][0], M + 0.3, y + 0.15, 2.0, 1.1, { fontSize: 40, bold: true, color: C.accent1, valign: "middle", objectName: n + "_num" });
    text(s, [{ text: stats[i][1], options: { bold: true, breakLine: true, color: C.text2 } }, { text: stats[i][2] }], M + 2.35, y + 0.2, 2.1, 1.0, { fontSize: 14, valign: "middle", objectName: n + "_label" });
  }
  s.addChart(pres.charts.BAR, [{ name: "Person-days saved", labels: ["50 apps / year", "100 apps / year", "200 apps / year"], values: [49, 99, 198] }], {
    x: 5.6, y: 1.45, w: 7.1, h: 4.75, barDir: "col", objectName: "a4_chart",
    chartColors: [HEX.blue], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.navy, dataLabelFontSize: 14, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "Entra ID team effort saved per year (person-days)", titleFontSize: 14, titleColor: HEX.navy, titleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.slate, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 60,
  });
  text(s, "≈ 0.2 / 0.45 / 0.9 of a full-time person at 220 working days a year. Multiply person-days by your internal day rate for a money figure.", 5.6, 6.25, 7.1, 0.5, { fontSize: 11, color: C.accent6, objectName: "a4_chart_note" });
  s.addNotes("The numbers use 8 hours manual effort vs about 5 minutes of review per request. Even at the lowest volume, one Premium licence costs a small fraction of the effort saved. Change requests (scopes, roles, assignments) add to this.");

  // 14 Tags and ownership ---------------------------------------------------
  s = content("Benefits", "Ownership by tags, not by naming convention");
  card(s, M, 1.45, 4.5, 4.6, "a1_today_card", C.background2);
  text(s, "Today", M + 0.3, 1.65, 3.9, 0.45, { fontSize: 20, bold: true, color: C.accent3, objectName: "a1_today_head" });
  text(s, [
    { text: "Ownership is only implied by the app's name", options: { bullet: true, breakLine: true } },
    { text: "No reliable link to the business application", options: { bullet: true, breakLine: true } },
    { text: "Hard to find who to ask, or what to clean up", options: { bullet: true, breakLine: true } },
    { text: "No record of who requested it, or when", options: { bullet: true } },
  ], M + 0.3, 2.2, 3.95, 3.6, { fontSize: 15, paraSpaceAfter: 10, objectName: "a1_today_list" });
  card(s, 5.4, 1.45, 7.33, 4.6, "a2_app_card", C.background1);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.4, y: 1.45, w: 7.33, h: 4.6, rectRadius: 0.12, fill: { color: C.background1 }, line: { color: C.accent2, width: 1 }, objectName: "a2_app_border" });
  await circleIcon(s, 5.7, 1.7, 0.7, "FaCube", "a2_app");
  text(s, [{ text: "APP-1234-P-ORDERS-orders-api", options: { bold: true, breakLine: true } }, { text: "App registration and enterprise app carry the same tags", options: { color: C.accent6, fontSize: 12 } }],
    6.6, 1.72, 5.9, 0.75, { fontSize: 17, color: C.text2, objectName: "a2_app_name" });
  const chips = [["appCatID:APP-1234", "business application"], ["team:group\\<group id>", "who may change it"], ["appEnv:P", "environment"], ["managedBy:entra-pp", "managed by the platform"],
    ["requestId:REQ-2610-…", "which request built it"], ["createdBy:alex@…", "who asked, and when"]];
  for (let i = 0; i < chips.length; i++) {
    const col = i % 2, row = Math.floor(i / 2), x = 5.7 + col * 3.5, y = 2.7 + row * 1.0, n = `a3_chip${i}`;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.25, h: 0.42, rectRadius: 0.2, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: n });
    text(s, chips[i][0], x + 0.15, y, 2.95, 0.42, { fontSize: 13, bold: true, color: C.background1, valign: "middle", objectName: n + "_t" });
    text(s, chips[i][1], x + 0.15, y + 0.46, 2.95, 0.35, { fontSize: 11, color: C.accent6, objectName: n + "_d" });
  }
  const wins = [["FaUserShield", "Ownership enforced"], ["FaHistory", "Full audit trail"], ["FaSearch", "Find and report"], ["FaCoins", "Chargeback-ready"]];
  for (let i = 0; i < wins.length; i++) {
    const x = M + i * 3.07, n = `a4_win${i}`;
    s.addImage({ data: await icon(wins[i][0], HEX.blue), x, y: 6.27, w: 0.35, h: 0.35, objectName: n + "_i", altText: "" });
    text(s, wins[i][1], x + 0.5, 6.25, 2.5, 0.4, { fontSize: 15, bold: true, color: C.text2, valign: "middle", objectName: n + "_t" });
  }
  s.addNotes("Contrast implied ownership (a name) with explicit tags the platform enforces. The team tag decides who can change the app (a person or a group); appCatID links it to the business application; the rest gives the audit trail and supports reporting and chargeback.");

  // 15 Future path ----------------------------------------------------------
  pres.addSection({ title: "Next" });
  s = content("Next", "Future path");
  const road = [
    ["FaTasks", "Complete the remaining flows", "Credentials (certificates, federated), decommission, periodic review"],
    ["FaFingerprint", "AppCatID on every identity", "Every identity the automation manages carries its business owner"],
    ["FaTicketAlt", "ServiceNow change, automatically", "A normal change is raised after manager approval"],
    ["FaComments", "Easier approvals in Teams", "Non-prod approvals posted to a Teams channel or chat"],
  ];
  for (let i = 0; i < road.length; i++) {
    const x = M + i * 3.07, n = `a${i + 1}_road${i}`;
    s.addShape(pres.shapes.CHEVRON, { x, y: 1.6, w: 2.95, h: 0.75, fill: { color: i === 0 ? C.accent1 : C.accent2 }, line: { color: i === 0 ? C.accent1 : C.accent2 }, objectName: n + "_chev" });
    text(s, `Phase ${i + 1}`, x + 0.45, 1.6, 2.1, 0.75, { fontSize: 15, bold: true, color: C.background1, valign: "middle", objectName: n + "_phase" });
    card(s, x, 2.65, 2.85, 3.3, n + "_card");
    await circleIcon(s, x + 0.3, 2.95, 0.75, road[i][0], n);
    text(s, road[i][1], x + 0.3, 3.85, 2.35, 0.8, { fontSize: 16, bold: true, color: C.text2, objectName: n + "_title" });
    text(s, road[i][2], x + 0.3, 4.7, 2.35, 1.15, { fontSize: 13, objectName: n + "_text" });
  }
  text(s, "Order and timing to agree together; phase 3 design on the next slide.", M, 6.25, 9, 0.35, { fontSize: 11, color: C.accent6, objectName: "road_note" });
  s.addNotes("One phase per click. Phase 1 completes the identity lifecycle; phase 2 extends AppCatID ownership to every identity the automation manages; phase 3 connects ServiceNow; phase 4 makes non-production approvals one tap in Teams.");

  // 16 ServiceNow design ----------------------------------------------------
  s = content("Next", "Phase 3 design: ServiceNow normal change after approval");
  picture(s, "future-sn-components.png", M, 1.3, W - 2 * M, 5.55, "sn_diagram", "Future ServiceNow integration: raise a normal change, run when the change reaches Implement, then close it");
  s.addNotes("Not built yet. After both approvals the flow raises a normal change; in gated mode the app registration is created only when the change reaches Implement, then the change is closed with the result. A record-only mode suits non-production. Editable source: diagrams/entra-powerplatform-future.drawio.");

  // 17 What helps -----------------------------------------------------------
  pres.addSection({ title: "Together" });
  s = content("Together", "What helps us deliver quickly");
  const pillars = [
    ["a1", "FaBrain", "Knowledge", ["Your platform standards and naming conventions", "How environments, DLP and licensing are set up", "Who to ask when something is blocked"]],
    ["a2", "FaHandsHelping", "Willingness to help and collaborate", ["Quick answers on environment questions", "Joint testing in QA before production", "Shared ownership of the outcome"]],
  ];
  for (let i = 0; i < pillars.length; i++) {
    const [p, ic, head, items] = pillars[i];
    const x = M + i * 6.15, n = `${p}_pillar${i}`;
    card(s, x, 1.7, 5.9, 3.9, n + "_card");
    await circleIcon(s, x + 0.35, 2.05, 1.0, ic, n);
    text(s, head, x + 1.6, 2.15, 4.0, 0.8, { fontSize: 22, bold: true, color: C.text2, valign: "middle", objectName: n + "_head" });
    text(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })), x + 0.4, 3.4, 5.2, 2.0,
      { fontSize: 16, paraSpaceAfter: 12, objectName: n + "_list" });
  }
  s.addNotes("Two things make the difference: knowledge of how your environment works, and the willingness to unblock us quickly. Ask for both explicitly.");

  // 18 51:49 model ----------------------------------------------------------
  s = content("Together", "Our working model: 51 : 49");
  s.addChart(pres.charts.DOUGHNUT, [{ name: "Credit", labels: ["Your team", "Our team"], values: [51, 49] }], {
    x: M, y: 1.4, w: 5.0, h: 4.9, holeSize: 62, chartColors: [HEX.blue, HEX.line], showLegend: false,
    showValue: false, showPercent: false, showLabel: false, dataBorder: { pt: 2, color: "FFFFFF" }, objectName: "model_chart",
  });
  text(s, [{ text: "51%", options: { bold: true, fontSize: 44, color: C.accent1, breakLine: true } }, { text: "of the credit to the team we work with", options: { fontSize: 13, color: C.accent6 } }],
    M + 1.35, 3.0, 2.3, 1.6, { align: "center", valign: "middle", objectName: "model_center" });
  const model = [
    ["FaGraduationCap", "We respect your knowledge", "You know the platform best; we build on it, not around it."],
    ["FaRoute", "We work the way your team works", "Your processes, tools and change rules come first."],
    ["FaBolt", "You unblock environment issues quickly", "Fast help when we hit a licence, DLP or access blocker."],
    ["FaTrophy", "You get 51% of the credit", "The delivery is presented as your team's success."],
  ];
  for (let i = 0; i < model.length; i++) {
    const y = 1.45 + i * 1.18, n = `a${i + 1}_model${i}`;
    await circleIcon(s, 6.1, y + 0.1, 0.75, model[i][0], n, i === 3 ? C.accent4 : C.accent1);
    text(s, model[i][1], 7.05, y, 5.7, 0.45, { fontSize: 18, bold: true, color: C.text2, objectName: n + "_head" });
    text(s, model[i][2], 7.05, y + 0.45, 5.7, 0.5, { fontSize: 14, objectName: n + "_text" });
  }
  s.addNotes("The 51:49 model: we bring the build effort; your team brings knowledge and fast unblocking; in return your team takes the larger share of the credit. Reveal the four points one by one and end on the credit.");

  // 19 Questions ------------------------------------------------------------
  s = pres.addSlide({ masterName: "Closing", sectionTitle: "Together" });
  s.addText("Questions", { placeholder: "title" });
  s.addText("Thank you", { placeholder: "body" });
  await circleIcon(s, (W - 1.2) / 2, 1.2, 1.2, "FaComments", "q");
  text(s, "Docs, diagrams and the importable solution: entra-powerplatform repository (docs/00-OVERVIEW.md)", M, 6.2, W - 2 * M, 0.4, { fontSize: 12, color: C.accent6, align: "center" });
  s.addNotes("Invite questions. Have the appendix ready: request sequence, ER-02 flowchart, request lifecycle and the security model.");

  // Appendix ----------------------------------------------------------------
  pres.addSection({ title: "Appendix" });
  const appendix = [
    ["sequence-approvals.png", "Appendix: submit and approve (ER-01)", "page 4"],
    ["sequence-create-app.png", "Appendix: creating an app registration (ER-02)", "page 5"],
    ["flow-er02.png", "Appendix: ER-02 Execute flowchart", "page 7"],
    ["lifecycle.png", "Appendix: request lifecycle", "page 10"],
    ["security.png", "Appendix: security and permissions", "page 12"],
  ];
  for (const [file, ttl, page] of appendix) {
    s = content("Appendix", ttl);
    picture(s, file, M, 1.3, W - 2 * M, 5.55, file.replace(".png", "_diagram"), ttl.replace("Appendix: ", ""));
    s.addNotes(`Editable source: diagrams/entra-powerplatform.drawio, ${page}. Open it in draw.io (desktop, web or the VS Code extension), edit, and export again as PNG.`);
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}
build().catch((e) => { console.error(e); process.exit(1); });
