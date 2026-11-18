import test from "node:test";
import assert from "node:assert/strict";
import { browserDue, count, dig, youtubeCounts, threadsCounts, xCounts, settle } from "../src/parse.js";

test("count reads the formats the pages use", () => {
  assert.equal(count("1,090 views"), 1090);
  assert.equal(count("3 subscribers"), 3);
  assert.equal(count("1.2K subscribers"), 1200);
  assert.equal(count("4.5M"), 4500000);
  assert.equal(count("No views"), 0);
  assert.equal(count(""), null);
  assert.equal(count(undefined), null);
});

test("dig follows dotted paths and returns null when missing", () => {
  const o = { a: { b: [10, { c: 5 }] } };
  assert.equal(dig(o, "a.b.0"), 10);
  assert.equal(dig(o, "a.b.1.c"), 5);
  assert.equal(dig(o, "a.x.c"), null);
});

test("youtube counts come from embedded page JSON", () => {
  const html = '..."subscriberCountText":"1.31K subscribers"...,"viewCountText":"88,400 views","videoCountText":"42 videos"';
  assert.deepEqual(youtubeCounts(html), { followers: 1310, views: 88400, videos: 42 });
  assert.deepEqual(youtubeCounts("<html>consent wall</html>"), { followers: null, views: null, videos: null });
});

test("threads and x counts come from rendered text", () => {
  assert.deepEqual(threadsCounts("your.handle\n2,398 followers · 96.3K recent views"), { followers: 2398, recent_views: 96300 });
  assert.deepEqual(threadsCounts("Log in to see more"), { followers: null, recent_views: null });
  assert.deepEqual(xCounts("180 Following  904 Followers"), { followers: 904, following: 180 });
});

test("a failed source keeps the previous numbers and says since when", () => {
  const old = { kind: "x", status: "ok", data: { followers: 900 } };
  const cur = settle("x", { ok: false, error: "login wall" }, old, "2026-11-19T06:00:00Z");
  assert.equal(cur.status, "error");
  assert.deepEqual(cur.data, { followers: 900 });
  assert.equal(cur.stale_since, "2026-11-19T06:00:00Z");
  assert.equal(settle("x", { ok: false, error: "boom" }, undefined).data, undefined);
  assert.equal(settle("json", { ok: true, data: null }).status, "not_configured");
});

test("browser sources run on the first cron of every second UTC hour", () => {
  assert.equal(browserDue(new Date("2026-11-19T08:00:00Z")), true);
  assert.equal(browserDue(new Date("2026-11-19T08:15:00Z")), false);
  assert.equal(browserDue(new Date("2026-11-19T09:00:00Z")), false);
});
