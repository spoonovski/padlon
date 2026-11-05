// Cloudflare Worker: spouští kontrolu kurtů na GitHubu.
//  - POST z webu (tlačítko "Zkontrolovat teď"): jen pro přihlášené hráče z Firebase
//  - Cron Trigger každých 10 min: spolehlivější než plánovač GitHubu
//
// Nastavení (Settings → Variables and Secrets):
//   GH_TOKEN          (Secret)  fine-grained GitHub token, repo padlon, Actions: Read and write
//   FIREBASE_API_KEY  (Text)    apiKey z docs/firebase-config.js
//   REPO              (Text)    spoonovski/padlon
//   ALLOWED_ORIGIN    (Text)    https://spoonovski.github.io

const WORKFLOW = "check.yml";

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${env.REPO}/actions/workflows/${WORKFLOW}${path}`, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${env.GH_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "padlon-refresh",
      ...(init.body ? {"Content-Type": "application/json"} : {}),
    },
  });
}

// Spustí kontrolu, pokud zrovna neběží a poslední nezačala před méně než 2 minutami.
async function dispatch(env) {
  const runs = await gh(env, "/runs?per_page=1");
  if (runs.ok) {
    const last = (await runs.json()).workflow_runs?.[0];
    if (last && (last.status !== "completed" || Date.now() - Date.parse(last.created_at) < 120_000)) {
      return {ok: true, already: true, started: last.created_at};
    }
  }
  const r = await gh(env, "/dispatches", {method: "POST", body: JSON.stringify({ref: "main"})});
  if (!r.ok) return {ok: false, status: r.status, detail: (await r.text()).slice(0, 200)};
  return {ok: true, started: new Date().toISOString()};
}

// Ověří přihlášení hráče: Firebase vrátí účet jen pro platný ID token.
async function isPlayer(env, idToken) {
  const r = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${env.FIREBASE_API_KEY}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({idToken}),
  });
  if (!r.ok) return false;
  const u = (await r.json()).users?.[0];
  return !!(u && u.email);
}

export default {
  async fetch(req, env) {
    const cors = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN || "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      "Content-Type": "application/json",
    };
    const reply = (data, status = 200) => new Response(JSON.stringify(data), {status, headers: cors});
    if (req.method === "OPTIONS") return new Response(null, {headers: cors});
    if (req.method !== "POST") return reply({ok: true, info: "padlon refresh worker"});

    const token = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
    if (!token || !(await isPlayer(env, token))) return reply({ok: false, error: "login"}, 401);

    const res = await dispatch(env);
    return reply(res, res.ok ? 200 : 502);
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
};
