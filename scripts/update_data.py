#!/usr/bin/env python3
"""抓取 NBA 官方排名并生成 data.json（供页面在实时接口不可用时兜底）。"""
import json, time, urllib.request, urllib.error, os, sys, datetime as dt

AB2KEY = {"SA": "SAS", "NY": "NYK", "WSH": "WAS", "GS": "GSW", "NO": "NOP", "UTAH": "UTA"}
LOGOS = {"SAS": "sa", "NYK": "ny", "WAS": "wsh", "GSW": "gs", "NOP": "no", "UTA": "utah"}
ENDPOINTS = [
    "https://cdn.espn.com/core/nba/standings?xhr=1",
    "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings",
]

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; nba-pred-board/1.0)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def groups_of(payload):
    c = payload.get("content") or {}
    st = c.get("standings") or {}
    if st.get("groups"):
        return st["groups"]
    return payload.get("children") or []

def num(stat, key, default=0):
    v = stat.get(key)
    if isinstance(v, dict):
        v = v.get("value")
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def normalize(payload):
    rows = []
    for g in groups_of(payload):
        side = "E" if str(g.get("abbreviation", "")).upper().startswith("E") else "W"
        entries = (g.get("standings") or {}).get("entries") or []
        for idx, en in enumerate(entries, 1):
            team = en.get("team") or {}
            raw = str(team.get("abbreviation", "")).upper()
            ab = AB2KEY.get(raw, raw)
            if not ab:
                continue
            st = {s.get("name"): s for s in (en.get("stats") or [])}
            seed = team.get("seed") or int(num(st, "playoffSeed", 0)) or idx
            streak = (st.get("streak") or {}).get("displayValue")
            logo = ((team.get("logos") or [{}])[0] or {}).get("href") or \
                "https://a.espncdn.com/i/teamlogos/nba/500/%s.png" % LOGOS.get(ab, ab.lower())
            rows.append({
                "ab": ab, "conf": "E" if ab in EAST else side, "seed": int(seed),
                "w": int(num(st, "wins")), "l": int(num(st, "losses")),
                "pct": round(num(st, "winPercent"), 4),
                "streak": streak, "logo": logo,
                "pf": round(num(st, "avgPointsFor"), 1), "pa": round(num(st, "avgPointsAgainst"), 1),
            })
    return rows

EAST = {"PHI","BOS","DET","MIA","ATL","NYK","CLE","ORL","TOR","IND","WAS","CHA","CHI","BKN","MIL"}

SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"

def recent_games(days=3):
    """抓最近几天已结束的比赛，取最后一个有比赛的日期。"""
    best = None
    today = dt.date.today()
    for k in range(days):
        d = today - dt.timedelta(days=k)
        try:
            j = fetch(SB.format(d.strftime("%Y%m%d")))
        except Exception:
            # 接口抖动时退回本地缓存（build_history.py 抓过同一批日期）
            cache = os.environ.get("SB_CACHE", "/tmp/sb_cache")
            path = os.path.join(cache, d.strftime("%Y%m%d") + ".json")
            if os.path.exists(path):
                try:
                    j = json.load(open(path, encoding="utf-8"))
                except Exception:
                    continue
            else:
                continue
        games = []
        for ev in j.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            if not (comp.get("status") or {}).get("type", {}).get("completed"):
                continue
            cs = []
            for c in comp.get("competitors") or []:
                raw = str((c.get("team") or {}).get("abbreviation", "")).upper()
                ab = AB2KEY.get(raw, raw)
                try:
                    sc = int(c.get("score"))
                except (TypeError, ValueError):
                    sc = 0
                cs.append({"ab": ab, "score": sc, "win": bool(c.get("winner"))})
            if len(cs) != 2:
                continue
            cs.sort(key=lambda x: (not x["win"], -x["score"]))
            games.append(cs)
        if games and (best is None):
            best = {"day": d.strftime("%Y-%m-%d"), "games": games}
            if k > 0:      # 今天没有比赛完成时，才向前找
                break
    return best

def main():
    last_err = None
    for attempt in range(4):
        for url in ENDPOINTS:
            try:
                rows = normalize(fetch(url))
                if len(rows) >= 28:
                    for r in rows:
                        r["conf"] = "E" if r["ab"] in EAST else "W"
                    out = {"updated": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
                           "source": url.split("/")[2], "rows": rows}
                    recent = recent_games()
                    if recent:
                        out["day"] = recent["day"]
                        out["games"] = recent["games"]
                    with open("data.json", "w", encoding="utf-8") as f:
                        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
                    print("OK", len(rows), "teams @", out["updated"])
                    return 0
                last_err = "only %d rows" % len(rows)
            except Exception as e:
                last_err = "%s: %s" % (url.split("/")[2], e)
        time.sleep(3 * (attempt + 1))
    print("FAILED:", last_err, file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
