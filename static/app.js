/* Farkora — tek sayfalık arayüz (hash yönlendirme, framework yok) */

// ===================================================================
// Yardımcılar
// ===================================================================

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const page = $("#page");
let pollTimer = null;

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
  clipboard: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/><path d="M4 19.5V22h16"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  check: '<path d="m9 11 3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  bot: '<rect x="3" y="8" width="18" height="12" rx="2"/><path d="M12 8V4M8 4h8"/><path d="M9 14h.01M15 14h.01"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  print: '<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  phone: '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/>',
  sparkles: '<path d="M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z"/><path d="M19 17v4M17 19h4"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
};

// ----- Açık / koyu tema -----
function isDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
function renderThemeButtons() {
  document.querySelectorAll(".theme-btn").forEach((b) => {
    b.innerHTML = icon(isDark() ? "sun" : "moon");
    b.title = isDark() ? "Açık temaya geç" : "Koyu temaya geç";
  });
}
document.addEventListener("click", (e) => {
  if (!e.target.closest(".theme-btn")) return;
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("farkora-tema", next); } catch (err) { /* depolama kapalı olabilir */ }
  renderThemeButtons();
});
const icon = (name, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const bullets = (items) => (items || []).length
  ? `<ul class="bullets">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : `<p class="muted">—</p>`;
const fmtDate = (iso, time = true) => {
  if (!iso) return "—";
  const d = new Date(iso);
  const day = d.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
  return time ? `${day}, ${d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}` : day;
};
const fmtSec = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const initials = (n) => n.replace(/\(.*?\)/g, "").trim().split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
const empty = (ic, title, text = "", action = "") =>
  `<div class="empty">${icon(ic, "empty-ic")}<h3>${title}</h3>${text ? `<p>${text}</p>` : ""}${action}</div>`;

let ME = null; // oturum açmış kullanıcı

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    ME = null;
    showAuth();
    throw new Error("Oturumunuz sona erdi, lütfen tekrar giriş yapın.");
  }
  if (!res.ok) throw new Error(data.detail || `Hata (${res.status})`);
  return data;
}
const sendJSON = (path, body, method = "POST") =>
  api(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function toast(msg, kind = "ok") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = `toast toast-${kind}`;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 3500);
}
function stopPolling() { clearInterval(pollTimer); pollTimer = null; }
function poll(fn, ms = 2500) { stopPolling(); pollTimer = setInterval(fn, ms); }

const CLIENT_TYPE = { bireysel: "Bireysel", yonetici: "Yönetici" };
const ORG_TYPE = { sirket: "Şirket", kamu: "Kamu kurumu", sosyal_birim: "Sosyal hizmet birimi", universite: "Üniversite", stk: "STK" };
const FOCUS = ["Bireysel gelişim", "İlişkiler", "Kurumsal gelişim", "Liderlik"];
const STATUS = {
  bekliyor: ["Sırada", "wait"], transkript: ["Analiz ediliyor", "wait"], konusmaci_ayrimi: ["Analiz ediliyor", "wait"],
  rapor: ["Analiz ediliyor", "wait"], icf: ["Analiz ediliyor", "wait"], gorsel: ["Analiz ediliyor", "wait"], analiz: ["Analiz ediliyor", "wait"],
  kaynak_arama: ["Hazırlanıyor", "wait"], icerik_uretimi: ["Hazırlanıyor", "wait"], tamamlandi: ["Hazır", "ok"], hata: ["Hata", "err"],
};
const badge = (s) => { const [l, k] = STATUS[s] || [s, "wait"]; return `<span class="badge badge-${k}">${l}</span>`; };
const done = (s) => ["tamamlandi", "hata"].includes(s);

function scoreClass(v) { return v == null ? "" : v >= 4 ? "good" : v >= 3 ? "mid" : "low"; }

// ===================================================================
// İskelet: menü, üst çubuk, yönlendirme
// ===================================================================

const NAV = {
  admin: [["#/panel", "home", "Genel Panel"], ["#/danisanlar", "users", "Danışanlar"], ["#/kurumlar", "building", "Kurumlar & Birimler"],
    ["#/ajanlar", "bot", "Yapay Zekâ Ajanları"], ["#/kullanicilar", "shield", "Kullanıcılar"], ["#/kapsam", "clipboard", "Proje Kapsamı"]],
  koc: [["#/panel", "home", "Genel Panel"], ["#/danisanlar", "users", "Danışanlarım"], ["#/kurumlar", "building", "Kurumlar & Birimler"],
    ["#/ajanlar", "bot", "Yapay Zekâ Ajanları"], ["#/kapsam", "clipboard", "Proje Kapsamı"]],
  danisan: [["#/gelisim", "trend", "Gelişimim"]],
  kurum: [["#/kurum-panel", "building", "Kurum Paneli"]],
  bireysel: [["#/gelisim", "trend", "Gelişimim"], ["#/asistan", "message", "Asistanım"]],  // koçsuz mod
};
const HOME = { admin: "#/panel", koc: "#/panel", danisan: "#/gelisim", kurum: "#/kurum-panel" };
// Hangi rotaya hangi roller girebilir
const ROUTE_ROLES = { gelisim: ["danisan"], "kurum-panel": ["kurum"], kullanicilar: ["admin"], egitim: ["admin", "koc", "danisan"],
  basla: ["danisan"], asistan: ["danisan"] };

function renderNav() {
  const hash = location.hash || HOME[ME.role];
  const section = { danisan: "#/danisanlar", seans: "#/danisanlar", portal: "#/danisanlar", kurum: "#/kurumlar",
    egitim: ME.role === "danisan" ? "#/gelisim" : "#/danisanlar" }[hash.split("/")[1]] || hash.split("/").slice(0, 2).join("/");
  $("#nav").innerHTML = (ME.self_guided ? NAV.bireysel : NAV[ME.role]).map(([href, ic, label]) =>
    `<a href="${href}" class="${section === href ? "active" : ""}" title="${label}">${icon(ic)}<span>${label}</span></a>`).join("");
  $("#brand-link").href = HOME[ME.role];
  $("#user-box").innerHTML = `
    <div class="user-card">${avatar(ME.name)}<div class="user-meta"><b>${esc(ME.name)}</b><small>${esc(ME.role_label)}${ME.is_demo ? " · örnek hesap" : ""}</small></div></div>
    <div class="user-actions">
      ${ME.is_demo ? "" : `<button class="side-btn" id="pw-btn">${icon("shield")}Şifre</button>`}
      <button class="side-btn" id="logout-btn">${icon("x")}Çıkış</button>
    </div>`;
  $("#logout-btn").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    ME = null;
    location.hash = "";
    showAuth();
  });
  $("#pw-btn")?.addEventListener("click", passwordForm);
}

function passwordForm() {
  openModal("Şifre değiştir", `
    ${field("Mevcut şifre", `<input name="current" type="password" required autocomplete="current-password">`)}
    ${field("Yeni şifre", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`, "En az 8 karakter")}`,
  async (fd) => {
    await sendJSON("/api/auth/password", Object.fromEntries(fd));
    toast("Şifreniz değiştirildi");
  }, "Değiştir");
}

function setHeader(crumbs, actions = "") {
  $("#crumbs").innerHTML = crumbs.map(([label, href], i) =>
    (i ? icon("chevron", "crumb-sep") : "") + (href ? `<a href="${href}">${esc(label)}</a>` : `<span>${esc(label)}</span>`)).join("");
  $("#topbar-actions").innerHTML = actions;
}

const ROUTES = [
  [/^#\/panel$/, () => viewDashboard()],
  [/^#\/danisanlar$/, () => viewClients()],
  [/^#\/danisan\/(\d+)(?:\/(\w+))?$/, (m) => viewClient(+m[1], m[2] || "genel")],
  [/^#\/seans\/(\d+)(?:\/(\w+))?$/, (m) => viewSession(+m[1], m[2] || "rapor")],
  [/^#\/egitim\/(\d+)$/, (m) => viewTraining(+m[1])],
  [/^#\/portal\/(\d+)(?:\?tab=\w+)?$/, (m) => viewPortal(+m[1])],
  [/^#\/kurumlar$/, () => viewOrganizations()],
  [/^#\/kurum\/(\d+)$/, (m) => viewOrganization(+m[1])],
  [/^#\/kapsam$/, () => viewScope()],
  [/^#\/ajanlar$/, () => viewAgents()],
  [/^#\/kullanicilar$/, () => viewUsers()],
  [/^#\/gelisim(?:\/(\w+))?$/, (m) => viewMyProgress(m[1] || "ozet")],
  [/^#\/kurum-panel$/, () => viewOrgPanel()],
  [/^#\/basla$/, () => viewSelfStart()],
  [/^#\/asistan$/, () => viewSelfChat()],
];

async function route() {
  if (!ME) return;
  stopPolling();
  document.body.classList.remove("nav-open");
  const hash = location.hash || HOME[ME.role];
  const key = hash.split("/")[1] || "";
  const allowed = ROUTE_ROLES[key] || ["admin", "koc"];
  if (!allowed.includes(ME.role)) { location.hash = HOME[ME.role]; return; }
  renderNav();
  for (const [re, fn] of ROUTES) {
    const m = hash.match(re);
    if (m) {
      try { await fn(m); } catch (e) { page.innerHTML = empty("alert", "Bir sorun oluştu", esc(e.message)); }
      window.scrollTo(0, 0);
      return;
    }
  }
  location.hash = HOME[ME.role];
}
window.addEventListener("hashchange", route);
// Sol menüyü daralt / genişlet (tercih tarayıcıda hatırlanır)
function setCollapsed(on) {
  document.body.classList.toggle("side-collapsed", on);
  const btn = $("#collapse-btn");
  const label = on ? "Menüyü genişlet" : "Menüyü daralt";
  btn.setAttribute("aria-label", label);
  btn.title = label;
  btn.setAttribute("aria-expanded", String(!on));
  try { localStorage.setItem("farkora-menu", on ? "dar" : "genis"); } catch { /* depolama kapalı olabilir */ }
}
$("#collapse-btn").innerHTML = icon("chevron");
$("#collapse-btn").addEventListener("click", () => setCollapsed(!document.body.classList.contains("side-collapsed")));
try { if (localStorage.getItem("farkora-menu") === "dar") setCollapsed(true); } catch { /* yok say */ }
$("#brand-link").addEventListener("click", (e) => {
  // Zaten ana sayfadaysa yeniden yükle (hash değişmeyince rota tetiklenmez)
  if (ME && location.hash === HOME[ME.role]) { e.preventDefault(); route(); }
  document.body.classList.remove("nav-open");
});
$("#menu-btn").innerHTML = icon("menu");
$("#menu-btn").addEventListener("click", () => document.body.classList.toggle("nav-open"));

function tabs(base, items, active) {
  return `<nav class="tabs">${items.map(([key, label, count]) =>
    `<a href="${base}/${key}" class="${key === active ? "active" : ""}">${label}${count != null ? `<span class="count">${count}</span>` : ""}</a>`).join("")}</nav>`;
}

function kpi(label, value, sub = "", ic = "trend", cls = "") {
  return `<div class="kpi"><div class="kpi-top"><span>${label}</span>${icon(ic)}</div>
    <div class="kpi-value ${cls}">${value}</div>${sub ? `<div class="kpi-sub">${sub}</div>` : ""}</div>`;
}

// ===================================================================
// Modal pencereler
// ===================================================================

const modal = $("#modal");
function openModal(title, body, onSubmit, submitLabel = "Kaydet", wide = false) {
  $("#modal-body").innerHTML = `
    <form class="modal-form" id="modal-form">
      <div class="modal-head"><h2>${title}</h2><button type="button" class="icon-only" data-close>${icon("x")}</button></div>
      <div class="modal-content">${body}</div>
      <p class="form-error" id="modal-error"></p>
      <div class="modal-foot">
        <button type="button" class="btn btn-secondary" data-close>Vazgeç</button>
        <button class="btn btn-primary" id="modal-submit">${submitLabel}</button>
      </div>
    </form>`;
  modal.classList.toggle("wide", wide);
  $$("[data-close]", modal).forEach((b) => b.addEventListener("click", () => modal.close()));
  $("#modal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#modal-submit");
    btn.disabled = true;
    $("#modal-error").textContent = "";
    try {
      await onSubmit(new FormData(e.target));
      modal.close();
    } catch (err) {
      $("#modal-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
  modal.showModal();
}

const field = (label, input, hint = "", cls = "") =>
  `<label class="field ${cls}"><span>${label}</span>${input}${hint ? `<small>${hint}</small>` : ""}</label>`;
const options = (pairs, selected) => pairs.map(([v, l]) => `<option value="${esc(v)}" ${String(v) === String(selected ?? "") ? "selected" : ""}>${esc(l)}</option>`).join("");

async function clientForm(existing = null) {
  const [orgs, coaches] = await Promise.all([api("/api/organizations"), ME.role === "admin" ? api("/api/coaches") : []]);
  const c = existing || { client_type: "bireysel", coach_id: ME.id };
  openModal(existing ? "Danışan bilgilerini düzenle" : "Yeni danışan", `
    <fieldset><legend>Kişisel bilgiler</legend>
      <div class="grid-form">
        ${field("Ad soyad *", `<input name="name" required value="${esc(c.name)}" placeholder="Ör. Ayşe Yılmaz">`)}
        ${field("Danışan tipi", `<select name="client_type">${options([["bireysel", "Bireysel danışan"], ["yonetici", "Yönetici"]], c.client_type)}</select>`)}
        ${field("E-posta", `<input name="email" type="email" value="${esc(c.email)}" placeholder="ornek@mail.com">`)}
        ${field("Telefon", `<input name="phone" value="${esc(c.phone)}" placeholder="05xx xxx xx xx">`)}
      </div>
    </fieldset>
    <fieldset><legend>Kurum ve rol</legend>
      <div class="grid-form">
        ${field("Kurum / birim", `<select name="organization_id"><option value="">— Bağımsız danışan —</option>${options(orgs.map((o) => [o.id, o.name]), c.organization_id)}</select>`,
          orgs.length ? "" : "Kurum eklemek için Kurumlar & Birimler sayfasını kullanın.")}
        ${field("Birim / program / departman", `<input name="unit" value="${esc(c.unit)}" placeholder="Ör. İstihdam Destek Programı">`)}
        ${field("Unvan / rol", `<input name="role_title" value="${esc(c.role_title)}" placeholder="Ör. Takım Lideri, Program katılımcısı">`)}
        ${field("Odak alanı", `<select name="focus_area"><option value="">Seçin</option>${options(FOCUS.map((f) => [f, f]), c.focus_area)}</select>`)}
      </div>
    </fieldset>
    <fieldset><legend>Koçluk süreci</legend>
      ${ME.role === "admin" ? field("Koç", `<select name="coach_id">${options(coaches.map((u) => [u.id, `${u.name}${u.role === "admin" ? " (yönetici)" : ""}`]), c.coach_id)}</select>`,
        "Danışanı yalnızca atanan koç (ve yöneticiler) görebilir.") : ""}
      ${field("Başlangıç hedefleri", `<textarea name="goals" rows="2" placeholder="Danışanın koçluktan beklentisi">${esc(c.goals)}</textarea>`)}
      ${field("Koçun ön notları", `<textarea name="notes" rows="2" placeholder="Ön görüşme notları, dikkat edilecekler">${esc(c.notes)}</textarea>`)}
    </fieldset>
    <fieldset><legend>Bildirim kanalları</legend>
      <div class="chips-pick">
        ${[["eposta", "📧 E-posta"], ["whatsapp", "💬 WhatsApp"]].map(([k, l]) => `<label class="pick-check"><input type="checkbox" name="notify_channels" value="${k}"
          ${(c.notify_channels || "").split(",").includes(k) ? "checked" : ""}><span>${l}</span></label>`).join("")}
      </div>
      <p class="muted small">Mesajlar her zaman uygulamaya düşer; izin varsa bu kanallardan da gider.</p>
    </fieldset>
    <label class="consent"><input type="checkbox" name="consent" ${c.consent ? "checked" : ""}>
      <span><b>KVKK açık rızası alındı.</b> Rıza olmadan kayıt yüklenemez.</span></label>`,
  async (fd) => {
    const body = Object.fromEntries(fd);
    body.consent = fd.has("consent");
    body.organization_id = body.organization_id ? Number(body.organization_id) : null;
    body.coach_id = body.coach_id ? Number(body.coach_id) : null;
    body.notify_channels = fd.getAll("notify_channels");
    const saved = existing ? await sendJSON(`/api/clients/${existing.id}`, body, "PUT") : await sendJSON("/api/clients", body);
    toast(existing ? "Danışan bilgileri güncellendi" : "Danışan eklendi");
    if (existing) route(); else location.hash = `#/danisan/${saved.id}`;
  }, existing ? "Kaydet" : "Danışanı ekle", true);
}

function orgForm(existing = null) {
  const o = existing || { org_type: "sirket" };
  openModal(existing ? "Kurumu düzenle" : "Yeni kurum / birim", `
    <div class="grid-form">
      ${field("Kurum / birim adı *", `<input name="name" required value="${esc(o.name)}" placeholder="Ör. X Belediyesi Sosyal Destek Birimi">`)}
      ${field("Tür", `<select name="org_type">${options(Object.entries(ORG_TYPE), o.org_type)}</select>`)}
    </div>
    ${field("Sektör / alan", `<input name="sector" value="${esc(o.sector)}" placeholder="Ör. Yazılım, Kamu / sosyal hizmet">`)}
    ${field("Kurumsal hafıza", `<textarea name="knowledge" rows="6" placeholder="Kurumun değerleri, yetkinlik modeli, programları, öncelikleri, ilkeleri…">${esc(o.knowledge)}</textarea>`,
      "Bu kurumdaki her danışanın raporu, eğitimi ve ajan mesajı bu bilgiye göre kişiselleşir.")}`,
  async (fd) => {
    const body = Object.fromEntries(fd);
    const saved = existing ? await sendJSON(`/api/organizations/${existing.id}`, body, "PUT") : await sendJSON("/api/organizations", body);
    toast(existing ? "Kurum güncellendi" : "Kurum eklendi");
    if (existing) route(); else location.hash = `#/kurum/${saved.id}`;
  }, existing ? "Kaydet" : "Kurumu ekle", true);
}

const TEXT_EXAMPLE = `Koç: Bugünkü görüşmemizden ne almak istersiniz?
Danışan: Ekibime geri bildirim vermekte zorlanıyorum.
Koç: Zorlandığınız anlarda neler yaşıyorsunuz?

veya WhatsApp dışa aktarma biçimi:
[04.11.2026 14:03] Ayşe Yılmaz: Merhaba, bu hafta…`;

function uploadSessionForm(client) {
  let mode = "ses";
  const recs = {}; // tür -> kaydedici durumu

  const recorderHtml = (kind) => `
    <div class="recorder" data-rec="${kind}">
      ${kind === "video" ? `<div class="segmented small rec-vsrc">
          <button type="button" data-vsrc="ekran" class="active">🖥️ Ekran (Zoom / Teams)</button>
          <button type="button" data-vsrc="kamera">📷 Kamera</button>
        </div>
        <p class="muted small rec-vsrc-note">Zoom/Teams penceresini seçin ve “sesi paylaş”ı işaretleyin.</p>
        <video class="rec-video" muted playsinline hidden></video>
        <p class="rec-warn" hidden></p>` : ""}
      <div class="rec-time">00:00</div>
      <div class="rec-level"><span></span></div>
      <p class="muted small rec-status">${kind === "video" ? "Kamera ve mikrofon izni istenecek" : "Mikrofon izni istenecek"}</p>
      <div class="row center">
        <button type="button" class="btn btn-primary rec-start">${icon(kind === "video" ? "image" : "mic")}Kaydı başlat</button>
        <button type="button" class="btn btn-secondary rec-pause" hidden>Duraklat</button>
        <button type="button" class="btn btn-secondary rec-stop" hidden>Bitir</button>
      </div>
      <div class="rec-result"></div>
    </div>`;

  const sourceHtml = (kind) => `
    <div class="source-switch">
      <label><input type="radio" name="src-${kind}" value="dosya" checked><span>${icon("upload")}Dosya yükle</span></label>
      <label><input type="radio" name="src-${kind}" value="canli"><span>${icon(kind === "video" ? "image" : "mic")}Canlı kaydet</span></label>
      ${kind === "video" ? `<label><input type="radio" name="src-video" value="foto"><span>${icon("image")}Fotoğraf</span></label>` : ""}
    </div>
    <div data-sub="${kind}-dosya">
      ${field(kind === "video" ? "Video dosyası" : "Ses dosyası",
        `<input name="file-${kind}" type="file" accept="${kind === "video" ? "video/*" : "audio/*,video/*"}">`,
        kind === "video" ? "Zoom / Teams video kaydı (mp4, webm, mov)" : "Telefon veya toplantı kaydı (mp3, m4a, wav…)")}
    </div>
    <div data-sub="${kind}-canli" hidden>${recorderHtml(kind)}</div>
    ${kind === "video" ? `<div data-sub="video-foto" hidden>
      ${field("Fotoğraflar", `<input name="photos" type="file" accept="image/jpeg,image/png,image/webp" multiple>`,
        "Beyaz tahta, not, çizim, hedef panosu… (en fazla 8)")}
      <div class="photo-previews"></div>
      ${field("Seans notu (isteğe bağlı)", `<textarea name="notes" rows="4" placeholder="Ör. Danışan hedef panosunu hazırlayıp getirdi; en çok kariyer kısmında zorlandı."></textarea>`)}
    </div>` : ""}`;

  openModal("Yeni seans", `
    <div class="segmented">
      <button type="button" data-mode="ses" class="active">${icon("mic")}Sesli</button>
      <button type="button" data-mode="video">${icon("image")}Görsel</button>
      <button type="button" data-mode="metin">${icon("message")}Yazılı</button>
      <button type="button" data-mode="bot">${icon("bot")}Toplantı botu</button>
    </div>
    ${field("Seans başlığı", `<input name="title" placeholder="Ör. 3. seans">`)}
    <div data-pane="ses">${sourceHtml("ses")}</div>
    <div data-pane="video" hidden>${sourceHtml("video")}</div>
    <div data-pane="metin" hidden>
      ${field("Görüşme metni", `<textarea name="text" rows="9" placeholder="${esc(TEXT_EXAMPLE)}"></textarea>`,
        "“Koç: / Danışan:” satırları veya WhatsApp dökümü")}
      ${field("veya .txt dosyası", `<input type="file" accept=".txt,text/plain" id="txt-file">`)}
    </div>
    <div data-pane="bot" hidden>
      ${field("Toplantı bağlantısı", `<input name="meeting_url" placeholder="https://us02web.zoom.us/j/… veya Teams / Meet bağlantısı">`,
        "Bot “Farkora Not Asistanı” adıyla görünür katılımcı olarak girer, toplantı bitince kaydı analiz eder.")}
    </div>
    <div class="note">${icon("sparkles")}<span id="mode-note"></span></div>`,
  async (fd) => {
    const title = fd.get("title");
    if (mode === "bot") {
      const b = await sendJSON(`/api/clients/${client.id}/meeting-bot`, { meeting_url: fd.get("meeting_url") || "", title });
      toast(b.provider === "simulasyon" ? "Simülasyon: bot toplantıya katılıyor" : "Bot toplantıya gönderildi");
      location.hash = `#/danisan/${client.id}/seanslar`;
      return;
    }
    if (mode === "metin") {
      const s = await sendJSON(`/api/clients/${client.id}/sessions/text`, { title, text: fd.get("text") || "" });
      location.hash = `#/seans/${s.id}`;
      return;
    }
    const src = $(`input[name=src-${mode}]:checked`, modal).value;
    if (src === "foto") {
      const photos = [...$("input[name=photos]", modal).files];
      if (!photos.length) throw new Error("En az bir fotoğraf seçin.");
      if (photos.length > 8) throw new Error("En fazla 8 fotoğraf seçebilirsiniz.");
      const body = new FormData();
      body.append("title", title || `Fotoğraflı seans · ${fmtDate(new Date().toISOString())}`);
      body.append("notes", fd.get("notes") || "");
      photos.forEach((f) => body.append("files", f));
      const s = await api(`/api/clients/${client.id}/sessions/photos`, { method: "POST", body });
      location.hash = `#/seans/${s.id}`;
      return;
    }
    const live = src === "canli";
    const body = new FormData();
    let file;
    if (live) {
      const r = recs[mode];
      if (r?.recorder && r.recorder.state !== "inactive") throw new Error("Önce kaydı “Bitir” ile tamamlayın.");
      if (!r?.blob) throw new Error("Henüz kayıt alınmadı.");
      file = new File([r.blob], mode === "video" ? "canli-video.webm" : "canli-ses.webm", { type: r.blob.type });
    } else {
      file = fd.get(`file-${mode}`);
      if (!file || !file.size) throw new Error("Bir dosya seçin.");
    }
    body.append("title", title || (live ? `Canlı ${mode === "video" ? "video" : "kayıt"} · ${fmtDate(new Date().toISOString())}` : ""));
    body.append("file", file);
    const s = await api(`/api/clients/${client.id}/sessions`, { method: "POST", body });
    location.hash = `#/seans/${s.id}`;
  }, "Analiz et", true);

  const NOTES = {
    ses: "Yazıya dökülür, raporlanır ve ICF’ye göre puanlanır.",
    video: "Video veya fotoğraftaki materyaller (tahta, not, çizim) yorumlanır. Yüzden duygu çıkarımı yapılmaz.",
    metin: "Yazılı seanslarda ses analizi yapılmaz.",
    bot: "Danışanın ve katılımcıların botun varlığından haberdar olması gerekir. Recall.ai anahtarı yoksa simülasyon çalışır.",
  };
  const setNote = () => ($("#mode-note").textContent = NOTES[mode]);
  setNote();
  $$("[data-mode]", modal).forEach((b) => b.addEventListener("click", () => {
    mode = b.dataset.mode;
    $$("[data-mode]", modal).forEach((x) => x.classList.toggle("active", x === b));
    $$("[data-pane]", modal).forEach((p) => (p.hidden = p.dataset.pane !== mode));
    setNote();
  }));
  ["ses", "video"].forEach((kind) => $$(`input[name=src-${kind}]`, modal).forEach((r) => r.addEventListener("change", () => {
    $$(`[data-sub^="${kind}-"]`, modal).forEach((sub) => (sub.hidden = sub.dataset.sub !== `${kind}-${r.value}`));
  })));
  $("input[name=photos]", modal).addEventListener("change", (e) => {
    const box = $(".photo-previews", modal);
    box.querySelectorAll("img").forEach((i) => URL.revokeObjectURL(i.src));
    box.innerHTML = [...e.target.files].slice(0, 8).map((f) => `<img src="${URL.createObjectURL(f)}" alt="${esc(f.name)}">`).join("");
  });
  $("#txt-file").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (f) $("textarea[name=text]", modal).value = await f.text();
  });

  const fmt = (ms) => fmtSec(ms / 1000);
  const cleanups = [];
  modal.addEventListener("close", () => cleanups.forEach((fn) => fn()), { once: true });

  $$("[data-rec]", modal).forEach((box) => {
    const kind = box.dataset.rec;
    const r = (recs[kind] = { recorder: null, stream: null, ctx: null, mixCtx: null, raw: [], vsrc: "ekran", chunks: [], blob: null, elapsed: 0, started: 0, timer: null, raf: null });
    const el = (c) => $(c, box);
    const tick = () => (el(".rec-time").textContent = fmt(r.elapsed + (r.started ? Date.now() - r.started : 0)));
    const stopMedia = () => {
      [r.stream, ...r.raw].forEach((s) => s?.getTracks().forEach((t) => t.stop()));
      r.ctx?.close(); r.ctx = null; r.mixCtx?.close(); r.mixCtx = null; r.raw = [];
    };
    const VSRC_NOTES = {
      ekran: "Zoom/Teams penceresini seçin ve “sesi paylaş”ı işaretleyin.",
      kamera: "Yüz yüze seans için bilgisayar kamerası ve mikrofonu kullanılır.",
    };
    $$("[data-vsrc]", box).forEach((b) => b.addEventListener("click", () => {
      if (r.recorder && r.recorder.state !== "inactive") return;
      r.vsrc = b.dataset.vsrc;
      $$("[data-vsrc]", box).forEach((x) => x.classList.toggle("active", x === b));
      el(".rec-vsrc-note").textContent = VSRC_NOTES[r.vsrc];
      el(".rec-status").textContent = r.vsrc === "ekran" ? "Ekran paylaşımı ve mikrofon izni istenecek" : "Kamera ve mikrofon izni istenecek";
    }));
    if (kind === "video") el(".rec-status").textContent = "Ekran paylaşımı ve mikrofon izni istenecek";

    // Ekran paylaşımı + mikrofon: iki ses kaynağını tek kayda karıştırır
    const screenStream = async () => {
      const display = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 15 }, audio: true });
      let mic = null;
      try { mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); } catch { /* mikrofonsuz devam */ }
      r.raw = [display, mic].filter(Boolean);
      const audioIn = r.raw.filter((s) => s.getAudioTracks().length);
      const tracks = [...display.getVideoTracks()];
      if (audioIn.length) {
        r.mixCtx = new AudioContext();
        const dest = r.mixCtx.createMediaStreamDestination();
        audioIn.forEach((s) => r.mixCtx.createMediaStreamSource(s).connect(dest));
        tracks.push(...dest.stream.getAudioTracks());
      }
      // Kullanıcı tarayıcının "Paylaşımı durdur" düğmesine basarsa kaydı bitir
      display.getVideoTracks()[0].addEventListener("ended", () => {
        if (r.recorder && r.recorder.state !== "inactive") el(".rec-stop").click();
      });
      if (!display.getAudioTracks().length) {
        warn(mic ? "Toplantı sesi paylaşılmadı; yalnızca sizin mikrofonunuz kaydediliyor. Karşı tarafın sesi için paylaşırken “sesi paylaş”ı işaretleyin."
                 : "Ses kaydı yok: toplantı sesi paylaşılmadı ve mikrofona erişilemedi.");
      }
      return new MediaStream(tracks);
    };
    const warn = (msg) => { const w = el(".rec-warn"); if (w) { w.textContent = msg; w.hidden = !msg; } };
    // Kamera görüntüsü siyahsa (kamera başka uygulamada açık / kapağı kapalı) uyar
    const checkDark = (v) => setTimeout(() => {
      if (!r.started || !v.videoWidth) return;
      const c = document.createElement("canvas"); c.width = 64; c.height = 36;
      const g = c.getContext("2d"); g.drawImage(v, 0, 0, 64, 36);
      const px = g.getImageData(0, 0, 64, 36).data;
      let sum = 0; for (let i = 0; i < px.length; i += 4) sum += px[i] + px[i + 1] + px[i + 2];
      if (sum / (px.length / 4) / 3 < 14) warn("Kamera görüntüsü siyah görünüyor. Kamera Zoom/Teams gibi başka bir uygulamada açık olabilir ya da kapağı kapalı olabilir. Online seansı kaydetmek için “Ekran” seçeneğini kullanın.");
    }, 1800);
    cleanups.push(() => {
      clearInterval(r.timer); cancelAnimationFrame(r.raf);
      if (r.recorder && r.recorder.state !== "inactive") r.recorder.stop();
      stopMedia();
    });

    el(".rec-start").addEventListener("click", async () => {
      warn("");
      const screen = kind === "video" && r.vsrc === "ekran";
      try {
        r.stream = screen ? await screenStream() : await navigator.mediaDevices.getUserMedia(kind === "video"
          ? { audio: { echoCancellation: true, noiseSuppression: true }, video: { width: 1280, height: 720 } }
          : { audio: { echoCancellation: true, noiseSuppression: true } });
      } catch {
        stopMedia();
        el(".rec-status").textContent = screen ? "Ekran paylaşımı başlatılamadı ya da iptal edildi."
          : kind === "video" ? "Kameraya erişilemedi. Tarayıcı izinlerini kontrol edin." : "Mikrofona erişilemedi.";
        return;
      }
      if (kind === "video") {
        const v = el(".rec-video");
        v.srcObject = r.stream; v.hidden = false; v.play();
        if (!screen) checkDark(v);
      }
      const types = kind === "video" ? ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"] : ["audio/webm;codecs=opus", "audio/webm"];
      const type = types.find((t) => MediaRecorder.isTypeSupported(t)) || "";
      r.recorder = new MediaRecorder(r.stream, type ? { mimeType: type } : undefined);
      r.chunks = [];
      r.recorder.ondataavailable = (e) => e.data.size && r.chunks.push(e.data);
      r.recorder.onstop = () => {
        r.blob = new Blob(r.chunks, { type: kind === "video" ? "video/webm" : "audio/webm" });
        const url = URL.createObjectURL(r.blob);
        el(".rec-result").innerHTML = kind === "video" ? `<video controls src="${url}"></video>` : `<audio controls src="${url}"></audio>`;
        if (kind === "video") el(".rec-video").hidden = true;
        el(".rec-status").textContent = `Kayıt hazır (${fmt(r.elapsed)})`;
        stopMedia();
      };
      r.recorder.start(1000);
      r.started = Date.now();
      r.timer = setInterval(tick, 500);
      r.ctx = new AudioContext();
      const analyser = r.ctx.createAnalyser();
      if (r.stream.getAudioTracks().length) r.ctx.createMediaStreamSource(r.stream).connect(analyser);
      const data = new Uint8Array(analyser.fftSize);
      const level = () => {
        analyser.getByteTimeDomainData(data);
        const rms = Math.sqrt(data.reduce((a, v) => a + ((v - 128) / 128) ** 2, 0) / data.length);
        el(".rec-level span").style.width = `${Math.min(100, rms * 400)}%`;
        r.raf = requestAnimationFrame(level);
      };
      level();
      el(".rec-start").hidden = true;
      el(".rec-pause").hidden = el(".rec-stop").hidden = false;
      el(".rec-status").innerHTML = `<span class="rec-dot"></span>Kaydediliyor…`;
    });
    el(".rec-pause").addEventListener("click", (e) => {
      if (r.recorder.state === "recording") {
        r.recorder.pause(); r.elapsed += Date.now() - r.started; r.started = 0;
        e.currentTarget.textContent = "Devam et"; el(".rec-status").textContent = "Duraklatıldı";
      } else {
        r.recorder.resume(); r.started = Date.now();
        e.currentTarget.textContent = "Duraklat"; el(".rec-status").innerHTML = `<span class="rec-dot"></span>Kaydediliyor…`;
      }
    });
    el(".rec-stop").addEventListener("click", () => {
      if (r.started) r.elapsed += Date.now() - r.started;
      r.started = 0; clearInterval(r.timer); cancelAnimationFrame(r.raf);
      el(".rec-level span").style.width = "0"; tick();
      r.recorder.stop();
      el(".rec-pause").hidden = el(".rec-stop").hidden = true;
    });
  });
}

function uploadImageForm(client) {
  openModal("Görsel yükle", `
    ${field("Görsel *", `<input name="file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" required>`,
      "Hedef panosu, el yazısı günlük, zihin haritası, çizim, beyaz tahta… (en fazla 8 MB)")}
    ${field("Not", `<input name="note" placeholder="Ör. Danışanın hazırladığı 2026 hedef panosu">`)}
    <div class="note">${icon("shield")}<span>Yüz analizi yapılmaz, yalnızca içerik yorumlanır.</span></div>`,
  async (fd) => {
    await api(`/api/clients/${client.id}/images`, { method: "POST", body: fd });
    toast("Görsel yüklendi, analiz ediliyor");
    location.hash = `#/danisan/${client.id}/gorsel`;
    route();
  }, "Yükle ve analiz et");
}

// ===================================================================
// Genel panel
// ===================================================================

async function viewDashboard() {
  const d = await api("/api/dashboard");
  setHeader([["Genel Panel"]], `<button class="btn btn-primary" id="new-client">${icon("plus")}Yeni danışan</button>`);
  $("#new-client").addEventListener("click", () => clientForm());

  if (!d.aktif_danisan) {
    page.innerHTML = `<div class="welcome card">
      <div><h1>Farkora'ya hoş geldiniz</h1>
      <p class="muted">Koçlar için yapay zekâ asistanı.</p>
      <div class="row"><button class="btn btn-primary" id="w-client">${icon("plus")}İlk danışanı ekle</button>
      ${ME.role === "admin" ? `<button class="btn btn-secondary" id="w-demo">${icon("database")}Örnek veriyle göster</button></div>
      <p class="muted small">Kurgusal verilerle hemen deneyin.</p>` : "</div>"}</div>
    </div>`;
    $("#w-client").addEventListener("click", () => clientForm());
    $("#w-demo")?.addEventListener("click", async (e) => {
      e.target.disabled = true;
      await api("/api/demo/seed", { method: "POST" });
      toast("Örnek veri yüklendi");
      route();
    });
    return;
  }

  page.innerHTML = `
    <div class="page-title"><h1>Genel Panel</h1><p class="muted">${fmtDate(new Date().toISOString(), false)}</p></div>
    <div class="kpis">
      ${kpi("Aktif danışan", d.aktif_danisan, "", "users")}
      ${kpi("Bu ay seans", d.bu_ay_seans, "", "mic")}
      ${kpi("Ortalama ICF puanı", d.icf_ortalama ?? "—", "5 üzerinden", "trend", scoreClass(d.icf_ortalama))}
      ${kpi("Görev tamamlama", d.gorev_tamamlama != null ? `%${d.gorev_tamamlama}` : "—", "Tüm danışanlar", "check")}
      ${kpi("Ajan eylemi", d.ajan_eylemi_7g, "Son 7 gün", "bot")}
    </div>
    <div class="grid-main">
      <div class="col">
        <section class="card">
          <div class="card-head"><h2>ICF puan gelişimi</h2><span class="muted small">Son ${d.icf_trendi.length} seans</span></div>
          ${lineChart(d.icf_trendi)}
        </section>
        <section class="card">
          <div class="card-head"><h2>Son seanslar</h2><a href="#/danisanlar" class="link">Tüm danışanlar</a></div>
          <table class="table"><thead><tr><th>Danışan</th><th>Seans</th><th>Tarih</th><th>ICF</th><th>Durum</th></tr></thead><tbody>
          ${d.son_seanslar.map((s) => `<tr data-href="#/seans/${s.id}">
            <td><div class="person">${avatar(s.client_name)}<span>${esc(s.client_name)}</span></div></td>
            <td>${esc(s.title)}</td><td class="muted">${fmtDate(s.created_at, false)}</td>
            <td><b class="score ${scoreClass(s.icf)}">${s.icf ?? "—"}</b></td><td>${badge(s.status)}</td></tr>`).join("")}
          </tbody></table>
        </section>
      </div>
      <div class="col">
        <section class="card">
          <div class="card-head"><h2>${icon("alert")} Dikkat gerektirenler</h2></div>
          ${d.uyarilar.length ? d.uyarilar.map((a) => `<a class="alert-item" href="#/danisan/${a.client_id}/ajan">
            <b>${esc(a.client_name)}</b><p>${esc(a.message)}</p><small>${fmtDate(a.created_at)}</small></a>`).join("")
            : `<p class="muted">Şu an dikkat gerektiren bir durum yok.</p>`}
        </section>
        <section class="card">
          <div class="card-head"><h2>${icon("clock")} Yaklaşan görevler</h2></div>
          ${d.yaklasan_gorevler.length ? d.yaklasan_gorevler.map((t) => `<a class="task-item" href="#/danisan/${t.client_id}/gorevler">
            <span class="due ${t.due_date < new Date().toISOString().slice(0, 10) ? "late" : ""}">${fmtDate(t.due_date, false)}</span>
            <div><b>${esc(t.text)}</b><small>${esc(t.client_name)}</small></div></a>`).join("")
            : `<p class="muted">Açık görev yok.</p>`}
        </section>
      </div>
    </div>`;
  bindRowLinks();
}

function avatar(name, cls = "") { return `<span class="avatar ${cls}">${esc(initials(name || "?"))}</span>`; }
function bindRowLinks() { $$("[data-href]", page).forEach((r) => r.addEventListener("click", () => (location.hash = r.dataset.href))); }

function lineChart(points) {
  if (points.length < 2) return `<p class="muted">Grafik için en az iki analiz edilmiş seans gerekir.</p>`;
  const W = 600, H = 180, P = 28;
  const x = (i) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (v) => H - P - ((v - 1) / 4) * (H - 2 * P);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.puan).toFixed(1)}`).join(" ");
  const grid = [1, 2, 3, 4, 5].map((v) => `<line x1="${P}" x2="${W - P}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${P - 8}" y="${y(v) + 4}" class="axis" text-anchor="end">${v}</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="ICF puan gelişimi">
    ${grid}<path d="${path} L${x(points.length - 1)},${H - P} L${x(0)},${H - P} Z" class="area"/>
    <path d="${path}" class="line"/>
    ${points.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.puan)}" r="4" class="pt"><title>${p.tarih}: ${p.puan}</title></circle>`).join("")}
  </svg>`;
}

// ===================================================================
// Danışanlar listesi
// ===================================================================

async function viewClients() {
  const [clients, orgs] = await Promise.all([api("/api/clients"), api("/api/organizations")]);
  setHeader([["Danışanlar"]], `<button class="btn btn-primary" id="new-client">${icon("plus")}Yeni danışan</button>`);
  $("#new-client").addEventListener("click", () => clientForm());

  page.innerHTML = `
    <div class="page-title"><h1>Danışanlar</h1><p class="muted">${clients.length} danışan</p></div>
    <div class="card">
      <div class="toolbar">
        <div class="search">${icon("search")}<input id="q" placeholder="İsim, kurum veya birim ara…"></div>
        <select id="f-org"><option value="">Tüm kurumlar</option>${options(orgs.map((o) => [o.id, o.name]))}<option value="none">Bağımsız</option></select>
        <select id="f-type"><option value="">Tüm tipler</option>${options(Object.entries(CLIENT_TYPE))}</select>
      </div>
      <div id="client-table"></div>
    </div>`;

  const render = () => {
    const q = $("#q").value.toLocaleLowerCase("tr");
    const org = $("#f-org").value, type = $("#f-type").value;
    const rows = clients.filter((c) =>
      (!q || [c.name, c.organization_name, c.unit, c.role_title].join(" ").toLocaleLowerCase("tr").includes(q)) &&
      (!org || (org === "none" ? !c.organization_id : String(c.organization_id) === org)) &&
      (!type || c.client_type === type));
    $("#client-table").innerHTML = rows.length ? `<table class="table"><thead><tr>
      <th>Danışan</th><th>Kurum / birim</th><th>Tip</th><th>Odak</th><th>Seans</th><th>Son ICF</th><th>Son seans</th><th></th></tr></thead><tbody>
      ${rows.map((c) => `<tr data-href="#/danisan/${c.id}">
        <td><div class="person">${avatar(c.name)}<div><b>${esc(c.name)}</b><small>${esc(c.role_title || c.email || "")}</small></div></div></td>
        <td>${c.organization_name ? `${esc(c.organization_name)}<small>${esc(c.unit)}</small>` : `<span class="muted">Bağımsız</span>`}</td>
        <td><span class="tag">${c.self_guided ? "Kendi başına" : CLIENT_TYPE[c.client_type] || "Bireysel"}</span></td>
        <td>${esc(c.focus_area || "—")}</td><td>${c.session_count}</td>
        <td><b class="score ${scoreClass(c.last_icf)}">${c.last_icf ?? "—"}</b></td>
        <td class="muted">${c.last_session_at ? fmtDate(c.last_session_at, false) : "—"}</td>
        <td>${c.alert_count ? `<span class="badge badge-err" title="Son 7 günde ajan uyarısı">${icon("alert")}Uyarı</span>` : ""}
            ${c.consent ? "" : `<span class="badge badge-wait" title="KVKK açık rızası yok">Rıza yok</span>`}</td>
      </tr>`).join("")}</tbody></table>`
      : empty("users", clients.length ? "Sonuç bulunamadı" : "Henüz danışan yok", clients.length ? "Filtreleri değiştirin." : "Sağ üstten yeni danışan ekleyin.");
    bindRowLinks();
  };
  ["#q", "#f-org", "#f-type"].forEach((s) => $(s).addEventListener("input", render));
  render();
}

// ===================================================================
// Danışan detayı
// ===================================================================

const CLIENT_TABS = [["genel", "Genel bakış"], ["seanslar", "Seanslar"], ["egitimler", "Eğitimler"],
  ["gorsel", "Görsel analiz"], ["gorevler", "Görevler & ruh hali"], ["kanit", "Davranış kanıtı"], ["ajan", "Ajan akışı"]];

async function viewClient(id, tab) {
  const [c, trainings, ag, images, ev] = await Promise.all([api(`/api/clients/${id}`), api(`/api/clients/${id}/trainings`),
    api(`/api/clients/${id}/agent`), api(`/api/clients/${id}/images`), api(`/api/clients/${id}/evidence`)]);
  setHeader([["Danışanlar", "#/danisanlar"], [c.name]], `
    <a class="btn btn-secondary" href="#/portal/${id}">${icon("phone")}Danışan görünümü</a>
    <button class="btn btn-primary" id="upload">${icon("upload")}Seans yükle</button>`);
  $("#upload").addEventListener("click", () => c.consent ? uploadSessionForm(c) : toast("Önce danışanın KVKK açık rızasını kaydedin", "err"));

  const counts = { seanslar: c.sessions.length, egitimler: trainings.length, gorsel: images.length,
    gorevler: ag.tasks.filter((t) => t.status === "acik").length, kanit: ev.commitments.length, ajan: ag.actions.length };
  page.innerHTML = `
    <div class="profile card">
      ${avatar(c.name, "avatar-xl")}
      <div class="profile-main">
        <div class="row"><h1>${esc(c.name)}</h1><span class="tag">${CLIENT_TYPE[c.client_type] || "Bireysel"}</span>
          ${c.consent ? `<span class="badge badge-ok" title="${fmtDate(c.consent_at)}">${icon("shield")}KVKK rızası</span>` : `<span class="badge badge-err">${icon("shield")}Rıza alınmadı</span>`}</div>
        <div class="profile-meta">
          ${c.role_title ? `<span>${esc(c.role_title)}</span>` : ""}
          ${c.organization_name ? `<a href="#/kurum/${c.organization_id}">${icon("building")}${esc(c.organization_name)}${c.unit ? ` · ${esc(c.unit)}` : ""}</a>` : c.unit ? `<span>${esc(c.unit)}</span>` : ""}
          ${c.focus_area ? `<span>${esc(c.focus_area)}</span>` : ""}
          ${c.email ? `<span>${esc(c.email)}</span>` : ""}${c.phone ? `<span>${esc(c.phone)}</span>` : ""}
        </div>
        ${c.goals ? `<p class="profile-goal"><b>Hedef:</b> ${esc(c.goals)}</p>` : ""}
        <div class="profile-foot">
          ${c.coach_name ? `<span>${icon("users")}Koç: <b>${esc(c.coach_name)}</b></span>` : `<span class="muted">${icon("users")}Koç atanmadı</span>`}
          <span>${icon("phone")}Danışan girişi: ${c.account ? `<b>${esc(c.account.email)}</b>` : `<span class="muted">yok</span>`}
            <button class="link-btn" id="account-btn">${c.account ? "Şifre sıfırla" : "Giriş oluştur"}</button></span>
        </div>
      </div>
      <div class="profile-actions">
        <button class="btn btn-secondary" id="edit-client">${icon("edit")}Düzenle</button>
        <button class="btn btn-secondary btn-sm danger" id="delete-client">${icon("x")}Sil</button>
      </div>
    </div>
    ${tabs(`#/danisan/${id}`, CLIENT_TABS.map(([k, l]) => [k, l, counts[k]]), tab)}
    <section id="tab-body"></section>`;
  $("#edit-client").addEventListener("click", () => clientForm(c));
  $("#delete-client").addEventListener("click", () => deleteClientForm(c));
  $("#account-btn").addEventListener("click", () => accountForm(c));

  const body = $("#tab-body");
  ({ genel: tabOverview, seanslar: tabSessions, egitimler: tabTrainings, gorsel: tabImages, gorevler: tabTasks, kanit: tabEvidence, ajan: tabAgent }[tab] || tabOverview)(body, { c, trainings, ag, images, ev });
}

function tabOverview(body, { c, ag, trainings }) {
  const completed = c.sessions.filter((s) => s.status === "tamamlandi");
  const last = completed[0];
  const b = ag.behavior;
  const alerts = ag.actions.filter((a) => a.kind === "uyari" && a.applied).slice(0, 2);
  body.innerHTML = `
    <div class="kpis">
      ${kpi("Seans", c.sessions.length, `${completed.length} analiz edildi`, "mic")}
      ${kpi("Son ICF puanı", last?.icf?.ortalama ?? "—", "5 üzerinden", "trend", scoreClass(last?.icf?.ortalama))}
      ${kpi("Görev tamamlama", b.gorev_tamamlama_orani != null ? `%${b.gorev_tamamlama_orani}` : "—", `${b.gorev_tamamlanan}/${b.gorev_toplam} görev`, "check")}
      ${kpi("Ruh hali", b.ruh_hali_ortalama ?? "—", `${b.checkin_sayisi} check-in`, "message", scoreClass(b.ruh_hali_ortalama))}
      ${kpi("Eğitim", trainings.length, "kişiye özel", "book")}
    </div>
    ${alerts.map((a) => `<div class="banner banner-err">${icon("alert")}<div><b>Ajan uyarısı</b><p>${esc(a.message)}</p></div></div>`).join("")}
    ${c.self ? selfCoachCard(c.self) : ""}
    <div class="grid-2">
      <section class="card">
        <div class="card-head"><h2>Son seans</h2>${last ? `<a class="link" href="#/seans/${last.id}">Raporu aç</a>` : ""}</div>
        ${last ? `<p class="muted small">${esc(last.title)} · ${fmtDate(last.created_at)}</p><p>${esc(last.report.ozet)}</p>
          <h4>Danışanın görevleri</h4>${bullets(last.report.danisan_gorevleri)}`
          : empty("mic", "Henüz analiz edilmiş seans yok", "Sağ üstten seans kaydı yükleyin.")}
      </section>
      <section class="card">
        <div class="card-head"><h2>${icon("sparkles")} Seans öncesi hazırlık</h2></div>
        <div id="brief">${completed.length
          ? `<p class="muted">Geçmiş seanslardan kısa bir hazırlık notu.</p>
             <button class="btn btn-primary" id="brief-btn">${icon("sparkles")}Hazırlık brifi oluştur</button>`
          : `<p class="muted">İlk seans analiz edildikten sonra kullanılabilir.</p>`}</div>
      </section>
    </div>`;
  $("#brief-btn")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    e.currentTarget.textContent = "Hazırlanıyor…";
    try {
      const br = await api(`/api/clients/${c.id}/brief`, { method: "POST" });
      $("#brief").innerHTML = `<p>${esc(br.danisan_durumu)}</p><h4>Takip edilecek konular</h4>${bullets(br.takip_edilecek_konular)}
        <h4>Sorabileceğiniz sorular</h4>${bullets(br.onerilen_sorular)}<h4>Dikkat noktaları</h4>${bullets(br.dikkat_noktalari)}`;
    } catch (err) { $("#brief").innerHTML = `<p class="form-error">${esc(err.message)}</p>`; }
  });
}

function tabSessions(body, { c }) {
  body.innerHTML = `<section class="card">${c.sessions.length ? `<table class="table"><thead><tr>
    <th>Seans</th><th>Tarih</th><th>Kaynak</th><th>ICF</th><th>Durum</th></tr></thead><tbody>
    ${c.sessions.map((s) => `<tr data-href="#/seans/${s.id}"><td><b>${esc(s.title)}</b></td><td class="muted">${fmtDate(s.created_at)}</td>
      <td class="muted">${{ ornek: "Örnek veri", metin: "Yazılı", video: "Görsel (video)", foto: "Görsel (fotoğraf)" }[s.source] || "Sesli"}</td>
      <td><b class="score ${scoreClass(s.icf?.ortalama)}">${s.icf?.ortalama ?? "—"}</b></td><td>${badge(s.status)}</td></tr>`).join("")}
    </tbody></table>` : empty("mic", "Henüz seans yok", "Sağ üstten seans kaydı yükleyin.")}</section>
    <div id="bots"></div>`;
  bindRowLinks();
  renderBots($("#bots", body), c.id);
}

function tabTrainings(body, { trainings }) {
  body.innerHTML = trainings.length ? `<div class="tiles">${trainings.map((t) => `
    <a class="tile" href="#/egitim/${t.id}">
      <div class="tile-art">${icon("book")}</div>
      <div class="tile-body"><b>${esc(t.title || t.area.baslik)}</b><small>${esc(t.area.baslik)}</small></div>
      <div class="tile-foot">${badge(t.status)}<span class="muted small">${fmtDate(t.created_at, false)}</span></div>
    </a>`).join("")}</div>`
    : `<section class="card">${empty("book", "Henüz eğitim yok", "Seans analizinden sonra otomatik hazırlanır.")}</section>`;
}

function tabImages(body, { c, images }) {
  body.innerHTML = `
    <div class="section-head"><p class="muted">Hedef panosu, günlük, zihin haritası…</p>
      <button class="btn btn-primary" id="img-upload">${icon("upload")}Görsel yükle</button></div>
    ${images.length ? images.map((i) => `<section class="card image-card">
      <img src="/api/images/${i.id}/file" alt="${esc(i.note || "Danışan görseli")}">
      <div>
        <div class="card-head"><h2>${esc(i.note || "Görsel")}</h2>${badge(i.status)}</div>
        <p class="muted small">${fmtDate(i.created_at)}</p>
        ${i.analysis ? `<p>${esc(i.analysis.gorsel_ozeti)}</p>
          <div class="grid-2 tight"><div><h4>Gözlemler</h4>${bullets(i.analysis.gozlemler)}</div><div><h4>Temalar</h4>${bullets(i.analysis.temalar)}</div></div>
          <h4>Koç için sorular</h4>${bullets(i.analysis.koc_icin_sorular)}
          <h4>Gelişim süreciyle bağlantısı</h4><p>${esc(i.analysis.gelisim_baglantisi)}</p>`
          : i.status === "hata" ? `<p class="form-error">${esc(i.error)}</p>` : `<p class="muted">Analiz ediliyor…</p>`}
      </div></section>`).join("")
      : `<section class="card">${empty("image", "Henüz görsel yok", "Görsel yükleyerek analiz başlatın.")}</section>`}`;
  $("#img-upload").addEventListener("click", () => c.consent ? uploadImageForm(c) : toast("Önce danışanın KVKK açık rızasını kaydedin", "err"));
  if (images.some((i) => !done(i.status))) poll(async () => {
    const fresh = await api(`/api/clients/${c.id}/images`);
    if (fresh.every((i) => done(i.status))) route();
  });
}

const MOOD = ["", "😞", "😕", "😐", "🙂", "😄"];

function tabTasks(body, { c, ag }) {
  const b = ag.behavior;
  body.innerHTML = `
    <div class="kpis">
      ${kpi("Görev tamamlama", b.gorev_tamamlama_orani != null ? `%${b.gorev_tamamlama_orani}` : "—", "", "check")}
      ${kpi("Tamamlanan", `${b.gorev_tamamlanan}/${b.gorev_toplam}`, "", "check")}
      ${kpi("Geciken", b.geciken_gorev, "", "clock", b.geciken_gorev ? "low" : "")}
      ${kpi("Ruh hali ort.", b.ruh_hali_ortalama ?? "—", `${b.checkin_sayisi} check-in`, "message")}
    </div>
    <div class="grid-2">
      <section class="card"><div class="card-head"><h2>Görevler</h2></div>${taskList(ag.tasks)}</section>
      <section class="card"><div class="card-head"><h2>Ruh hali seyri</h2></div>${moodChart(b.ruh_hali_serisi)}
        ${ag.checkins.length ? `<h4>Son notlar</h4>${ag.checkins.slice(-4).reverse().map((ch) =>
          `<div class="note-line"><span>${MOOD[ch.mood]}</span><div>${esc(ch.note || "—")}<small>${fmtDate(ch.created_at)}</small></div></div>`).join("")}` : ""}
      </section>
    </div>`;
  bindTaskButtons(() => route());
}

function taskList(tasks) {
  if (!tasks.length) return `<p class="muted">Seans analizinden sonra görevler burada otomatik oluşur.</p>`;
  const label = { acik: "Açık", yapildi: "Tamamlandı", yapilmadi: "Yapılmadı" };
  return tasks.map((t) => `<div class="task task-${t.status}">
    <div><b>${esc(t.text)}</b><small>Son gün ${fmtDate(t.due_date, false)} · ${label[t.status]}</small></div>
    <div class="task-actions">
      <button class="icon-btn ${t.status === "yapildi" ? "on" : ""}" title="Tamamlandı" data-task="${t.id}" data-status="yapildi">✓</button>
      <button class="icon-btn ${t.status === "yapilmadi" ? "on-bad" : ""}" title="Yapılmadı" data-task="${t.id}" data-status="yapilmadi">✕</button>
    </div></div>`).join("");
}

function bindTaskButtons(refresh) {
  $$("[data-task]", page).forEach((btn) => btn.addEventListener("click", async () => {
    await sendJSON(`/api/tasks/${btn.dataset.task}`, { status: btn.dataset.status }, "PATCH");
    refresh();
  }));
}

function moodChart(series) {
  if (!series.length) return `<p class="muted">Danışan check-in yaptıkça burada grafik oluşur.</p>`;
  return `<div class="mood-chart">${series.map((m) => `<div class="mood-col" title="${esc(m.tarih)}: ${m.puan}/5">
    <div class="mood-bar"><span class="${scoreClass(m.puan)}" style="height:${m.puan * 20}%"></span></div>
    <span>${MOOD[m.puan]}</span><small>${esc(m.tarih.slice(5))}</small></div>`).join("")}</div>`;
}

const KIND = {
  takip: ["message", "Seans sonrası takip"], hatirlatma: ["clock", "Görev hatırlatma"], checkin: ["message", "Check-in daveti"],
  uyari: ["alert", "Koça uyarı"], egitim: ["book", "Otomatik eğitim"], plan: ["check", "Plan takibi"],
};

function tabAgent(body, { c, ag, ev }) {
  const sent = (id) => (ev?.notifications || []).filter((n) => n.action_id === id && n.channel !== "uygulama");
  body.innerHTML = `
    <section class="card">
      <div class="card-head"><div><h2>Ajan akışı</h2></div>
        <button class="btn btn-secondary" id="agent-run">${icon("bot")}Şimdi kontrol et</button></div>
      ${ag.actions.length ? `<div class="timeline">${ag.actions.map((a) => `
        <div class="event ${a.applied ? "" : "skipped"} kind-${a.kind}">
          <span class="event-ic">${icon(KIND[a.kind]?.[0] || "bot")}</span>
          <div class="event-body">
            <div class="row"><b>${KIND[a.kind]?.[1] || a.kind}</b><span class="tag">${a.target === "koc" ? "Koça" : "Danışana"}</span>
              ${a.applied ? "" : `<span class="tag">Atlandı</span>`}<span class="muted small">${fmtDate(a.created_at)}</span></div>
            ${a.message ? `<p>${esc(a.message)}</p>` : ""}
            ${sent(a.id).length ? `<div class="chips">${sent(a.id).map((n) => `<span class="tag" title="${esc(n.detail)}">${CHANNEL[n.channel]}: ${NSTATUS[n.status]}</span>`).join("")}</div>` : ""}
            <details><summary>Ajanın gerekçesi</summary><p class="muted small">${esc(a.reason)}</p></details>
          </div></div>`).join("")}</div>` : empty("bot", "Ajan henüz bir eylem yapmadı")}
    </section>`;
  $("#agent-run").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      const r = await api(`/api/clients/${c.id}/agent/run`, { method: "POST" });
      toast(r.done.length ? `Ajan ${r.done.length} eylem değerlendirdi` : "Şu an yapılacak yeni bir şey yok");
      if (r.done.length) route();
    } catch (err) { toast(err.message, "err"); }
    btn.disabled = false;
  });
}

// ===================================================================
// Seans detayı
// ===================================================================

const SESSION_STEPS = [["transkript", "Transkript"], ["konusmaci_ayrimi", "Konuşmacı ayrımı"], ["gorsel", "Görsel analiz"], ["rapor", "Seans raporu"], ["icf", "ICF puanlaması"]];
const SESSION_TABS = [["rapor", "Seans raporu"], ["icf", "Koç değerlendirmesi"], ["gorsel", "Görsel analiz"], ["ses", "Ses analizi"], ["transkript", "Transkript"]];

async function viewSession(id, tab) {
  const s = await api(`/api/sessions/${id}`);
  const c = await api(`/api/clients/${s.client_id}`);
  setHeader([["Danışanlar", "#/danisanlar"], [c.name, `#/danisan/${c.id}/seanslar`], [s.title]],
    s.status === "tamamlandi" ? `<button class="btn btn-secondary" onclick="window.print()">${icon("print")}Yazdır / PDF</button>` : "");

  const head = `<div class="page-title row between"><div><h1>${esc(s.title)}</h1>
    <p class="muted">${esc(c.name)} · ${fmtDate(s.created_at)}</p></div>${badge(s.status)}</div>`;

  if (s.status !== "tamamlandi") {
    const steps = s.source === "foto" ? SESSION_STEPS.filter(([k]) => k === "gorsel" || k === "rapor")
      : SESSION_STEPS.filter(([k]) => k !== "gorsel" || s.source === "video");
    const idx = steps.findIndex(([k]) => k === s.status);
    page.innerHTML = head + (s.status === "hata"
      ? `<section class="card banner-err"><h2>Analiz tamamlanamadı</h2><p>${esc(s.error)}</p><button class="btn btn-primary" id="retry">Tekrar dene</button></section>`
      : `<section class="card"><h2>Seans analiz ediliyor</h2>
        <div class="stepper">${steps.map(([k, l], i) => `<div class="step ${i < idx ? "done" : i === idx ? "now" : ""}">
          <span class="step-dot">${i < idx ? "✓" : i + 1}</span><span>${l}</span></div>`).join("")}</div>
        <p class="muted small">Arka planda sürer.</p></section>`);
    $("#retry")?.addEventListener("click", async () => { await api(`/api/sessions/${id}/retry`, { method: "POST" }); route(); });
    if (s.status !== "hata") poll(async () => {
      const f = await api(`/api/sessions/${id}`);
      if (f.status !== s.status) route();
    });
    return;
  }

  const isText = s.metrics?.kaynak_turu === "metin";
  const isPhoto = s.source === "foto";
  const has = { icf: !!s.icf, gorsel: !!s.visual, ses: !isText && !isPhoto, transkript: !!s.transcript?.length };
  const sTabs = SESSION_TABS.filter(([k]) => has[k] ?? true)
    .map(([k, l]) => [k, k === "transkript" && isText ? "Yazışma" : l]);
  if (tab && !sTabs.some(([k]) => k === tab)) tab = "rapor";
  if (isText && tab === "ses") tab = "rapor";
  page.innerHTML = head + tabs(`#/seans/${id}`, sTabs, tab) + `<section id="tab-body"></section>`;
  ({ rapor: sessionReport, icf: sessionICF, gorsel: sessionVisual, ses: sessionVoice, transkript: sessionTranscript }[tab] || sessionReport)($("#tab-body"), s);
}

function sessionReport(body, s) {
  const r = s.report;
  body.innerHTML = `
    <section class="card"><h2>Seans özeti</h2><p class="lead">${esc(r.ozet)}</p>
      <div class="banner banner-info">${icon("database")}<div><b>Danışan hafızası</b><p>${esc(r.onceki_seanslarla_baglanti)}</p></div></div></section>
    <div class="grid-3">
      <section class="card"><h2>Hedefler</h2>${bullets(r.danisan_hedefleri)}</section>
      <section class="card"><h2>Ana temalar</h2><div class="chips">${r.ana_temalar.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div></section>
      <section class="card"><h2>Danışanın görevleri</h2>${bullets(r.danisan_gorevleri)}</section>
    </div>
    <section class="card"><div class="card-head"><div><h2>Gelişim alanları</h2></div></div>
      ${r.gelisim_alanlari.map((g, i) => `<div class="area-row">
        <div><b>${esc(g.baslik)}</b><p>${esc(g.aciklama)}</p><blockquote>${esc(g.kanit)}</blockquote></div>
        <button class="btn btn-secondary no-print" data-area="${i}">${icon("sparkles")}Eğitim oluştur</button></div>`).join("")}
    </section>
    ${(r.duygu_dili || []).length ? `<section class="card"><div class="card-head"><h2>💬 Duygu dili</h2>
        <span class="muted small">Danışanın kendi kelimeleriyle söyledikleri · yüz ve ses tonundan çıkarım yok</span></div>
      <div class="emotions">${r.duygu_dili.map((e) => `<div class="emotion"><b>${esc(e.duygu)}</b><span>${esc(e.alinti)}</span></div>`).join("")}</div></section>` : ""}
    ${(r.plan_degerlendirmesi || []).length ? `<section class="card"><h2>🎯 Önceki planların izi</h2>${r.plan_degerlendirmesi.map((p) => `
      <div class="obs-line">${p.bahsedildi ? "✅" : "➖"}<span><b>${esc(p.plan)}</b><br><span class="muted">${esc(p.kanit)}</span></span></div>`).join("")}</section>` : ""}
    <section class="card"><h2>Sonraki seans için öneriler</h2>${bullets(r.sonraki_seans_onerileri)}</section>`;
  $$("[data-area]", body).forEach((btn) => btn.addEventListener("click", async () => {
    btn.disabled = true;
    const t = await sendJSON(`/api/sessions/${s.id}/trainings`, { area_index: Number(btn.dataset.area) });
    location.hash = `#/egitim/${t.id}`;
  }));
}

function sessionVisual(body, s) {
  const v = s.visual;
  if (v.hata) {
    body.innerHTML = `<section class="card">${empty("image", "Görsel analiz yapılamadı", esc(v.hata))}</section>`;
    return;
  }
  body.innerHTML = `
    <section class="card"><h2>Görsel özet</h2><p class="lead">${esc(v.genel_gozlem)}</p>
      <p class="muted small">${icon("shield")} Yüz ifadesinden duygu çıkarımı yapılmaz; yalnızca görünen içerik yorumlanır.</p></section>
    <div class="frames">${v.kareler.map((k) => `
      <figure class="frame">
        ${k.n != null ? `<img src="/api/sessions/${s.id}/frames/${k.n}" alt="Kare ${k.kare_no}">` : ""}
        <figcaption><span class="tag">${k.t != null ? fmtSec(k.t) : `Foto ${k.kare_no}`}</span> ${esc(k.gorulen)}</figcaption>
      </figure>`).join("")}</div>
    <div class="grid-2">
      <section class="card"><h2>Paylaşılan materyaller</h2>${bullets(v.paylasilan_materyaller)}</section>
      <section class="card"><h2>Koç için notlar</h2>${bullets(v.koc_icin_notlar)}</section>
    </div>
    <section class="card"><h2>${v.tur === "foto" ? "Koçun notuyla bağlantısı" : "Konuşmayla bağlantısı"}</h2><p>${esc(v.konusmayla_baglanti)}</p></section>`;
}

function sessionICF(body, s) {
  const icf = s.icf;
  body.innerHTML = `
    <div class="grid-icf">
      <section class="card score-card"><span class="muted">ICF ortalaması</span>
        <div class="big-score ${scoreClass(icf.ortalama)}">${icf.ortalama}<small>/5</small></div>
        <p class="muted small">Gelişim amaçlı ön değerlendirme</p></section>
      <section class="card"><h2>Güçlü yönler</h2>${bullets(icf.guclu_yonler)}</section>
      <section class="card"><h2>Gelişim önerileri</h2>${bullets(icf.gelisim_onerileri)}</section>
    </div>
    <section class="card"><div class="card-head"><h2>Yetkinlik puanları</h2><span class="muted small">Ayrıntı için tıklayın</span></div>
      ${icf.yetkinlikler.map((c) => `<details class="comp">
        <summary><span class="comp-code">${esc(c.kod)}</span><span class="comp-name">${esc(c.ad)}</span>
          <span class="meter"><span class="${scoreClass(c.puan)}" style="width:${c.puan * 20}%"></span></span><b class="score ${scoreClass(c.puan)}">${c.puan}</b></summary>
        <div class="comp-body"><p>${esc(c.gerekce)}</p>${c.kanitlar.map((k) => `<blockquote>${esc(k)}</blockquote>`).join("")}
          <p><b>Öneri:</b> ${esc(c.gelistirme_onerisi)}</p></div></details>`).join("")}
      <p class="muted">${esc(icf.genel_yorum)}</p>
    </section>`;
}

function sessionVoice(body, s) {
  const m = s.metrics;
  const v = (x, suf = "") => (x == null ? "—" : `${x}${suf}`);
  body.innerHTML = `
    <div class="kpis">
      ${kpi("Süre", `${m.sure_dk} dk`, `${m.segment_sayisi} konuşma bölümü`, "clock")}
      ${kpi("Koçun konuşma payı", `%${m.koc_konusma_orani}`, "İdeal: %20–40", "mic", m.koc_konusma_orani <= 40 ? "good" : m.koc_konusma_orani <= 55 ? "mid" : "low")}
      ${kpi("Açık uçlu soru oranı", v(m.acik_uclu_oran, "%"), `${m.koc_soru_sayisi} soru`, "message", scoreClass(m.acik_uclu_oran == null ? null : m.acik_uclu_oran / 20))}
      ${kpi("Düşünme alanı", v(m.ort_bekleme_sn, " sn"), "Sorudan sonra ortalama bekleme", "clock")}
    </div>
    <section class="card"><h2>Konuşma dengesi</h2>
      <div class="balance"><span style="width:${m.koc_konusma_orani}%" class="b-koc">Koç %${m.koc_konusma_orani}</span>
        <span style="width:${m.danisan_konusma_orani}%" class="b-dan">Danışan %${m.danisan_konusma_orani}</span></div>
      <table class="table compact"><tbody>
        <tr><td>Koçun konuşma hızı</td><td><b>${v(m.koc_konusma_hizi, " kelime/dk")}</b></td></tr>
        <tr><td>Danışanın konuşma hızı</td><td><b>${v(m.danisan_konusma_hizi, " kelime/dk")}</b></td></tr>
        <tr><td>Açık uçlu / kapalı soru</td><td><b>${m.acik_uclu_soru} / ${m.kapali_soru}</b></td></tr>
        <tr><td>En uzun kesintisiz koç konuşması</td><td><b>${m.en_uzun_koc_konusmasi_sn} sn</b></td></tr>
        <tr><td>3 sn üzeri sessizlik</td><td><b>${v(m.uzun_sessizlik)}</b></td></tr>
      </tbody></table>
    </section>`;
}

function sessionTranscript(body, s) {
  const isText = s.metrics?.kaynak_turu === "metin";
  body.innerHTML = `<section class="card transcript">${s.transcript.map((t, i) => `
    <div class="line line-${t.speaker}"><span class="time">${isText ? `#${i + 1}` : fmtSec(t.start)}</span>
      <b>${t.speaker === "koc" ? "Koç" : "Danışan"}${t.name ? `<small>${esc(t.name)}</small>` : ""}</b><p>${esc(t.text)}</p></div>`).join("")}</section>`;
}

// ===================================================================
// Eğitim içeriği
// ===================================================================

const CARD_TINTS = ["#fef3c7", "#d1fae5", "#dbeafe", "#fce7f3", "#ede9fe", "#ffedd5"];

async function viewTraining(id) {
  const t = await api(`/api/trainings/${id}`);
  const title = t.content?.baslik || t.area.baslik;
  const crumbs = ME.role === "danisan"
    ? [["Gelişimim", "#/gelisim"], ["Eğitimlerim", "#/gelisim/egitimler"], [title]]
    : await api(`/api/clients/${t.client_id}`).then((c) => [["Danışanlar", "#/danisanlar"], [c.name, `#/danisan/${c.id}/egitimler`], [title]]);
  setHeader(crumbs,
    t.content ? `<button class="btn btn-secondary" onclick="window.print()">${icon("print")}Yazdır / PDF</button>` : "");
  const papers = t.papers || [];
  const cite = (nums) => (nums || []).filter((n) => papers[n - 1]).map((n) => `<a href="#src-${n}" class="cite" onclick="event.preventDefault();document.getElementById('src-${n}').scrollIntoView({behavior:'smooth'})">[${n}]</a>`).join(" ");

  if (!t.content) {
    page.innerHTML = `<section class="card"><h1>${esc(t.area.baslik)}</h1>${badge(t.status)}
      ${t.status === "hata" ? `<p class="form-error">${esc(t.error)}</p><button class="btn btn-primary" id="retry">Tekrar dene</button>`
        : `<div class="stepper">${[["kaynak_arama", "Bilimsel kaynak tarama"], ["icerik_uretimi", "Kişiye özel içerik üretimi"]].map(([k, l], i) => {
          const idx = t.status === "icerik_uretimi" ? 1 : 0;
          return `<div class="step ${i < idx ? "done" : i === idx ? "now" : ""}"><span class="step-dot">${i < idx ? "✓" : i + 1}</span><span>${l}</span></div>`; }).join("")}</div>`}
    </section>`;
    $("#retry")?.addEventListener("click", async () => { await api(`/api/trainings/${id}/retry`, { method: "POST" }); route(); });
    if (t.status !== "hata") poll(async () => { const f = await api(`/api/trainings/${id}`); if (f.status !== t.status) route(); });
    return;
  }
  renderLearning(t, cite, papers);
}

// ----- Oyunlaştırılmış eğitim -----
// Araştırmaya dayalı tasarım: geri getirme (quiz, mit kartları, eşleştirme), aralıklı tekrar
// (2 gün sonra tekrar turu), eğer–o zaman planı (Gollwitzer & Sheeran 2006), hata yapma özgürlüğü
// (eşleştirmede ceza yok), puan/seviye/rozet. Danışanlar arası yarış (liderlik tablosu) bilerek yok.

const XP = { quiz: 20, myth: 10, best: 30, choice: 10, step: 5, match: 10, plan: 20, conf: 5, story: 10, review: 10 };
const LEVELS = [[0, "🌱", "Çaylak"], [0.3, "🧭", "Kâşif"], [0.6, "🚀", "Uzman"], [0.9, "🏆", "Usta"]];
const REVIEW_DAYS = 2;
const DAY = 86400000;

function learningState(id) {
  try { return JSON.parse(localStorage.getItem(`farkora-egitim-${id}`)) || {}; } catch { return {}; }
}
function saveLearningState(id, st) {
  try { localStorage.setItem(`farkora-egitim-${id}`, JSON.stringify(st)); } catch { /* depolama kapalı olabilir */ }
}

function confetti(x, y) {
  const colors = ["#7c3aed", "#db2777", "#f59e0b", "#10b981", "#3b82f6"];
  for (let i = 0; i < 26; i++) {
    const c = document.createElement("i");
    c.className = "confetti";
    c.style.left = `${x}px`;
    c.style.top = `${y}px`;
    c.style.background = colors[i % colors.length];
    c.style.setProperty("--dx", `${(Math.random() - 0.5) * 360}px`);
    c.style.setProperty("--dy", `${-120 - Math.random() * 220}px`);
    c.style.setProperty("--r", `${Math.random() * 720}deg`);
    document.body.appendChild(c);
    setTimeout(() => c.remove(), 1100);
  }
}

function floatXp(el, amount) {
  if (!amount) return;
  const r = el.getBoundingClientRect();
  const f = document.createElement("b");
  f.className = "xp-float";
  f.textContent = `+${amount}`;
  f.style.left = `${r.left + r.width / 2}px`;
  f.style.top = `${r.top}px`;
  document.body.appendChild(f);
  setTimeout(() => f.remove(), 1000);
}

function shuffled(arr, seed) {
  // Sayfa her açıldığında aynı sırada kalsın diye tohumlu karıştırma
  const a = arr.map((x, i) => [x, i]);
  let s = seed || 1;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 9301 + 49297) % 233280;
    const j = Math.floor((s / 233280) * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function renderLearning(t, cite, papers) {
  const ct = t.content;
  const st = learningState(t.id);
  const savedPlans = t.commitments || [];
  if (savedPlans.length) st.plan = true;
  st.quiz ||= {}; st.myth ||= {}; st.steps ||= {}; st.match ||= {}; st.review ||= {};
  st.first ||= Date.now();
  const myths = ct.mit_gercek || [];
  const sc = ct.senaryo;
  const steps = ct.haftalik_deneme.adimlar;
  const pairs = ct.eslestirme || [];
  const ifThen = ct.eger_o_zaman;
  const cards = ct.kartlar;

  const total = ct.quiz.length + myths.length + (sc ? 1 : 0) + steps.length + pairs.length
    + (ifThen ? 1 : 0) + 1 /* güven ölçer */ + 1 /* hikâye kartları */;
  const maxXp = ct.quiz.length * XP.quiz + myths.length * XP.myth + (sc ? XP.best : 0) + steps.length * XP.step
    + pairs.length * XP.match + (ifThen ? XP.plan : 0) + XP.conf * 2 + XP.story;

  const score = () => {
    let xp = 0, done = 0;
    ct.quiz.forEach((q, i) => { if (st.quiz[i] != null) { done++; if (st.quiz[i] === q.dogru_index) xp += XP.quiz; } });
    myths.forEach((m, i) => { if (st.myth[i] != null) { done++; if (st.myth[i] === m.gercek_mi) xp += XP.myth; } });
    if (sc && st.scenario != null) { done++; xp += sc.secenekler[st.scenario]?.en_iyi ? XP.best : XP.choice; }
    steps.forEach((_, i) => { if (st.steps[i]) { done++; xp += XP.step; } });
    pairs.forEach((_, i) => { if (st.match[i]) { done++; xp += XP.match; } });
    if (ifThen && st.plan) { done++; xp += XP.plan; }
    if (st.confBefore != null) { done++; xp += XP.conf; }
    if (st.storyDone) { done++; xp += XP.story; }
    if (st.confAfter != null) xp += XP.conf;
    Object.values(st.review).forEach((ok) => { if (ok) xp += XP.review; });
    return { xp, done, pct: Math.round((done / total) * 100) };
  };
  const levelOf = (xp) => [...LEVELS].reverse().find(([f]) => xp >= f * maxXp);

  const s0 = score();
  const finished = s0.done === total;
  if (finished && !st.finishedAt) st.finishedAt = Date.now();
  const reviewOpen = st.finishedAt && Date.now() - st.finishedAt >= REVIEW_DAYS * DAY;
  const daysLeft = st.finishedAt ? Math.max(1, Math.ceil((st.finishedAt + REVIEW_DAYS * DAY - Date.now()) / DAY)) : REVIEW_DAYS;
  const reviewQs = [
    ...ct.quiz.map((q, i) => ({ key: `q${i}`, soru: q.soru, secenekler: q.secenekler, dogru: q.dogru_index, aciklama: q.aciklama })),
    ...myths.map((m, i) => ({ key: `m${i}`, soru: `“${m.ifade}” Mit mi, gerçek mi?`, secenekler: ["🙅 Mit", "✅ Gerçek"], dogru: m.gercek_mi ? 1 : 0, aciklama: m.aciklama })),
  ].slice(0, 4);

  const matchRight = shuffled(pairs, t.id * 7 + 3);
  const storyIdx = Math.min(st.storyIdx || 0, cards.length - 1);
  const lowerFirst = (x) => x.trim().replace(/[.\s]+$/, "").replace(/^\S/, (ch) => ch.toLocaleLowerCase("tr"));
  const planText = (p) => `Eğer ${lowerFirst(p.durum)}, o zaman ${lowerFirst(p.davranis)}.`;

  page.innerHTML = `
    <div class="hero">
      <span class="hero-tag">${icon("sparkles")}Kişiye özel mikro-eğitim · ${esc(t.area.baslik)}</span>
      <h1>${esc(ct.baslik)}</h1><p>${esc(ct.kanca)}</p>
    </div>
    <div class="xpbar no-print">
      <div class="xp-level" id="xp-level"></div>
      <div class="xp-pill">⭐ <b id="xp">0</b> / ${maxXp}</div>
      <div class="xp-track"><span id="xp-fill"></span></div>
      <div class="xp-pct" id="xp-pct">%0</div>
    </div>
    <div id="badge-slot"></div>
    ${ct.koc_ozeti && ME.role !== "danisan" ? `<div class="banner banner-info no-print">${icon("sparkles")}<div><b>Koç için özet</b><p>${esc(ct.koc_ozeti)}</p></div></div>` : ""}

    <section class="card game conf no-print">
      <div class="game-head"><span class="game-ic">🎚️</span><div><h2>Başlamadan önce</h2>
        <p class="muted">Bu konuda kendini şu an ne kadar hazır hissediyorsun?</p></div></div>
      ${st.confBefore != null
        ? `<p class="conf-saved">Başlangıç puanın: <b>${st.confBefore}/10</b>. Sonda tekrar soracağız.</p>`
        : `<div class="conf-row"><span>1</span><input type="range" min="1" max="10" value="5" id="conf-before"><span>10</span>
            <b class="conf-val" id="conf-before-val">5</b><button class="btn btn-primary" id="conf-before-save">Kaydet</button></div>`}
    </section>

    <h2 class="section-title">💡 Bilmen gerekenler <span class="muted small">· hikâye gibi kaydır</span></h2>
    <section class="story no-print" style="--tint:${CARD_TINTS[storyIdx % CARD_TINTS.length]}">
      <div class="story-bars">${cards.map((_, i) => `<span class="${i < storyIdx ? "done" : i === storyIdx ? "now" : ""}"></span>`).join("")}</div>
      <button class="story-nav prev" aria-label="Önceki kart" ${storyIdx === 0 ? "disabled" : ""}>‹</button>
      <div class="story-card">
        <div class="story-ic">${esc(cards[storyIdx].ikon)}</div>
        <h3>${esc(cards[storyIdx].baslik)}</h3><p>${esc(cards[storyIdx].metin)}</p><div>${cite(cards[storyIdx].kaynak_no)}</div>
        <span class="muted small">${storyIdx + 1} / ${cards.length}</span>
      </div>
      <button class="story-nav next" aria-label="Sonraki kart">${storyIdx === cards.length - 1 ? "✓" : "›"}</button>
    </section>
    <div class="lcards print-only">${cards.map((k, i) => `<div class="lcard" style="--tint:${CARD_TINTS[i % CARD_TINTS.length]}">
      <div class="lcard-ic">${esc(k.ikon)}</div><b>${esc(k.baslik)}</b><p>${esc(k.metin)}</p><div>${cite(k.kaynak_no)}</div></div>`).join("")}</div>

    ${myths.length ? `<h2 class="section-title">🕵️ Mit mi, gerçek mi?</h2>
    <div class="myths">${myths.map((m, i) => `
      <div class="myth ${st.myth[i] != null ? "flipped" : ""}" data-i="${i}">
        <div class="myth-inner">
          <div class="myth-front"><p>“${esc(m.ifade)}”</p>
            <div class="row center"><button class="btn btn-secondary" data-ans="false">🙅 Mit</button><button class="btn btn-secondary" data-ans="true">✅ Gerçek</button></div></div>
          <div class="myth-back ${st.myth[i] === m.gercek_mi ? "ok" : "no"}">
            <b>${m.gercek_mi ? "✅ Gerçek" : "🙅 Mit"} · ${st.myth[i] === m.gercek_mi ? "Bildin! +" + XP.myth : "Bu sefer olmadı"}</b>
            <p>${esc(m.aciklama)}</p><div>${cite(m.kaynak_no)}</div></div>
        </div>
      </div>`).join("")}</div>` : ""}

    <h2 class="section-title">📖 Mini hikâye</h2>
    <div class="comic">${ct.cizgi_roman.map((p, i) => `<div class="panel"><span class="panel-no">${i + 1}</span>
      <div class="scene">${esc(p.sahne)}</div><div class="bubble">${esc(p.konusma)}</div>
      <div class="who"><span>${esc(p.ikon)}</span>${esc(p.karakter)}</div></div>`).join("")}</div>

    ${pairs.length ? `<h2 class="section-title">🧩 Eşleştir <span class="muted small">· önce soldan, sonra sağdan seç; yanlışta ceza yok</span></h2>
    <section class="card match">
      <div class="match-col">${pairs.map((p, i) => `<button class="match-item ${st.match[i] ? "ok" : ""}" data-l="${i}" ${st.match[i] ? "disabled" : ""}>${esc(p.kavram)}</button>`).join("")}</div>
      <div class="match-col">${matchRight.map(([p, i]) => `<button class="match-item ${st.match[i] ? "ok" : ""}" data-r="${i}" ${st.match[i] ? "disabled" : ""}>${esc(p.anlam)}</button>`).join("")}</div>
    </section>` : ""}

    ${sc ? `<h2 class="section-title">🎬 Sen olsan ne yapardın?</h2>
    <section class="card scenario"><p class="lead">${esc(sc.durum)}</p>
      ${sc.secenekler.map((o, i) => {
        const chosen = st.scenario === i, shown = st.scenario != null;
        return `<button class="choice ${shown && o.en_iyi ? "best" : ""} ${chosen && !o.en_iyi ? "picked" : ""}" data-c="${i}" ${shown ? "disabled" : ""}>
          <span>${esc(o.metin)}</span>${shown && (chosen || o.en_iyi) ? `<small>${esc(o.sonuc)}</small>` : ""}</button>`;
      }).join("")}
    </section>` : ""}

    <div class="grid-2">
      <section class="card"><h2>🧠 Kendini dene</h2>${ct.quiz.map((q, qi) => {
        const ans = st.quiz[qi];
        return `<div class="quiz" data-q="${qi}"><p><b>${qi + 1}. ${esc(q.soru)}</b></p>
          ${q.secenekler.map((o, oi) => `<button class="option ${ans != null && oi === q.dogru_index ? "right" : ""} ${ans === oi && oi !== q.dogru_index ? "wrong" : ""}" data-i="${oi}" ${ans != null ? "disabled" : ""}>${esc(o)}</button>`).join("")}
          <p class="explain" ${ans != null ? "" : "hidden"}>${esc(q.aciklama)}</p></div>`;
      }).join("")}</section>
      <section class="card"><h2>🧪 Bu haftanın deneyi</h2><p class="muted">${esc(ct.haftalik_deneme.baslik)}</p>
        ${steps.map((a, i) => `<label class="check"><input type="checkbox" data-s="${i}" ${st.steps[i] ? "checked" : ""}><span>${esc(a)}</span></label>`).join("")}
        <p class="closing">${esc(ct.kapanis)}</p></section>
    </div>

    ${ifThen ? `<h2 class="section-title">🎯 Eğer–o zaman planım <span class="muted small">· bilimsel olarak hedefe ulaşmayı kolaylaştırıyor</span></h2>
    <section class="card plan">
      ${savedPlans.length && !st.addPlan ? `${savedPlans.map((k) => `<div class="plan-card"><span>📌</span><p>${esc(planText(k))}</p></div>`).join("")}
          <p class="muted small plan-note">${icon("bot")} Davranış Takip ajanı ${fmtDate(savedPlans[0].check_date, false)} günü “oldu mu, ne yaptın?” diye soracak.
            <button class="link-btn no-print" id="plan-edit">Bir plan daha kur</button></p>`
        : `<div class="plan-build">
          <div><b class="plan-label">Eğer…</b><div class="chips-pick">${ifThen.durumlar.map((d, i) => `<button class="pick" data-d="${i}">${esc(d)}</button>`).join("")}</div>
            <input id="plan-d" placeholder="ya da kendi durumunu yaz"></div>
          <div><b class="plan-label">o zaman…</b><div class="chips-pick">${ifThen.davranislar.map((d, i) => `<button class="pick" data-b="${i}">${esc(d)}</button>`).join("")}</div>
            <input id="plan-b" placeholder="ya da kendi davranışını yaz"></div>
          <div class="plan-preview" id="plan-preview">Bir durum ve bir davranış seç 👆</div>
          <button class="btn btn-primary" id="plan-save" disabled>Planımı kaydet · +${XP.plan}</button>
        </div>`}
    </section>` : ""}

    <section class="card game conf no-print" id="conf-after-box" ${finished ? "" : "hidden"}>
      <div class="game-head"><span class="game-ic">📈</span><div><h2>Şimdi nasılsın?</h2>
        <p class="muted">Eğitimin başında kendine <b>${st.confBefore ?? "?"}/10</b> vermiştin. Şimdi?</p></div></div>
      ${st.confAfter != null
        ? `<p class="conf-saved">${st.confAfter}/10 ${st.confAfter > st.confBefore ? `· <b class="up">+${st.confAfter - st.confBefore} puan artış 🎉</b>` : "· Kaydedildi. Deney yaptıkça değişecek."}</p>`
        : `<div class="conf-row"><span>1</span><input type="range" min="1" max="10" value="${st.confBefore ?? 5}" id="conf-after"><span>10</span>
            <b class="conf-val" id="conf-after-val">${st.confBefore ?? 5}</b><button class="btn btn-primary" id="conf-after-save">Kaydet</button></div>`}
    </section>

    <section class="card game review no-print">
      <div class="game-head"><span class="game-ic">${reviewOpen ? "🔁" : "🔒"}</span><div><h2>Tekrar turu</h2>
        <p class="muted">${reviewOpen ? "Birkaç gün geçti; hatırlıyor musun? Her doğru +" + XP.review
          : finished ? `${daysLeft} gün sonra açılacak. Aralıklı tekrar, öğrendiğini kalıcı yapar.`
          : "Eğitimi bitir; 2 gün sonra kısa bir tekrar turu açılacak."}</p></div></div>
      ${reviewOpen ? reviewQs.map((q) => {
        const ans = st.review[q.key];
        return `<div class="quiz" data-rq="${q.key}"><p><b>${esc(q.soru)}</b></p>
          ${q.secenekler.map((o, oi) => `<button class="option ${ans != null && oi === q.dogru ? "right" : ""}" data-i="${oi}" ${ans != null ? "disabled" : ""}>${esc(o)}</button>`).join("")}
          <p class="explain" ${ans != null ? "" : "hidden"}>${esc(q.aciklama)}</p></div>`;
      }).join("") : ""}
    </section>

    <section class="card"><h2>📚 Bilimsel kaynaklar</h2>
      <p class="muted small">OpenAlex · “${esc(t.query)}”</p>
      ${papers.length ? `<ol class="refs">${papers.map((p, i) => `<li id="src-${i + 1}">${esc(p.authors)} (${esc(p.year)}).
        <a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a> <span class="muted">· ${p.cited_by} atıf</span></li>`).join("")}</ol>`
        : `<p class="muted">Bu içerik için kaynak bulunamadı; genel bilgi olarak hazırlandı.</p>`}
    </section>`;

  let lastLevel = levelOf(s0.xp)[2];
  const update = () => {
    const s = score();
    const [, emo, name] = levelOf(s.xp);
    $("#xp").textContent = s.xp;
    $("#xp-pct").textContent = `%${s.pct}`;
    $("#xp-fill").style.width = `${s.pct}%`;
    $("#xp-level").textContent = `${emo} ${name}`;
    if (name !== lastLevel) {
      $("#xp-level").classList.remove("level-up"); void $("#xp-level").offsetWidth; $("#xp-level").classList.add("level-up");
      lastLevel = name;
    }
    if (s.done === total) {
      if (!st.finishedAt) {
        st.finishedAt = Date.now();
        saveLearningState(t.id, st);
        const r = $("#badge-slot").getBoundingClientRect(); confetti(r.left + r.width / 2, Math.max(80, r.top + 30));
      }
      $("#badge-slot").innerHTML = `<div class="badge-done">🏆 <div><b>Tebrikler, eğitimi tamamladın!</b><span>${s.xp} / ${maxXp} puan · ${emo} ${name}. Planını bu hafta dene; 2 gün sonra tekrar turu açılacak.</span></div></div>`;
      $("#conf-after-box").hidden = false;
    }
    saveLearningState(t.id, st);
  };
  const award = (el, amount, fn) => { fn(); floatXp(el, amount); update(); };
  const at = (el) => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  const rerender = () => { saveLearningState(t.id, st); const y = scrollY; renderLearning(t, cite, papers); scrollTo(0, y); };

  // Güven ölçer
  [["before", "confBefore"], ["after", "confAfter"]].forEach(([k, key]) => {
    const range = $(`#conf-${k}`);
    if (!range) return;
    range.addEventListener("input", () => ($(`#conf-${k}-val`).textContent = range.value));
    $(`#conf-${k}-save`).addEventListener("click", (e) => {
      award(e.target, XP.conf, () => { st[key] = Number(range.value); });
      if (key === "confAfter" && st.confAfter > (st.confBefore ?? 10)) confetti(...at(e.target));
      rerender();
    });
  });

  // Hikâye kartları
  const go = (d) => {
    const next = storyIdx + d;
    if (next >= cards.length) {
      if (!st.storyDone) { award($(".story"), XP.story, () => { st.storyDone = true; }); confetti(...at($(".story-nav.next"))); }
      st.storyIdx = 0;
    } else st.storyIdx = Math.max(0, next);
    rerender();
  };
  $(".story-nav.prev").addEventListener("click", () => go(-1));
  $(".story-nav.next").addEventListener("click", () => go(1));
  const story = $(".story");
  let touchX = null;
  story.addEventListener("touchstart", (e) => (touchX = e.touches[0].clientX), { passive: true });
  story.addEventListener("touchend", (e) => {
    if (touchX == null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
    touchX = null;
  });

  // Mit mi, gerçek mi?
  $$(".myth", page).forEach((card) => $$("[data-ans]", card).forEach((btn) => btn.addEventListener("click", () => {
    const i = Number(card.dataset.i), ans = btn.dataset.ans === "true";
    const ok = ans === myths[i].gercek_mi;
    award(card, ok ? XP.myth : 0, () => { st.myth[i] = ans; });
    const back = $(".myth-back", card);
    back.classList.toggle("ok", ok); back.classList.toggle("no", !ok);
    $("b", back).textContent = `${myths[i].gercek_mi ? "✅ Gerçek" : "🙅 Mit"} · ${ok ? `Bildin! +${XP.myth}` : "Bu sefer olmadı"}`;
    card.classList.add("flipped");
    if (ok) confetti(...at(card));
  })));

  // Eşleştir
  let pickL = null;
  $$("[data-l]", page).forEach((b) => b.addEventListener("click", () => {
    $$("[data-l]", page).forEach((x) => x.classList.remove("sel"));
    b.classList.add("sel"); pickL = Number(b.dataset.l);
  }));
  $$("[data-r]", page).forEach((b) => b.addEventListener("click", () => {
    if (pickL == null) { b.classList.add("shake"); setTimeout(() => b.classList.remove("shake"), 400); return; }
    const left = $(`[data-l="${pickL}"]`, page);
    if (Number(b.dataset.r) === pickL) {
      award(b, XP.match, () => { st.match[pickL] = true; });
      [left, b].forEach((x) => { x.classList.remove("sel"); x.classList.add("ok"); x.disabled = true; });
      confetti(...at(b));
      pickL = null;
    } else {
      [left, b].forEach((x) => { x.classList.add("shake"); setTimeout(() => x.classList.remove("shake"), 400); });
    }
  }));

  // Senaryo
  $$(".choice", page).forEach((btn) => btn.addEventListener("click", () => {
    const i = Number(btn.dataset.c), best = sc.secenekler[i].en_iyi;
    award(btn, best ? XP.best : XP.choice, () => { st.scenario = i; });
    if (best) confetti(...at(btn));
    rerender();
  }));

  // Quiz
  $$(".quiz[data-q]", page).forEach((quiz) => $$(".option", quiz).forEach((btn) => btn.addEventListener("click", () => {
    const qi = Number(quiz.dataset.q), q = ct.quiz[qi], oi = Number(btn.dataset.i);
    award(btn, oi === q.dogru_index ? XP.quiz : 0, () => { st.quiz[qi] = oi; });
    $$(".option", quiz).forEach((b) => { b.disabled = true; if (Number(b.dataset.i) === q.dogru_index) b.classList.add("right"); });
    if (oi !== q.dogru_index) btn.classList.add("wrong"); else confetti(...at(btn));
    $(".explain", quiz).hidden = false;
  })));

  // Haftalık deney
  $$("[data-s]", page).forEach((cb) => cb.addEventListener("change", () => {
    const i = Number(cb.dataset.s);
    award(cb.closest(".check"), cb.checked ? XP.step : 0, () => { st.steps[i] = cb.checked; });
  }));

  // Eğer–o zaman planı
  if (ifThen && (!savedPlans.length || st.addPlan)) {
    const draft = { durum: "", davranis: "" };
    const refresh = () => {
      const ok = draft.durum.trim() && draft.davranis.trim();
      $("#plan-preview").textContent = ok ? planText(draft) : "Bir durum ve bir davranış seç 👆";
      $("#plan-preview").classList.toggle("ready", !!ok);
      $("#plan-save").disabled = !ok;
    };
    $$("[data-d]", page).forEach((b) => b.addEventListener("click", () => {
      $$("[data-d]", page).forEach((x) => x.classList.toggle("on", x === b));
      draft.durum = ifThen.durumlar[Number(b.dataset.d)]; $("#plan-d").value = ""; refresh();
    }));
    $$("[data-b]", page).forEach((b) => b.addEventListener("click", () => {
      $$("[data-b]", page).forEach((x) => x.classList.toggle("on", x === b));
      draft.davranis = ifThen.davranislar[Number(b.dataset.b)]; $("#plan-b").value = ""; refresh();
    }));
    $("#plan-d").addEventListener("input", (e) => { $$("[data-d]", page).forEach((x) => x.classList.remove("on")); draft.durum = e.target.value; refresh(); });
    $("#plan-b").addEventListener("input", (e) => { $$("[data-b]", page).forEach((x) => x.classList.remove("on")); draft.davranis = e.target.value; refresh(); });
    $("#plan-save").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        const k = await sendJSON(`/api/trainings/${t.id}/commitment`, { durum: draft.durum.trim().slice(0, 200), davranis: draft.davranis.trim().slice(0, 200) });
        t.commitments = [k, ...savedPlans];
        const first = !st.plan;
        st.addPlan = false;
        award(btn, first ? XP.plan : 0, () => { st.plan = true; });
        confetti(...at(btn));
        rerender();
      } catch (err) { toast(err.message, "err"); btn.disabled = false; }
    });
  }
  $("#plan-edit")?.addEventListener("click", () => { st.addPlan = true; rerender(); });

  // Tekrar turu
  $$(".quiz[data-rq]", page).forEach((quiz) => $$(".option", quiz).forEach((btn) => btn.addEventListener("click", () => {
    const q = reviewQs.find((x) => x.key === quiz.dataset.rq), oi = Number(btn.dataset.i), ok = oi === q.dogru;
    award(btn, ok ? XP.review : 0, () => { st.review[q.key] = ok; });
    $$(".option", quiz).forEach((b) => { b.disabled = true; if (Number(b.dataset.i) === q.dogru) b.classList.add("right"); });
    if (!ok) btn.classList.add("wrong"); else confetti(...at(btn));
    $(".explain", quiz).hidden = false;
  })));

  update();
}


// ===================================================================
// 4 yapay zekâ ajanı
// ===================================================================

async function viewAgents() {
  const d = await api("/api/agents");
  setHeader([["Yapay Zekâ Ajanları"]]);
  const ch = d.kanallar;
  const chip = (on, label, offText = "simüle") => `<span class="tag ${on ? "tag-ok" : ""}">${label}: ${on ? "bağlı" : offText}</span>`;
  page.innerHTML = `
    <div class="page-title"><h1>Yapay zekâ ajanları</h1>
      <p class="muted">Dört ajan zincir gibi çalışır: biri bitirdiğinde diğerini besler.</p></div>
    <div class="agent-flow no-print">${d.agents.map((a, i) => `<span class="agent-step"><b>${a.ikon}</b>${esc(a.ad.split(" ").slice(0, 2).join(" "))}</span>${i < d.agents.length - 1 ? `<span class="agent-arrow">→</span>` : ""}`).join("")}</div>
    <div class="agent-grid">${d.agents.map((a) => `
      <section class="card agent-card">
        <div class="agent-head"><span class="agent-no">${a.no}</span><span class="agent-ic">${a.ikon}</span>
          <div><h2>${esc(a.ad)}</h2><p class="muted small">${esc(a.temel)}</p></div></div>
        ${bullets(a.gorev)}
        <div class="agent-io"><div><small>Girdi</small><p>${esc(a.girdi)}</p></div><span>→</span><div><small>Çıktı</small><p>${esc(a.cikti)}</p></div></div>
        <div class="agent-stats">${a.istatistik.map((s) => `<div><b>${s.deger}</b><small>${esc(s.ad)}</small></div>`).join("")}</div>
        <p class="muted small">${icon("database")} ${esc(a.modul)}</p>
      </section>`).join("")}</div>
    <section class="card"><h2>Bağlantılar</h2>
      <div class="chips">${chip(true, "Uygulama içi mesaj")}${chip(ch.eposta, "E-posta")}${chip(ch.whatsapp, "WhatsApp")}
        <span class="tag ${d.toplanti_botu === "recall" ? "tag-ok" : ""}">Toplantı botu: ${d.toplanti_botu === "recall" ? "Recall.ai bağlı" : "simülasyon"}</span></div>
      <p class="muted small">Bağlı olmayan kanallar “simüle” görünür.</p></section>`;
}

// ===================================================================
// Davranış kanıtı (koç): plan -> öz-bildirim -> paydaş gözlemi -> sonraki seans
// ===================================================================

const PLAN_STATUS = { aktif: ["Bekliyor", ""], yapildi: ["Yaptım", "ok"], kismen: ["Kısmen", "wait"], firsat_olmadi: ["Fırsat olmadı", ""], yapilamadi: ["Yapamadım", "err"] };
const OBS_SCALE = ["Hiç görmedim", "Bir kez", "Birkaç kez", "Düzenli olarak"];
const CHANNEL = { uygulama: "📱 Uygulama", eposta: "📧 E-posta", whatsapp: "💬 WhatsApp" };
const NSTATUS = { gonderildi: "gönderildi", simule: "simüle", hata: "hata" };

const lowerFirstTr = (x) => (x || "").trim().replace(/[.\s]+$/, "").replace(/^\S/, (ch) => ch.toLocaleLowerCase("tr"));

function planLine(k) {
  return `Eğer ${esc(lowerFirstTr(k.durum))}, o zaman ${esc(lowerFirstTr(k.davranis))}.`;
}

function tabEvidence(body, { c, ev }) {
  const s = ev.summary;
  const obsBy = (id) => ev.observations.filter((o) => o.commitment_id === id);
  body.innerHTML = `
    <div class="kpis">
      ${kpi("Eğer–o zaman planı", s.plan_sayisi, `${s.plan_yanitlanan} yanıtlandı`, "check")}
      ${kpi("Öz-bildirim: uyguladı", s.plan_yanitlanan ? `${s.plan_uygulanan}/${s.plan_yanitlanan}` : "—", "yaptım + kısmen", "trend")}
      ${kpi("Paydaş gözlemi", s.gozlem_sayisi, s.gozlem_ortalama != null ? `ort. ${s.gozlem_ortalama}/3` : "henüz yok", "users")}
      ${kpi("Seansta kanıt", ev.session_reviews.filter((r) => r.bahsedildi).length, `${ev.session_reviews.length} değerlendirme`, "mic")}
    </div>
    <div class="banner banner-info">${icon("shield")}<div><b>Üç kaynaklı doğrulama</b>
      <p>Danışanın beyanı, bir paydaşın gözlemi ve sonraki seans birlikte değerlendirilir.</p></div></div>
    <section class="card"><div class="card-head"><h2>Planlar</h2></div>
      ${ev.commitments.length ? ev.commitments.map((k) => `<div class="plan-row">
        <div class="plan-main"><b>📌 ${planLine(k)}</b>
          <small>Kontrol günü ${fmtDate(k.check_date, false)} · <span class="badge badge-${PLAN_STATUS[k.status][1] || "muted"}">${PLAN_STATUS[k.status][0]}</span></small>
          ${k.reflection ? `<p class="muted">“${esc(k.reflection)}”</p>` : ""}
          ${obsBy(k.id).map((o) => `<div class="obs-line">${icon("users")}<span><b>${esc(o.observer_name)}</b>${o.relation ? ` (${esc(o.relation)})` : ""}:
            ${o.status === "yanitlandi" ? `<b class="score ${["low", "mid", "good", "good"][o.rating]}">${OBS_SCALE[o.rating]}</b>${o.example ? ` — “${esc(o.example)}”` : ""}` : `<span class="muted">yanıt bekleniyor</span>`}</span></div>`).join("")}
        </div>
        <button class="btn btn-secondary" data-observer="${k.id}">${icon("users")}Gözlemci ekle</button>
      </div>`).join("") : empty("check", "Henüz plan yok", "Danışan eğitimde planını kurunca burada görünür.")}
    </section>
    ${ev.session_reviews.length ? `<section class="card"><h2>Sonraki seanslarda kanıt</h2>${ev.session_reviews.map((r) => `
      <div class="obs-line">${r.bahsedildi ? "✅" : "➖"}<span><b>${esc(r.plan)}</b><br><span class="muted">${esc(r.kanit)}</span>
        <a class="link" href="#/seans/${r.session_id}">${esc(r.seans)}</a></span></div>`).join("")}</section>` : ""}
    <section class="card"><h2>Giden kutusu</h2>
      ${ev.notifications.length ? `<table class="table"><thead><tr><th>Kanal</th><th>Alıcı</th><th>Mesaj</th><th>Durum</th></tr></thead><tbody>
        ${ev.notifications.map((n) => `<tr><td>${CHANNEL[n.channel] || n.channel}</td><td class="muted">${esc(n.recipient)}</td>
          <td>${esc(n.body.slice(0, 90))}${n.body.length > 90 ? "…" : ""}</td>
          <td><span class="badge badge-${n.status === "gonderildi" ? "ok" : n.status === "hata" ? "err" : "muted"}" title="${esc(n.detail)}">${NSTATUS[n.status] || n.status}</span></td></tr>`).join("")}
      </tbody></table>` : `<p class="muted">Ajanın gönderdiği mesajlar ve hangi kanaldan gittikleri burada listelenir.</p>`}
    </section>`;
  $$("[data-observer]", body).forEach((b) => b.addEventListener("click", () => observerForm(Number(b.dataset.observer), true)));
}

function observerForm(commitmentId, staffSide) {
  openModal("Gözlemci ekle", `
    <p class="muted">Danışanı gerçek hayatta gören biri tek bir soruya cevap verir; yalnızca danışanın adını ve davranışı görür.</p>
    <div class="grid-form">
      ${field("Gözlemcinin adı *", `<input name="observer_name" required placeholder="Ör. Ayşe">`)}
      ${field("Yakınlık", `<input name="relation" placeholder="Ör. Ekip arkadaşı">`)}
    </div>
    ${staffSide ? `<label class="consent"><input type="checkbox" name="consent"><span><b>Danışanın onayı alındı.</b> Danışan bu kişiye sorulmasını kabul etti.</span></label>` : ""}`,
  async (fd) => {
    const o = await sendJSON(`/api/commitments/${commitmentId}/observer`, {
      observer_name: fd.get("observer_name"), relation: fd.get("relation"), consent: fd.has("consent") });
    setTimeout(() => openModal("Bağlantı hazır", `
      <p>Bu bağlantıyı <b>${esc(o.observer_name)}</b> ile paylaşın (WhatsApp, e-posta…). Giriş gerekmez, tek seferlik cevaplanır.</p>
      <div class="copy-row"><input readonly value="${esc(o.link)}" id="obs-link"><button type="button" class="btn btn-primary" id="copy-link">Kopyala</button></div>`,
    async () => route(), "Tamam"), 50);
    setTimeout(() => $("#copy-link")?.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(o.link); toast("Bağlantı kopyalandı"); } catch { $("#obs-link").select(); }
    }), 120);
  }, "Bağlantı oluştur");
}

// Danışan portalı: Planlarım
function renderPlans(body, d) {
  const obsBy = (id) => d.observations.filter((o) => o.commitment_id === id);
  body.innerHTML = d.commitments.length ? d.commitments.map((k) => `
    <section class="card plan-portal">
      <div class="plan-card"><span>📌</span><p>${planLine(k)}</p></div>
      ${k.status === "aktif" ? `<form class="plan-answer" data-k="${k.id}">
          <b>Bu durum yaşandı mı, ne yaptınız?</b>
          <div class="chips-pick">${["yapildi", "kismen", "firsat_olmadi", "yapilamadi"].map((st) =>
            `<label class="pick-radio"><input type="radio" name="status" value="${st}" required><span>${PLAN_STATUS[st][0]}</span></label>`).join("")}</div>
          <input name="reflection" placeholder="Kısaca ne oldu? (isteğe bağlı)">
          <button class="btn btn-primary">Kaydet</button>
        </form>`
        : `<p><span class="badge badge-${PLAN_STATUS[k.status][1] || "muted"}">${PLAN_STATUS[k.status][0]}</span> ${k.reflection ? esc(k.reflection) : ""}</p>`}
      <div class="row between"><span class="muted small">${obsBy(k.id).length ? obsBy(k.id).map((o) => `${esc(o.observer_name)}: ${o.status === "yanitlandi" ? "yanıtladı ✓" : "bekleniyor"}`).join(" · ") : "Bir gözlemci, gelişiminizi dışarıdan doğrulayabilir."}</span>
        <button class="btn btn-secondary" data-observer="${k.id}">${icon("users")}Gözlemci davet et</button></div>
    </section>`).join("")
    : `<section class="card">${empty("check", "Henüz planınız yok", "İlk planınızı bir eğitimin sonunda kurabilirsiniz.")}</section>`;
  $$(".plan-answer", body).forEach((f) => f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(f);
    await sendJSON(`/api/commitments/${f.dataset.k}/response`, { status: fd.get("status"), reflection: fd.get("reflection") });
    toast("Kaydedildi. Koçunuz bunu görecek 💪");
    route();
  }));
  $$("[data-observer]", body).forEach((b) => b.addEventListener("click", () => observerForm(Number(b.dataset.observer), false)));
}

// Gözlemci sayfası (giriş gerekmez)
async function viewObserver(token) {
  document.body.className = "observe-body";
  document.body.innerHTML = `<main class="observe-page"><section class="card observe-card" id="obs">Yükleniyor…</section></main>`;
  const box = document.getElementById("obs");
  let info;
  try { info = await (await fetch(`/api/observe/${encodeURIComponent(token)}`)).json(); } catch { info = null; }
  if (!info || info.detail) { box.innerHTML = `<h1>Bağlantı geçersiz</h1><p class="muted">Bu gözlem bağlantısı bulunamadı.</p>`; return; }
  if (info.yanitlandi) { box.innerHTML = `<img src="/static/logo.svg" alt="" class="brand-mark"><h1>Teşekkürler 🙏</h1><p>Bu gözlem daha önce yanıtlandı.</p>`; return; }
  box.innerHTML = `
    <img src="/static/logo.svg" alt="Farkora" class="brand-mark">
    <h1>Merhaba ${esc(info.gozlemci)} 👋</h1>
    <p><b>${esc(info.danisan)}</b> koçluk sürecinde şu davranışı deniyor ve sizin gözleminizi merak ediyor:</p>
    <div class="plan-card"><span>📌</span><p>${info.durum ? `Eğer ${esc(lowerFirstTr(info.durum))}, o zaman ` : ""}${esc(lowerFirstTr(info.davranis))}.</p></div>
    <form id="obs-form">
      <b>Son günlerde bunu ne sıklıkla gördünüz?</b>
      <div class="obs-scale">${OBS_SCALE.map((l, i) => `<label class="pick-radio"><input type="radio" name="rating" value="${i}" required><span>${l}</span></label>`).join("")}</div>
      <textarea name="example" rows="3" maxlength="500" placeholder="İsterseniz kısa bir örnek yazın (kimlik veya özel bilgi yazmayın)"></textarea>
      <button class="btn btn-primary">Gönder</button>
      <p class="muted small">Cevabınız yalnızca ${esc(info.danisan)} ve koçu tarafından görülür. Tek seferlik bir bağlantıdır.</p>
    </form>`;
  document.getElementById("obs-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const r = await fetch(`/api/observe/${encodeURIComponent(token)}`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: Number(fd.get("rating")), example: fd.get("example") || "" }) });
    box.innerHTML = r.ok ? `<img src="/static/logo.svg" alt="" class="brand-mark"><h1>Teşekkürler 🙏</h1><p>Gözleminiz ${esc(info.danisan)}'nın gelişimine katkı sağlayacak.</p>`
      : `<h1>Gönderilemedi</h1><p class="muted">${esc((await r.json()).detail || "Bir sorun oluştu.")}</p>`;
  });
}

// Toplantı botları (seanslar sekmesinde)
const BOT_STATUS = { katiliyor: "Toplantıya katılıyor", kayitta: "Kaydediyor", isleniyor: "Analiz ediliyor", tamamlandi: "Tamamlandı", hata: "Hata" };

async function renderBots(box, clientId) {
  const bots = await api(`/api/clients/${clientId}/meeting-bots`);
  if (!bots.length) { box.innerHTML = ""; return; }
  box.innerHTML = `<section class="card"><div class="card-head"><h2>🤖 Toplantı botları</h2></div>
    ${bots.map((b) => `<div class="obs-line">${b.status === "tamamlandi" ? "✅" : b.status === "hata" ? "⚠️" : `<span class="rec-dot"></span>`}
      <span><b>${esc(b.title)}</b> · ${BOT_STATUS[b.status] || b.status}${b.provider === "simulasyon" ? ` <span class="tag">simülasyon</span>` : ""}
      <br><span class="muted small">${esc(b.meeting_url)}</span>${b.error ? `<br><span class="form-error">${esc(b.error)}</span>` : ""}
      ${b.session_id ? ` <a class="link" href="#/seans/${b.session_id}">Seansı aç</a>` : ""}</span></div>`).join("")}</section>`;
  if (bots.some((b) => ["katiliyor", "kayitta", "isleniyor"].includes(b.status))) poll(async () => {
    const fresh = await api(`/api/clients/${clientId}/meeting-bots`);
    if (JSON.stringify(fresh.map((b) => b.status)) !== JSON.stringify(bots.map((b) => b.status))) route();
  });
}

// ===================================================================
// Danışan: gelişim portalı (danışan girişi + koç önizlemesi)
// ===================================================================

const PROGRESS_TABS = [["ozet", "Genel bakış"], ["yolculuk", "Gelişim yolculuğum"], ["egitimler", "Eğitimlerim"], ["planlar", "Planlarım"], ["mesajlar", "Mesajlar"]];

async function viewMyProgress(tab) {
  if (ME.self_guided) return viewSelfProgress(tab);  // koçsuz mod (self.js)
  const data = await api("/api/me/portal");
  setHeader([["Gelişimim"]]);
  renderProgress(data, tab, { base: "#/gelisim", checkinUrl: "/api/me/checkins" });
}

async function viewPortal(id) {
  const data = await api(`/api/clients/${id}/portal`);
  setHeader([["Danışanlar", "#/danisanlar"], [data.profile.name, `#/danisan/${id}`], ["Danışan görünümü"]]);
  const tab = (location.hash.split("?tab=")[1]) || "ozet";
  renderProgress(data, tab, { base: `#/portal/${id}?tab=`, checkinUrl: `/api/clients/${id}/checkins`, preview: true, id });
}

function renderProgress(d, tab, opt) {
  const p = d.profile, b = d.behavior;
  const first = p.name.replace(/\(.*?\)/g, "").trim().split(" ")[0];
  const week = opt.self ? selfWeek(opt.self) : 0;
  const open = d.tasks.filter((t) => t.status === "acik" && (!opt.self || !t.detail || t.detail.hafta <= week));
  const progressTabs = opt.self ? SELF_TABS : PROGRESS_TABS;
  const tabLink = (k) => opt.preview ? `${opt.base}${k}` : `${opt.base}/${k}`;
  page.innerHTML = `
    ${opt.preview ? `<div class="banner banner-info no-print">${icon("phone")}<div><b>Önizleme: danışanın gördüğü ekran</b>
      <p>Danışan yalnızca bu sayfayı görür; ICF ve transkript gizlidir.</p></div></div>` : ""}
    <div class="welcome-band">
      <div><small>${opt.self ? "Kendi kendine koçluk" : esc(p.organization_name || "Bireysel koçluk")}${p.coach_name ? ` · Koçunuz: ${esc(p.coach_name)}` : ""}</small>
        <h1>Merhaba ${esc(first)} 👋</h1>
        ${p.goals ? `<p>Hedefiniz: <b>${esc(p.goals)}</b></p>` : ""}</div>
      <form id="checkin" class="checkin-inline">
        <span>${opt.self ? "Bugün nasılsın?" : "Bugün nasılsınız?"}</span>
        <div class="moods">${[1, 2, 3, 4, 5].map((m) => `<label><input type="radio" name="mood" value="${m}" required><span>${MOOD[m]}</span></label>`).join("")}</div>
        <div class="row"><input name="note" placeholder="Kısa bir not (isteğe bağlı)"><button class="btn btn-primary">Gönder</button></div>
      </form>
    </div>
    <nav class="tabs">${progressTabs.map(([k, l]) => `<a href="${tabLink(k)}" class="${k === tab ? "active" : ""}">${l}${k === "mesajlar" && d.messages.length ? `<span class="count">${d.messages.length}</span>` : ""}${k === "planlar" && d.commitments.some((x) => x.status === "aktif") ? `<span class="count">${d.commitments.filter((x) => x.status === "aktif").length}</span>` : ""}</a>`).join("")}</nav>
    <section id="tab-body"></section>`;

  const body = $("#tab-body");
  if (tab === "planim" && opt.self) {
    renderSelfPlan(body, opt.self);
  } else if (tab === "yolculuk") {
    body.innerHTML = d.sessions.length ? `<div class="journey">${d.sessions.map((s, i) => `
      <div class="journey-item"><div class="journey-dot">${d.sessions.length - i}</div>
        <section class="card"><div class="card-head"><div><h2>${esc(s.title)}</h2><small>${fmtDate(s.created_at, false)}</small></div></div>
          <p>${esc(s.ozet)}</p>
          ${s.calisilan_konular.length ? `<h4>Üzerinde çalıştığımız konular</h4><div class="chips">${s.calisilan_konular.map((k) => `<span class="tag">${esc(k)}</span>`).join("")}</div>` : ""}
          ${s.gorevler.length ? `<h4>Üstlendiğim adımlar</h4>${bullets(s.gorevler)}` : ""}
        </section></div>`).join("")}</div>`
      : `<section class="card">${empty("trend", "Yolculuğunuz ilk seansla başlayacak", "Seanslarınızın özetleri burada görünecek.")}</section>`;
  } else if (tab === "egitimler") {
    body.innerHTML = d.trainings.length ? `<div class="tiles">${d.trainings.map((t) => `<a class="tile" href="#/egitim/${t.id}">
      <div class="tile-art">${icon("book")}</div><div class="tile-body"><b>${esc(t.title)}</b><small>${esc(t.area)}</small></div>
      <div class="tile-foot"><span class="muted small">${fmtDate(t.created_at, false)}</span>${icon("chevron")}</div></a>`).join("")}</div>`
      : `<section class="card">${empty("book", "Henüz eğitim yok", "Size özel hazırlanan eğitimler burada görünecek.")}</section>`;
  } else if (tab === "planlar") {
    renderPlans(body, d);
  } else if (tab === "mesajlar") {
    body.innerHTML = `<section class="card">${d.messages.length ? d.messages.map((m) => `<div class="msg-row">
      <img class="brand-mark sm" src="/static/logo.svg" alt=""><div class="msg">${esc(m.message)}<small>${fmtDate(m.created_at)}</small></div></div>`).join("")
      : empty("message", "Henüz mesaj yok", "Koçluk asistanınızın mesajları burada görünecek.")}</section>`;
  } else {
    body.innerHTML = `
      <div class="kpis">
        ${kpi("Tamamlanan adımlar", `${b.gorev_tamamlanan}/${b.gorev_toplam}`, b.gorev_toplam ? `${open.length} adım devam ediyor` : "", "check")}
        ${opt.self ? kpi("Plan haftası", `${Math.min(week, 4)}/4`, esc(opt.self.plan?.baslik || ""), "clock") : kpi("Seans", d.sessions.length, "tamamlandı", "mic")}
        ${kpi("Ruh hali ortalaması", b.ruh_hali_ortalama ?? "—", `${b.checkin_sayisi} check-in`, "message", scoreClass(b.ruh_hali_ortalama))}
        ${kpi("Eğitim", d.trainings.length, "size özel", "book")}
      </div>
      <div class="grid-2">
        <section class="card"><div class="card-head"><h2>Bu haftaki adımlarım</h2>${opt.self ? `<a class="link" href="#/gelisim/planim">Planım</a>` : ""}</div>${taskList(open)}</section>
        <section class="card"><div class="card-head"><h2>Ruh hali seyrim</h2></div>${moodChart(b.ruh_hali_serisi)}</section>
      </div>
      ${d.messages[0] ? `<section class="card"><div class="card-head"><h2>Son mesaj</h2><a class="link" href="${tabLink("mesajlar")}">Tümü</a></div>
        <div class="msg-row"><img class="brand-mark sm" src="/static/logo.svg" alt=""><div class="msg">${esc(d.messages[0].message)}<small>${fmtDate(d.messages[0].created_at)}</small></div></div></section>` : ""}`;
    bindTaskButtons(() => route());
  }

  $("#checkin").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    await sendJSON(opt.checkinUrl, { mood: Number(f.get("mood")), note: f.get("note") });
    e.target.reset();
    toast(opt.self ? "Teşekkürler, kaydettim 💜" : "Teşekkürler! Koçunuz bunu görecek.");
    route();
  });
}

// ===================================================================
// Kurum yöneticisi: anonim kurum paneli
// ===================================================================

async function viewOrgPanel() {
  const o = await api("/api/me/organization");
  setHeader([["Kurum Paneli"]], `<button class="btn btn-secondary" onclick="window.print()">${icon("print")}Yazdır / PDF</button>`);
  const maxT = Math.max(1, ...o.temalar.map(([, n]) => n));
  const hbars = (rows) => rows.length ? rows.map(([t, n]) => `<div class="hbar"><span>${esc(t)}</span><div><i style="width:${(n / Math.max(1, ...rows.map(([, x]) => x))) * 100}%"></i></div><b>${n}</b></div>`).join("") : `<p class="muted">Henüz veri yok.</p>`;
  page.innerHTML = `
    <div class="page-title"><span class="tag">${esc(o.org_type_label)}</span><h1>${esc(o.name)}</h1>
      <p class="muted">Anonim kurum görünümü</p></div>
    <div class="kpis">
      ${kpi("Katılımcı", o.danisan_sayisi, `${o.birimler.length} birim/program`, "users")}
      ${kpi("Tamamlanan seans", o.seans_sayisi, "", "mic")}
      ${kpi("Koçluk kalitesi", o.icf_ortalama ?? "—", "ICF ortalaması / 5", "trend", scoreClass(o.icf_ortalama))}
      ${kpi("Görev tamamlama", o.gorev_tamamlama != null ? `%${o.gorev_tamamlama}` : "—", "davranış değişimi", "check")}
      ${kpi("Ruh hali", o.ruh_hali_ortalama ?? "—", "katılımcı ortalaması", "message", scoreClass(o.ruh_hali_ortalama))}
    </div>
    <div class="grid-main">
      <div class="col">
        <section class="card"><div class="card-head"><div><h2>${icon("sparkles")} Kurumsal içgörü raporu</h2></div></div>
          <div id="insight"><button class="btn btn-primary" id="insight-btn" ${o.seans_sayisi ? "" : "disabled"}>${icon("sparkles")}Rapor oluştur</button></div></section>
        <section class="card"><h2>Sık görülen temalar</h2>${o.temalar.length ? o.temalar.map(([t, n]) => `<div class="hbar"><span>${esc(t)}</span><div><i style="width:${(n / maxT) * 100}%"></i></div><b>${n}</b></div>`).join("") : `<p class="muted">Henüz veri yok.</p>`}</section>
      </div>
      <div class="col">
        <section class="card"><h2>Birim / program dağılımı</h2>${hbars(o.birimler)}</section>
        <section class="card"><h2>Odak alanları</h2>${hbars(o.odak_alanlari)}</section>
        <section class="card"><h2>Ortak gelişim alanları</h2>${bullets(o.gelisim_alanlari.map(([a, n]) => `${a} (${n})`))}</section>
        <section class="card"><h2>🧩 Tema kümeleri</h2>${(o.tema_kumeleri || []).length ? o.tema_kumeleri.map((k) => `<div class="cluster">
          <div class="row between"><b>${esc(k.etiket)}</b><span class="tag">${k.kisi_sayisi} kişi</span></div>
          <small class="muted">${k.temalar.map(esc).join(" · ")}</small></div>`).join("") : `<p class="muted">En az ${o.min_grup || 3} kişide görülen ortak tema henüz yok.</p>`}</section>
        ${(o.risk_sinyalleri || []).length ? `<section class="card"><h2>⚠️ Birim risk sinyalleri</h2>${bullets(o.risk_sinyalleri)}</section>` : ""}
      </div>
    </div>
    ${o.kucuk_grup ? `<div class="banner banner-info">${icon("shield")}<div><b>Gizlilik eşiği</b><p>Kurumda ${o.min_grup} kişiden az katılımcı olduğu için tema ve gelişim alanı ayrıntıları gizlendi.</p></div></div>` : ""}`;
  $("#insight-btn")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    e.currentTarget.textContent = "Hazırlanıyor…";
    try {
      const r = await api("/api/me/organization/insight", { method: "POST" });
      $("#insight").innerHTML = `<p class="lead">${esc(r.genel_durum)}</p>
        <div class="grid-2 tight"><div><h4>Ortak temalar</h4>${bullets(r.ortak_temalar)}</div><div><h4>Riskler</h4>${bullets(r.riskler)}</div></div>
        <h4>Kurumsal öneriler</h4>${bullets(r.kurumsal_oneriler)}<h4>İzlenecek göstergeler</h4>${bullets(r.izlenecek_gostergeler)}`;
    } catch (err) { $("#insight").innerHTML = `<p class="form-error">${esc(err.message)}</p>`; }
  });
}

// ===================================================================
// Kullanıcı yönetimi (yönetici)
// ===================================================================

const ROLE_LABEL = { admin: "Yönetici", koc: "Koç", danisan: "Danışan", kurum: "Kurum yöneticisi" };

async function viewUsers() {
  const users = await api("/api/users");
  setHeader([["Kullanıcılar"]], `<button class="btn btn-primary" id="new-user">${icon("plus")}Yeni kullanıcı</button>`);
  $("#new-user").addEventListener("click", userForm);
  page.innerHTML = `
    <div class="page-title"><h1>Kullanıcılar</h1>
      <p class="muted">Danışan girişleri, danışan profilinden açılır.</p></div>
    <div class="role-cards">
      ${[["admin", "shield", "Her şeyi görür, kullanıcıları yönetir"], ["koc", "users", "Yalnızca kendi danışanlarını görür ve yönetir"],
        ["danisan", "trend", "Yalnızca kendi gelişimini görür (ICF ve transkript hariç)"], ["kurum", "building", "Kendi kurumunun anonim panelini görür"]]
        .map(([r, ic, d]) => `<div class="role-card">${icon(ic)}<div><b>${ROLE_LABEL[r]}</b><small>${d}</small></div><span class="count">${users.filter((u) => u.role === r).length}</span></div>`).join("")}
    </div>
    <section class="card"><table class="table"><thead><tr><th>Kullanıcı</th><th>Rol</th><th>Bağlı olduğu</th><th>Oluşturulma</th><th></th></tr></thead><tbody>
      ${users.map((u) => `<tr>
        <td><div class="person">${avatar(u.name)}<div><b>${esc(u.name)}</b><small>${esc(u.email)}</small></div></div></td>
        <td><span class="tag">${ROLE_LABEL[u.role]}</span>${u.is_demo ? ` <span class="badge badge-info">Örnek</span>` : ""}</td>
        <td>${u.client_name ? `<a href="#/danisan/${u.client_id}">${esc(u.client_name)}</a>` : u.organization_name ? esc(u.organization_name) : `<span class="muted">—</span>`}</td>
        <td class="muted">${fmtDate(u.created_at, false)}</td>
        <td class="actions">${u.id === ME.id ? `<span class="muted small">Siz</span>` : `
          ${u.role === "danisan" ? "" : `<button class="btn btn-secondary btn-sm" data-role-user="${u.id}">Yetki</button>`}
          <button class="btn btn-secondary btn-sm" data-reset="${u.id}">Şifre sıfırla</button>
          <button class="btn btn-secondary btn-sm danger" data-del="${u.id}" data-name="${esc(u.name)}">Sil</button>`}</td>
      </tr>`).join("")}
    </tbody></table></section>`;
  $$("[data-role-user]", page).forEach((b) => b.addEventListener("click", () => roleForm(users.find((u) => u.id === Number(b.dataset.roleUser)))));
  $$("[data-reset]", page).forEach((b) => b.addEventListener("click", () => openModal("Şifre sıfırla",
    field("Yeni şifre", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`, "En az 8 karakter"),
    async (fd) => { await sendJSON(`/api/users/${b.dataset.reset}/password`, { password: fd.get("password") }); toast("Şifre sıfırlandı"); }, "Sıfırla")));
  $$("[data-del]", page).forEach((b) => b.addEventListener("click", async () => {
    if (!confirm(`${b.dataset.name} kullanıcısı silinsin mi? Bu işlem geri alınamaz.`)) return;
    await api(`/api/users/${b.dataset.del}`, { method: "DELETE" });
    toast("Kullanıcı silindi");
    route();
  }));
}

async function roleForm(u) {
  const orgs = await api("/api/organizations");
  openModal(`Yetki: ${esc(u.name)}`, `
    ${field("Rol", `<select name="role" id="rf-role">${options([["koc", "Koç: kendi danışanlarını yönetir"], ["admin", "Yönetici: her şeyi görür ve yönetir"], ["kurum", "Kurum yöneticisi: anonim kurum paneli"]], u.role)}</select>`)}
    <div id="rf-org" ${u.role === "kurum" ? "" : "hidden"}>${field("Kurum", `<select name="organization_id"><option value="">Seçin</option>${options(orgs.map((o) => [o.id, o.name]), u.organization_id)}</select>`)}</div>
    <p class="muted small">Koç, kurum yöneticisi yapılırsa danışanları koçsuz kalır; yönetici onları başka koça atayabilir.</p>`,
  async (fd) => {
    await sendJSON(`/api/users/${u.id}`, { role: fd.get("role"), organization_id: fd.get("organization_id") ? Number(fd.get("organization_id")) : null }, "PATCH");
    toast("Yetki güncellendi");
    route();
  }, "Kaydet");
  $("#rf-role").addEventListener("change", (e) => { $("#rf-org").hidden = e.target.value !== "kurum"; });
}

function deleteClientForm(c) {
  openModal("Danışanı sil", `
    <p><b>${esc(c.name)}</b> ve ona ait <b>tüm veriler</b> (seanslar, kayıtlar, raporlar, eğitimler, planlar, mesajlar, giriş hesabı) kalıcı olarak silinecek. Bu işlem <b>geri alınamaz</b>.</p>
    ${field("Onaylamak için danışanın adını yazın", `<input name="confirm" autocomplete="off">`)}`,
  async (fd) => {
    if ((fd.get("confirm") || "").trim() !== c.name.trim()) throw new Error("Ad eşleşmiyor.");
    await api(`/api/clients/${c.id}`, { method: "DELETE" });
    toast("Danışan silindi");
    location.hash = "#/danisanlar";
  }, "Kalıcı olarak sil");
}

async function userForm() {
  const orgs = await api("/api/organizations");
  openModal("Yeni kullanıcı", `
    <div class="grid-form">
      ${field("Ad soyad *", `<input name="name" required>`)}
      ${field("E-posta *", `<input name="email" type="email" required autocomplete="off">`)}
      ${field("Rol", `<select name="role" id="role-select">${options([["koc", "Koç"], ["kurum", "Kurum yöneticisi"], ["admin", "Yönetici"]])}</select>`)}
      ${field("Geçici şifre *", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`, "En az 8 karakter")}
    </div>
    <div id="org-field" hidden>${field("Kurum *", `<select name="organization_id"><option value="">Seçin</option>${options(orgs.map((o) => [o.id, o.name]))}</select>`,
      "Kurum yöneticisi yalnızca bu kurumun anonim panelini görür.")}</div>`,
  async (fd) => {
    const body = Object.fromEntries(fd);
    body.organization_id = body.organization_id ? Number(body.organization_id) : null;
    await sendJSON("/api/users", body);
    toast("Kullanıcı oluşturuldu");
    route();
  }, "Oluştur", true);
  $("#role-select").addEventListener("change", (e) => ($("#org-field").hidden = e.target.value !== "kurum"));
}

function accountForm(client) {
  const has = !!client.account;
  openModal(has ? "Danışan şifresini sıfırla" : "Danışan girişi oluştur", `
    ${has ? `<p class="muted">Hesap: <b>${esc(client.account.email)}</b></p>`
      : field("E-posta *", `<input name="email" type="email" required value="${esc(client.email)}" autocomplete="off">`)}
    ${field(has ? "Yeni şifre *" : "Geçici şifre *", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`,
      "En az 8 karakter. Şifreyi danışana güvenli bir yoldan iletin; danışan girişten sonra değiştirebilir.")}
    <div class="note">${icon("shield")}<span>Danışan ICF puanını ve transkripti göremez.</span></div>`,
  async (fd) => {
    if (has) await sendJSON(`/api/clients/${client.id}/account/password`, { password: fd.get("password") });
    else await sendJSON(`/api/clients/${client.id}/account`, Object.fromEntries(fd));
    toast(has ? "Şifre sıfırlandı" : "Danışan girişi oluşturuldu");
    route();
  }, has ? "Sıfırla" : "Oluştur");
}

// ===================================================================
// Kurumlar & birimler
// ===================================================================

async function viewOrganizations() {
  const orgs = await api("/api/organizations");
  setHeader([["Kurumlar & Birimler"]], `<button class="btn btn-primary" id="new-org">${icon("plus")}Yeni kurum / birim</button>`);
  $("#new-org").addEventListener("click", () => orgForm());
  page.innerHTML = `
    <div class="page-title"><h1>Kurumlar & Birimler</h1>
      <p class="muted">Şirketler, kamu kurumları ve sosyal birimler</p></div>
    ${orgs.length ? `<div class="tiles">${orgs.map((o) => `<a class="tile org-tile" href="#/kurum/${o.id}">
      <div class="tile-art org-${o.org_type}">${icon("building")}</div>
      <div class="tile-body"><b>${esc(o.name)}</b><small>${ORG_TYPE[o.org_type] || o.org_type}${o.sector ? ` · ${esc(o.sector)}` : ""}</small></div>
      <div class="tile-foot"><span class="muted small">${o.client_count} danışan</span>${o.knowledge ? `<span class="tag">${icon("database")}Kurumsal hafıza</span>` : ""}</div>
    </a>`).join("")}</div>` : `<section class="card">${empty("building", "Henüz kurum yok", "Danışanları gruplamak için kurum ekleyin.")}</section>`}`;
}

async function viewOrganization(id) {
  const o = await api(`/api/organizations/${id}`);
  setHeader([["Kurumlar & Birimler", "#/kurumlar"], [o.name]], `<button class="btn btn-secondary" id="edit-org">${icon("edit")}Düzenle</button>`);
  $("#edit-org").addEventListener("click", () => orgForm(o));
  const maxT = Math.max(1, ...o.temalar.map(([, n]) => n));
  page.innerHTML = `
    <div class="page-title"><span class="tag">${esc(o.org_type_label)}</span><h1>${esc(o.name)}</h1><p class="muted">${esc(o.sector)}</p></div>
    <div class="kpis">
      ${kpi("Danışan", o.clients.length, `${o.birimler.length} birim/program`, "users")}
      ${kpi("Seans", o.seans_sayisi, "analiz edildi", "mic")}
      ${kpi("Ortalama ICF", o.icf_ortalama ?? "—", "koçluk kalitesi", "trend", scoreClass(o.icf_ortalama))}
      ${kpi("Görev tamamlama", o.gorev_tamamlama != null ? `%${o.gorev_tamamlama}` : "—", "davranış değişimi", "check")}
      ${kpi("Ruh hali ort.", o.ruh_hali_ortalama ?? "—", "check-in", "message", scoreClass(o.ruh_hali_ortalama))}
    </div>
    <div class="grid-main">
      <div class="col">
        <section class="card"><div class="card-head"><div><h2>${icon("sparkles")} Kurumsal içgörü raporu</h2></div></div>
          <div id="insight"><button class="btn btn-primary" id="insight-btn" ${o.seans_sayisi ? "" : "disabled"}>${icon("sparkles")}Rapor oluştur</button>
          ${o.seans_sayisi ? "" : `<p class="muted small">Rapor için kurumda en az bir analiz edilmiş seans olmalı.</p>`}</div></section>
        <section class="card"><div class="card-head"><h2>Danışanlar</h2></div>
          ${o.clients.length ? `<table class="table"><thead><tr><th>Danışan</th><th>Birim / program</th><th>Tip</th><th>Seans</th><th>Son ICF</th></tr></thead><tbody>
          ${o.clients.map((c) => `<tr data-href="#/danisan/${c.id}"><td><div class="person">${avatar(c.name)}<b>${esc(c.name)}</b></div></td>
            <td>${esc(c.unit || "—")}</td><td><span class="tag">${CLIENT_TYPE[c.client_type]}</span></td><td>${c.session_count}</td>
            <td><b class="score ${scoreClass(c.last_icf)}">${c.last_icf ?? "—"}</b></td></tr>`).join("")}</tbody></table>`
            : `<p class="muted">Henüz danışan yok.</p>`}</section>
      </div>
      <div class="col">
        <section class="card"><h2>Sık görülen temalar</h2>${o.temalar.length ? o.temalar.map(([t, n]) => `<div class="hbar">
          <span>${esc(t)}</span><div><i style="width:${(n / maxT) * 100}%"></i></div><b>${n}</b></div>`).join("") : `<p class="muted">Henüz veri yok.</p>`}</section>
        <section class="card"><h2>Ortak gelişim alanları</h2>${bullets(o.gelisim_alanlari.map(([a, n]) => `${a} (${n})`))}</section>
        <section class="card"><h2>🧩 Tema kümeleri</h2>${(o.tema_kumeleri || []).length ? o.tema_kumeleri.map((k) => `<div class="cluster">
          <div class="row between"><b>${esc(k.etiket)}</b><span class="tag">${k.kisi_sayisi} kişi</span></div>
          <small class="muted">${k.temalar.map(esc).join(" · ")}</small></div>`).join("") : `<p class="muted">En az ${o.min_grup || 3} kişide görülen ortak tema henüz yok.</p>`}</section>
        ${(o.risk_sinyalleri || []).length ? `<section class="card"><h2>⚠️ Birim risk sinyalleri</h2>${bullets(o.risk_sinyalleri)}</section>` : ""}
        <section class="card"><div class="card-head"><h2>${icon("database")} Kurumsal hafıza</h2></div>
          ${o.knowledge ? `<p class="pre">${esc(o.knowledge)}</p>` : `<p class="muted">Henüz girilmedi.</p>`}</section>
      </div>
    </div>`;
  bindRowLinks();
  $("#insight-btn")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    e.currentTarget.textContent = "Hazırlanıyor…";
    try {
      const r = await api(`/api/organizations/${id}/insight`, { method: "POST" });
      $("#insight").innerHTML = `<p class="lead">${esc(r.genel_durum)}</p>
        <div class="grid-2 tight"><div><h4>Ortak temalar</h4>${bullets(r.ortak_temalar)}</div><div><h4>Riskler</h4>${bullets(r.riskler)}</div></div>
        <h4>Kurumsal öneriler</h4>${bullets(r.kurumsal_oneriler)}<h4>İzlenecek göstergeler</h4>${bullets(r.izlenecek_gostergeler)}`;
    } catch (err) { $("#insight").innerHTML = `<p class="form-error">${esc(err.message)}</p>`; }
  });
}

// ===================================================================
// Proje kapsamı (hocanın gereksinimleri ↔ sistemdeki karşılığı)
// ===================================================================

const SCOPE = [
  ["Durağan değil, dinamik ve aktif olmalı", "done", "Aktif ajan: algıla → karar ver → uygula. Seans sonrası takip, görev hatırlatma, check-in daveti, koça uyarı ve otomatik eğitim üretimi.", "#/danisanlar"],
  ["Yazı değil, görsel ve ses analizi", "done", "Ses: Whisper transkript, konuşmacı ayrımı, konuşma payı/hızı, düşünme alanı (bekleme süresi), sessizlikler. Görsel: hedef panosu, günlük, zihin haritası yorumlama (yüzden duygu çıkarımı yok).", null],
  ["Bireysel ve kurumsal verimlilik, davranış değişikliği ajanı (Behavioral AI)", "done", "4 ajanlı yapı. Davranış döngüsü kapalı: eğer–o zaman planı → ajanın kontrol günü sorusu → danışanın öz-bildirimi → izin verilen paydaşın (yönetici / ekip arkadaşı) tek seferlik gözlemi → sonraki seansta kanıt. Kurum düzeyinde k-anonim (en az 3 kişi) tema kümeleri ve birim risk sinyalleri.", "#/kurumlar"],
  ["Koç (insan koç) destek sistemi + danışan (bireysel ve yönetici) odaklı", "done", "Rol bazlı ayrı girişler: Koç (yalnızca kendi danışanları), Danışan (kendi gelişimi; ICF ve transkript gizli), Kurum yöneticisi (anonim kurum paneli), Yönetici. Danışan tipi (bireysel / yönetici), rol, kurum ve birim bilgileri.", null],
  ["Web + mobil", "partial", "Web uygulaması telefon ekranına uyumlu; danışan görünümü mobil için tasarlandı. PWA / mağaza uygulaması sonraki faz.", null],
  ["Zoom, MS Teams ve ses kayıt sistemleriyle uyum", "partial", "Kayıt yükleme, canlı ses/kamera/ekran kaydı, fotoğraf, yazışma ve toplantı botu (Zoom/Teams/Meet bağlantısıyla katılıp kaydı analiz eder; Recall.ai anahtarıyla gerçek, anahtarsız simülasyon). Kurumsal Zoom/Teams uygulama onayı sırada.", null],
  ["Odak: bireysel gelişim, ilişkiler, kurumsal gelişim, liderlik", "done", "Danışan odak alanı; a) danışana hizmet (portal, eğitim, takip) b) koça destek (rapor, ICF, brif).", null],
  ["AI rolü a) Koç / kurumsal hafıza", "done", "Danışan hafızası (önceki seanslar) + kurum düzeyinde kurumsal hafıza (değerler, yetkinlik modeli, programlar).", "#/kurumlar"],
  ["AI rolü b) Bilimsel çalışmalardan yararlanma", "done", "OpenAlex akademik veri tabanından ilgili ve çok atıf almış makaleler; içerikte kaynak numarasıyla atıf.", null],
  ["AI rolü c) Mevcut AI uygulamalarından yararlanma", "done", "Gemini / Claude (dil ve görsel), Whisper (ses) — sağlayıcı bağımsız katman.", null],
  ["AI rolü d) Koç asistanlığı: hazırlık + seans sonrası, ICF'ye göre puanlama", "done", "Seans öncesi hazırlık brifi, seans sonrası rapor, ICF 8 temel yetkinlikte kanıtlı puanlama.", null],
  ["Coaching + Training: bilimsel kaynak → eğlenceli görsel anlatım, eksik hususa özel üretim (en orijinal kısım)", "done", "Seansta tespit edilen gelişim alanı → kaynak tarama → bilgi kartları, mini çizgi roman, quiz, haftalık deneme.", null],
  ["Sosyal birimlerde koçluğa destek veren AI agent", "done", "Kurum türü “Sosyal hizmet birimi”; program/birim bazlı danışan yönetimi, gizlilik ilkeli anonim birim raporu.", "#/kurumlar"],
  ["Proaktif bildirimler: WhatsApp / e-posta", "partial", "Ajan mesajları uygulamaya düşer; danışan izin verdiyse e-posta (SMTP) ve WhatsApp Business Cloud API ile de gönderilir. Her gönderim giden kutusunda; anahtarlar girilene kadar “simüle”.", "#/ajanlar"],
  ["Ölçeklenebilir altyapı (PostgreSQL)", "done", "DATABASE_URL ile PostgreSQL; varsayılan SQLite. Tüm testler iki veritabanında da geçiyor.", null],
  ["TÜBİTAK TEYDEB 1507/1501 başvurusu", "planned", "Ar-Ge özgünlüğü: Coaching→Training döngüsü, proaktif ajan, ses tabanlı koçluk metrikleri. Başvuru için şirketleşme (ör. 1512 BiGG) gerekir.", null],
];

const COMPETITORS = [
  ["Okampus (Yıldız Teknopark)", "YKS sürecinde veriyle çalışan kişisel koç", "Tek alan yerine 4 odak alanı; ölçülebilir seans metrikleri hem danışan hem koç için."],
  ["vMind (Yıldız Teknopark)", "İK süreçlerinde eylem yetkisine sahip otonom ajanlar", "Ajan kendiliğinden eğitim üretir, mesaj gönderir, koçu uyarır; her eylemin gerekçesi koça şeffaf gösterilir."],
  ["Waytogo (İTÜ Arı Teknokent)", "AI destekli koçluk ve mentorluk; küresel pazara açıldı", "ICF standardına göre koç değerlendirmesi + kişiye özel bilimsel eğitim; AB Yapay Zekâ Yasası'na uygun tasarım (yüzden duygu çıkarımı yok)."],
];

function viewScope() {
  setHeader([["Proje Kapsamı"]], `<button class="btn btn-secondary" onclick="window.print()">${icon("print")}Yazdır / PDF</button>`);
  const label = { done: ["Tamamlandı", "ok"], partial: ["Kısmen", "wait"], planned: ["Planlandı", "info"] };
  const n = (k) => SCOPE.filter((s) => s[1] === k).length;
  page.innerHTML = `
    <div class="page-title"><h1>Proje Kapsamı</h1><p class="muted">Gereksinimler ve benzer çalışmalar</p></div>
    <div class="kpis">${kpi("Tamamlanan", n("done"), `${SCOPE.length} gereksinim`, "check", "good")}${kpi("Kısmen", n("partial"), "sonraki fazda tamamlanacak", "clock", "mid")}${kpi("Planlanan", n("planned"), "", "clipboard")}</div>
    <section class="card"><h2>Gereksinimler</h2><table class="table scope"><thead><tr><th>Gereksinim</th><th>Durum</th><th>Sistemdeki karşılığı</th></tr></thead><tbody>
      ${SCOPE.map(([req, st, how, href]) => `<tr><td><b>${esc(req)}</b></td><td><span class="badge badge-${label[st][1]}">${label[st][0]}</span></td>
        <td>${esc(how)}${href ? ` <a class="link" href="${href}">Göster →</a>` : ""}</td></tr>`).join("")}
    </tbody></table></section>
    <section class="card"><h2>Benzer çalışmalar ve farklılaşma</h2><table class="table"><thead><tr><th>Çalışma</th><th>Ne yapıyor</th><th>Bu projenin farkı</th></tr></thead><tbody>
      ${COMPETITORS.map(([a, b, c]) => `<tr><td><b>${esc(a)}</b></td><td>${esc(b)}</td><td>${esc(c)}</td></tr>`).join("")}
    </tbody></table></section>`;
}

// ===================================================================
// Giriş / ilk kurulum
// ===================================================================

const DEMO_BTNS = {
  koc: ["users", "Koç", "Danışanlar, seans analizi, ICF, ajan"],
  danisan: ["trend", "Danışan", "Kendi gelişimi, adımlar, eğitimler"],
  kurum: ["building", "Kurum", "Anonim kurum paneli"],
};

async function showAuth() {
  stopPolling();
  if (modal.open) modal.close();
  document.body.classList.add("logged-out");
  const st = await api("/api/auth/state");
  const auth = $("#auth");
  auth.hidden = false;
  const setup = st.setup_needed;
  auth.innerHTML = `
    <button class="theme-btn" aria-label="Açık / koyu tema"></button>
    <div class="auth-side">
      <div class="brand"><img class="brand-mark" src="/static/logo.svg" alt="Farkora logosu"><div><b>Farkora</b><small>Yapay zekâ destekli koçluk</small></div></div>
      <h1>İnsan koçu güçlendiren, danışanla birlikte gelişen yapay zekâ.</h1>
      <ul class="auth-points">
        <li>${icon("mic")}Ses, yazışma ve görsel analizi</li>
        <li>${icon("trend")}ICF standartlarına göre koç değerlendirmesi</li>
        <li>${icon("book")}Bilimsel kaynaklı, kişiye özel eğitim</li>
        <li>${icon("bot")}Kendiliğinden harekete geçen aktif ajan</li>
      </ul>
    </div>
    <div class="auth-main"><div class="auth-box">
      <h2>${setup ? "İlk kurulum" : "Giriş yap"}</h2>
      ${setup ? `<p class="muted">İlk yönetici hesabını oluşturun.</p>` : ""}
      <form id="auth-form">
        ${setup ? field("Ad soyad", `<input name="name" required autocomplete="name">`) : ""}
        ${field("E-posta", `<input name="email" type="email" required autocomplete="email">`)}
        ${field("Şifre", `<input name="password" type="password" required ${setup ? 'minlength="8" autocomplete="new-password"' : 'autocomplete="current-password"'}>`, setup ? "En az 8 karakter" : "")}
        ${setup ? "" : `<button type="button" class="link-btn forgot-link" id="forgot">Şifremi unuttum</button>`}
        <p class="form-error" id="auth-error"></p>
        <button class="btn btn-primary full">${setup ? "Hesabı oluştur ve başla" : "Giriş yap"}</button>
      </form>
      ${setup ? "" : `<button class="self-start" id="go-register">
          <span class="self-start-ic">${icon("bot")}</span>
          <span><b>Koçum yok, yapay zekâ asistanıyla başla</b>
            <small>Kendini anlat, asistan sana özel bir plan hazırlasın. Ücretsiz kayıt.</small></span>
          ${icon("chevron")}
        </button>`}
      ${st.demo_roles.length ? `<div class="demo-area">
        <span class="muted small">Örnek hesapla dene</span>
        <div class="demo-row">${["koc", "danisan", "kurum"].filter((r) => st.demo_roles.includes(r)).map((r) => `
          <button class="demo-chip" data-role="${r}" title="${DEMO_BTNS[r][2]}">${icon(DEMO_BTNS[r][0])}${DEMO_BTNS[r][1]}</button>`).join("")}</div>
      </div>` : ""}
    </div></div>`;
  renderThemeButtons();
  $("#auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#auth-error").textContent = "";
    try {
      await sendJSON(setup ? "/api/auth/setup" : "/api/auth/login", Object.fromEntries(new FormData(e.target)));
      startApp();
    } catch (err) { $("#auth-error").textContent = err.message; }
  });
  $("#go-register")?.addEventListener("click", () => showRegister());
  $("#forgot")?.addEventListener("click", () => showForgot($("#auth-form [name=email]").value));
  $$("[data-role]", auth).forEach((b) => b.addEventListener("click", async () => {
    await sendJSON("/api/auth/demo-login", { role: b.dataset.role });
    location.hash = "";
    startApp();
  }));
}

// Şifremi unuttum: e-postaya 6 haneli kod -> kod + yeni şifre
function showForgot(email = "") {
  const box = $(".auth-box");
  box.innerHTML = `
    <button class="link-btn" id="back-login">← Girişe dön</button>
    <h2>Şifremi unuttum</h2>
    <p class="muted">E-postanı yaz, sana 6 haneli bir kod gönderelim.</p>
    <form id="forgot-form">
      ${field("E-posta", `<input name="email" type="email" required autocomplete="email" value="${esc(email)}">`)}
      <p class="form-error" id="forgot-error"></p>
      <button class="btn btn-primary full">Kod gönder</button>
    </form>`;
  $("#back-login").addEventListener("click", showAuth);
  $("#forgot-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("button.btn-primary", e.target);
    btn.disabled = true;
    try {
      const mail = new FormData(e.target).get("email");
      const r = await sendJSON("/api/auth/forgot", { email: mail });
      showResetCode(mail, r);
    } catch (err) { $("#forgot-error").textContent = err.message; btn.disabled = false; }
  });
}

function showResetCode(email, info) {
  const box = $(".auth-box");
  box.innerHTML = `
    <button class="link-btn" id="back-forgot">← Geri</button>
    <h2>Kodu gir</h2>
    <p class="muted">Bu e-postayla kayıtlı bir hesap varsa <b>${esc(email)}</b> adresine kod gönderildi. Kod ${info.dakika} dakika geçerli.</p>
    ${info.eposta_ayarli ? "" : `<div class="banner banner-info">${icon("alert")}<p>E-posta gönderimi henüz ayarlı değil. Kod, uygulamanın çalıştığı bilgisayardaki siyah pencereye yazıldı; oradan ya da yöneticiden alabilirsin.</p></div>`}
    <form id="reset-form">
      ${field("6 haneli kod", `<input name="code" required inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code">`)}
      ${field("Yeni şifre", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`, "En az 8 karakter")}
      ${field("Yeni şifre (tekrar)", `<input name="password2" type="password" required minlength="8" autocomplete="new-password">`)}
      <p class="form-error" id="reset-error"></p>
      <button class="btn btn-primary full">Şifreyi değiştir ve giriş yap</button>
    </form>`;
  $("#back-forgot").addEventListener("click", () => showForgot(email));
  $("#reset-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    $("#reset-error").textContent = "";
    if (f.get("password") !== f.get("password2")) { $("#reset-error").textContent = "Şifreler aynı değil."; return; }
    try {
      await sendJSON("/api/auth/reset", { email, code: f.get("code"), password: f.get("password") });
      location.hash = "";
      toast("Şifren değiştirildi");
      startApp();
    } catch (err) { $("#reset-error").textContent = err.message; }
  });
}

async function startApp() {
  const obs = (location.hash || "").match(/^#\/gozlem\/([\w-]+)$/);
  if (obs) return viewObserver(obs[1]);  // paydaş gözlem sayfası: giriş gerekmez
  const st = await api("/api/auth/state");
  if (!st.user) return showAuth();
  ME = st.user;
  $("#auth").hidden = true;
  document.body.classList.remove("logged-out");
  const staffRole = ["admin", "koc"].includes(ME.role);
  $("#mode").hidden = !staffRole;
  if (staffRole) {
    api("/api/status").then((s) => {
      const names = { mock: "Demo modu", gemini: "Gemini", claude: "Claude" };
      $("#mode").innerHTML = `<span class="dot ${s.llm === "mock" ? "" : "on"}"></span><div><b>${names[s.llm] || s.llm}</b><small>${s.llm === "mock" ? "Örnek cevaplar" : "Yapay zekâ bağlı"}</small></div>`;
    });
  }
  const key = (location.hash || "").split("/")[1] || "";
  if (!location.hash || !(ROUTE_ROLES[key] || ["admin", "koc"]).includes(ME.role)) location.hash = HOME[ME.role];
  route();
}

// Yazdırırken (PDF) açılır bölümlerin içeriği de görünsün
window.addEventListener("beforeprint", () => $$("details").forEach((d) => (d.open = true)));

// Cihazın teması değişirse (ve kullanıcı seçim yapmadıysa) düğme simgesi de güncellensin
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderThemeButtons);
renderThemeButtons();
// self.js (koçsuz mod) da yüklendikten sonra başla
window.addEventListener("DOMContentLoaded", startApp);
// "Uygulama olarak yükle" (masaüstü / telefon) desteği
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
