// Pure helpers, no Workers APIs, so `node --test` can check them.

// "1,090 views" / "3 subscribers" / "1.2K followers" / "No views" -> number (or null)
export function count(text) {
  if (text === null || text === undefined) return null;
  const s = String(text).replace(/,/g, "");
  const m = s.match(/(\d+(?:\.\d+)?)\s*([KMB])?\b/i);
  if (!m) return /^\s*no\b/i.test(s) ? 0 : null;
  const mult = { K: 1e3, M: 1e6, B: 1e9 }[(m[2] || "").toUpperCase()] || 1;
  return Math.round(parseFloat(m[1]) * mult);
}

// First number matching `re` (one capture group) in rendered page text.
export function pageCount(text, re) {
  const m = String(text || "").match(re);
  return m ? count(m[1]) : null;
}

// dig({a: {b: [1, 2]}}, "a.b.1") -> 2; missing -> null
export function dig(obj, path) {
  let cur = obj;
  for (const k of String(path).split(".")) {
    if (cur === null || typeof cur !== "object" || !(k in cur)) return null;
    cur = cur[k];
  }
  return cur ?? null;
}

// The YouTube channel page embeds its counts as JSON strings.
export function youtubeCounts(html) {
  const pick = key => (html.match(new RegExp(`"${key}":"([^"]*)"`)) || [])[1];
  return {
    followers: count(pick("subscriberCountText")),
    views: count(pick("viewCountText")),
    videos: count(pick("videoCountText")),
  };
}

// Threads / X profile text after the page's JavaScript has run.
export const threadsCounts = text => ({
  followers: pageCount(text, /([\d.,]+[KMB]?)\s+followers/i),
  recent_views: pageCount(text, /([\d.,]+[KMB]?)\s+recent views/i), // only shown when logged in
});
export const xCounts = text => ({
  followers: pageCount(text, /([\d.,]+[KMB]?)\s+Followers/),
  following: pageCount(text, /([\d.,]+[KMB]?)\s+Following/),
});

// Previous snapshot's data is kept when a source fails, marked with when it went stale.
export function settle(kind, result, old, prevAt) {
  if (result.ok) return result.data === null ? { kind, status: "not_configured" } : { kind, status: "ok", data: result.data };
  const cur = { kind, status: "error", error: String(result.error).slice(0, 300) };
  if (old?.data) Object.assign(cur, { data: old.data, stale_since: old.stale_since || prevAt });
  return cur;
}

// Browser Run (formerly Browser Rendering) on the Workers Free plan allows 10 browser-minutes a day. A pass over a
// handful of Threads/X profiles takes ~25 s, so browser groups run on the first cron of every
// second hour (UTC) and other runs carry their last numbers forward.
export const browserDue = (now = new Date()) => now.getUTCHours() % 2 === 0 && now.getUTCMinutes() < 15;
