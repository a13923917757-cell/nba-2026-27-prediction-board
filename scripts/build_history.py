#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按比赛日重建 2026-27 赛季逐日战绩，计算张颖 / 陈锵每天的累计失分，生成 history.json。

做法：
  1. 逐个日期抓 ESPN 当日比分（site.api scoreboard），只取已结束的比赛；
  2. 按日期累加每队胜负，得到「当天比赛结束后」的战绩；
  3. 每个分区按 胜率 → 胜场 → 官方种子序（稳定 tiebreak）排出 1-15 名；
  4. 与两人固定预测名次相减取绝对值，累加成分区/总计失分。

用法：python3 scripts/build_history.py [--out history.json]
"""
import json
import os
import sys
import time
import urllib.request
import datetime as dt

SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

# ESPN 简称 → 站内简称
MAP = {"SA": "SAS", "NY": "NYK", "WSH": "WAS", "GS": "GSW", "NO": "NOP", "UTAH": "UTA", "PHO": "PHX",
       "BKN": "BKN", "CHA": "CHA", "CHO": "CHA", "NOP": "NOP"}

EAST = {"BOS", "BKN", "NYK", "PHI", "TOR", "CHI", "CLE", "DET", "IND", "MIL",
        "ATL", "CHA", "MIA", "ORL", "WAS"}
WEST = {"DEN", "MIN", "OKC", "POR", "UTA", "GSW", "LAC", "LAL", "PHX", "SAC",
        "DAL", "HOU", "MEM", "NOP", "SAS"}

PRED = {
    "zy": {"W": ["OKC", "SAS", "HOU", "LAL", "MIN", "DEN", "POR", "MEM", "DAL", "PHX", "UTA", "LAC", "GSW", "NOP", "SAC"],
           "E": ["DET", "PHI", "NYK", "CLE", "BOS", "TOR", "MIA", "ORL", "IND", "ATL", "CHA", "WAS", "CHI", "MIL", "BKN"]},
    "cq": {"W": ["OKC", "HOU", "SAS", "MIN", "LAL", "POR", "DAL", "DEN", "GSW", "PHX", "LAC", "MEM", "NOP", "UTA", "SAC"],
           "E": ["NYK", "BOS", "PHI", "DET", "CLE", "TOR", "IND", "WAS", "MIA", "ORL", "CHA", "CHI", "ATL", "MIL", "BKN"]},
}


def norm(ab):
    ab = (ab or "").upper()
    return MAP.get(ab, ab)


CACHE = os.environ.get("SB_CACHE", "/tmp/sb_cache")


def fetch_day(d):
    cache_path = os.path.join(CACHE, d + ".json")
    body = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                body = json.load(f)
        except Exception:
            body = None
    for _ in range(4):
        if body:
            break
        try:
            req = urllib.request.Request(SB.format(d), headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.load(r)
            os.makedirs(CACHE, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(body, f)
            break
        except Exception:
            time.sleep(1.5)
    if not body:
        return []
    games = []
    for ev in body.get("events", []):
        # 只统计常规赛（season.type=2），排除季前赛与季后赛
        if (ev.get("season") or {}).get("type") != 2:
            continue
        comp = (ev.get("competitions") or [{}])[0]
        if not comp.get("status", {}).get("type", {}).get("completed"):
            continue
        cs = comp.get("competitors") or []
        if len(cs) != 2:
            continue
        rows = []
        for c in cs:
            ab = norm(c.get("team", {}).get("abbreviation"))
            try:
                sc = int(c.get("score"))
            except (TypeError, ValueError):
                sc = 0
            rows.append((ab, sc))
        if rows[0][0] not in EAST | WEST or rows[1][0] not in EAST | WEST:
            continue
        w = rows[0][0] if rows[0][1] > rows[1][1] else rows[1][0]
        l = rows[1][0] if rows[0][1] > rows[1][1] else rows[0][0]
        games.append((w, l))
    return games


def main():
    out = "history.json"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]

    # 官方当前种子序作为同战绩 tiebreak
    seed_order = {}
    try:
        with open("data.json", encoding="utf-8") as f:
            dj = json.load(f)
        for t in (dj.get("teams") or dj.get("rows") or []):
            seed_order[t["ab"]] = t["seed"]
    except Exception:
        pass

    start = dt.date(2026, 10, 1)
    end = dt.date.today()
    rec = {ab: [0, 0] for ab in EAST | WEST}  # [W, L]
    hist = []
    season_start = None

    d = start
    while d <= end:
        games = fetch_day(d.strftime("%Y%m%d"))
        if games:
            if season_start is None:
                season_start = d
            for w, l in games:
                if w in rec:
                    rec[w][0] += 1
                if l in rec:
                    rec[l][1] += 1

            def rank(conf_set, player):
                order = PRED[player]["W" if conf_set == WEST else "E"]
                teams = sorted(conf_set, key=lambda ab: (
                    -(rec[ab][0] / max(1, rec[ab][0] + rec[ab][1])),
                    -rec[ab][0],
                    seed_order.get(ab, 99),
                    ab))
                return order, teams

            zy_total = cq_total = 0
            zy_w = cq_w = zy_e = cq_e = 0
            for conf_set in (WEST, EAST):
                for player in ("zy", "cq"):
                    pred, teams = rank(conf_set, player)
                    loss = sum(abs(pred.index(ab) + 1 - (teams.index(ab) + 1))
                               for ab in pred if ab in teams) if all(ab in teams for ab in pred) else None
                    if loss is None:
                        continue
                    if player == "zy":
                        zy_total += loss
                        zy_w += loss if conf_set == WEST else 0
                        zy_e += loss if conf_set == EAST else 0
                    else:
                        cq_total += loss
                        cq_w += loss if conf_set == WEST else 0
                        cq_e += loss if conf_set == EAST else 0

            # 当日比赛数
            hist.append({"d": d.strftime("%Y-%m-%d"), "g": len(games),
                         "zy": zy_total, "cq": cq_total,
                         "zyW": zy_w, "zyE": zy_e, "cqW": cq_w, "cqE": cq_e})
            print(f"{d}  games={len(games):2d}  zy={zy_total:3d}  cq={cq_total:3d}", flush=True)
        d += dt.timedelta(days=1)

    payload = {
        "updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "season_start": season_start.isoformat() if season_start else None,
        "note": "按每日已结束比赛累计战绩推算，同战绩按官方种子序排序；仅用于走势参考",
        "points": hist,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("写入", out, "共", len(hist), "个比赛日")


if __name__ == "__main__":
    main()
