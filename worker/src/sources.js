// One function per account group in accounts.json. Each returns the account's numbers,
// returns null when it is not configured, or throws.
import { dig, youtubeCounts, threadsCounts, xCounts } from "./parse.js";

export const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36";

// Any JSON endpoint you own: GET acc.url (Bearer env[acc.auth_secret] if set), then
// map acc.fields = {name: "dotted.path"} into flat numbers the `stats` tile can show.
export async function json(env, acc) {
  if (!acc.url) return null;
  const headers = { Accept: "application/json" };
  if (acc.auth_secret) {
    if (!env[acc.auth_secret]) return null;
    headers.Authorization = `Bearer ${env[acc.auth_secret]}`;
  }
  const r = await fetch(acc.url, { headers });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const body = await r.json();
  return Object.fromEntries(Object.entries(acc.fields || {}).map(([k, path]) => [k, dig(body, path)]));
}

// Public channel page; no API key.
export async function youtube(_env, acc) {
  const r = await fetch(`https://www.youtube.com/channel/${acc.channel}/about`, {
    headers: { "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", Cookie: "CONSENT=YES+1" },
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const c = youtubeCounts(await r.text());
  if (c.followers === null && c.views === null) throw new Error("counts not found (page layout changed or consent wall)");
  return c;
}

// Threads and X render counts with JavaScript, so read them through a headless browser.
// ctx.pageText(url, marker) is provided by index.js (Cloudflare Browser Rendering).
export async function threads(_env, acc, ctx) {
  const c = threadsCounts(await ctx.pageText(`https://www.threads.com/@${acc.handle}`, "followers"));
  if (c.followers === null) throw new Error("followers not found on rendered page");
  return c;
}

export async function x(_env, acc, ctx) {
  const c = xCounts(await ctx.pageText(`https://x.com/${acc.handle}`, "Followers"));
  if (c.followers === null) throw new Error("followers not found on rendered page (login wall?)");
  return c;
}
