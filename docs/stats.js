// Společné výpočty pro žebříček, profil hráče a návrh týmů.
//
// ELO: každý začíná na 1000. Síla týmu = průměr ELO hráčů. Po zápase se každému
// hráči vítězného týmu přičte K × (1 − očekávaná šance na výhru) a poraženým
// stejně odečte. Výhra nad silnějším tak dá víc, nad slabším méně.

export const ELO_START = 1000;
export const ELO_K = 32;

export const isResult = m => Array.isArray(m.winners) && Array.isArray(m.losers) && m.winners.length && m.losers.length;
const chrono = (a, b) => a.date.localeCompare(b.date) || a.start - b.start || (a.created || 0) - (b.created || 0);
const avg = (ids, r) => ids.reduce((s, id) => s + (r[id] ?? ELO_START), 0) / ids.length;
export const winChance = (ra, rb) => 1 / (1 + Math.pow(10, (rb - ra) / 400));

export function computeElo(matches){
  const r = {}, history = {};
  for (const m of matches.filter(isResult).sort(chrono)){
    const ra = avg(m.winners, r), rb = avg(m.losers, r);
    const delta = Math.round(ELO_K * (1 - winChance(ra, rb)));
    for (const [ids, sign] of [[m.winners, 1], [m.losers, -1]]){
      for (const id of ids){
        r[id] = (r[id] ?? ELO_START) + sign * delta;
        (history[id] ||= []).push({date: m.date, elo: r[id], delta: sign * delta, match: m.id});
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
export function avatar(player, size = 32){
  const name = (player && player.name) || "?";
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const st = `width:${size}px;height:${size}px;border-radius:50%;flex:none;display:inline-grid;place-items:center;overflow:hidden;vertical-align:middle;`;
  if (player && typeof player.photo === "string" && player.photo.startsWith("data:image/"))
    return `<img src="${esc(player.photo)}" alt="" style="${st}object-fit:cover" width="${size}" height="${size}">`;
  return `<span aria-hidden="true" style="${st}background:var(--ball-3);color:var(--ball-ink);font-weight:800;font-size:${Math.round(size * .45)}px">${esc(name.charAt(0).toUpperCase())}</span>`;
}
