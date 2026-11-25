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
    // 1단계: 댓글 단 사람에게 보내는 첫 DM (팔로우 요청 + 확인 버튼)
    ask:
      "안녕하세요! 칼퇴연구소예요 🙌\n" +
      "'업무용 AI 프롬프트 30'은 팔로워분들께만 보내드려요.\n\n" +
      "① @worksmart.kr 팔로우\n" +
      "② 아래 '팔로우 했어요' 버튼 누르기\n\n" +
      "확인되면 바로 링크 보내드릴게요!",
    // 2단계: 팔로우 확인되면 보내는 자료
    dm:
      "팔로우 확인됐어요, 감사합니다 🙏\n" +
      "요청하신 '업무용 AI 프롬프트 30'이에요 👇\n" +
      "https://worksmartkr.github.io/kaltoe-lab/prompts/\n\n" +
      "저장해두고 필요할 때 꺼내 쓰세요. 매일 저녁 7시에 칼퇴 팁 올라가요!",
    replies: ["DM 보내드렸어요! 📩", "DM 확인해주세요 🙌", "DM 보냈어요! 칼퇴하세요 🏃"],
  },
];
const NOT_YET =
  "아직 팔로우가 확인되지 않아요 😢\n" +
  "@worksmart.kr 팔로우 후 '팔로우 했어요'를 다시 눌러주세요!";
const FOLLOW_BTN = [{ content_type: "text", title: "팔로우 했어요 ✅", payload: "FOLLOW_CHECK" }];
const CHECK_WORDS = /팔로우|했어|했습니다|완료|ok|확인|프롬프트/i;

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

async function graphGet(env, path, fields) {
  const base = env.API_BASE || "https://graph.facebook.com/v25.0";
  const r = await fetch(`${base}/${path}?fields=${fields}&access_token=${encodeURIComponent(env.IG_TOKEN)}`);
  const j = await r.json().catch(() => ({}));
  console.log("GET", path, r.status, JSON.stringify(j));
  return { ok: r.ok, j };
}

// 팔로우 여부 확인. API가 실패하면 null (판단 불가)
async function isFollower(env, igsid) {
  const r = await graphGet(env, igsid, "is_user_follow_business");
  return r.ok && typeof r.j.is_user_follow_business === "boolean" ? r.j.is_user_follow_business : null;
}

async function handleComment(env, v) {
  if (!v || !v.id || !v.text) return;
  if (v.from && v.from.id === env.IG_USER_ID) return; // 내 답글은 무시
  const rule = matchRule(v.text);
  if (!rule) return;
  // 1) 비공개 답장(Private Reply, 댓글당 1회): 팔로우 요청 + 확인 버튼
  let dm = await graph(env, `${env.IG_USER_ID}/messages`, {
    recipient: { comment_id: v.id },
    message: { text: rule.ask, quick_replies: FOLLOW_BTN },
  });
  if (!dm.ok) { // 버튼이 거부되면 글로만 안내
    dm = await graph(env, `${env.IG_USER_ID}/messages`, {
      recipient: { comment_id: v.id },
      message: { text: rule.ask.replace("아래 '팔로우 했어요' 버튼 누르기", "이 메시지에 '팔로우 했어요'라고 답장") },
    });
  }
  // 2) 공개 답글: 다른 사람들도 댓글 달게 유도
  if (dm.ok) {
    const msg = rule.replies[Math.floor(Math.random() * rule.replies.length)];
    await graph(env, `${v.id}/replies`, { message: msg });
  }
}

// DM으로 '팔로우 했어요' 버튼/답장이 오면 팔로우 확인 후 자료 전송
async function handleMessage(env, m) {
  const sender = m.sender && m.sender.id;
  if (!sender || sender === env.IG_USER_ID || !m.message || m.message.is_echo) return;
  const payload = m.message.quick_reply && m.message.quick_reply.payload;
  if (payload !== "FOLLOW_CHECK" && !CHECK_WORDS.test(m.message.text || "")) return;
  const rule = RULES[0];
  const follows = await isFollower(env, sender);
  if (follows === false) {
    await graph(env, `${env.IG_USER_ID}/messages`, {
      recipient: { id: sender }, message: { text: NOT_YET, quick_replies: FOLLOW_BTN },
    });
    return;
  }
  // true 이거나 확인 불가(null)면 자료 전송 (API 오류로 사람을 놓치지 않게)
  await graph(env, `${env.IG_USER_ID}/messages`, { recipient: { id: sender }, message: { text: rule.dm } });
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
      for (const m of entry.messaging || []) jobs.push(handleMessage(env, m));
    }
    ctx.waitUntil(Promise.all(jobs));
    return new Response("EVENT_RECEIVED", { status: 200 });
  },
};
