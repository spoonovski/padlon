// Tlačítko účtu vpravo nahoře, stejné na všech stránkách.
// Nepřihlášený: "Přihlásit" → okno s přihlášením / registrací.
// Přihlášený: jméno → nabídka Odhlásit / Smazat účet.

const AUTH_ERR = {
  "auth/email-already-in-use": "Tohle jméno už někdo má. Zvol jiné, nebo se přihlas.",
  "auth/weak-password": "Heslo musí mít aspoň 6 znaků.",
  "auth/invalid-credential": "Špatné jméno nebo heslo.",
  "auth/invalid-login-credentials": "Špatné jméno nebo heslo.",
  "auth/wrong-password": "Špatné heslo.",
  "auth/user-not-found": "Hráč s tímhle jménem neexistuje.",
  "auth/too-many-requests": "Moc pokusů. Zkus to za pár minut.",
  "auth/operation-not-allowed": "Přihlašování heslem není ve Firebase zapnuté.",
  "auth/network-request-failed": "Chybí připojení k internetu.",
};
export const authErr = e => AUTH_ERR[e.code] || `Nepovedlo se (${e.code || e.message}).`;

const CSS = `
.acct{position:relative;flex:none}
.acct-btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--paper);color:var(--ink);
  border-radius:999px;padding:5px 12px 5px 5px;font:inherit;font-size:15px;font-weight:650;cursor:pointer;max-width:150px}
.acct-btn.out{padding:8px 14px;background:var(--ink);color:var(--glass);border-color:var(--ink)}
.acct-av{width:28px;height:28px;border-radius:50%;background:var(--ball-3);color:var(--ball-ink);display:grid;place-items:center;font-weight:800;font-size:14px;flex:none}
.acct-nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.acct-menu{position:absolute;right:0;top:calc(100% + 6px);background:var(--paper);border:1px solid var(--line);border-radius:12px;
  box-shadow:0 8px 24px rgba(20,34,53,.14);padding:6px;min-width:180px;z-index:20;display:grid}
.acct-menu button{border:0;background:none;text-align:left;padding:10px 12px;border-radius:8px;font:inherit;font-size:15px;color:var(--ink);cursor:pointer}
.acct-menu button:hover,.acct-menu button:focus-visible{background:var(--glass)}
.acct-menu .danger{color:var(--warn)}
.acct-menu .who{padding:8px 12px 6px;font-size:13px;color:var(--muted)}
dialog.acct-dlg{border:1px solid var(--line);border-radius:16px;padding:0;width:min(400px,calc(100vw - 32px));background:var(--paper);color:var(--ink)}
dialog.acct-dlg::backdrop{background:rgba(15,28,46,.45)}
.acct-dlg form{padding:20px;display:grid;gap:12px}
.acct-dlg h2{margin:0;font-size:21px;font-weight:750}
.acct-dlg p{margin:0;font-size:14px;color:var(--muted)}
.acct-dlg label{display:grid;gap:4px;font-size:13px;color:var(--muted)}
.acct-dlg input{font:inherit;font-size:16px;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--glass);color:var(--ink)}
.acct-dlg .msg{color:var(--warn);font-size:14px;min-height:0}
.acct-dlg .msg:empty{display:none}
.acct-dlg .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.acct-dlg .b{border:0;border-radius:10px;padding:10px 16px;font:inherit;font-weight:650;cursor:pointer;background:var(--ink);color:var(--glass)}
.acct-dlg .b.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.acct-dlg .b.danger{background:var(--warn);color:#fff}
.acct-dlg .lnk{border:0;background:none;padding:0;color:var(--turf-3);font:inherit;font-size:14px;font-weight:600;cursor:pointer}
`;

export function mountAccount(api, el){
  if (!el || !api) return;
  if (!document.getElementById("acct-css")){
    const st = document.createElement("style"); st.id = "acct-css"; st.textContent = CSS; document.head.appendChild(st);
  }
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  let user = null, name = "", signup = false;

  // --- okno přihlášení / registrace
  const dlg = document.createElement("dialog");
  dlg.className = "acct-dlg";
  dlg.innerHTML = `<form method="dialog" novalidate>
    <h2 data-t></h2><p data-s></p>
    <label>Jméno<input name="n" maxlength="24" autocomplete="username" autocapitalize="words"></label>
    <label>Heslo<input name="p" type="password" autocomplete="current-password"></label>
    <p class="msg" role="alert"></p>
    <div class="row"><button class="b" data-go type="submit"></button><button class="b ghost" data-x type="button">Zavřít</button></div>
    <button class="lnk" data-sw type="button"></button>
  </form>`;
  document.body.appendChild(dlg);
  const f = dlg.querySelector("form"), msg = dlg.querySelector(".msg");
  const setMode = s => {
    signup = s;
    dlg.querySelector("[data-t]").textContent = s ? "Nový hráč" : "Přihlášení";
    dlg.querySelector("[data-s]").textContent = s
      ? "Zvol si jméno, pod kterým tě uvidí ostatní, a heslo (aspoň 6 znaků). Stejným jménem a heslem se přihlásíš i na mobilu."
      : "Jménem a heslem, které sis zvolil při registraci.";
    dlg.querySelector("[data-go]").textContent = s ? "Zaregistrovat" : "Přihlásit";
    dlg.querySelector("[data-sw]").textContent = s ? "Už máš účet? Přihlas se" : "Nový hráč? Zaregistruj se";
    f.p.autocomplete = s ? "new-password" : "current-password";
    msg.textContent = "";
  };
  dlg.querySelector("[data-sw]").onclick = () => setMode(!signup);
  dlg.querySelector("[data-x]").onclick = () => dlg.close();
  f.onsubmit = async e => {
    e.preventDefault();
    const n = f.n.value.trim().replace(/\s+/g, " "), p = f.p.value;
    if (!n) return msg.textContent = "Zadej jméno.";
    if (signup && p.length < 6) return msg.textContent = "Heslo musí mít aspoň 6 znaků.";
    if (!p) return msg.textContent = "Zadej heslo.";
    const go = dlg.querySelector("[data-go]"); go.disabled = true; msg.textContent = "";
    try {
      if (signup) await api.signUp(n, p); else await api.signIn(n, p);
      f.p.value = ""; dlg.close();
    } catch(err){ msg.textContent = authErr(err); }
    go.disabled = false;
  };
  const openLogin = (s = false) => { setMode(s); msg.textContent = ""; dlg.showModal(); f.n.focus(); };

  // --- okno smazání účtu
  const del = document.createElement("dialog");
  del.className = "acct-dlg";
  del.innerHTML = `<form method="dialog" novalidate>
    <h2>Smazat účet</h2>
    <p>Smaže se tvoje volno a odhlásíš se ze všech budoucích zápasů. Odehrané zápasy zůstanou ostatním, ty zmizíš ze žebříčku. Nejde to vrátit.</p>
    <label>Pro potvrzení zadej heslo<input name="p" type="password" autocomplete="current-password"></label>
    <p class="msg" role="alert"></p>
    <div class="row"><button class="b danger" data-go type="submit">Smazat natrvalo</button><button class="b ghost" data-x type="button">Zrušit</button></div>
  </form>`;
  document.body.appendChild(del);
  const df = del.querySelector("form"), dmsg = del.querySelector(".msg");
  del.querySelector("[data-x]").onclick = () => del.close();
  const upcoming = uid => new Promise(res => {
    const d = new Date(), ymd = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
    const now = d.getHours()*60 + d.getMinutes();
    let un = null, done = false;
    un = api.watchMatches(ymd, rows => {
      if (done) return; done = true;
      res(rows.filter(m => (m.players || []).includes(uid) && !m.winners && (m.date > ymd || m.start >= now)));
      setTimeout(() => typeof un === "function" && un(), 0);
    });
  });
  df.onsubmit = async e => {
    e.preventDefault();
    const p = df.p.value;
    if (!p) return dmsg.textContent = "Zadej heslo.";
    const go = del.querySelector("[data-go]"); go.disabled = true; dmsg.textContent = "Mažu…";
    try { await api.deleteAccount(name, p, await upcoming(user.uid)); df.p.value = ""; del.close(); }
    catch(err){ dmsg.textContent = ["auth/invalid-credential","auth/wrong-password","auth/invalid-login-credentials"].includes(err.code) ? "Špatné heslo." : authErr(err); }
    go.disabled = false;
  };

  // --- tlačítko a nabídka
  const close = () => { const m = el.querySelector(".acct-menu"); if (m){ m.remove(); el.querySelector(".acct-btn").setAttribute("aria-expanded", "false"); } };
  document.addEventListener("click", e => { if (!el.contains(e.target)) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
  function render(){
    el.className = "acct";
    if (!user){
      el.innerHTML = `<button class="acct-btn out" type="button">Přihlásit</button>`;
      el.querySelector("button").onclick = () => openLogin(false);
      return;
    }
    el.innerHTML = `<button class="acct-btn" type="button" aria-haspopup="menu" aria-expanded="false"><span class="acct-av" aria-hidden="true">${esc((name || "?").charAt(0).toUpperCase())}</span><span class="acct-nm">${esc(name || "Účet")}</span></button>`;
    const b = el.querySelector("button");
    b.onclick = e => {
      e.stopPropagation();
      if (el.querySelector(".acct-menu")) return close();
      const m = document.createElement("div");
      m.className = "acct-menu"; m.setAttribute("role", "menu");
      m.innerHTML = `<div class="who">Přihlášen jako ${esc(name)}</div>
        <button role="menuitem" data-out type="button">Odhlásit</button>
        <button role="menuitem" class="danger" data-del type="button">Smazat účet</button>`;
      m.querySelector("[data-out]").onclick = () => { close(); api.signOut(); };
      m.querySelector("[data-del]").onclick = () => { close(); dmsg.textContent = ""; df.p.value = ""; del.showModal(); df.p.focus(); };
      el.appendChild(m); b.setAttribute("aria-expanded", "true");
      m.querySelector("button").focus();
    };
  }
  api.onAuth(async u => {
    user = u; name = "";
    render();
    // po registraci se profil zapíše o chvilku později, tak to chvíli zkoušíme
    for (let i = 0; u && user === u && i < 4; i++){
      const p = await api.getPlayer(u.uid).catch(() => null);
      if (p && p.name){ name = p.name; render(); break; }
      await new Promise(r => setTimeout(r, 800));
    }
  });
  // stránky můžou okno otevřít i odjinud (např. výzva "Přihlas se")
  window.padelOpenLogin = openLogin;
}
