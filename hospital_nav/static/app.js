// 医院陪诊楼内导航 - 前端逻辑
let state = null;
let selected = new Set(["registration","laboratory","imaging","pharmacy","exit"]);
let mode = "walk";
let plans = {};   // 三种模式的结果缓存

const $ = (s) => document.querySelector(s);
const SVGNS = "http://www.w3.org/2000/svg";
const MODE_LABEL = {walk:"少走路", queue:"少排队", accessible:"无障碍"};

const post = (url, body={}) =>
  fetch(url, {method:"POST", headers:{"Content-Type":"application/json"},
              body: JSON.stringify(body)}).then(r => r.json());

async function init(){
  state = await fetch("/api/state").then(r => r.json());
  renderControls();
  renderMap();
  await runPlan();
}

// ---------------- 控制面板 ----------------
function renderControls(){
  const startSel = $("#startSel");
  const entrances = state.nodes.filter(n => n.category === "entrance");
  startSel.innerHTML = entrances.map(n => `<option value="${n.id}">${n.label}</option>`).join("");

  const box = $("#destBox");
  box.innerHTML = state.categoryOrder.map((cat, i) => {
    const on = selected.has(cat) ? "on" : "";
    const q = categoryQueue(cat);
    const qTxt = q != null ? `当前约 ${q} 分钟起` : "";
    return `<div class="dest-item ${on}" data-cat="${cat}">
      <span class="ord">${i+1}</span><span>${state.categoryLabel[cat]}</span>
      <span class="q">${qTxt}</span></div>`;
  }).join("");
  box.querySelectorAll(".dest-item").forEach(el => el.onclick = () => {
    const c = el.dataset.cat;
    selected.has(c) ? selected.delete(c) : selected.add(c);
    renderControls();
  });

  document.querySelectorAll(".mode-btn").forEach(b => {
    b.classList.toggle("on", b.dataset.mode === mode);
    b.onclick = () => { mode = b.dataset.mode; renderControls(); switchResult(mode); };
  });
}

function categoryQueue(cat){
  const qs = state.nodes.filter(n => n.category === cat && n.queue != null)
                        .map(n => n.queue);
  return qs.length ? Math.min(...qs) : null;
}

// ---------------- SVG 地图 ----------------
function tx(x){ return (x + 65) * 5.2; }
function ty(y){ return (50 - y) * 5.2; }

function renderMap(){
  const W = 130 * 5.2, H = 100 * 5.2;
  const svg = document.createElementNS(SVGNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.id = "floorMap";

  // 房间区块
  state.rooms.forEach(r => {
    const g = el("g");
    g.appendChild(el("rect", {x:tx(r.x), y:ty(r.y+r.h), width:r.w*5.2, height:r.h*5.2,
      rx:8, fill:"#e6f2f1", stroke:"#bcd7d4", "stroke-width":1.5}));
    const t = el("text", {x:tx(r.x+r.w/2), y:ty(r.y+r.h)+20, "text-anchor":"middle",
      "font-size":14, fill:"#5b8a86", "font-weight":"600"});
    t.textContent = r.name;
    g.appendChild(t);
    svg.appendChild(g);
  });

  // 边：先画底图通道
  state.edges.forEach(e => svg.appendChild(edgeLine(e)));

  // 规划路线层（后画，在节点下）
  const routeLayer = el("g", {id:"routeLayer"});
  svg.appendChild(routeLayer);

  // 节点
  state.nodes.forEach(n => svg.appendChild(nodeMark(n)));
  $("#map").innerHTML = "";
  $("#map").appendChild(svg);
}

function edgeLine(e){
  const a = node(e.a), b = node(e.b);
  let attrs = {x1:tx(a.x), y1:ty(a.y), x2:tx(b.x), y2:ty(b.y),
    "stroke-width":7, "stroke-linecap":"round", fill:"none"};
  if (e.type === "stairs"){
    attrs.stroke = "#fca5a5"; attrs["stroke-dasharray"] = "3 7";
  } else if (e.type === "ramp"){
    attrs.stroke = "#93c5fd"; attrs["stroke-dasharray"] = "9 5";
  } else {
    attrs.stroke = "#cbd5e1";
  }
  return el("line", attrs);
}

function nodeMark(n){
  const g = el("g", {"class":"nmark", "data-id":n.id});
  const cx = tx(n.x), cy = ty(n.y);
  const isService = n.queue != null;
  const isGate = ["entrance","exit"].includes(n.category) || n.categoryAlt === "exit";

  g.appendChild(el("circle", {cx, cy, r: isGate ? 9 : isService ? 7 : 4.5,
    fill: isGate ? "#0f766e" : isService ? "#f59e0b" : "#64748b",
    stroke:"#fff", "stroke-width":2}));

  if (isService || isGate || ["entrance_hall","lab_hall","img_hall","reg_hall","phar_hall"]
        .includes(n.id)){
    const t = el("text", {x:cx, y:cy - 12, "text-anchor":"middle",
      "font-size":11.5, fill:"#334155", "font-weight":"600",
      paintOrder:"stroke", stroke:"#f8fbfb", "stroke-width":3.5,
      "stroke-linejoin":"round"});
    t.textContent = n.label;
    g.appendChild(t);
  }
  if (isService){
    const q = el("text", {x:cx, y:cy + 21, "text-anchor":"middle",
      "font-size":10, fill:"#b45309"});
    q.textContent = `排队约${n.queue}分`;
    g.appendChild(q);
  }
  if (!n.accessible && isService){
    const w = el("text", {x:cx+10, y:cy-6, "font-size":11, fill:"#dc2626"});
    w.textContent = "⚠"; g.appendChild(w);
  }
  return g;
}

function drawRoute(result){
  const layer = $("#routeLayer");
  layer.innerHTML = "";
  if (!result) return;
  const used = new Set(result.edgePath.map(p => p.join("|")));
  const color = result.mode === "walk" ? "#0d9488"
              : result.mode === "queue" ? "#d97706" : "#2563eb";

  result.edgePath.forEach(([a,b]) => {
    const A = node(a), B = node(b);
    layer.appendChild(el("line", {x1:tx(A.x), y1:ty(A.y), x2:tx(B.x), y2:ty(B.y),
      "stroke-width":6, "stroke-linecap":"round", fill:"none",
      stroke:color, "stroke-opacity":.85}));
  });

  // 站点序号徽章
  let ord = 0;
  [result.start, ...result.stops].forEach((id, i) => {
    const n = node(id);
    const g = el("g");
    g.appendChild(el("circle", {cx:tx(n.x), cy:ty(n.y), r:11, fill:"#fff",
      stroke:color, "stroke-width":3}));
    const t = el("text", {x:tx(n.x), y:ty(n.y)+4.5, "text-anchor":"middle",
      "font-size":12, "font-weight":"700", fill:color});
    t.textContent = i === 0 ? "起" : String(i);
    g.appendChild(t);
    layer.appendChild(g);
  });
}

// ---------------- 规划 ----------------
async function runPlan(){
  const start = $("#startSel").value || "south_gate";
  const cats = state.categoryOrder.filter(c => selected.has(c));
  plans = {};
  if (!cats.length){
    $("#stepList").innerHTML = `<li class="empty">请至少选择一个目的地</li>`;
    drawRoute(null);
    return;
  }
  for (const m of ["walk","queue","accessible"]){
    plans[m] = await post("/api/plan", {start, categories:cats, mode:m});
  }
  switchResult(mode);
  renderCompare();
}

function switchResult(m){
  mode = m;
  const r = plans[m];
  if (!r || r.error) return;
  drawRoute(r);
  renderSteps(r);
  renderSummary(r);
  document.querySelectorAll(".mode-btn")
    .forEach(b => b.classList.toggle("on", b.dataset.mode === m));
}

function renderSteps(r){
  $("#stepList").innerHTML = r.steps.map(s =>
    `<li class="step ${s.kind}"><span class="dot"></span><p>${s.text}</p></li>`
  ).join("");
}

function renderSummary(r){
  const s = r.stats;
  $("#summaryMode").textContent = MODE_LABEL[r.mode] + "路线";
  $("#totalTime").innerHTML = `约 ${s.total_min} <small>分钟</small>`;
  $("#mDist").textContent = `${s.distance_m} m`;
  $("#mWalk").textContent = `${s.walk_min} 分`;
  $("#mQueue").textContent = `${s.queue_min} 分`;
  $("#mSvc").textContent = `${s.service_min} 分`;
  document.querySelector(".summary-label")
    .style.background = r.mode==="walk" ? "#ccfbf1" :
      r.mode==="queue" ? "#fef3c7" : "#dbeafe";
  document.querySelector(".summary-label")
    .style.color = r.mode==="walk" ? "#0f766e" :
      r.mode==="queue" ? "#b45309" : "#1d4ed8";
}

function renderCompare(){
  $("#compareBox").innerHTML = ["walk","queue","accessible"].map(m => {
    const r = plans[m];
    if (!r || r.error) return "";
    return `<div class="chip ${m===mode?'active':''}" data-m="${m}">
      ${MODE_LABEL[m]}<b>${r.stats.total_min} 分钟</b></div>`;
  }).join("");
  $("#compareBox").querySelectorAll(".chip").forEach(c =>
    c.onclick = () => switchResult(c.dataset.m));
}

// ---------------- 工具 ----------------
function node(id){ return state.nodes.find(n => n.id === id); }
function el(name, attrs={}){
  const e = document.createElementNS(SVGNS, name);
  Object.entries(attrs).forEach(([k,v]) => e.setAttribute(k, v));
  return e;
}

// 事件
$("#planBtn").onclick = runPlan;
$("#startSel").onchange = runPlan;
$("#checkAll").onclick = (e) => { e.preventDefault();
  state.categoryOrder.forEach(c => selected.add(c)); renderControls(); };
$("#clearAll").onclick = (e) => { e.preventDefault();
  selected.clear(); renderControls(); };
$("#refreshBtn").onclick = async () => {
  state = await post("/api/refresh", {seed: Date.now() % 100000});
  renderControls();
  await runPlan();
};

init();
