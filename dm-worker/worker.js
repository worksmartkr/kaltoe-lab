// 칼퇴연구소 댓글 키워드 → 자동 DM (Cloudflare Worker, 무료 플랜으로 충분)
//
// 필요한 Secret (Cloudflare 대시보드 → Worker → Settings → Variables and Secrets):
//   VERIFY_TOKEN  : Meta 웹훅 등록 때 같이 적는 임의 문자열
//   APP_SECRET    : Meta 앱 시크릿 (웹훅 서명 검증용)
//   IG_TOKEN      : 인스타 액세스 토큰 (GitHub Secrets 의 IG_WORK_TOKEN 과 같은 값)
//   IG_USER_ID    : 17841438430452513
// 선택: API_BASE (기본 https://graph.facebook.com/v25.0)

const SITE = "https://worksmartkr.github.io/kaltoe-lab";
const FALLBACK = { title: "업무용 AI 프롬프트 30", url: `${SITE}/prompts/` };
// 댓글 단 사람에게 보내는 첫 DM (팔로우 요청 + 확인 버튼)
const ASK = (o) =>
  "안녕하세요! 칼퇴연구소예요 🙌\n" +
  `'${o.title}' 정리본은 팔로워분들께만 보내드려요.\n\n` +
  "① @worksmart.kr 팔로우 (이미 팔로우 중이면 건너뛰기)\n" +
  "② 아래 '팔로우 했어요' 버튼 누르기\n\n" +
  "확인되면 바로 링크 보내드릴게요!";
// 팔로우 확인되면 보내는 링크
const LINK = (o) =>
  "감사합니다 🙏\n" +
  `요청하신 '${o.title}' 정리본이에요 👇\n` +
  `${o.url}\n\n` +
  "복사해서 바로 쓰세요. 매일 저녁 7시에 칼퇴 팁 올라가요!";
const NOT_YET =
  "아직 팔로우가 확인되지 않아요 😢\n" +
  "@worksmart.kr 팔로우 후 '팔로우 했어요'를 다시 눌러주세요!";
// 대댓글
const R_SENT = ["DM으로 링크 보내드렸어요! 📩", "DM으로 링크 보내드렸어요! 확인해주세요 🙌", "DM으로 링크 보내드렸어요! 칼퇴하세요 🏃"];
const R_FOLLOW_DM = [
  "팔로우 해주셔야 자료를 보내드릴 수 있어요 🙏 @worksmart.kr 팔로우 후 DM의 '팔로우 했어요' 버튼을 눌러주세요!",
  "팔로워분들께만 보내드려요! 팔로우 후 DM에서 '팔로우 했어요' 눌러주시면 바로 보내드릴게요 🙌",
];
// 팔로우 여부를 아직 확인할 수 없는 경우 (처음 연락하는 사람은 인스타가 확인을 막음)
const R_CHECK_DM = ["DM 보내드렸어요! 📩 DM에서 '팔로우 했어요' 누르면 링크 바로 보내드려요", "DM 확인해주세요 🙌 버튼 하나만 누르면 링크 보내드려요!"];
const R_FOLLOW = ["팔로우 해주셔야 DM으로 보내드릴 수 있어요 🙏 @worksmart.kr 팔로우 후 댓글 다시 달아주세요!"];
const BTN = (mediaId) => [{ content_type: "text", title: "팔로우 했어요 ✅", payload: `FOLLOW_CHECK|${mediaId || ""}` }];
const CHECK_WORDS = /팔로우|했어|했습니다|완료|ok|확인|프롬프트/i;
const pick = (a) => a[Math.floor(Math.random() * a.length)];

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

// 캡션 첫 줄 SHA-1 앞 10자리 = 정리본 페이지 주소 (pages.py 와 같은 규칙)
async function slugFor(caption) {
  const first = ((caption || "").split("\n").map((l) => l.trim()).find((l) => l) || "").normalize("NFC");
  const h = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(first));
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 10);
}

// 게시물 → 보낼 정리본 {title, url}. 페이지가 없으면 프롬프트 30 페이지
async function offerFor(env, mediaId) {
  if (!mediaId) return FALLBACK;
  const m = await graphGet(env, mediaId, "caption");
  if (!m.ok || !m.j.caption) return FALLBACK;
  const url = `${SITE}/p/${await slugFor(m.j.caption)}/`;
  const r = await fetch(url, { cf: { cacheTtl: 60 } });
  if (!r.ok) { console.log("정리본 없음 →", url); return FALLBACK; }
  const t = ((await r.text()).match(/<title>([^<|]+)/) || [])[1];
  return { title: (t || "이 게시물").trim(), url };
}

// 같은 사람이 같은 게시물에 여러 번 댓글 달면 첫 댓글에만 반응 (Cache API, 최선 노력)
async function seenBefore(userId, mediaId) {
  const key = new Request(`https://kaltoe-dm.internal/seen/${userId}/${mediaId}`);
  if (await caches.default.match(key)) return true;
  await caches.default.put(key, new Response("1", { headers: { "cache-control": "max-age=2592000" } }));
  return false;
}

async function handleComment(env, v) {
  console.log("COMMENT", JSON.stringify(v));
  if (!v || !v.id || !v.from) return console.log("skip: 내용 없음");
  if (v.from.id === env.IG_USER_ID) return console.log("skip: 내 댓글");
  if (v.parent_id) return console.log("skip: 대댓글");
  const mediaId = v.media && v.media.id;
  if (await seenBefore(v.from.id, mediaId)) return console.log("skip: 이미 보낸 사람");
  const offer = await offerFor(env, mediaId);
  const follows = await isFollower(env, v.from.id);
  if (follows === true) {
    const dm = await graph(env, `${env.IG_USER_ID}/messages`, {
      recipient: { comment_id: v.id }, message: { text: LINK(offer) },
    });
    if (dm.ok) await graph(env, `${v.id}/replies`, { message: pick(R_SENT) });
    return;
  }
  // 미팔로워(false) 또는 확인 불가(null): 팔로우 요청 DM(버튼) + 팔로우 요청 대댓글
  let dm = await graph(env, `${env.IG_USER_ID}/messages`, {
    recipient: { comment_id: v.id }, message: { text: ASK(offer), quick_replies: BTN(mediaId) },
  });
  if (!dm.ok) {
    dm = await graph(env, `${env.IG_USER_ID}/messages`, {
      recipient: { comment_id: v.id },
      message: { text: ASK(offer).replace("아래 '팔로우 했어요' 버튼 누르기", "이 메시지에 '팔로우 했어요'라고 답장") },
    });
  }
  if (dm.ok) await rememberOffer(v.from.id, mediaId);
  await graph(env, `${v.id}/replies`, { message: pick(!dm.ok ? R_FOLLOW : follows === false ? R_FOLLOW_DM : R_CHECK_DM) });
}

// 버튼 대신 글로 답장한 경우를 위해 마지막 요청 게시물 기억
async function rememberOffer(userId, mediaId) {
  await caches.default.put(new Request(`https://kaltoe-dm.internal/last/${userId}`),
    new Response(mediaId || "", { headers: { "cache-control": "max-age=604800" } }));
}
async function lastOffer(userId) {
  const r = await caches.default.match(new Request(`https://kaltoe-dm.internal/last/${userId}`));
  return r ? await r.text() : "";
}

// DM으로 '팔로우 했어요' 버튼/답장이 오면 팔로우 확인 후 링크 전송
async function handleMessage(env, m) {
  const sender = m.sender && m.sender.id;
  if (!sender || sender === env.IG_USER_ID || !m.message || m.message.is_echo) return;
  const payload = (m.message.quick_reply && m.message.quick_reply.payload) || "";
  if (!payload.startsWith("FOLLOW_CHECK") && !CHECK_WORDS.test(m.message.text || "")) return;
  const mediaId = payload.split("|")[1] || (await lastOffer(sender));
  const follows = await isFollower(env, sender);
  if (follows === false) {
    await graph(env, `${env.IG_USER_ID}/messages`, {
      recipient: { id: sender }, message: { text: NOT_YET, quick_replies: BTN(mediaId) },
    });
    return;
  }
  // true 이거나 확인 불가(null)면 링크 전송 (API 오류로 사람을 놓치지 않게)
  const offer = await offerFor(env, mediaId);
  await graph(env, `${env.IG_USER_ID}/messages`, { recipient: { id: sender }, message: { text: LINK(offer) } });
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
    console.log("WEBHOOK", body.slice(0, 1500));
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
