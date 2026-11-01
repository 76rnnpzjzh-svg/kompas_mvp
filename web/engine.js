// Браузерная версия ядра Компаса — те же алгоритмы, что в kompas/*.py, и те же данные (data.js).
// Позволяет показывать демо на GitHub Pages без сервера и без ключей.
(function () {
  const D = window.KOMPAS_DATA;
  const LANGS = ["ru", "en", "zh"];
  const CJK = /[一-鿿]/;

  // ---------- план ----------
  function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
  function addBusinessDays(d, n) {
    let x = new Date(d), added = 0;
    while (added < n) { x.setDate(x.getDate() + 1); const w = x.getDay(); if (w !== 0 && w !== 6) added++; }
    return x;
  }
  const iso = (d) => d.toISOString().slice(0, 10);

  function buildPlan(country, entryDate, lang) {
    if (!LANGS.includes(lang)) lang = "en";
    country = (country || "").toUpperCase();
    let group = null;
    for (const [g, m] of Object.entries(D.rules.groups || {})) if (m.includes(country)) group = g;
    const steps = [];
    for (const r of D.rules.steps) {
      if (country && (r.skip_for || []).includes(country)) continue;
      const byGroup = group && r.days_by_group && r.days_by_group[group] !== undefined;
      const days = byGroup ? r.days_by_group[group] : r.days;
      let due = null;
      if (entryDate) {
        const start = new Date(entryDate + "T12:00:00");
        due = iso(r.business_days && !byGroup ? addBusinessDays(start, days) : addDays(start, days));
      }
      steps.push({ id: r.id, order: r.order, title: r.title[lang], hint: r.hint[lang], kind: r.kind,
                   days, due, source: r.source, kb: r.kb });
    }
    steps.sort((a, b) => entryDate ? (a.due.localeCompare(b.due) || a.order - b.order) : a.order - b.order);
    return steps;
  }

  // ---------- поиск ----------
  const norm = (t) => t.toLowerCase().replace(/ё/g, "е").replace(/[^\p{L}\p{N}_一-鿿]+/gu, " ");
  function ngrams(text) {
    const g = [];
    for (const w of norm(text).split(/\s+/).filter(Boolean)) {
      if (CJK.test(w)) { if (w.length < 2) g.push(w); for (let i = 0; i < w.length - 1; i++) g.push(w.slice(i, i + 2)); }
      else { const p = ` ${w} `; for (let i = 0; i < Math.max(1, p.length - 3); i++) g.push(p.slice(i, i + 4)); }
    }
    return g;
  }
  const count = (arr) => arr.reduce((m, t) => (m.set(t, (m.get(t) || 0) + 1), m), new Map());
  const cards = D.kb.cards;
  const docs = cards.map((c) => count(ngrams([c.keywords, c.keywords, c.keywords, c.ru, c.en, c.zh].join(" "))));
  const lens = docs.map((d) => [...d.values()].reduce((a, b) => a + b, 0));
  const avg = lens.reduce((a, b) => a + b, 0) / lens.length;
  const df = new Map();
  docs.forEach((d) => d.forEach((_, t) => df.set(t, (df.get(t) || 0) + 1)));
  const idf = new Map([...df].map(([t, f]) => [t, Math.log(1 + (docs.length - f + 0.5) / (f + 0.5))]));
  const K1 = 1.5, B = 0.75;

  function search(query, k = 3) {
    const q = count(ngrams(query));
    const qn = [...q.values()].reduce((a, b) => a + b, 0);
    if (!qn) return [];
    return cards.map((card, i) => {
      let s = 0;
      for (const t of q.keys()) {
        const tf = docs[i].get(t);
        if (tf) s += idf.get(t) * tf * (K1 + 1) / (tf + K1 * (1 - B + B * lens[i] / avg));
      }
      return { card, score: s / Math.sqrt(qn) };
    }).sort((a, b) => b.score - a.score).slice(0, k);
  }

  function keywordMatch(query, card) {
    const q = norm(query), words = q.split(/\s+/).filter((w) => w.length >= 3);
    for (let kw of card.keywords.split(/\s+/)) {
      kw = norm(kw).trim();
      if (!kw) continue;
      if (CJK.test(kw)) { if (q.includes(kw)) return true; }
      else { const stem = kw.slice(0, 5); if (words.some((w) => w.startsWith(stem) || (w.length >= 4 && kw.startsWith(w)))) return true; }
    }
    return false;
  }

  // ---------- ограничители ----------
  const PII = [
    ["CARD", /\b(?:\d[ -]?){15,18}\d\b/g],
    ["EMAIL", /\b[\w.+-]+@[\w-]+\.[\w.]+\b/g],
    ["PASSPORT", /\b(?:[A-Z]{1,2}\d{7,8}|\d{2}\s?\d{2}\s?\d{6})\b/g],
    ["PHONE", /(?<!\w)\+?\d[\d\s()-]{9,15}\d\b/g],
  ];
  const FORBIDDEN = /обойти|обход|обхитр|дробить|раздробить|обнал|не попасть под|чтобы банк не|скрыть от банка|фиктивн|bypass|evade|avoid (?:the )?(?:check|control|aml)|split (?:the )?transfer|structur(?:e|ing)|hide from (?:the )?bank|绕过|规避|拆分转账|逃避|隐瞒银行/i;
  const REFUSAL = {
    ru: "Я не подсказываю способы обойти проверки банка или валютный контроль: это нарушает закон и может привести к блокировке счёта. Могу объяснить, почему перевод задержали, и какие документы помогут пройти проверку законно.",
    en: "I can't help with bypassing bank checks or currency control: it breaks the law and can get your account blocked. I can explain why a transfer was delayed and which documents help you pass the check legally.",
    zh: "我无法提供规避银行审查或外汇管制的方法：这违反法律，并可能导致账户被冻结。我可以解释汇款被延迟的原因，以及哪些文件能帮助您合法通过审查。",
  };
  const HANDOFF = {
    ru: "В проверенной базе пока нет точного ответа. Передаю вопрос сотруднику международного отдела вуза — ответ придёт сюда же.",
    en: "There is no verified answer in my knowledge base yet. I'm forwarding your question to the university international office — the reply will come here.",
    zh: "知识库中暂无经过核实的答案。我会将您的问题转交给大学国际处的工作人员——回复将发送到这里。",
  };

  function maskPII(text) {
    const found = [];
    for (const [label, rx] of PII) { if (text.match(rx)) { found.push(label); text = text.replace(rx, `[${label}]`); } }
    return { text, found };
  }
  function detectLang(t) { return CJK.test(t) ? "zh" : /[а-яё]/i.test(t) ? "ru" : "en"; }

  function ask(question, lang) {
    lang = lang || detectLang(question);
    const { text: masked, found } = maskPII(question);
    if (FORBIDDEN.test(masked)) return { text: REFUSAL[lang], lang, refused: true, sources: [], pii_masked: found, mode: "guard" };
    const hits = search(masked).filter((h) => h.score >= 0.8 && keywordMatch(masked, h.card));
    if (!hits.length) return { text: HANDOFF[lang], lang, handoff: true, sources: [], pii_masked: found, mode: "handoff" };
    const c = hits[0].card;
    return { text: c[lang], lang, card_id: c.id, sources: [c.source], pii_masked: found, mode: "extractive" };
  }

  window.Kompas = { buildPlan, ask, detectLang, search };
})();
