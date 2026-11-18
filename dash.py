#!/usr/bin/env python3
"""Render five 128x128 tiles for a Divoom Times Gate, optionally push them, then exit.

  python3 dash.py --demo              # render examples/ into out/ (no lamp, no network)
  python3 dash.py                     # render from config/ + data/ into out/
  python3 dash.py --push 192.168.x.x  # also push to the lamp (needs DIVOOM_TOKEN)
  python3 dash.py --scene a,b         # put pool tiles a,b on screens 4-5 (state untouched)

Inputs   config/scenes.json   fixed tiles (screens 1-3), random pool (4-5), redraw interval
         config/accounts.json account ids, labels, themes (the collector reads the same file)
         config/themes.json   optional: your own themes (merged over the built-in ones)
         data/latest.json     snapshot pulled from the collector (run.sh)
         ~/.claude/projects   Claude Code transcripts, for the `claude` tile
Outputs  data/state.json (which pool tiles are showing), data/claude.json (5-minute cache),
         out/screen1..5.png, out/preview.png
Nothing keeps running: launchd (or cron) calls run.sh, which calls this once.
"""
import base64, datetime as dt, glob, io, json, os, random, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
S = 128

# ------------------------------------------------------------------ theme

_pf = glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc")
CJK_FONT = os.environ.get("DASH_CJK_FONT") or (_pf[0] if _pf else None)
CJK_INDEX = {400: 2, 500: 6}  # PingFang.ttc: TC Regular / Medium; anything heavier -> Semibold (10)

THEMES = {
    # Quiet: thin rules, the accent colours the text of a rising number.
    "night": dict(bg="#0e1116", ink="#e8edf2", ink3="#9aa5b1", ink4="#6b7684", edge="#262d36", accent="#5eead4",
                  sans="/System/Library/Fonts/SFNS.ttf", mono="/System/Library/Fonts/SFNSMono.ttf", num="sans",
                  head=dict(face="sans", weight=600, size=15, width=None, upper=False), heavy_rule=False,
                  up="text", mark=None, wordmark="Dashboard"),
    # Loud: condensed upper-case titles, a 2px ink rule, rising numbers on an accent chip.
    "poster": dict(bg="#111111", ink="#fafafa", ink3="#a3a3a3", ink4="#737373", edge="#2e2e2e", accent="#facc15",
                   sans="/System/Library/Fonts/SFNS.ttf", mono="/System/Library/Fonts/SFNSMono.ttf", num="sans",
                   head=dict(face="sans", weight=860, size=17, width=72, upper=True), heavy_rule=True,
                   up="chip", mark=None, wordmark="Dashboard"),
}

# Platform colour for main numbers, bars and the logo. None = the theme's ink
# (Threads and X have black marks, drawn in the ink colour on a dark lamp).
PLATFORMS = {
    "youtube": dict(logo="youtube", name="YouTube", color="#FF0000"),
    "threads": dict(logo="threads", name="Threads", color=None),
    "x": dict(logo="x", name="X", color=None),
    "claude": dict(logo="claude", name="Claude", color="#D97757"),
    "json": dict(logo=None, name="Stats", color="accent"),
}

LABELS = {"collecting": "Collecting…", "not_set": "Not set up", "followers": "followers",
          "weekly_soon": "weekly change soon", "total": "total followers", "sessions": "Sessions",
          "output": "Output", "through": "through"}

_cache = {}


def cached(key, make):
    if key not in _cache:
        _cache[key] = make()
    return _cache[key]


def logo(name, size):
    path = name if os.path.isabs(name) else os.path.join(ROOT, "assets", "logos", f"{name}.png")
    return cached(("logo", path, size),
                  lambda: Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS))


def font(path, size, weight=400, width=None):
    def make():
        if path == "cjk":
            if not CJK_FONT:
                return None
            return ImageFont.truetype(CJK_FONT, size, index=CJK_INDEX.get(weight, 10) if CJK_FONT.endswith(".ttc") else 0)
        f = ImageFont.truetype(path, size)
        try:
            axes = f.get_variation_axes()
        except Exception:
            return f  # not a variable font
        want = {b"Weight": weight, b"Width": width, b"Optical Size": size}
        f.set_variation_by_axes([max(a["minimum"], min(a["maximum"], want.get(a["name"]) or a["default"]))
                                 for a in axes])
        return f
    return cached(("font", path, size, weight, width), make)


def is_cjk(ch):
    return "⺀" <= ch <= "鿿" or "＀" <= ch <= "￯"


def human(n):
    if n is None:
        return "–"
    if abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M".replace(".0M", "M")
    if abs(n) >= 1e4:
        return f"{n / 1e3:.1f}K".replace(".0K", "K")
    return f"{n:,}"


class Tile:
    def __init__(self, theme, labels):
        self.t, self.L = theme, labels
        self.img = Image.new("RGB", (S, S), theme["bg"])
        self.d = ImageDraw.Draw(self.img)

    def face(self, role):
        return self.t.get(role) or self.t["sans"]

    def runs(self, s):
        out = []
        for ch in s:
            k = is_cjk(ch) and font("cjk", 10) is not None
            if out and out[-1][0] == k:
                out[-1][1] += ch
            else:
                out.append([k, ch])
        return out

    def width_of(self, s, size, weight=400, role="sans", width=None):
        latin, cjk = font(self.face(role), size, weight, width), font("cjk", size, weight)
        return sum(self.d.textlength(r, font=cjk if k else latin, features=["tnum"]) for k, r in self.runs(s))

    def text(self, xy, s, size, color="ink", weight=400, anchor="la", role="sans", width=None):
        """Mixed Latin/CJK on one baseline; CJK uses the CJK font and is never condensed."""
        fill = self.t.get(color, color)
        latin, cjk = font(self.face(role), size, weight, width), font("cjk", size, weight)
        total = self.width_of(s, size, weight, role, width)
        x, y = xy
        x -= {"l": 0, "m": total / 2, "r": total}[anchor[0]]
        asc = latin.getmetrics()[0]
        base = {"t": y + asc, "m": y + asc * 0.36, "s": y}.get(anchor[1], y + asc)
        for k, r in self.runs(s):
            f = cjk if k else latin
            self.d.text((x, base), r, font=f, fill=fill, anchor="ls", features=["tnum"])
            x += self.d.textlength(r, font=f, features=["tnum"])
        return total

    def header(self, platform=None, title=None):
        """32px band: platform logo + name left, theme mark right (if the theme has one), rule below.
        No platform: the theme mark (if any) goes left and the theme wordmark is the title."""
        h, p = self.t["head"], PLATFORMS.get(platform) or {}
        icon = p.get("logo") or self.t.get("mark")
        name = title or p.get("name") or self.t["wordmark"]
        x = 8
        if icon:
            self.img.paste(logo(icon, 22), (8, 5), logo(icon, 22))
            x = 35
        right = 8
        if p.get("logo") and self.t.get("mark"):
            self.img.paste(logo(self.t["mark"], 18), (S - 26, 7), logo(self.t["mark"], 18))
            right = 30
        label = name.upper() if h["upper"] else name
        size = h["size"]
        while size > 10 and self.width_of(label, size, h["weight"], h["face"], h["width"]) > S - x - right:
            size -= 1
        self.text((x, 16), label, size, "ink", h["weight"], anchor="lm", role=h["face"], width=h["width"])
        heavy = self.t["heavy_rule"]
        self.d.line([(0, 32), (S, 32)], fill=self.t["ink" if heavy else "edge"], width=2 if heavy else 1)

    def pcolor(self, platform):
        c = (PLATFORMS.get(platform) or {}).get("color")
        if c == "accent":
            return "accent" if self.t["up"] == "text" else "ink"  # a chip accent stays a fill colour
        return c or "ink"

    def number(self, xy, s, size, anchor="mm", color="ink", max_w=S - 16):
        """Shrinks until it fits in max_w, so a long number never runs into its neighbours."""
        role = self.t["num"]
        weight = 700 if role == "sans" else 600
        while size > 9 and self.width_of(s, size, weight, role) > max_w:
            size -= 1
        self.text(xy, s, size, color, weight, anchor=anchor, role=role)

    def delta(self, xy, d, anchor="mm", size=11):
        """Change since last week. "text": accent text when up. "chip": accent box with bg-coloured text."""
        if not d:
            return
        s, up = d
        if up and self.t["up"] == "chip":
            w = self.width_of(s, size, 600, self.t["num"]) + 8
            x, y = xy
            x0 = {"l": x, "m": x - w / 2, "r": x - w}[anchor[0]]
            self.d.rounded_rectangle([x0, y - size / 2 - 3, x0 + w, y + size / 2 + 2], radius=2, fill=self.t["accent"])
            self.text((x0 + 4, y), s, size, self.t["bg"], 600, anchor="lm", role=self.t["num"])
        else:
            self.text(xy, s, size, "accent" if up else "ink3", 600, anchor=anchor, role=self.t["num"])

    def rule(self, y):
        heavy = self.t["heavy_rule"]
        self.d.line([(10, y), (S - 10, y)], fill=self.t["ink" if heavy else "edge"], width=2 if heavy else 1)

    def bars(self, values, top, bottom, color):
        if not values:
            return
        hi, gap, x0, x1 = max(values) or 1, 3, 12, S - 12
        w = (x1 - x0 - gap * (len(values) - 1)) / len(values)
        for i, v in enumerate(values):
            h = round((bottom - top) * (v or 0) / hi)
            if h:
                x = x0 + i * (w + gap)
                last = i == len(values) - 1
                self.d.rounded_rectangle([x, bottom - h, x + w, bottom], radius=min(2, h / 2),
                                         fill=self.t.get(color, color) if last else self.t["ink4"])
        self.d.line([(x0, bottom + 1), (x1, bottom + 1)], fill=self.t["ink4"], width=1)

    def pending(self, msg):
        """Dotted frame: this tile has no data yet. Never an error screen."""
        for x in range(16, S - 15, 4):
            self.d.point([(x, 46), (x, 106)], fill=self.t["ink4"])
        for y in range(46, 107, 4):
            self.d.point([(16, y), (S - 16, y)], fill=self.t["ink4"])
        self.text((S / 2, 76), msg, 11, "ink4", 500, anchor="mm")


# ------------------------------------------------------------------ data

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def dig(obj, path):
    """'a.b.0.c' -> obj['a']['b'][0]['c'], or None."""
    for k in str(path).split("."):
        try:
            obj = obj[int(k)] if isinstance(obj, list) else obj[k]
        except Exception:
            return None
    return obj


def week_old(snapshot, aid, field="followers"):
    """The value from the oldest stored day in the 7 days before the newest one, or None. Never the
    newest day itself, so a fresh snapshot is not compared with itself."""
    days = snapshot.get("days") or {}
    if not days:
        return None
    newest = dt.date.fromisoformat(max(days))
    for i in range(7, 0, -1):
        old = (days.get((newest - dt.timedelta(days=i)).isoformat()) or {}).get(aid) or {}
        if old.get(field) is not None:
            return old[field]
    return None


def signed(diff):
    return f"{'+' if diff >= 0 else '−'}{human(abs(diff))}", diff > 0


def week_change(snapshot, aid, cur, field="followers"):
    """(text, up) against week_old(), or None until there is an older day."""
    old = week_old(snapshot, aid, field)
    return None if cur is None or old is None else signed(cur - old)


def claude_today(cache_path, root="~/.claude/projects"):
    """Today's Claude Code sessions and output tokens from local transcripts; cached 5 minutes."""
    cached_ = load_json(cache_path, {})
    today = dt.date.today().isoformat()
    if cached_.get("date") == today and time.time() - cached_.get("at", 0) < 300:
        return cached_
    start = dt.datetime.combine(dt.date.today(), dt.time()).astimezone()
    sessions, seen, out_tok = set(), set(), 0
    for p in glob.glob(os.path.join(os.path.expanduser(root), "**", "*.jsonl"), recursive=True):
        if dt.datetime.fromtimestamp(os.path.getmtime(p)).astimezone() < start:
            continue
        with open(p, errors="ignore") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    ts = dt.datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    continue
                if ts < start:
                    continue
                sessions.add(rec.get("sessionId") or p)
                msg = rec.get("message") or {}
                usage, key = msg.get("usage"), (msg.get("id"), rec.get("requestId"))
                if usage and key not in seen:  # one API response is logged once per content block
                    seen.add(key)
                    out_tok += usage.get("output_tokens") or 0
    res = {"date": today, "at": time.time(), "sessions": len(sessions), "output_tokens": out_tok}
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(res, f)
    return res


class Ctx:
    def __init__(self, cfg_dir, data_dir, claude=None):
        self.snapshot = load_json(os.path.join(data_dir, "latest.json"), {})
        accounts = load_json(os.path.join(cfg_dir, "accounts.json"), {})
        self.accounts = {a["id"]: {**a, "platform": group}
                         for group, items in accounts.items() if isinstance(items, list) for a in items}
        themes = {**THEMES, **load_json(os.path.join(cfg_dir, "themes.json"), {})}
        self.themes = {k: {**THEMES["night"], **v} for k, v in themes.items()}
        scenes = load_json(os.path.join(cfg_dir, "scenes.json"), {})
        self.labels = {**LABELS, **scenes.get("labels", {})}
        self.default_theme = scenes.get("theme", "night")
        self._claude = claude
        self.claude_cache = os.path.join(data_dir, "claude.json")

    @property
    def claude(self):
        if self._claude is None:
            self._claude = claude_today(self.claude_cache)
        return self._claude

    def data(self, aid):
        return ((self.snapshot.get("accounts") or {}).get(aid) or {}).get("data")

    def acc(self, aid):
        return self.accounts.get(aid, {})

    def tile(self, spec, aid=None):
        name = spec.get("theme") or self.acc(aid).get("theme") or self.default_theme
        return Tile(self.themes.get(name, self.themes["night"]), self.labels)

    def change(self, aid, field="followers"):
        return week_change(self.snapshot, aid, (self.data(aid) or {}).get(field), field)


# ------------------------------------------------------------------ tiles

def t_claude(ctx, spec):
    """Clock + today's Claude Code sessions and output tokens (read locally, never uploaded)."""
    t, now, c = ctx.tile(spec), dt.datetime.now(), ctx.claude
    t.header("claude", spec.get("title"))
    date_w = t.text((S - 10, 52), now.strftime("%m/%d"), 11, "ink4", 600, anchor="rm", role="mono")
    t.number((10, 52), now.strftime("%H:%M"), 26, anchor="lm", max_w=S - 26 - date_w)
    t.rule(68)
    for y, label, val in ((86, t.L["sessions"], str(c["sessions"])), (110, t.L["output"], human(c["output_tokens"]))):
        w = t.text((10, y), label, 11, "ink3", 500, anchor="lm")
        t.number((S - 10, y), val, 18, anchor="rm", color=t.pcolor("claude"), max_w=S - 26 - w)
    return t


def t_stats(ctx, spec):
    """One JSON-endpoint account: a main number, a second number with % change, optional bars."""
    aid = spec["account"]
    t, d, plat = ctx.tile(spec, aid), ctx.data(aid), ctx.acc(aid).get("platform", "json")
    t.header(plat, spec.get("title") or ctx.acc(aid).get("label"))
    if not d:
        t.pending(spec.get("pending") or t.L["collecting"])
        return t
    main, second = spec.get("main") or {}, spec.get("second")
    w = t.text((10, 50), main.get("label", ""), 11, "ink3", 500, anchor="lm")
    t.number((S - 10, 50), human(d.get(main.get("field"))), 24, anchor="rm", color=t.pcolor(plat), max_w=S - 26 - w)
    if second:
        cur, prev = d.get(second["field"]), d.get(second.get("prev", ""))
        w = t.text((10, 74), second.get("label", ""), 11, "ink3", 500, anchor="lm")
        pct = round((cur - prev) / prev * 100) if cur is not None and prev else None
        t.delta((S - 10, 74), (f"{'▲' if pct >= 0 else '▼'}{abs(pct)}%", pct > 0) if pct is not None else None,
                anchor="rm", size=10)
        t.number((S - 52, 74), human(cur), 15, anchor="rm", max_w=S - 68 - w)
    if spec.get("bars"):
        t.bars([v for v in (d.get(spec["bars"]) or [])][-8:], 88, 110, t.pcolor(plat))
    if spec.get("note") and d.get(spec["note"]):
        t.text((S / 2, 121), f"{t.L['through']} {d[spec['note']]}", 9, "ink4", 500, anchor="mm")
    return t


def t_big(ctx, spec):
    """One account: followers (large), change since last week, handle."""
    aid = spec["account"]
    t, d, plat = ctx.tile(spec, aid), ctx.data(aid), ctx.acc(aid).get("platform")
    t.header(plat, spec.get("title"))
    if not d:
        t.pending(spec.get("pending") or t.L["collecting"])
        return t
    t.number((S / 2, 62), human(d.get("followers")), 42, color=t.pcolor(plat))
    change = ctx.change(aid)
    if change:
        t.delta((S / 2, 94), change)
    else:
        t.text((S / 2, 94), f"{t.L['followers']} · {t.L['weekly_soon']}", 10, "ink4", 500, anchor="mm")
    a = ctx.acc(aid)
    handle = "@" + a["handle"] if a.get("handle") else a.get("label", aid)
    t.text((S / 2, 117), handle, 9, "ink4", 500, anchor="mm", role="mono")
    return t


def t_rows(ctx, spec):
    """Two or three accounts on one platform: label | followers | change."""
    ids = spec["accounts"][:3]
    plat = ctx.acc(ids[0]).get("platform")
    t = ctx.tile(spec, ids[0])
    t.header(plat, spec.get("title"))
    if not any(ctx.data(i) for i in ids):
        t.pending(spec.get("pending") or t.L["collecting"])
        return t
    top, bottom = 34, 126
    step = (bottom - top) / len(ids)
    for n, aid in enumerate(ids):
        y = top + step * (n + 0.5)
        w = t.text((10, y), ctx.acc(aid).get("label", aid), 11, "ink3", 500, anchor="lm", role=t.t["num"])
        t.number((S - 42, y), human((ctx.data(aid) or {}).get("followers")), 20, anchor="rm", color=t.pcolor(plat),
                 max_w=S - 58 - w)
        t.delta((S - 9, y), ctx.change(aid), anchor="rm", size=10)
        if n < len(ids) - 1:
            t.d.line([(10, top + step * (n + 1)), (S - 10, top + step * (n + 1))], fill=t.t["edge"], width=1)
    return t


def t_total(ctx, spec):
    """Followers summed over accounts, with a per-platform breakdown."""
    ids = spec["accounts"]
    t = ctx.tile(spec, ids[0])
    t.header(None, spec.get("title"))
    vals = {i: (ctx.data(i) or {}).get("followers") for i in ids}
    have = {i: v for i, v in vals.items() if v is not None}
    if not have:
        t.pending(spec.get("pending") or t.L["collecting"])
        return t
    t.number((S / 2, 56), human(sum(have.values())), 38)
    t.text((10, 84), t.L["total"], 10, "ink3", 500, anchor="lm")
    olds = [week_old(ctx.snapshot, i) for i in have]
    if None not in olds:
        t.delta((S - 10, 84), signed(sum(have.values()) - sum(olds)), anchor="rm", size=10)
    t.rule(95)
    per = {}
    for i, v in have.items():
        p = ctx.acc(i).get("platform")
        per[p] = per.get(p, 0) + v
    items = [((PLATFORMS.get(p) or {}).get("logo"), human(v)) for p, v in per.items()]
    size = 11  # shrink the breakdown until every platform fits on one line
    while size > 7 and sum(13 * bool(ic) + t.width_of(txt, size, 600, t.t["num"]) + 7 for ic, txt in items) - 7 > S - 20:
        size -= 1
    x = 10
    for ic, txt in items:
        if ic:
            t.img.paste(logo(ic, 11), (int(x), 105), logo(ic, 11))
            x += 13
        x += t.text((x, 110), txt, size, "ink", 600, anchor="lm", role=t.t["num"]) + 7
    return t


def t_pending(ctx, spec):
    t = ctx.tile(spec)
    t.header(spec.get("platform"), spec.get("title"))
    t.pending(spec.get("pending") or t.L["not_set"])
    return t


TILES = {"claude": t_claude, "stats": t_stats, "big": t_big, "rows": t_rows, "total": t_total, "pending": t_pending}


# ------------------------------------------------------------------ which tiles are showing

def draw(pool_ids, prev=(), first=None):
    """Two distinct pool ids at random, never the same pair as last time. `first` pins screen 4."""
    rest = [i for i in pool_ids if i != first]
    if len(pool_ids) < 2:
        return list(pool_ids) * 2
    while True:
        pick = [first, random.choice(rest)] if first else random.sample(pool_ids, 2)
        if sorted(pick) != sorted(prev) or len(pool_ids) == 2 or (first and len(rest) == 1):
            return pick


def current_tiles(cfg, state_path=None, forced=None, now=None):
    """Fixed tiles + two pool tiles. Redraws when the interval has passed (if auto). state_path=None
    means read-only (demo)."""
    pool = {t["id"]: t for t in cfg.get("pool", [])}
    st = load_json(state_path, {}) if state_path else {}
    now = time.time() if now is None else now
    picks = forced.split(",") if forced else st.get("picks")
    rot = cfg.get("rotate", {})
    due = now - st.get("since", 0) >= rot.get("every_minutes", 5) * 60
    stale = not picks or any(p not in pool for p in picks)
    if pool and not forced and (stale or (st.get("auto", rot.get("auto", True)) and due)):
        picks = draw(list(pool), st.get("picks") or ()) if state_path else list(pool)[:2]
        if state_path:
            st.update(picks=picks, since=now)
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "w") as f:
                json.dump(st, f)
    picks = picks or []
    return "+".join(picks) or "fixed", (cfg.get("fixed", []) + [pool[p] for p in picks if p in pool])[:5]


def render(cfg_dir, data_dir, forced=None, claude=None, write_state=True):
    cfg = load_json(os.path.join(cfg_dir, "scenes.json"), None)
    if cfg is None:
        sys.exit(f"missing {cfg_dir}/scenes.json (copy config/scenes.example.json)")
    state = os.path.join(data_dir, "state.json") if write_state else None
    name, specs = current_tiles(cfg, state, forced)
    ctx = Ctx(cfg_dir, data_dir, claude)
    return name, [TILES[s["tile"]](ctx, s).img for s in specs]


# ------------------------------------------------------------------ lamp

def push(ip, token, imgs):
    """Times Gate local API. Uses /usr/bin/curl: on macOS a launchd-started python is blocked from the
    LAN by Local Network privacy, curl is not."""
    def post(command, **params):
        body = json.dumps({"Command": command, "LocalToken": token, **params})
        out = subprocess.run(["/usr/bin/curl", "-s", "-m", "10", "-X", "POST", f"http://{ip}/post",
                              "-H", "Content-Type: application/json", "--data-binary", "@-"],
                             input=body, capture_output=True, text=True, check=True).stdout
        return json.loads(out or "{}")

    for i, img in enumerate(imgs):
        pic_id = int(post("Draw/GetHttpGifId").get("PicId") or 0) + 1  # must be above the lamp's last id
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, subsampling=0)
        r = post("Draw/SendHttpGif", LcdArray=[int(j == i) for j in range(5)], PicNum=1, PicWidth=S,
                 PicOffset=0, PicID=pic_id, PicSpeed=1000, PicData=base64.b64encode(buf.getvalue()).decode())
        if r.get("error_code") != 0:
            print(f"screen {i + 1}: {r}", file=sys.stderr)


def save(imgs, out):
    os.makedirs(out, exist_ok=True)
    for i, img in enumerate(imgs):
        img.save(os.path.join(out, f"screen{i + 1}.png"))
    strip = Image.new("RGB", (S * 5 + 40, S), "#000000")
    for i, img in enumerate(imgs):
        strip.paste(img, (i * (S + 10), 0))
    strip.resize((strip.width * 3, strip.height * 3), Image.NEAREST).save(os.path.join(out, "preview.png"))


if __name__ == "__main__":
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    if "--demo" in sys.argv:
        ex = os.path.join(ROOT, "examples")
        name, imgs = render(ex, ex, arg("--scene"), claude=load_json(os.path.join(ex, "claude.json"), None),
                            write_state=False)
    else:
        name, imgs = render(os.path.join(ROOT, "config"), os.path.join(ROOT, "data"), arg("--scene"))
    save(imgs, os.path.join(ROOT, "out"))
    print(f"rendered {name} -> out/preview.png")
    if arg("--push"):
        push(arg("--push"), int(os.environ["DIVOOM_TOKEN"]), imgs)
