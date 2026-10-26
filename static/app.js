const $ = (s) => document.querySelector(s);
let sessionId = localStorage.getItem("campus_sid") || "";
const CHIPS = ["明天有什么课？", "下节课在哪，从建工楼怎么过去？", "周一3-4节建工楼有空教室吗", "从金菊园到南楼怎么走",
  "推荐几个AI和编程的活动", "宿舍水龙头坏了一直漏水", "校园卡丢了怎么办？", "提醒我明天下午2点去绿岛讲堂听讲座", "图书馆在哪？", "坐公交怎么来学校？", "西山会所食堂几点开饭"];

function esc(s) { return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function md(text) {
  let h = esc(text).replace(/&lt;small&gt;/g, "<small>").replace(/&lt;\/small&gt;/g, "</small>");
  h = h.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  const lines = h.split("\n"); let out = "", inList = false;
  for (const ln of lines) {
    const m = ln.match(/^\s*-\s+(.*)/);
    if (m) { if (!inList) { out += "<ul>"; inList = true; } out += `<li>${m[1]}</li>`; continue; }
    if (inList) { out += "</ul>"; inList = false; }
    out += ln ? ln + "<br>" : "<br>";
  }
  if (inList) out += "</ul>";
  return out.replace(/(<br>)+$/, "");
}

function addMsg(role, text, steps) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = role === "user" ? esc(text) : md(text);
  if (steps && steps.length) {
    const marks = steps.filter((s) => s.type === "tool_result" && s.result && s.result.地图标注).flatMap((s) => s.result.地图标注);
    if (marks.length) bubble.appendChild(renderMap(marks));
    bubble.appendChild(renderTrace(steps));
  }
  if (role === "bot") { const av = document.createElement("div"); av.className = "avatar"; av.textContent = "城"; wrap.appendChild(av); }
  wrap.appendChild(bubble);
  $("#messages").appendChild(wrap);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return wrap;
}

const MAP_W = 1992, MAP_H = 1377;  // 官方鸟瞰图原始像素尺寸
function renderMap(marks) {
  const box = document.createElement("div");
  box.className = "mapcard";
  const seen = new Set();
  let html = '<div class="mapwrap"><img src="/static/campus_map.jpg" alt="沈阳城市学院官方鸟瞰图">';
  for (const m of marks) {
    if (seen.has(m.name)) continue; seen.add(m.name);
    const x = (m.px[0] / MAP_W * 100).toFixed(2), y = (m.px[1] / MAP_H * 100).toFixed(2);
    html += `<span class="pin ${m.role === "起点" ? "start" : m.role === "途经" ? "via" : "end"}" style="left:${x}%;top:${y}%"><i></i><em>${esc(m.role)}·${esc(m.name)}</em></span>`;
  }
  html += '</div><div class="mapnote">底图：学校官方鸟瞰图（点击放大）；标注位置按图例编号定位</div>';
  box.innerHTML = html;
  box.querySelector("img").addEventListener("click", () => window.open("/static/campus_map.jpg", "_blank"));
  return box;
}

function renderTrace(steps) {
  const d = document.createElement("details");
  d.className = "trace";
  const calls = steps.filter((s) => s.type === "tool_call").length;
  d.innerHTML = `<summary>🧠 思考与工具调用（规划 ${steps.filter((s) => s.type === "plan").length} 步 · 调用工具 ${calls} 次）</summary>`;
  for (const s of steps) {
    const div = document.createElement("div");
    div.className = `step ${s.type}`;
    if (s.type === "plan") div.innerHTML = `<span class="tag">规划</span>${esc(s.content)}`;
    else if (s.type === "error") div.innerHTML = `<span class="tag">异常</span>${esc(s.content)}`;
    else if (s.type === "tool_call") div.innerHTML = `<span class="tag">调用</span><b>${esc(s.label)}</b> <code>${esc(s.name)}</code><pre>${esc(JSON.stringify(s.args, null, 2))}</pre>`;
    else if (s.type === "tool_result") div.innerHTML = `<span class="tag">结果</span>${esc(s.label)}<pre>${esc(JSON.stringify(s.result, null, 2))}</pre>`;
    d.appendChild(div);
  }
  return d;
}

async function send(text) {
  text = text.trim();
  if (!text) return;
  addMsg("user", text);
  $("#input").value = ""; autoSize();
  $("#sendBtn").disabled = true;
  const typing = addMsg("bot", "");
  typing.querySelector(".bubble").innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, session_id: sessionId || null }) });
    const data = await r.json();
    typing.remove();
    if (!r.ok) throw new Error(data.detail ? JSON.stringify(data.detail) : r.status);
    sessionId = data.session_id; localStorage.setItem("campus_sid", sessionId);
    addMsg("bot", data.reply, data.steps);
    setBadge(data.mode, data.mode_label);
    loadSide();
  } catch (e) {
    typing.remove();
    addMsg("bot", "抱歉，服务暂时不可用：" + e.message);
  } finally { $("#sendBtn").disabled = false; $("#input").focus(); }
}

function setBadge(mode, label) {
  const b = $("#modeBadge");
  b.className = "badge " + (mode === "llm" ? "llm" : "mock");
  b.textContent = (mode === "llm" ? "🤖 " : "🧩 ") + label;
  b.title = mode === "llm" ? "由大模型进行推理、规划与工具调用" : "未配置大模型密钥：使用内置规则规划器，调用同一套工具";
}

async function loadStatus() {
  const s = await (await fetch("/api/status")).json();
  setBadge(s.mode, s.mode_label + (s.model ? " · " + s.model : ""));
  $("#todayLabel").textContent = `${s.today} · 第${s.week}周`;
  $("#toolList").innerHTML = s.tools.map((t) => `<span title="${esc(t.description)}">${esc(t.label)}</span>`).join("");
}

async function loadSide() {
  const d = await (await fetch(`/api/sidebar/${sessionId || "anonymous"}`)).json();
  const cs = d.today.课程 || [];
  $("#todayCourses").innerHTML = cs.length ? cs.map((c) => `<div class="row">${c.时间} <b>${esc(c.课程)}</b><br><small>${esc(c.教室)}</small></div>`).join("") : "今天没有课 🎉";
  const rs = d.reminders.待办 || [];
  $("#myReminders").innerHTML = rs.length ? rs.map((x) => `<div class="row">${esc(x.内容)}<br><small>${esc(x.时间)}</small></div>`).join("") : "暂无";
  const ts = d.tickets.工单 || [];
  $("#myTickets").innerHTML = ts.length ? ts.map((t) => `<div class="row">${esc(t.宿舍)} · ${esc(t.类型)} · <b>${esc(t.状态)}</b><br><small>${esc(t.工单号)}</small></div>`).join("") : "暂无";
}

function autoSize() { const t = $("#input"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 120) + "px"; }

$("#form").addEventListener("submit", (e) => { e.preventDefault(); send($("#input").value); });
$("#input").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($("#input").value); } });
$("#input").addEventListener("input", autoSize);
$("#sideToggle").addEventListener("click", () => $("#side").classList.toggle("open"));
$("#resetBtn").addEventListener("click", async () => {
  if (sessionId) await fetch("/api/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }) });
  sessionId = ""; localStorage.removeItem("campus_sid"); $("#messages").innerHTML = ""; welcome(); loadSide();
});
$("#chips").innerHTML = CHIPS.map((c) => `<button class="chip" type="button">${esc(c)}</button>`).join("");
$("#chips").addEventListener("click", (e) => { if (e.target.classList.contains("chip")) send(e.target.textContent); });

function welcome() {
  addMsg("bot", "你好，我是**城院小助手** 👋 你的校园服务智能体。\n我可以帮你：\n- 📅 查课表、下节课、空教室\n- 🧭 校园导航（官方地图标注 + 步行估算）\n- 🎉 活动聚合与兴趣推荐\n- 🔧 宿舍报修与进度查询\n- 📚 办事指南问答（图书馆、选课、校园卡…）\n- ⏰ 提醒待办、食堂与交通出行\n\n点击下方快捷问题试试，或展开回答下方的「思考与工具调用」查看我的推理过程。");
}

async function restore() {
  if (!sessionId) return welcome();
  const h = await (await fetch(`/api/history/${sessionId}`)).json();
  if (!h.messages.length) return welcome();
  for (const m of h.messages) addMsg(m.role === "user" ? "user" : "bot", m.content);
}

loadStatus(); restore(); loadSide();
