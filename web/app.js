// Интерфейс демо. Если страница открыта с сервера kompas.api — вопросы идут в /api/ask (там может работать LLM),
// иначе (GitHub Pages) — в браузерное ядро engine.js. Персональные данные остаются в браузере.
const I18N = {
  ru: { tagline: "ИИ-навигатор первых 30 дней в России для иностранных студентов", planTitle: "Мой план на первые 30 дней",
    country: "Страна гражданства", entry: "Дата въезда (необязательно)",
    privacy: "Дата въезда хранится только в вашем браузере и не передаётся третьим лицам. Без даты план будет списком шагов по порядку.",
    build: "Построить план", legal: "срок по закону", rec: "рекомендуем", noDate: "сделать по порядку", due: "до",
    ask: "Спросить", source: "Источник",
    bankText: "Шаг «Банковская карта»: в пилоте банк-партнёр готовит список документов и записывает в отделение рядом с вузом.",
    bankBtn: "Записаться в отделение", bankDone: "Демо: заявка сформирована. В пилоте — запись через API банка.",
    chatTitle: "Спросите на своём языке", send: "→",
    chatNote: "Помощник отвечает только по проверенной базе и всегда даёт ссылку. Если ответа нет — передаёт вопрос человеку. Номера паспорта и телефона маскируются.",
    hello: "Здравствуйте! Я Компас. Спросите про учёт, медосвидетельствование, SIM-карту, банковскую карту или переводы из дома.",
    handoff: "передано человеку", refused: "запрещённая тема", masked: "скрыто",
    chips: ["Кто ставит меня на миграционный учёт?", "Перевод от родителей заблокировали", "Какие документы нужны для карты?", "Мне звонят из банка и просят код"],
    footer: "Демо команды «Крейсер», Академия финтеха ВТБ 2026. Не официальный продукт ВТБ. Не является юридической консультацией: сроки сверяйте с международным отделом вуза." },
  en: { tagline: "AI navigator for international students' first 30 days in Russia", planTitle: "My first-30-days plan",
    country: "Citizenship", entry: "Entry date (optional)",
    privacy: "Your entry date stays in your browser and is never shared with third parties. Without a date you get an ordered checklist.",
    build: "Build my plan", legal: "legal deadline", rec: "recommended", noDate: "do in this order", due: "by",
    ask: "Ask", source: "Source",
    bankText: "Bank card step: in the pilot the partner bank prepares your document list and books a branch visit near campus.",
    bankBtn: "Book a branch visit", bankDone: "Demo: request created. In the pilot this goes through the bank API.",
    chatTitle: "Ask in your language", send: "→",
    chatNote: "Answers come only from a verified knowledge base, always with a source. If there is no answer, a human takes over. Passport and phone numbers are masked.",
    hello: "Hi! I'm Kompas. Ask me about migration registration, the medical exam, SIM cards, bank cards or money transfers from home.",
    handoff: "forwarded to a human", refused: "restricted topic", masked: "masked",
    chips: ["Who does my migration registration?", "My parents' transfer was blocked", "What documents do I need for a bank card?", "Someone called from the bank asking for a code"],
    footer: "Demo by team Kreiser, VTB Fintech Academy 2026. Not an official VTB product. Not legal advice: confirm deadlines with your university international office." },
  zh: { tagline: "外国留学生在俄罗斯头30天的AI导航", planTitle: "我的头30天计划",
    country: "国籍", entry: "入境日期（可选）",
    privacy: "入境日期只保存在您的浏览器中，绝不提供给第三方。不填日期时，计划将按步骤顺序列出。",
    build: "生成计划", legal: "法定期限", rec: "建议", noDate: "按顺序完成", due: "截止",
    ask: "提问", source: "来源",
    bankText: "银行卡步骤：试点阶段由合作银行为您准备材料清单，并预约学校附近的网点。",
    bankBtn: "预约网点", bankDone: "演示：申请已生成。试点中将通过银行API完成预约。",
    chatTitle: "用您的语言提问", send: "→",
    chatNote: "助手只根据经过核实的知识库回答，并始终附上来源。没有答案时会转交人工。护照号和电话号码会被隐藏。",
    hello: "您好！我是Kompas。可以问我移民登记、体检、手机卡、银行卡或从家里汇款的问题。",
    handoff: "已转人工", refused: "受限话题", masked: "已隐藏",
    chips: ["谁给我办理落地登记？", "父母的转账被冻结了", "开银行卡需要什么材料？", "有人冒充银行打电话要验证码"],
    footer: "Kreiser团队演示，VTB金融科技学院2026。非VTB官方产品。非法律咨询：请向学校国际处核实期限。" },
};

let lang = "ru";
let useApi = false;
const $ = (s) => document.querySelector(s);
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } },
                set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

function applyLang(l) {
  lang = l; store.set("kompas.lang", l);
  document.documentElement.lang = l === "zh" ? "zh-CN" : l;
  document.querySelectorAll("[data-i]").forEach((el) => { el.textContent = I18N[l][el.dataset.i]; });
  document.querySelectorAll(".langs button").forEach((b) => b.classList.toggle("on", b.dataset.l === l));
  $("#q").placeholder = I18N[l].chips[0];
  $("#chips").innerHTML = "";
  I18N[l].chips.forEach((c) => { const b = document.createElement("button"); b.className = "chip"; b.textContent = c; b.onclick = () => send(c); $("#chips").append(b); });
  $("#chat").innerHTML = ""; addBot({ text: I18N[l].hello, sources: [] });
  if ($("#steps").children.length) renderPlan();
}

function fmt(d) { return new Date(d + "T12:00:00").toLocaleDateString(lang === "zh" ? "zh-CN" : lang, { day: "numeric", month: "long" }); }

function renderPlan() {
  const entry = $("#entry").value || null;
  const steps = Kompas.buildPlan($("#country").value, entry, lang);
  const t = I18N[lang];
  const done = JSON.parse(store.get("kompas.done") || "[]");
  $("#steps").innerHTML = steps.map((s) => `
    <li class="step ${done.includes(s.id) ? "done" : ""}" data-id="${s.id}">
      <input type="checkbox" ${done.includes(s.id) ? "checked" : ""} aria-label="done">
      <div class="t">${esc(s.title)}</div>
      <div class="meta"><span class="pill ${s.kind === "legal" ? "legal" : "rec"}">${s.kind === "legal" ? t.legal : t.rec}</span>
        <span class="due">${s.due ? `${t.due} ${fmt(s.due)}` : t.noDate}</span></div>
      <div class="hint">${esc(s.hint)}</div>
      <div class="links"><a data-ask="${esc(s.title)}">${t.ask}</a><a href="${esc(s.source)}" target="_blank" rel="noopener">${t.source}</a></div>
    </li>`).join("");
  $("#steps").querySelectorAll(".step input").forEach((cb) => cb.onchange = () => {
    const id = cb.closest(".step").dataset.id;
    const d = new Set(JSON.parse(store.get("kompas.done") || "[]"));
    cb.checked ? d.add(id) : d.delete(id);
    store.set("kompas.done", JSON.stringify([...d])); cb.closest(".step").classList.toggle("done", cb.checked);
  });
  $("#steps").querySelectorAll("[data-ask]").forEach((a) => a.onclick = () => send(a.dataset.ask));
  $("#bank").hidden = false;
}

function addMe(text) { const d = document.createElement("div"); d.className = "msg me"; d.textContent = text; $("#chat").append(d); }
function addBot(a) {
  const t = I18N[lang];
  const d = document.createElement("div");
  d.className = "msg bot" + (a.handoff || a.refused ? " warn" : "");
  d.innerHTML = esc(a.text) +
    (a.sources && a.sources.length ? `<span class="src">${t.source}: <a href="${esc(a.sources[0])}" target="_blank" rel="noopener">${esc(a.sources[0])}</a></span>` : "") +
    (a.handoff ? `<span class="tag">● ${t.handoff}</span>` : "") +
    (a.refused ? `<span class="tag">● ${t.refused}</span>` : "") +
    (a.pii_masked && a.pii_masked.length ? `<span class="tag">🔒 ${t.masked}: ${a.pii_masked.join(", ")}</span>` : "");
  $("#chat").append(d); $("#chat").scrollTop = 1e6;
}

async function send(q) {
  q = q.trim(); if (!q) return;
  addMe(q); $("#q").value = "";
  let a;
  if (useApi) {
    try { a = await (await fetch("api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) })).json(); }
    catch { a = Kompas.ask(q); }
  } else a = Kompas.ask(q);
  addBot(a);
}

document.querySelectorAll(".langs button").forEach((b) => b.onclick = () => applyLang(b.dataset.l));
$("#build").onclick = renderPlan;
$("#askForm").onsubmit = (e) => { e.preventDefault(); send($("#q").value); };
$("#bankBtn").onclick = () => addBot({ text: I18N[lang].bankDone, sources: [] });
if (location.protocol.startsWith("http")) fetch("api/health").then((r) => r.ok && r.json()).then((j) => { useApi = !!(j && j.status === "ok"); }).catch(() => {});
applyLang(store.get("kompas.lang") || (navigator.language || "ru").slice(0, 2).replace(/^(?!ru|en|zh).*/, "ru"));
