// 칼퇴연구소 댓글 키워드 → 자동 DM (Cloudflare Worker, 무료 플랜으로 충분)
//
// 필요한 Secret (Cloudflare 대시보드 → Worker → Settings → Variables and Secrets):
//   VERIFY_TOKEN  : Meta 웹훅 등록 때 같이 적는 임의 문자열
//   APP_SECRET    : Meta 앱 시크릿 (웹훅 서명 검증용)
//   IG_TOKEN      : 인스타 액세스 토큰 (GitHub Secrets 의 IG_WORK_TOKEN 과 같은 값)
//   IG_USER_ID    : 17841438430452513
// 선택: API_BASE (기본 https://graph.facebook.com/v25.0)

const RULES = [
  {
    keywords: ["프롬프트", "prompt"],
    dm:
      "안녕하세요! 칼퇴연구소예요 🙌\n" +
      "요청하신 '업무용 AI 프롬프트 30'이에요 👇\n" +
      "https://worksmartkr.github.io/kaltoe-lab/prompts/\n\n" +
      "저장해두고 필요할 때 꺼내 쓰세요. 매일 저녁 7시에 칼퇴 팁 올라가요!",
    replies: ["DM 보내드렸어요! 📩", "DM 확인해주세요 🙌", "보내드렸어요! 칼퇴하세요 🏃"],
  },
];

const norm = (s) => (s || "").toLowerCase().replace(/\s+/g, "");

function matchRule(text) {
  const t = norm(text);
  return RULES.find((r) => r.keywords.some((k) => t.includes(norm(k))));
}

async function verifySignature(req, body, secret) {
  const sig = req.headers.get("x-hub-signature-256") || "";
  if (!secret || !sig.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  const hex = [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");
  return hex === sig.slice(7);
}

async function graph(env, path, payload) {
  const base = env.API_BASE || "https://graph.facebook.com/v25.0";
  const r = await fetch(`${base}/${path}?access_token=${encodeURIComponent(env.IG_TOKEN)}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const j = await r.json().catch(() => ({}));
  console.log(path, r.status, JSON.stringify(j));
  return { ok: r.ok, j };
}

async function handleComment(env, v) {
  if (!v || !v.id || !v.text) return;
  if (v.from && v.from.id === env.IG_USER_ID) return; // 내 답글은 무시
  const rule = matchRule(v.text);
  if (!rule) return;
  // 1) 비공개 답장(Private Reply): 댓글 단 사람에게 DM 1회
  const dm = await graph(env, `${env.IG_USER_ID}/messages`, {
    recipient: { comment_id: v.id },
    message: { text: rule.dm },
  });
  // 2) 공개 답글: 다른 사람들도 댓글 달게 유도
  if (dm.ok) {
    const msg = rule.replies[Math.floor(Math.random() * rule.replies.length)];
    await graph(env, `${v.id}/replies`, { message: msg });
  }
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (req.method === "GET") {
      if (url.searchParams.get("hub.mode") === "subscribe" &&
          url.searchParams.get("hub.verify_token") === env.VERIFY_TOKEN) {
        return new Response(url.searchParams.get("hub.challenge") || "", { status: 200 });
      }
      return new Response("kaltoe-dm ok", { status: 200 });
    }
    if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
    const body = await req.text();
    if (!(await verifySignature(req, body, env.APP_SECRET))) {
      console.log("서명 불일치 — 무시");
      return new Response("bad signature", { status: 401 });
    }
    let data = {};
    try { data = JSON.parse(body); } catch { return new Response("bad json", { status: 400 }); }
    const jobs = [];
    for (const entry of data.entry || []) {
      for (const ch of entry.changes || []) {
        if (ch.field === "comments") jobs.push(handleComment(env, ch.value));
      }
    }
    ctx.waitUntil(Promise.all(jobs));
    return new Response("EVENT_RECEIVED", { status: 200 });
  },
};
