// Cron collector: fetches every account in accounts.json (stored in KV "config"), keeps the
// latest snapshot plus one snapshot per day in KV, and serves it to the Mac at GET /latest.
//
// KV keys
//   config          accounts.json, uploaded by `./lamp.sh push-config` (no redeploy)
//   latest          { generated_at, accounts: {<id>: {kind, status, data, error?, stale_since?}}, days }
//   day:YYYY-MM-DD  { <id>: {followers, views} }, 60-day TTL, for "since last week"
//   last_error      the last run that crashed as a whole
import puppeteer from "@cloudflare/puppeteer";
import { browserDue, settle } from "./parse.js";
import { UA, json, youtube, threads, x } from "./sources.js";

const SOURCES = { json, youtube, threads, x }; // accounts.json group -> collector

const DAY_TTL = 60 * 86400;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const politeGap = () => sleep(1500 + Math.random() * 3000); // 1.5–4.5 s between requests

const BROWSER_GROUPS = new Set(["threads", "x"]); // see browserDue() in parse.js

function browserCtx(env) {
  const ctx = {
    browser: null,
    async pageText(url, marker) {
      ctx.browser ||= await puppeteer.launch(env.BROWSER);
      const page = await ctx.browser.newPage();
      try {
        await page.setUserAgent(UA);
        // These pages never go network-idle; wait for the text we need instead.
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
        await page.waitForFunction(m => new RegExp(m, "i").test(document.body.innerText), { timeout: 15000 }, marker)
          .catch(() => {});
        return await page.evaluate(() => document.body.innerText);
      } finally {
        await page.close();
      }
    },
    close: () => ctx.browser?.close(),
  };
  return ctx;
}

async function collect(env) {
  const config = (await env.KV.get("config", "json")) || {};
  const prev = (await env.KV.get("latest", "json")) || { accounts: {} };
  const accounts = {}, ctx = browserCtx(env), due = browserDue();
  try {
    for (const [group, items] of Object.entries(config)) {
      const fn = Array.isArray(items) && SOURCES[group];
      if (!fn) continue;
      for (const [i, acc] of items.entries()) {
        const old = prev.accounts?.[acc.id];
        if (BROWSER_GROUPS.has(group) && !due && old) { accounts[acc.id] = old; continue; }
        if (i) await politeGap();
        let result;
        try { result = { ok: true, data: await fn(env, acc, ctx) }; }
        catch (e) { result = { ok: false, error: e.message || e }; }
        accounts[acc.id] = settle(group, result, old, prev.generated_at);
      }
    }
  } finally {
    await ctx.close();
  }
  const today = new Date().toISOString().slice(0, 10);
  const daily = {};
  for (const [id, a] of Object.entries(accounts)) {
    if (a.data && "followers" in a.data) daily[id] = { followers: a.data.followers ?? null, views: a.data.views ?? null };
  }
  await env.KV.put(`day:${today}`, JSON.stringify(daily), { expirationTtl: DAY_TTL });
  const days = { [today]: daily };
  for (let i = 1; i <= 8; i++) {
    const d = new Date(Date.now() - i * 86400e3).toISOString().slice(0, 10);
    const v = await env.KV.get(`day:${d}`, "json");
    if (v) days[d] = v;
  }
  const snapshot = { generated_at: new Date().toISOString(), accounts, days };
  await env.KV.put("latest", JSON.stringify(snapshot));
  return snapshot;
}

async function collectLogged(env) {
  try {
    return await collect(env);
  } catch (e) {
    await env.KV.put("last_error", JSON.stringify({ at: new Date().toISOString(), error: String(e.stack || e).slice(0, 2000) }));
    throw e;
  }
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(collectLogged(env));
  },
  async fetch(req, env, ctx) {
    if (!env.PULL_TOKEN || req.headers.get("Authorization") !== `Bearer ${env.PULL_TOKEN}`) {
      return new Response("unauthorized", { status: 401 });
    }
    const url = new URL(req.url);
    if (url.pathname === "/latest") {
      return new Response((await env.KV.get("latest")) || "{}", { headers: { "Content-Type": "application/json" } });
    }
    if (url.pathname === "/collect" && req.method === "POST") {
      // Runs after the response (a manual run is cut off sooner than a cron run); read /latest in a minute.
      ctx.waitUntil(collectLogged(env));
      return Response.json({ started: true }, { status: 202 });
    }
    if (url.pathname === "/config" && req.method === "PUT") {
      await env.KV.put("config", JSON.stringify(await req.json()));
      return Response.json({ ok: true });
    }
    if (url.pathname === "/probe") {
      // One account, synchronously: /probe?group=threads&handle=someone  or  ?group=youtube&channel=UC...
      const group = url.searchParams.get("group"), c = browserCtx(env);
      if (!SOURCES[group]) return Response.json({ error: "unknown group" }, { status: 400 });
      try {
        return Response.json(await SOURCES[group](env, Object.fromEntries(url.searchParams), c));
      } catch (e) {
        return Response.json({ error: String(e.message || e) }, { status: 500 });
      } finally {
        await c.close();
      }
    }
    if (url.pathname === "/last_error") return new Response((await env.KV.get("last_error")) || "{}");
    return new Response("not found", { status: 404 });
  },
};
