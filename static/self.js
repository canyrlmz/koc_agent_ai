/* Farkora — koçsuz mod (kendi kendine koçluk): kayıt, kendini tanıt, asistanla sohbet, kişiye özel plan */

const SELF_TABS = [["ozet", "Genel bakış"], ["planim", "Planım"], ["egitimler", "Eğitimlerim"], ["planlar", "Eğer–o zaman"], ["mesajlar", "Mesajlar"]];
const HOBBIES = ["Kitap", "Müzik", "Spor", "Yürüyüş", "Doğa", "Yemek yapmak", "Bahçe işleri", "Film / dizi", "Oyun",
  "Sanat / el işi", "Dans", "Satranç / tavla", "Seyahat", "Gönüllülük", "Hayvanlar", "Teknoloji", "Fotoğraf", "Sohbet"];
const PLACES = ["Sakin ortamlar", "Kalabalık ortamlar", "Doğa / açık hava", "Şehir hayatı", "Evde vakit", "Küçük gruplar"];
const SCALE7 = ["Hiç katılmıyorum", "Katılmıyorum", "Biraz katılmıyorum", "Kararsızım", "Biraz katılıyorum", "Katılıyorum", "Tamamen katılıyorum"];

const pills = (name, pairs, selected, multi = false) => `<div class="pills">${pairs.map(([v, l]) => {
  const on = multi ? (selected || []).includes(v) : selected === v;
  return `<label class="pill"><input type="${multi ? "checkbox" : "radio"}" name="${name}" value="${esc(v)}" ${on ? "checked" : ""}><span>${esc(l)}</span></label>`;
}).join("")}</div>`;

function selfWeek(st) {
  if (!st?.plan?.baslangic) return 1;
  const days = Math.floor((Date.now() - new Date(st.plan.baslangic + "T00:00:00")) / 86400000);
  return Math.max(1, Math.floor(days / 7) + 1);
}

const mapLink = (q) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${q} yakınımda`)}`;
const dots = (n) => `<span class="dots" title="Zorluk ${n}/5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= n ? "on" : ""}"></i>`).join("")}</span>`;

// ===================================================================
// Kayıt (giriş ekranından)
// ===================================================================

function showRegister() {
  const box = $(".auth-box");
  box.innerHTML = `
    <button class="link-btn" id="back-login">← Girişe dön</button>
    <h2>Kendi başına başla</h2>
    <p class="muted">Kendini tanıt, sana özel planını hazırlayalım.</p>
    <form id="reg-form">
      ${field("Adın ya da takma adın", `<input name="name" required maxlength="80" autocomplete="given-name">`)}
      ${field("Yaşın (18+)", `<input name="age" type="number" min="18" max="110" required inputmode="numeric">`)}
      ${field("E-posta", `<input name="email" type="email" required autocomplete="email">`)}
      ${field("Şifre", `<input name="password" type="password" required minlength="8" autocomplete="new-password">`, "En az 8 karakter")}
      <label class="consent-check"><input type="checkbox" name="kvkk" required><span>Bilgilerimin yapay zekâyla işlenmesine izin veriyorum (KVKK).</span></label>
      <label class="consent-check"><input type="checkbox" name="not_therapy" required><span>Bunun terapi olmadığını biliyorum; acil durumda <b>112</b>'yi ararım.</span></label>
      <p class="form-error" id="reg-error"></p>
      <button class="btn btn-primary full">Hesabımı oluştur</button>
    </form>`;
  $("#back-login").addEventListener("click", showAuth);
  $("#reg-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    $("#reg-error").textContent = "";
    try {
      await sendJSON("/api/auth/register", { name: f.get("name"), email: f.get("email"), password: f.get("password"),
        age: Number(f.get("age")), kvkk: f.get("kvkk") === "on", not_therapy: f.get("not_therapy") === "on" });
      location.hash = "#/basla";
      startApp();
    } catch (err) { $("#reg-error").textContent = err.message; }
  });
}

// ===================================================================
// Yönlendirme: aşamaya göre doğru ekran
// ===================================================================

async function viewSelfProgress(tab) {
  const st = await api("/api/me/self");
  if (st.phase === "form") { location.hash = "#/basla"; return; }
  if (st.phase !== "aktif") { location.hash = "#/asistan"; return; }
  const data = await api("/api/me/portal");
  setHeader([["Gelişimim"]]);
  renderProgress(data, tab, { base: "#/gelisim", checkinUrl: "/api/me/checkins", self: st });
}

// ===================================================================
// 1. Kendini tanıt (5 adım)
// ===================================================================

let WIZ = null;

async function viewSelfStart() {
  const st = await api("/api/me/self");
  if (st.phase !== "form") { location.hash = st.phase === "aktif" ? "#/gelisim" : "#/asistan"; return; }
  setHeader([["Kendini tanıt"]]);
  WIZ = WIZ || { step: 0, intake: { hobiler: [], ortamlar: [] }, tipi: Array(10).fill(0), st };
  WIZ.st = st;
  renderWizard();
}

const WIZ_STEPS = [
  ["Seni biraz tanıyalım", "Temel bilgiler"],
  ["Nelerden hoşlanırsın?", "Zevkler"],
  ["Kısa bir kişilik testi", "Karakter"],
  ["Zamanın ve imkânların", "İmkânlar"],
  ["Seni ne zorluyor?", "Konu"],
];

function renderWizard() {
  const { step, intake: v, st } = WIZ;
  const bodies = [
    () => `
      ${field("Mesleğin ya da okulun", `<input name="meslek" value="${esc(v.meslek || "")}" placeholder="ör. öğretmen, emekli, öğrenci">`)}
      <div class="field"><span>Nerede yaşıyorsun?</span>${pills("yer", [["buyuksehir", "Büyükşehir"], ["sehir", "Şehir"], ["ilce", "İlçe / kasaba"], ["koy", "Köy"]], v.yer)}</div>
      <div class="field"><span>Kiminle yaşıyorsun?</span>${pills("yasam", [["yalniz", "Yalnız"], ["aile", "Ailemle"], ["partner", "Eşim / partnerimle"], ["arkadas", "Ev arkadaşımla"], ["yurt", "Yurtta"]], v.yasam)}</div>`,
    () => `
      <div class="field"><span>Hobilerin</span>${pills("hobiler", HOBBIES.map((h) => [h, h]), v.hobiler, true)}</div>
      <div class="field"><span>Nerede iyi hissedersin?</span>${pills("ortamlar", PLACES.map((h) => [h, h]), v.ortamlar, true)}</div>
      ${field("Sevdiğin başka şeyler", `<input name="sevdikleri" value="${esc(v.sevdikleri || "")}" placeholder="ör. Türk sanat müziği, futbol">`)}
      ${field("Sevdiğin renkler", `<input name="renkler" value="${esc(v.renkler || "")}" placeholder="İsteğe bağlı">`)}`,
    () => `
      <p class="muted">“Kendimi … biri olarak görüyorum.”</p>
      <div class="tipi">${st.tipi_items.map((item, i) => `
        <div class="tipi-row"><b>${i + 1}. ${esc(item)}</b>
          <div class="scale7" role="radiogroup" aria-label="${esc(item)}">${SCALE7.map((l, j) => `
            <label title="${l}"><input type="radio" name="t${i}" value="${j + 1}" ${WIZ.tipi[i] === j + 1 ? "checked" : ""} required><span>${j + 1}</span></label>`).join("")}</div>
        </div>`).join("")}
        <div class="scale-legend"><span>1 · Hiç katılmıyorum</span><span>7 · Tamamen katılıyorum</span></div>
      </div>`,
    () => `
      <div class="field"><span>Haftada ayırabileceğin zaman</span>${pills("zaman", [["az", "1-2 saat"], ["orta", "3-5 saat"], ["cok", "5 saatten fazla"]], v.zaman)}</div>
      <div class="field"><span>Bütçen</span>${pills("butce", [["yok", "Ücretsiz olsun"], ["az", "Biraz harcayabilirim"], ["rahat", "Sorun değil"]], v.butce)}</div>
      ${field("Sağlık ya da hareket kısıtın", `<input name="kisit" value="${esc(v.kisit || "")}" placeholder="Yoksa boş bırak">`)}`,
    () => `
      <div class="field"><span>Konu</span>${pills("konu", Object.entries(st.topics), v.konu)}</div>
      ${field("Biraz anlatır mısın?", `<textarea name="sorun" rows="5" required minlength="10" placeholder="ör. Yeni insanlarla tanışırken çok geriliyorum…">${esc(v.sorun || "")}</textarea>`)}`,
  ];
  page.innerHTML = `
    <div class="wizard">
      <div class="wiz-steps">${WIZ_STEPS.map(([, short], i) => `<span class="${i < step ? "done" : i === step ? "now" : ""}"><i>${i < step ? "✓" : i + 1}</i>${short}</span>`).join("")}</div>
      <form class="card wiz-card" id="wiz-form">
        <h1>${WIZ_STEPS[step][0]}</h1>
        ${bodies[step]()}
        <p class="form-error" id="wiz-error"></p>
        <div class="row between">
          ${step ? `<button type="button" class="btn btn-secondary" id="wiz-back">← Geri</button>` : "<span></span>"}
          <button class="btn btn-primary" id="wiz-next">${step === WIZ_STEPS.length - 1 ? `${icon("sparkles")}Asistanımla tanış` : "İleri →"}</button>
        </div>
      </form>
    </div>`;
  const form = $("#wiz-form");
  const collect = () => {
    const f = new FormData(form);
    if (step === 0) Object.assign(v, { meslek: f.get("meslek") || "", yer: f.get("yer") || "", yasam: f.get("yasam") || "" });
    if (step === 1) Object.assign(v, { hobiler: f.getAll("hobiler"), ortamlar: f.getAll("ortamlar"), sevdikleri: f.get("sevdikleri") || "", renkler: f.get("renkler") || "" });
    if (step === 2) WIZ.tipi = WIZ.tipi.map((x, i) => Number(f.get(`t${i}`)) || 0);
    if (step === 3) Object.assign(v, { zaman: f.get("zaman") || "", butce: f.get("butce") || "", kisit: f.get("kisit") || "" });
    if (step === 4) Object.assign(v, { konu: f.get("konu") || "diger", sorun: f.get("sorun") || "" });
  };
  $("#wiz-back")?.addEventListener("click", () => { collect(); WIZ.step--; renderWizard(); window.scrollTo(0, 0); });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    collect();
    if (step < WIZ_STEPS.length - 1) { WIZ.step++; renderWizard(); window.scrollTo(0, 0); return; }
    const btn = $("#wiz-next");
    btn.disabled = true;
    btn.textContent = "Asistanın seni okuyor…";
    try {
      await sendJSON("/api/me/self/start", { intake: v, tipi: WIZ.tipi });
      WIZ = null;
      location.hash = "#/asistan";
    } catch (err) {
      $("#wiz-error").textContent = err.message;
      btn.disabled = false;
      btn.innerHTML = `${icon("sparkles")}Asistanımla tanış`;
    }
  });
}

// ===================================================================
// 2. Asistanla sohbet + "seni böyle anladım" + plan hazırlanıyor
// ===================================================================

async function viewSelfChat() {
  const st = await api("/api/me/self");
  if (st.phase === "form") { location.hash = "#/basla"; return; }
  setHeader([["Asistanım"]], st.phase === "aktif" ? `<a class="btn btn-secondary" href="#/gelisim/planim">${icon("clipboard")}Planım</a>` : "");
  renderChat(st);
  if (st.phase === "plan_hazirlaniyor") {
    poll(async () => {
      const f = await api("/api/me/self");
      if (f.phase !== "plan_hazirlaniyor") { stopPolling(); renderChat(f); if (f.phase === "aktif") toast("Planın hazır 🎉"); }
    }, 3000);
  }
}

const bubble = (m) => m.sender === "kullanici"
  ? `<div class="cbubble me">${esc(m.text)}</div>`
  : `<div class="cb-row"><img class="brand-mark sm" src="/static/logo.svg" alt=""><div class="cbubble ai ${m.kind === "kriz" ? "crisis" : ""}">${esc(m.text).replace(/\n/g, "<br>")}</div></div>`;

function renderChat(st) {
  page.innerHTML = `
    <div class="chat-wrap">
      ${st.crisis ? `<div class="banner banner-err crisis-banner">${icon("alert")}<div><b>Tehlikedeysen hemen <a href="tel:112">112</a>'yi ara.</b>
        <button class="btn btn-secondary btn-sm" id="resume">Güvendeyim, devam et</button></div></div>` : ""}
      <div class="chat" id="chat">${st.messages.map(bubble).join("")}</div>
      ${st.phase === "onay" ? profileCard(st) : ""}
      ${st.phase === "plan_hazirlaniyor" ? `<section class="card plan-wait"><div class="spinner"></div><div><b>Planın hazırlanıyor…</b><p class="muted">Bir dakika kadar sürebilir.</p></div></section>` : ""}
      ${st.phase === "aktif" ? `<div class="row chat-actions"><a class="btn btn-primary" href="#/gelisim/planim">${icon("clipboard")}Planıma git</a></div>` : ""}
      ${["sohbet", "aktif", "kriz", "onay"].includes(st.phase) ? `
        <form class="chat-input" id="chat-form">
          <textarea name="text" rows="1" maxlength="2000" placeholder="${st.phase === "onay" ? "Düzeltmek istediğini yaz…" : "Mesajını yaz…"}" required></textarea>
          <button class="btn btn-primary" aria-label="Gönder">Gönder</button>
        </form>` : ""}
      <p class="disclaimer">${icon("shield")}${esc(st.disclaimer)}</p>
    </div>`;
  const chat = $("#chat");
  // son mesaj görünsün (telefonda sayfanın kendisi kayar; route() önce en üste kaydırır)
  requestAnimationFrame(() => setTimeout(() => {
    const target = $(".profile-card") || $(".plan-wait");
    if (target) target.scrollIntoView({ block: "start" });
    else window.scrollTo(0, document.documentElement.scrollHeight);  // yazma kutusu yapışkan: sayfanın sonuna in
  }, 0));
  $("#resume")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    try { renderChat(await sendJSON("/api/me/self/resume", {})); } catch (err) { toast(err.message, "err"); e.currentTarget.disabled = false; }
  });
  $("#confirm-profile")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    await sendJSON("/api/me/self/confirm", {});
    viewSelfChat();
  });
  $("#fix-profile")?.addEventListener("click", () => { const t = $("#chat-form textarea"); t.focus(); t.placeholder = "ör. Aslında kalabalıktan değil, tanımadığım insanlardan geriliyorum."; });
  $("#restart")?.addEventListener("click", async () => { await sendJSON("/api/me/self/restart", {}); location.hash = "#/basla"; });
  const form = $("#chat-form");
  if (!form) return;
  const ta = $("textarea", form);
  ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`; });
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = ta.value.trim();
    if (!text) return;
    chat.insertAdjacentHTML("beforeend", bubble({ sender: "kullanici", text }) +
      `<div class="cb-row typing"><img class="brand-mark sm" src="/static/logo.svg" alt=""><div class="cbubble ai"><span></span><span></span><span></span></div></div>`);
    chat.scrollTop = chat.scrollHeight;
    ta.value = "";
    $("button", form).disabled = true;
    try {
      const url = st.phase === "onay" ? "/api/me/self/correct" : "/api/me/self/chat";
      renderChat(await sendJSON(url, { text }));
    } catch (err) {
      $(".typing", chat)?.remove();
      toast(err.message, "err");
      $("button", form).disabled = false;
    }
  });
  ta.focus();
}

function profileCard(st) {
  const p = st.profile || {};
  const chips = (arr) => (arr || []).map((x) => `<span class="tag">${esc(x)}</span>`).join("");
  return `<section class="card profile-card">
    <div class="card-head"><h2>${icon("sparkles")} Seni böyle anladım</h2></div>
    <p class="lead">${esc(p.ozet || "")}</p>
    <div class="chips">${chips([...(p.karakter || []), ...(p.zevkler || [])].slice(0, 7))}</div>
    <div class="goal-box"><small>Hedefin</small><b>${esc(p.hedef || "")}</b></div>
    ${p.uzman_onerisi ? `<div class="banner banner-info">${icon("shield")}<div><p>${esc(p.uzman_gerekcesi || "Bir uzmanla görüşmeni de öneririm.")}</p></div></div>` : ""}
    ${st.error ? `<p class="form-error">Plan hazırlanamadı, tekrar dene. (${esc(st.error)})</p>` : ""}
    <div class="row">
      <button class="btn btn-primary" id="confirm-profile">Doğru, planımı hazırla</button>
      <button class="btn btn-secondary" id="fix-profile">${icon("edit")}Düzelt</button>
      <button class="link-btn" id="restart">Baştan başla</button>
    </div>
  </section>`;
}

// ===================================================================
// 3. Planım
// ===================================================================

function renderSelfPlan(body, st) {
  const plan = st.plan;
  const now = selfWeek(st);
  const reviews = Object.fromEntries((plan.degerlendirmeler || []).map((r) => [r.hafta, r]));
  const prof = st.profile || {};
  body.innerHTML = `
    <section class="card plan-head">
      <h2>${esc(plan.baslik)}</h2>
      <p>${esc(plan.giris)}</p>
      <details><summary>Neye dayanıyor?</summary><p>${esc(plan.yontem)}</p></details>
    </section>
    ${prof.uzman_onerisi ? `<div class="banner banner-info">${icon("shield")}<p>${esc(prof.uzman_gerekcesi || "Bir uzmanla görüşmek de iyi gelebilir.")}</p></div>` : ""}
    ${plan.haftalar.map((w) => {
      const tasks = st.plan_tasks.filter((t) => t.detail.hafta === w.hafta);
      const doneN = tasks.filter((t) => t.status === "yapildi").length;
      const state = w.hafta < now ? "past" : w.hafta === now ? "now" : "next";
      const head = `<small>${w.hafta}. hafta${state === "now" ? " · bu hafta" : ""}</small><h2>${esc(w.tema)}</h2>`;
      if (state === "next") {  // sonraki haftalar kapalı durur, istenirse açılır
        return `<details class="card week week-next"><summary class="card-head"><div>${head}</div><span class="muted small">${tasks.length} görev</span></summary>
          ${tasks.map((t) => planTaskRow(t, false)).join("")}</details>`;
      }
      return `<section class="card week week-${state}">
        <div class="card-head"><div>${head}</div><span class="muted small">${doneN}/${tasks.length}</span></div>
        ${reviews[w.hafta - 1] ? `<div class="review-note">${icon("bot")}<p>${esc(reviews[w.hafta - 1].mesaj)}</p></div>` : ""}
        ${tasks.map((t) => planTaskRow(t, true)).join("")}
      </section>`;
    }).join("")}
    <div class="coach-cta"><span class="muted">Bir koçla çalışmak ister misin?</span>
      ${st.coach_request ? `<span class="badge badge-ok">İstek gönderildi</span>` : `<button class="btn btn-secondary btn-sm" id="coach-req">${icon("users")}Koçla eşleş</button>`}</div>`;
  bindTaskButtons(() => route());
  $$("[data-swap]", body).forEach((b) => b.addEventListener("click", () => swapForm(Number(b.dataset.swap))));
  $("#coach-req")?.addEventListener("click", () => openModal("Bir koçla eşleş", `<p>Koç atanınca <b>profilin, planın, ilerlemen ve sohbetlerin</b> onunla paylaşılır.</p>`,
    async () => { await sendJSON("/api/me/self/coach", {}); toast("İsteğin gönderildi"); route(); }, "Gönder"));
}

function planTaskRow(t, active) {
  const d = t.detail;
  return `<div class="ptask ptask-${t.status}">
    <div class="ptask-main">
      <b>${esc(t.text)}</b>${d.degisti ? `<span class="tag">yenilendi</span>` : ""}
      <p>${esc(d.aciklama)}</p>
      <div class="ptask-meta">${dots(d.zorluk)}<span>${d.sure_dk} dk</span>
        ${d.harita_arama ? `<a href="${mapLink(d.harita_arama)}" target="_blank" rel="noopener">📍 Haritada bul</a>` : ""}
        <span class="why" title="Neden sana uygun">💡 ${esc(d.neden)}</span></div>
    </div>
    ${active ? `<div class="ptask-actions">
      <button class="icon-btn ${t.status === "yapildi" ? "on" : ""}" title="Yaptım" data-task="${t.id}" data-status="yapildi">✓</button>
      <button class="icon-btn ${t.status === "yapilmadi" ? "on-bad" : ""}" title="Yapamadım" data-task="${t.id}" data-status="yapilmadi">✕</button>
      ${t.status === "acik" ? `<button class="link-btn" data-swap="${t.id}">Uymadı</button>` : ""}
    </div>` : ""}
  </div>`;
}

function swapForm(taskId) {
  openModal("Görevi değiştir", `
    ${field("Neden uymadı? (isteğe bağlı)", `<input name="text" placeholder="ör. Dizlerim ağrıyor, vaktim yok…">`)}`,
  async (fd) => {
    await sendJSON(`/api/me/self/tasks/${taskId}/swap`, { text: fd.get("text") });
    toast("Görevin yenilendi ✨");
    route();
  }, "Değiştir");
}

// ===================================================================
// Koç / yönetici tarafı: koçsuz mod profili
// ===================================================================

function selfCoachCard(self) {
  const p = self.profile || {};
  const plan = self.plan;
  return `<section class="card">
    <div class="card-head"><h2>${icon("sparkles")} Koçsuz mod profili</h2>
      ${self.coach_request ? `<span class="badge badge-info">Koç istedi</span>` : ""}</div>
    ${p.ozet ? `<p>${esc(p.ozet)}</p>
      <div class="grid-2 tight">
        <div><h4>Ana konu</h4><p>${esc(p.ana_sorun)}</p></div>
        <div><h4>Hedef</h4><p>${esc(p.hedef)}</p></div>
        <div><h4>Karakter</h4><div class="chips">${(p.karakter || []).map((x) => `<span class="tag">${esc(x)}</span>`).join("")}</div></div>
        <div><h4>Zorlanma</h4><p>${p.zorlanma}/10${p.uzman_onerisi ? " · uzman önerildi" : ""}</p></div>
      </div>` : `<p class="muted">Kullanıcı henüz kendini tanıtmayı bitirmedi (aşama: ${esc(self.phase)}).</p>`}
    ${plan ? `<h4>Plan: ${esc(plan.baslik)}</h4>${bullets(plan.haftalar.map((w) => `${w.hafta}. hafta · ${w.tema}`))}` : ""}
  </section>`;
}
