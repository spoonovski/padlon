// Společné výpočty pro žebříček, profil hráče a návrh týmů.
//
// ELO: každý začíná na 700 (skrytě, do prvního zápasu je "Unranked"). Síla týmu = průměr ELO hráčů. Vítězové dostanou
// K × (1 − očekávaná šance na výhru), poražení ztratí 75 % této částky.
// Proti stejně silným je to +100 / −75, nad silnějšími víc, nad slabšími méně.
// Protože se za prohru bere o něco méně, ELO s hraním postupně roste a vyšší
// úrovně jsou dosažitelné. ELO nespadne pod 0.

export const ELO_START = 700;
export const ELO_K = 200;          // výhra nad stejně silnými = K/2 = +100
export const ELO_LOSS = 0.75;      // prohra = 75 % toho, co by získal vítěz
export const ELO_SCALE = 2000;     // jak moc rozdíl ELO mění šanci (vyšší = pozvolněji)

// Úrovně podle ELO
export const TIERS = [
  {min: 1500, name: "Demonic",          icon: "😈", bg: "linear-gradient(135deg,#0d0000 0%,#3a0006 45%,#b3001b 100%)", fg: "#ffd9dd", ring: "#c4001f", glow: "0 0 10px rgba(196,0,31,.55)"},
  {min: 1300, name: "Master", icon: "💗", bg: "linear-gradient(135deg,#ffe3f3 0%,#ff9fd2 50%,#ff5fae 100%)",  fg: "#5a0632", ring: "#ff6fb5", glow: "0 0 8px rgba(255,111,181,.45)"},
  {min: 1100, name: "Diamond",        icon: "💎", bg: "linear-gradient(135deg,#e8fbff 0%,#9be7ff 50%,#4cc3f5 100%)",  fg: "#063a52", ring: "#4cc3f5", glow: "0 0 8px rgba(76,195,245,.45)"},
  {min: 900,  name: "Emerald",         icon: "",   bg: "linear-gradient(135deg,#6fdc8c 0%,#24a148 100%)",              fg: "#03290f", ring: "#24a148", glow: "none"},
  {min: 700,  name: "Gold",          icon: "",   bg: "linear-gradient(135deg,#ffe58a 0%,#f2b51c 55%,#c98a0b 100%)",  fg: "#3d2a00", ring: "#e0a313", glow: "none"},
  {min: 500,  name: "Silver",           icon: "",   bg: "linear-gradient(135deg,#e3e7eb 0%,#a7b0ba 100%)",              fg: "#2a3138", ring: "#9aa4ae", glow: "none"},
  {min: 0,    name: "Bronze",          icon: "",   bg: "linear-gradient(135deg,#b07a4a 0%,#7a4b25 100%)",              fg: "#fff3e6", ring: "#8b5a2b", glow: "none"},
];
export const tierOf = elo => TIERS.find(t => elo >= t.min) || TIERS[TIERS.length - 1];
// Hráč bez zápasu: ELO se neukazuje
export const UNRANKED = {name: "Unranked", icon: "", bg: "repeating-linear-gradient(135deg,var(--busy) 0 6px,var(--paper) 6px 12px)", fg: "var(--muted)", ring: "var(--line)", glow: "none"};
export function tierBadge(elo, {big = false, withElo = false, text = null} = {}){
  const t = elo === null ? UNRANKED : tierOf(elo);
  if (elo === null) withElo = false;
  const fs = big ? 14 : 11, pad = big ? "4px 11px" : "2px 7px";
  return `<span class="tier" title="${t.name}" style="display:inline-flex;align-items:center;gap:4px;white-space:nowrap;vertical-align:middle;border-radius:999px;padding:${pad};font-size:${fs}px;font-weight:750;line-height:1.3;background:${t.bg};color:${t.fg};box-shadow:${t.glow}">${text !== null ? text : (t.icon ? t.icon + " " : "") + t.name + (withElo ? " · " + elo : "")}</span>`;
}

export const isResult = m => Array.isArray(m.winners) && Array.isArray(m.losers) && m.winners.length && m.losers.length;
const chrono = (a, b) => a.date.localeCompare(b.date) || a.start - b.start || (a.created || 0) - (b.created || 0);
const avg = (ids, r) => ids.reduce((s, id) => s + (r[id] ?? ELO_START), 0) / ids.length;
export const winChance = (ra, rb) => 1 / (1 + Math.pow(10, (rb - ra) / ELO_SCALE));

export function computeElo(matches){
  const r = {}, history = {};
  for (const m of matches.filter(isResult).sort(chrono)){
    const ra = avg(m.winners, r), rb = avg(m.losers, r);
    const gain = ELO_K * (1 - winChance(ra, rb));
    for (const [ids, change] of [[m.winners, Math.round(gain)], [m.losers, -Math.round(gain * ELO_LOSS)]]){
      for (const id of ids){
        const before = r[id] ?? ELO_START;
        r[id] = Math.max(0, before + change);
        (history[id] ||= []).push({date: m.date, elo: r[id], delta: r[id] - before, match: m.id});
      }
    }
  }
  return {ratings: r, history};
}

export const ratingOf = (ratings, id) => Math.round(ratings[id] ?? ELO_START);

// Nejvyrovnanější rozdělení 4 hráčů do dvou dvojic.
export function balanceTeams(ids, ratings){
  if (ids.length !== 4) return null;
  const [a, b, c, d] = ids;
  const options = [[[a, b], [c, d]], [[a, c], [b, d]], [[a, d], [b, c]]].map(([t1, t2]) => {
    const p = winChance(avg(t1, ratings), avg(t2, ratings));
    return {t1, t2, p1: p, diff: Math.abs(p - 0.5)};
  });
  return options.sort((x, y) => x.diff - y.diff)[0];
}

// Statistiky jednoho hráče.
export function playerStats(id, matches){
  const res = matches.filter(m => isResult(m) && (m.winners.includes(id) || m.losers.includes(id))).sort(chrono);
  const partner = {}, rival = {};
  let w = 0, l = 0;
  for (const m of res){
    const won = m.winners.includes(id);
    won ? w++ : l++;
    const mine = won ? m.winners : m.losers, theirs = won ? m.losers : m.winners;
    for (const p of mine) if (p !== id){ const s = partner[p] ||= {id: p, w: 0, l: 0}; won ? s.w++ : s.l++; }
    for (const o of theirs){ const s = rival[o] ||= {id: o, w: 0, l: 0}; won ? s.w++ : s.l++; }
  }
  // aktuální série (výhry nebo prohry v řadě od posledního zápasu)
  let streak = 0, streakWin = null;
  for (let i = res.length - 1; i >= 0; i--){
    const won = res[i].winners.includes(id);
    if (streakWin === null) streakWin = won;
    if (won !== streakWin) break;
    streak++;
  }
  const parts = Object.values(partner), rivals = Object.values(rival);
  const bestPartner = parts.filter(p => p.w > 0).sort((a, b) => b.w - a.w || (b.w / (b.w + b.l)) - (a.w / (a.w + a.l)))[0] || null;
  const mostPartner = parts.sort((a, b) => (b.w + b.l) - (a.w + a.l))[0] || null;
  const nemesis = rivals.filter(o => o.l > 0 && o.l >= o.w).sort((a, b) => b.l - a.l || (b.l / (b.w + b.l)) - (a.l / (a.w + a.l)))[0] || null;
  const victim = rivals.filter(o => o.w > o.l).sort((a, b) => b.w - a.w)[0] || null;
  return {
    played: w + l, w, l, pts: 3 * w, pct: w + l ? Math.round(100 * w / (w + l)) : 0,
    form: res.slice(-5).map(m => m.winners.includes(id)),
    streak, streakWin, bestPartner, mostPartner, nemesis, victim,
    matches: res.slice().reverse(),
  };
}

// Kolečko s fotkou nebo iniciálou.
export function avatar(player, size = 32, elo = null){
  // s ELO dostane fotka rámeček v barvě úrovně
  if (elo !== null){
    const t = elo === "unranked" ? UNRANKED : tierOf(elo), w = Math.max(2, Math.round(size / 16));
    return `<span style="display:inline-grid;place-items:center;border-radius:50%;padding:${w}px;background:${t.bg};box-shadow:${t.glow};flex:none;vertical-align:middle">${avatar(player, size - 2 * w)}</span>`;
  }
  const name = (player && player.name) || "?";
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const st = `width:${size}px;height:${size}px;border-radius:50%;flex:none;display:inline-grid;place-items:center;overflow:hidden;vertical-align:middle;`;
  if (player && typeof player.photo === "string" && player.photo.startsWith("data:image/"))
    return `<img src="${esc(player.photo)}" alt="" style="${st}object-fit:cover" width="${size}" height="${size}">`;
  return `<span aria-hidden="true" style="${st}background:var(--ball-3);color:var(--ball-ink);font-weight:800;font-size:${Math.round(size * .45)}px">${esc(name.charAt(0).toUpperCase())}</span>`;
}
