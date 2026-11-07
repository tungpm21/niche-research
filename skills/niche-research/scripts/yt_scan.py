#!/usr/bin/env python3
"""Quét YouTube công khai cho việc research ngách, không cần key hay đăng nhập.

Chỉ dùng thư viện chuẩn. Đọc trang công khai của YouTube (ytInitialData) với hl=en, gl=US
để số view có dạng "12K views" và mốc thời gian dạng "3 weeks ago".

Lệnh:
  channel <@handle> [--popular] [-n 30]   kênh: số người đăng ký, video mới nhất hoặc phổ biến nhất
  search "<từ khoá>" [--when week|month|year] [--by views] [-n 20]
  suggest "<từ khoá>"                      gợi ý tìm kiếm của YouTube (từ khoá người ta đang gõ)
  video <id hoặc url>                      tiêu đề, kênh, view, ngày đăng, độ dài, mô tả, tag
  run <niche.json> [--out <thư mục>]       quét theo file cấu hình ngách, ghi data.json + scan.md + thumbs/
  thumbs <data.json> [--out <thư mục>]     ghép thumbnail video vượt nền và video hụt thành bảng ảnh (cần ffmpeg)

Thêm --json để in JSON thay cho bảng. YouTube đổi cấu trúc trang thường xuyên: nếu một lệnh
trả về rỗng, hãy kiểm lại bằng trình duyệt trước khi kết luận là không có dữ liệu.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
HEAD = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Cookie": "SOCS=CAI; CONSENT=YES+1"}
SP = {  # bộ lọc tìm kiếm của YouTube
    ("", ""): "",
    ("week", ""): "EgIIAw%3D%3D", ("month", ""): "EgIIBA%3D%3D", ("year", ""): "EgIIBQ%3D%3D",
    ("", "views"): "CAM%3D",
    ("week", "views"): "CAMSAggD", ("month", "views"): "CAMSAggE", ("year", "views"): "CAMSAggF",
}

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")


def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            h = dict(HEAD)
            body = None
            if data is not None:
                body = json.dumps(data).encode()
                h["Content-Type"] = "application/json"
            with urllib.request.urlopen(urllib.request.Request(url, body, h), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def initial_data(html):
    m = re.search(r"(?:var ytInitialData|window\[\"ytInitialData\"\]) = (\{.*?\});\s*(?:</script>|window\[)", html, re.S)
    if not m:
        raise RuntimeError("Không thấy ytInitialData (YouTube đổi trang, hoặc bị chặn/consent)")
    return json.loads(m.group(1))


def page_data(url, tries=3):
    """Tải trang và lấy ytInitialData; YouTube đôi khi trả một trang rút gọn, nên thử lại."""
    for i in range(tries):
        html = get(url)
        try:
            return html, initial_data(html)
        except RuntimeError:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def client_version(html):
    m = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html)
    return m.group(1) if m else "2.20250101.00.00"


def walk(o, key):
    """Mọi object con có khoá `key`."""
    st = [o]
    while st:
        x = st.pop()
        if isinstance(x, dict):
            if key in x:
                yield x[key]
            st.extend(x.values())
        elif isinstance(x, list):
            st.extend(reversed(x))


def num(s):
    """'12K views' -> 12000, '5,890,474 views' -> 5890474, 'No views' -> 0."""
    if not s:
        return None
    s = s.replace(",", "")
    m = re.search(r"([\d.]+)\s*(thousand|million|billion|[KMB])?", s, re.I)
    if not m:
        return 0
    n = float(m.group(1))
    u = (m.group(2) or "").upper()[:1]
    return int(n * {"K": 1e3, "T": 1e3, "M": 1e6, "B": 1e9}.get(u, 1))


def age_days(s):
    """'3 weeks ago' -> 21. 'Streamed 2 days ago' cũng được. Trả None nếu không đọc được."""
    if not s:
        return None
    m = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year|min|mo|h|d|w|y)s?\b", s)
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    u = {"s": "second", "min": "minute", "h": "hour", "d": "day", "w": "week", "mo": "month", "y": "year"}.get(u, u)
    return n * {"second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7,
                "month": 30.4, "year": 365}[u]


def secs(t):
    if not t or not re.match(r"^\d+(:\d\d)+$", t):
        return None
    v = 0
    for p in t.split(":"):
        v = v * 60 + int(p)
    return v


def text(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        if "simpleText" in x:
            return x["simpleText"]
        if "runs" in x:
            return "".join(r.get("text", "") for r in x["runs"])
        if "content" in x:
            return x["content"]
    return ""


def finish(v):
    v["views"] = num(v.get("views_text"))
    v["age_days"] = age_days(v.get("published"))
    v["length_s"] = secs(v.get("length"))
    a = v["age_days"]
    v["per_day"] = round(v["views"] / max(a, 1)) if (v["views"] is not None and a is not None) else None
    return v


def from_lockup(l):
    md = (l.get("metadata") or {}).get("lockupMetadataViewModel") or {}
    parts = []  # (chữ hiện ra, nhãn đọc màn hình). Trang kênh hiện "17K" với nhãn "17 thousand views"
    for row in ((md.get("metadata") or {}).get("contentMetadataViewModel") or {}).get("metadataRows") or []:
        for p in row.get("metadataParts") or []:
            parts.append((text(p.get("text")), p.get("accessibilityLabel") or ""))
    viewp = next((p for p in parts if "view" in (p[0] + " " + p[1]).lower()), None)
    agep = next((p for p in parts if "ago" in (p[0] + " " + p[1]).lower()), None)
    v = {"id": l.get("contentId"), "title": text(md.get("title")), "channel": None,
         "views_text": (viewp[0] if "view" in viewp[0].lower() else viewp[1]) if viewp else None,
         "published": (agep[1] or agep[0]) if agep else None, "length": None}
    if parts and not viewp is parts[0] and not agep is parts[0]:
        v["channel"] = parts[0][0]
    for b in walk(l.get("contentImage") or {}, "thumbnailBadgeViewModel"):
        if re.match(r"^\d+(:\d\d)+$", b.get("text", "")):
            v["length"] = b["text"]
            break
    return finish(v)


def from_renderer(r):
    v = {"id": r.get("videoId"), "title": text(r.get("title")),
         "channel": text(r.get("ownerText") or r.get("longBylineText")),
         "handle": next(iter(walk(r.get("ownerText") or {}, "canonicalBaseUrl")), None),
         "views_text": text(r.get("viewCountText")), "published": text(r.get("publishedTimeText")),
         "length": text(r.get("lengthText"))}
    return finish(v)


def videos_in(j):
    out = [from_renderer(r) for r in walk(j, "videoRenderer")]
    out += [from_lockup(l) for l in walk(j, "lockupViewModel") if l.get("contentType", "").endswith("VIDEO")]
    seen, res = set(), []
    for v in out:
        if v["id"] and v["id"] not in seen:
            seen.add(v["id"])
            res.append(v)
    return res


def norm_handle(h):
    h = h.strip()
    m = re.search(r"youtube\.com/(@[^/?#]+)", h)
    if m:
        return m.group(1)
    return h if h.startswith("@") else "@" + h


def channel(handle, popular=False, n=30):
    handle = norm_handle(handle)
    url = f"https://www.youtube.com/{urllib.parse.quote(handle)}/videos?hl=en&gl=US"
    html, j = page_data(url)
    dump = json.dumps(j.get("header") or {}, ensure_ascii=False, separators=(",", ":"))
    subs = re.search(r'"(?:content|text)":"([\d.,]+[KMB]? subscribers?)"', dump)
    nvid = re.search(r'"(?:content|text)":"([\d.,]+[KMB]? videos?)"', dump)
    title = text(((j.get("metadata") or {}).get("channelMetadataRenderer") or {}).get("title")) or handle
    vids = videos_in(j)
    if popular:
        tok = None
        for chip in walk(j, "chipViewModel"):
            if chip.get("text", "").lower() == "popular":
                tok = next(iter(walk(chip, "token")), None)
        if tok is None:
            for chip in walk(j, "chipCloudChipRenderer"):
                if text(chip.get("text")).lower() == "popular":
                    tok = next(iter(walk(chip, "token")), None)
        if tok:
            body = {"context": {"client": {"clientName": "WEB", "clientVersion": client_version(html),
                                           "hl": "en", "gl": "US"}}, "continuation": tok}
            r = json.loads(get("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false", body))
            vids = videos_in(r)
        else:
            print(f"[{handle}] không thấy nút Popular, dùng danh sách mới nhất", file=sys.stderr)
    for v in vids:
        v["channel"] = title
        v["handle"] = handle
    if not popular:  # mức nền của kênh: trung vị view các video mới nhất; outlier = view / mức nền
        vs = sorted(v["views"] for v in vids[:n] if v.get("views") is not None)
        med = vs[len(vs) // 2] if vs else None
        for v in vids:
            v["outlier"] = round(v["views"] / med, 1) if med and v.get("views") is not None else None
    return {"handle": handle, "title": title, "subscribers": num(subs.group(1)) if subs else None,
            "subscribers_text": subs.group(1) if subs else None, "videos_text": nvid.group(1) if nvid else None,
            "sort": "popular" if popular else "latest", "videos": vids[:n]}


def search(q, when="", by="", n=20):
    sp = SP[(when or "", by or "")]
    url = "https://www.youtube.com/results?hl=en&gl=US&search_query=" + urllib.parse.quote(q) + (f"&sp={sp}" if sp else "")
    vids = videos_in(page_data(url)[1])
    for v in vids:
        v["query"] = q
    return vids[:n]


def suggest(q):
    url = ("https://suggestqueries-clients6.youtube.com/complete/search?client=youtube&ds=yt&hl=en&gl=us&q="
           + urllib.parse.quote(q))
    t = get(url)
    return [json.loads('"' + m + '"') for m in re.findall(r'\["((?:[^"\\]|\\.)*)",0', t)]


def video(vid):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", vid)
    vid = m.group(1) if m else vid
    html = get(f"https://www.youtube.com/watch?v={vid}&hl=en&gl=US")
    m = re.search(r"var ytInitialPlayerResponse = (\{.*?\});(?:var|</script>)", html, re.S)
    p = json.loads(m.group(1)) if m else {}
    d = p.get("videoDetails") or {}
    mf = (p.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    return {"id": vid, "title": d.get("title"), "channel": d.get("author"), "views": int(d.get("viewCount") or 0),
            "length_s": int(d.get("lengthSeconds") or 0), "published": mf.get("publishDate"),
            "handle": (mf.get("ownerProfileUrl") or "").rsplit("/", 1)[-1], "keywords": d.get("keywords") or [],
            "description": d.get("shortDescription") or ""}


def fmt_n(n):
    if n is None:
        return "?"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.0f}K"
    return str(n)


def table(vids, cols=("views", "per_day", "published", "length", "channel", "title")):
    head = {"views": "View", "per_day": "View/ngày", "published": "Đăng", "length": "Dài",
            "channel": "Kênh", "title": "Tiêu đề", "outlier": "× nền kênh"}
    rows = ["| " + " | ".join(head[c] for c in cols) + " |", "|" + "---|" * len(cols)]
    for v in vids:
        cell = []
        for c in cols:
            x = v.get(c)
            if c in ("views", "per_day"):
                x = fmt_n(x)
            elif c == "outlier" and x is not None:
                x = f"{x}×"
            cell.append(str(x if x is not None else "").replace("|", "/")[:80])
        rows.append("| " + " | ".join(cell) + " |")
    return "\n".join(rows)


FONTS = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]


def short_age(d):
    if d is None:
        return "?"
    if d < 1:
        return f"{max(1, round(d * 24))}h"
    if d < 14:
        return f"{round(d)}d"
    if d < 60:
        return f"{round(d / 7)}w"
    if d < 365:
        return f"{round(d / 30.4)}mo"
    return f"{round(d / 365)}y"


def thumbs(data_path, out_dir=None, min_outlier=2.0, low_outlier=0.5, top_search=12, per_sheet=24):
    """Bảng thumbnail: video vượt nền kênh (và video đang lên trong kết quả tìm) so với video hụt.
    Mỗi ô ghi số thứ tự, view, × nền kênh, tuổi video, kênh và tiêu đề; index.md liệt kê cùng số thứ tự."""
    import os
    import shutil
    import subprocess
    data = json.load(open(data_path, encoding="utf-8"))
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(data_path)), "thumbs")
    os.makedirs(out_dir, exist_ok=True)
    if not shutil.which("ffmpeg"):
        print("Không có ffmpeg: bỏ qua bảng thumbnail", file=sys.stderr)
        return
    f = data.get("filters") or {}
    excl = re.compile(f["exclude_title"], re.I) if f.get("exclude_title") else None
    mn, mx = f.get("min_length_s", 0), f.get("max_length_s", 10 ** 6)

    win, low, seen = [], [], set()

    def add(lst, v, why):
        if v.get("id") and v["id"] not in seen:
            seen.add(v["id"])
            lst.append(dict(v, why=why))

    for c in data.get("channels", []):
        vs = c.get("videos") or []
        if c.get("sort") == "latest":
            for v in sorted(vs, key=lambda v: -(v.get("outlier") or 0)):
                if (v.get("outlier") or 0) >= min_outlier:
                    add(win, v, f"{v['outlier']}× nền kênh")
            for v in sorted(vs, key=lambda v: (v.get("outlier") or 99)):
                if v.get("outlier") is not None and v["outlier"] <= low_outlier and (v.get("age_days") or 0) >= 3:
                    add(low, v, f"{v['outlier']}× nền kênh")
    for c in data.get("channels", []):
        if c.get("sort") == "popular":
            for v in (c.get("videos") or [])[:4]:
                add(win, v, "phổ biến nhất kênh")
    pool = [v for v in data.get("searches", []) if v.get("per_day") and mn <= (v.get("length_s") or 0) <= mx
            and not (excl and excl.search(v.get("title") or ""))]
    for v in sorted(pool, key=lambda v: -v["per_day"])[:top_search]:
        add(win, v, "đang lên trong kết quả tìm")
    font = next((p for p in FONTS if os.path.exists(p)), None)
    if not font:
        print("Không thấy font: bảng thumbnail sẽ không có chữ, xem index.md", file=sys.stderr)

    idx = ["# Bảng thumbnail", "", f"Từ `{os.path.basename(data_path)}` ngày {data.get('date')}. "
           "Số thứ tự khớp với ô trong ảnh.", ""]
    for name, lst, title in (("winners", win, "Vượt nền kênh, phổ biến nhất, hoặc đang lên"),
                             ("low", low, f"Hụt: dưới {low_outlier}× nền kênh")):
        if not lst:
            continue
        idx += [f"## {title} ({name}-*.jpg)", "", "| # | View | × nền | Tuổi | Kênh | Tiêu đề | Vì sao chọn |",
                "|---|---|---|---|---|---|---|"]
        tmp = os.path.join(out_dir, "_tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        if font:
            shutil.copy(font, os.path.join(tmp, "font.ttf"))
        for i, v in enumerate(lst, 1):
            idx.append(f"| {i} | {fmt_n(v.get('views'))} | {v.get('outlier') if v.get('outlier') is not None else ''} | "
                       f"{short_age(v.get('age_days'))} | {(v.get('channel') or '').replace('|', '/')} | "
                       f"[{(v.get('title') or '').replace('|', '/')[:70]}](https://youtu.be/{v['id']}) | {v['why']} |")
            jpg = os.path.join(tmp, f"{i:03d}.jpg")
            try:
                open(jpg, "wb").write(get_bytes(f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg"))
            except Exception:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x333333:s=320x180",
                                "-frames:v", "1", jpg])
            o = f"× {v['outlier']}" if v.get("outlier") is not None else v["why"]
            l1 = f"#{i}  {fmt_n(v.get('views'))}  ·  {o}  ·  {short_age(v.get('age_days'))}  ·  {(v.get('channel') or '')[:22]}"
            l2 = (v.get("title") or "")[:46]
            open(os.path.join(tmp, f"{i:03d}.txt"), "w", encoding="utf-8").write(l1 + "\n" + l2)
            vf = "scale=320:180,pad=320:224:0:0:color=0x15151a"
            if font:
                vf += f",drawtext=fontfile=font.ttf:textfile={i:03d}.txt:fontsize=13:fontcolor=white:x=6:y=186:line_spacing=4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{i:03d}.jpg", "-vf", vf, f"{i:03d}_l.png"],
                           cwd=tmp, capture_output=True)
            time.sleep(0.1)
        n_sheets = (len(lst) + per_sheet - 1) // per_sheet
        for s in range(n_sheets):
            start = s * per_sheet + 1
            rows = (min(per_sheet, len(lst) - s * per_sheet) + 3) // 4
            dst = os.path.join(out_dir, f"{name}-{s + 1}.jpg")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-start_number", str(start),
                            "-i", "%03d_l.png", "-frames:v", "1", "-vf",
                            f"tile=4x{rows}:padding=4:margin=4:color=0x000000", "-q:v", "3", os.path.abspath(dst)],
                           cwd=tmp, capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)
        idx.append("")
    open(os.path.join(out_dir, "index.md"), "w", encoding="utf-8").write("\n".join(idx) + "\n")
    print(f"Bảng thumbnail ở {out_dir}: {len(win)} video vượt nền/đang lên, {len(low)} video hụt")


def get_bytes(url):
    with urllib.request.urlopen(urllib.request.Request(url, None, {"User-Agent": UA}), timeout=30) as r:
        return r.read()


def run(cfg_path, out_dir=None):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    today = dt.date.today().isoformat()
    out_dir = out_dir or "."
    import os
    os.makedirs(out_dir, exist_ok=True)
    data = {"niche": cfg.get("niche"), "date": today, "channels": [], "searches": [], "suggest": {},
            "filters": {k: cfg.get(k) for k in ("exclude_title", "min_length_s", "max_length_s")}}
    excl = re.compile(cfg["exclude_title"], re.I) if cfg.get("exclude_title") else None
    for h in cfg.get("channels", []):
        handle = h["handle"] if isinstance(h, dict) else h
        for pop in (False, True):
            try:
                data["channels"].append(channel(handle, popular=pop, n=cfg.get("per_channel", 30)))
            except Exception as e:
                print(f"[{handle}] lỗi: {e}", file=sys.stderr)
            time.sleep(0.6)
    for s in cfg.get("searches", []):
        q, when, by = (s, "month", "") if isinstance(s, str) else (s["q"], s.get("when", "month"), s.get("by", ""))
        try:
            data["searches"].extend(search(q, when, by, n=cfg.get("per_search", 20)))
        except Exception as e:
            print(f"[search {q}] lỗi: {e}", file=sys.stderr)
        time.sleep(0.6)
    for q in cfg.get("suggest", []):
        try:
            data["suggest"][q] = suggest(q)
        except Exception as e:
            print(f"[suggest {q}] lỗi: {e}", file=sys.stderr)
    json.dump(data, open(os.path.join(out_dir, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    md = [f"# Quét ngách {cfg.get('niche')} ngày {today}", "",
          "Số liệu công khai lúc quét. View/ngày = view chia số ngày từ lúc đăng, mốc ngày của YouTube làm tròn "
          "(\"3 weeks ago\"), nên chỉ dùng để so tương đối.", ""]
    md += ["## Kênh", "", "| Kênh | Người đăng ký | Số video |", "|---|---|---|"]
    seen = set()
    for c in data["channels"]:
        if c["handle"] in seen:
            continue
        seen.add(c["handle"])
        md.append(f"| {c['title']} ({c['handle']}) | {c['subscribers_text'] or '?'} | {c['videos_text'] or '?'} |")
    for c in data["channels"]:
        pop = c["sort"] == "popular"
        md += ["", f"### {c['title']}: {'phổ biến nhất' if pop else 'mới nhất (× nền kênh = view / trung vị view các video mới nhất)'}", "",
               table(c["videos"], ("views", "per_day", "published", "length", "title") if pop
                     else ("views", "outlier", "per_day", "published", "length", "title"))]
    pool = {v["id"]: v for v in data["searches"]}
    vids = [v for v in pool.values() if v.get("views") is not None]
    mn, mx = cfg.get("min_length_s", 0), cfg.get("max_length_s", 10 ** 6)
    longf = [v for v in vids if (v["length_s"] or 0) >= mn and (v["length_s"] or 0) <= mx
             and not (excl and excl.search(v["title"] or ""))]
    shorts = [v for v in vids if v["length_s"] is not None and v["length_s"] < 90
              and not (excl and excl.search(v["title"] or ""))]
    longf.sort(key=lambda v: -(v["per_day"] or 0))
    shorts.sort(key=lambda v: -(v["per_day"] or 0))
    md += ["", f"## Video tìm thấy, xếp theo view/ngày ({len(longf)} video dài {mn}–{mx} giây)", "",
           table(longf[: cfg.get("top", 40)])]
    md += ["", "## Short (dưới 90 giây) đang lên", "", table(shorts[:15])]
    by_ch = {}
    for v in longf:
        k = v.get("channel") or "?"
        b = by_ch.setdefault(k, {"n": 0, "best": v})
        b["n"] += 1
        if (v["views"] or 0) > (b["best"]["views"] or 0):
            b["best"] = v
    md += ["", "## Kênh xuất hiện trong kết quả tìm kiếm", "", "| Kênh | Số video | Video mạnh nhất | View |", "|---|---|---|---|"]
    for k, b in sorted(by_ch.items(), key=lambda kv: -(kv[1]["best"]["views"] or 0))[:30]:
        md.append(f"| {k} | {b['n']} | {(b['best']['title'] or '')[:60].replace('|', '/')} | {fmt_n(b['best']['views'])} |")
    md += ["", "## Gợi ý tìm kiếm", ""]
    for q, s in data["suggest"].items():
        md.append(f"- **{q}**: " + "; ".join(s[1:9]))
    open(os.path.join(out_dir, "scan.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"Ghi {out_dir}/data.json và {out_dir}/scan.md: {len(data['channels'])} lượt kênh, "
          f"{len(pool)} video tìm kiếm, {len(data['suggest'])} gợi ý")
    t = cfg.get("thumbs") or {}
    thumbs(os.path.join(out_dir, "data.json"), os.path.join(out_dir, "thumbs"),
           t.get("min_outlier", 2.0), t.get("low_outlier", 0.5), t.get("top_search", 12))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("channel"); a.add_argument("handle"); a.add_argument("--popular", action="store_true"); a.add_argument("-n", type=int, default=30)
    a = sub.add_parser("search"); a.add_argument("q"); a.add_argument("--when", default="", choices=["", "week", "month", "year"]); a.add_argument("--by", default="", choices=["", "views"]); a.add_argument("-n", type=int, default=20)
    a = sub.add_parser("suggest"); a.add_argument("q")
    a = sub.add_parser("video"); a.add_argument("id")
    a = sub.add_parser("run"); a.add_argument("config"); a.add_argument("--out")
    a = sub.add_parser("thumbs"); a.add_argument("data"); a.add_argument("--out"); a.add_argument("--min-outlier", type=float, default=2.0); a.add_argument("--low-outlier", type=float, default=0.5); a.add_argument("--top-search", type=int, default=12)
    for p in sub.choices.values():
        p.add_argument("--json", action="store_true")
    x = ap.parse_args()
    if x.cmd == "run":
        return run(x.config, x.out)
    if x.cmd == "thumbs":
        return thumbs(x.data, x.out, x.min_outlier, x.low_outlier, x.top_search)
    if x.cmd == "channel":
        r = channel(x.handle, x.popular, x.n)
        if x.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(f"{r['title']} ({r['handle']}): {r['subscribers_text']}, {r['videos_text']}, {r['sort']}\n")
            print(table(r["videos"], ("views", "per_day", "published", "length", "title") if x.popular
                        else ("views", "outlier", "per_day", "published", "length", "title")))
    elif x.cmd == "search":
        r = search(x.q, x.when, x.by, x.n)
        print(json.dumps(r, ensure_ascii=False, indent=1) if x.json else table(r))
    elif x.cmd == "suggest":
        r = suggest(x.q)
        print(json.dumps(r, ensure_ascii=False) if x.json else "\n".join(r))
    elif x.cmd == "video":
        r = video(x.id)
        if x.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            for k, v in r.items():
                print(f"{k}: {v if k != 'description' else v[:600]}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print(f"YouTube trả HTTP {e.code} cho {e.url}" + (": sai handle hoặc trang không tồn tại" if e.code == 404 else ""),
              file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, RuntimeError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)
