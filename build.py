#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이랑 갈 만한 곳 — 큐레이션 가이드 페이지 생성기

두 소스를 읽어 카테고리 → 권역(도)으로 그룹핑한 필터형 정적 페이지를 만든다.
  · places.json       = 손으로 고른 큐레이션 (정본, 우선)
  · places_auto.json  = TourAPI 자동수집 (후보, 사진 썸네일·'자동수집' 배지 표시)
이름이 겹치면 큐레이션이 이긴다(자동수집 중복 제거).

UI:
  · 모바일 최적화(1열·가로스크롤 내비·큰 터치 타깃)
  · 필터는 기본 접힘 → '필터' 버튼으로 열고 닫기
  · 검색 · 권역 · 카테고리 · 출처 · 실내외 · 비용 · 계절 필터
  · 권역=전체일 때 권역을 라벨로 명확히 구분
  · 권역별 8곳까지 먼저, 나머지는 '더보기'
  · 자동수집분은 실내외·무료가 미확인('?') → 해당 필터 켜면 제외

실행:  python3 build.py   →  open index.html
"""

import json
import os
import html
import re
import unicodedata
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "places.json")
AUTO = os.path.join(BASE, "places_auto.json")
OUT = os.path.join(BASE, "index.html")

CATEGORIES = ["숙소", "놀이터", "공원", "물놀이터", "테마파크·놀이공원",
              "박물관·과학·전시", "동물·자연", "체험·교육", "캠핑", "액티비티"]
CAT_ICON = {"숙소": "🛏️", "놀이터": "🎠", "공원": "🌳", "물놀이터": "💦",
            "테마파크·놀이공원": "🎢", "박물관·과학·전시": "🔬", "동물·자연": "🦒",
            "체험·교육": "🎨", "캠핑": "⛺", "액티비티": "🎟️"}
CAT_SUB = {"숙소": "키즈 프렌들리", "놀이터": "순수 놀이터", "물놀이터": "여름 위주",
           "박물관·과학·전시": "실내·날씨무관", "캠핑": "키즈"}
REGIONS = ["수도권", "강원", "충청", "전라", "경상", "제주"]
REGION_ICON = {"수도권": "🏙️", "강원": "⛰️", "충청": "🌾",
               "전라": "🌽", "경상": "🌊", "제주": "🌴"}


def norm(s):
    return re.sub(r"[\s()·]", "", unicodedata.normalize("NFC", s or "")).lower()


def map_query(name, area):
    # 괄호 별칭 제거 + 지역 결합 → 별칭이어도 위치가 잡히게
    name_clean = re.sub(r"\s*\([^)]*\)", "", name).strip()
    return (name_clean + " " + (area or "")).strip()


def naver_map_link(query):
    return "https://map.naver.com/p/search/" + urllib.parse.quote(query)


def tag(text, cls="tag"):
    return f'<span class="{cls}">{html.escape(text)}</span>'


def card_html(p):
    kind = p.get("_kind", "curated")
    is_auto = kind == "auto"
    raw_name = p.get("name", "?")
    raw_area = p.get("area", "")
    name = html.escape(raw_name)
    area = html.escape(raw_area)
    # 검색용: 공백 제거 + 소문자 (띄어쓰기 편차 무시)
    search = html.escape(re.sub(r"\s+", "", raw_name + raw_area).lower(), quote=True)

    desc_raw = p.get("desc", "") or ""
    if is_auto and desc_raw.startswith("(TourAPI"):
        desc_raw = ""
    desc = html.escape(desc_raw)

    seasons = p.get("season", []) or []
    season_attr = ",".join(seasons)

    if is_auto:
        indoor, free = "?", "?"
    else:
        indoor = "y" if p.get("indoor") else "n"
        free = "y" if p.get("free") else "n"

    tags = []
    if is_auto:
        tags.append(tag("🤖 자동수집", "tag auto"))
    else:
        tags.append(tag("★ 큐레이션", "tag cur"))
        tags.append(tag("🏠 실내" if indoor == "y" else "🌳 실외", "tag place"))
        tags.append(tag("무료" if free == "y" else "유료", "tag cost"))
        for s in seasons:
            tags.append(tag("사계절" if s == "올시즌" else s, "tag season"))
        if p.get("age"):
            tags.append(tag("👶 " + p["age"], "tag age"))
        for a in p.get("amenities", []):
            tags.append(tag(a, "tag amen"))

    img = p.get("_img", "") if is_auto else ""
    thumb = (
        f'<img class="thumb" loading="lazy" src="{html.escape(img)}" alt="">'
        if img else ""
    )
    desc_html = f'<div class="cdesc">{desc}</div>' if desc else ""

    # 링크: 지도 + (출처가 URL이면) 정보 글
    map_url = naver_map_link(map_query(raw_name, raw_area))
    links = f'<a class="clink" href="{map_url}" target="_blank" rel="noopener">🗺️ 지도</a>'
    src = (p.get("source") or "").strip()
    if src.startswith("http"):
        links += (
            f'<a class="clink src" href="{html.escape(src, quote=True)}" '
            f'target="_blank" rel="noopener">📄 정보 글</a>'
        )
    links_html = f'<div class="clinks">{links}</div>'

    return (
        f'<div class="card{" auto" if is_auto else ""}" '
        f'data-region="{html.escape(p.get("region",""))}" '
        f'data-cat="{html.escape(p.get("category",""))}" '
        f'data-indoor="{indoor}" data-free="{free}" '
        f'data-season="{html.escape(season_attr)}" data-source="{kind}" '
        f'data-search="{search}">'
        f"{thumb}"
        f'<div class="card-h"><span class="cname">{name}</span>'
        f'<span class="carea">{area}</span></div>'
        f"{desc_html}"
        f'<div class="ctags">{"".join(tags)}</div>'
        f"{links_html}"
        f"</div>"
    )


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("places", [])


def chip_row(label, group, values):
    """values = [(data-v, 표시텍스트, active?)]"""
    chips = "".join(
        f'<span class="chip{" active" if act else ""}" data-g="{group}" data-v="{html.escape(v)}">{html.escape(t)}</span>'
        for v, t, act in values
    )
    return f'<div class="frow"><span class="flabel">{html.escape(label)}</span>{chips}</div>'


def build():
    curated = load(DATA)
    auto = load(AUTO)
    for p in curated:
        p["_kind"] = "curated"
    have = {norm(p.get("name", "")) for p in curated}
    auto_dedup = []
    for p in auto:
        if norm(p.get("name", "")) in have:
            continue
        have.add(norm(p.get("name", "")))
        p["_kind"] = "auto"
        auto_dedup.append(p)
    places = curated + auto_dedup

    # 점프 내비
    nav = ['<a class="navchip" href="#top">⤴ 맨위</a>']
    sections = []
    for cat in CATEGORIES:
        in_cat = [p for p in places if p.get("category") == cat]
        if not in_cat:
            continue
        cat_id = "cat-" + str(CATEGORIES.index(cat))
        nav.append(
            f'<a class="navchip" href="#{cat_id}">{CAT_ICON.get(cat,"")} {html.escape(cat)} '
            f'<b>{len(in_cat)}</b></a>'
        )
        groups = []
        for region in REGIONS:
            in_region = [p for p in in_cat if p.get("region") == region]
            if not in_region:
                continue
            cards = "\n".join(card_html(p) for p in in_region)
            groups.append(
                f'<div class="region-group" data-region="{region}">'
                f'<h3><span class="rlabel">{REGION_ICON.get(region,"")} {region}</span>'
                f' <span class="rcount"></span></h3>'
                f'<div class="cards">{cards}</div>'
                f'<button class="more" type="button">더보기</button>'
                f"</div>"
            )
        sub = CAT_SUB.get(cat, "")
        sub_html = f' <span class="muted">({html.escape(sub)})</span>' if sub else ""
        sections.append(
            f'<section class="cat" id="{cat_id}" data-cat="{html.escape(cat)}">'
            f'<h2>{CAT_ICON.get(cat,"")} {html.escape(cat)}{sub_html}'
            f' <span class="ccount"></span></h2>'
            f'{"".join(groups)}</section>'
        )

    # 카테고리 필터칩 (전체 + 10종)
    cat_vals = [("all", "전체", True)] + [
        (c, f'{CAT_ICON.get(c,"")} {c}', False)
        for c in CATEGORIES if any(p.get("category") == c for p in places)
    ]
    region_vals = [("all", "전체", True)] + [(r, r, False) for r in REGIONS]

    filters_html = "\n".join([
        chip_row("권역", "region", region_vals),
        chip_row("분류", "cat", cat_vals),
        chip_row("출처", "source", [("all", "전체", False), ("curated", "★ 큐레이션", True), ("auto", "🤖 자동수집", False)]),
        chip_row("실내외", "place", [("all", "전체", True), ("y", "🏠 실내", False), ("n", "🌳 실외", False)]),
        chip_row("비용", "cost", [("all", "전체", True), ("y", "무료", False), ("n", "유료", False)]),
        chip_row("계절", "season", [("all", "전체", True), ("봄", "봄", False), ("여름", "여름", False), ("가을", "가을", False), ("겨울", "겨울", False)]),
    ])

    page = (
        PAGE.replace("__NAV__", "\n".join(nav))
        .replace("__FILTERS__", filters_html)
        .replace("__SECTIONS__", "\n".join(sections))
        .replace("__TOTAL__", str(len(places)))
        .replace("__CUR__", str(len(curated)))
        .replace("__AUTO__", str(len(auto_dedup)))
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"✅ 큐레이션 {len(curated)} + 자동수집 {len(auto_dedup)} = 총 {len(places)}곳 → {OUT}")
    print("열기:  open index.html")


PAGE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>아이랑 갈 만한 곳</title>
<style>
  :root { color-scheme: light dark; }
  * { -webkit-tap-highlight-color: transparent; }
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 960px;
         margin: 0 auto; padding: 20px 16px 60px; color: #1d1d1f; background: #fbfbfd; }
  h1 { font-size: 23px; margin: 0 0 2px; }
  .meta { color: #6e6e73; font-size: 13px; margin-bottom: 12px; }
  .muted { color: #86868b; font-weight: 400; font-size: 15px; }

  /* 상단 고정바: 검색 + 필터버튼 */
  .topbar { position: sticky; top: 0; z-index: 20; background: rgba(251,251,253,.97);
            backdrop-filter: blur(10px); padding: 10px 0 8px;
            display: flex; gap: 8px; align-items: center; }
  .search { flex: 1; min-width: 0; box-sizing: border-box; font-size: 16px; padding: 10px 14px;
            border: 1px solid #ddd; border-radius: 12px; background: #fff; }
  .filter-toggle { flex: none; font-size: 14px; font-weight: 600; padding: 10px 14px;
                   border: 1px solid #ddd; border-radius: 12px; background: #fff; cursor: pointer;
                   display: flex; align-items: center; gap: 6px; }
  .fbadge { font-size: 11px; min-width: 17px; height: 17px; padding: 0 4px; box-sizing: border-box;
            border-radius: 999px; background: #1d1d1f; color: #fff; display: none;
            align-items: center; justify-content: center; }
  .fbadge.on { display: inline-flex; }

  /* 필터 패널 (기본 접힘) */
  .panel { display: none; position: sticky; top: 58px; z-index: 15;
           background: #fff; border: 1px solid #eee; border-radius: 14px;
           padding: 12px 14px; margin: 6px 0 4px; box-shadow: 0 6px 20px rgba(0,0,0,.08); }
  .panel.open { display: block; }
  .frow { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 7px 0; }
  .flabel { font-size: 12px; color: #86868b; width: 46px; flex: none; }
  .chip { font-size: 13px; padding: 6px 12px; border-radius: 999px; border: 1px solid #ddd;
          background: #fff; cursor: pointer; user-select: none; }
  .chip.active { background: #1d1d1f; color: #fff; border-color: #1d1d1f; }
  .panel-actions { display: flex; gap: 8px; margin-top: 12px; }
  .pbtn { flex: 1; font-size: 14px; font-weight: 600; padding: 10px; border-radius: 10px;
          border: 1px solid #ddd; background: #fff; cursor: pointer; }
  .pbtn.primary { background: #1d1d1f; color: #fff; border-color: #1d1d1f; }

  .resultbar { font-size: 13px; color: #6e6e73; margin: 8px 0 2px; }
  .resultbar b { color: #1d1d1f; }
  .nav { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 2px; }
  .navchip { font-size: 12px; padding: 4px 10px; border-radius: 999px; background: #eef0f2;
             color: #515154; text-decoration: none; white-space: nowrap; }
  .navchip b { color: #1d1d1f; }

  section.cat { margin: 26px 0; scroll-margin-top: 76px; }
  h2 { font-size: 19px; margin: 0 0 4px; }
  .ccount, .rcount { font-size: 12px; color: #aeaeb2; font-weight: 500; }
  /* 권역 라벨 — 전체 보기에서 구분 명확히 */
  h3 { margin: 16px 0 10px; }
  .rlabel { display: inline-block; font-size: 14px; font-weight: 700; color: #1d1d1f;
            background: #e8ecf2; padding: 4px 12px; border-radius: 8px;
            border-left: 4px solid #b9c2d0; }

  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(248px, 1fr)); gap: 12px; }
  .card { background: #fff; border-radius: 14px; padding: 14px 15px;
          box-shadow: 0 1px 3px rgba(0,0,0,.06); display: flex; flex-direction: column; }
  .card.auto { background: #fcfcfd; }
  .thumb { width: 100%; height: 130px; object-fit: cover; border-radius: 10px;
           margin-bottom: 10px; background: #f0f0f2; }
  .card-h { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
  .cname { font-weight: 700; font-size: 15px; }
  .carea { font-size: 12px; color: #86868b; flex: none; }
  .cdesc { font-size: 13px; color: #3a3a3c; margin: 7px 0 10px; line-height: 1.5; flex: 1; }
  .ctags { display: flex; flex-wrap: wrap; gap: 5px; margin: 7px 0 10px; }
  .tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #f0f0f2; color: #515154; }
  .tag.place { background: #e6f0ff; color: #0040a0; }
  .tag.cost { background: #e3f6e9; color: #1a7f37; }
  .tag.season { background: #fff1e0; color: #9a5b00; }
  .tag.cur { background: #efe6ff; color: #6b1ac4; }
  .tag.auto { background: #eef0f2; color: #8a8a8e; }
  .clinks { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; }
  .clink { font-size: 13px; color: #0066cc; text-decoration: none; padding: 5px 10px;
           border: 1px solid #d6e4f5; border-radius: 8px; background: #f4f8fd; }
  .clink.src { color: #6b6b70; border-color: #e3e3e6; background: #f5f5f7; }
  .more { display: none; margin: 12px auto 0; font-size: 13px; padding: 8px 18px;
          border: 1px solid #ddd; border-radius: 999px; background: #fff; cursor: pointer; }
  .empty { color: #86868b; font-size: 14px; padding: 24px 0; display: none; }
  .note { color: #86868b; font-size: 12px; margin-top: 24px; line-height: 1.6; }

  /* 모바일 최적화 */
  @media (max-width: 600px) {
    body { padding: 14px 12px 50px; }
    h1 { font-size: 20px; }
    .cards { grid-template-columns: 1fr; }
    .chip { padding: 8px 14px; }
    .nav { flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch;
           padding-bottom: 4px; }
    .panel { max-height: 64vh; overflow-y: auto; top: 56px; }
    .flabel { width: 100%; margin-bottom: 1px; }
  }
</style></head><body>
<a id="top"></a>
<h1>👨‍👩‍👧 아이랑 갈 만한 곳</h1>
<div class="meta">전국 권역별 가이드 · 총 <b>__TOTAL__</b>곳
  (★ 큐레이션 <b>__CUR__</b> · 🤖 자동수집 <b>__AUTO__</b>)</div>

<div class="topbar">
  <input id="q" class="search" type="search" placeholder="🔍 이름·지역 검색">
  <button id="filterBtn" class="filter-toggle" type="button">⚙️ 필터 <span id="fbadge" class="fbadge"></span></button>
</div>

<div id="panel" class="panel">
  __FILTERS__
  <div class="panel-actions">
    <button id="resetBtn" class="pbtn" type="button">초기화</button>
    <button id="closeBtn" class="pbtn primary" type="button">닫기</button>
  </div>
</div>

<div class="resultbar">표시 <b id="vcount">0</b>곳 / 전체 __TOTAL__곳</div>
<div class="nav">__NAV__</div>

__SECTIONS__

<div class="empty">조건에 맞는 곳이 없어요. 검색어나 필터를 줄여보세요.</div>
<p class="note">※ ★ 큐레이션은 직접 검증한 곳, 🤖 자동수집은 공공데이터(TourAPI) 후보입니다(기본은 큐레이션만 표시).
자동수집분은 실내외·요금이 확인되지 않아 해당 필터를 켜면 제외됩니다.
운영시간·요금·물놀이장 개장은 방문 전 확인하세요.</p>

<script>
  var CAP = 8;
  var DEF = { region: [], cat: "all", source: "curated", place: "all", cost: "all", season: "all", q: "" };
  var F = JSON.parse(JSON.stringify(DEF));
  var expanded = {};

  function pass(card) {
    if (F.region.length && F.region.indexOf(card.dataset.region) < 0) return false;
    if (F.cat !== "all" && card.dataset.cat !== F.cat) return false;
    if (F.source !== "all" && card.dataset.source !== F.source) return false;
    if (F.place  !== "all" && card.dataset.indoor !== F.place) return false;
    if (F.cost   !== "all" && card.dataset.free !== F.cost) return false;
    if (F.season !== "all") {
      var s = card.dataset.season;
      if (s) {
        var arr = s.split(",");
        if (arr.indexOf(F.season) < 0 && arr.indexOf("올시즌") < 0) return false;
      }
    }
    if (F.qtoks && F.qtoks.length) {
      var hay = card.dataset.search;
      for (var qi = 0; qi < F.qtoks.length; qi++) {
        if (hay.indexOf(F.qtoks[qi]) < 0) return false;
      }
    }
    return true;
  }

  function activeCount() {
    var n = 0;
    if (F.region.length) n++;
    if (F.cat !== "all") n++;
    if (F.source !== "all") n++;
    if (F.place !== "all") n++;
    if (F.cost !== "all") n++;
    if (F.season !== "all") n++;
    return n;
  }

  function apply() {
    var total = 0;
    document.querySelectorAll(".region-group").forEach(function (g, gi) {
      var shown = 0, vis = 0;
      g.querySelectorAll(".card").forEach(function (c) {
        if (pass(c)) {
          vis++;
          if (expanded[gi] || shown < CAP) { c.style.display = "flex"; shown++; }
          else c.style.display = "none";
        } else c.style.display = "none";
      });
      total += vis;
      var btn = g.querySelector(".more");
      if (!expanded[gi] && vis > CAP) {
        btn.style.display = "block";
        btn.textContent = "더보기 (+" + (vis - CAP) + ")";
      } else btn.style.display = "none";
      g.querySelector(".rcount").textContent = vis ? vis : "";
      g.style.display = vis ? "block" : "none";
    });
    document.querySelectorAll("section.cat").forEach(function (s) {
      var cv = 0;
      s.querySelectorAll(".region-group").forEach(function (g) {
        if (g.style.display !== "none") cv += parseInt(g.querySelector(".rcount").textContent || "0", 10);
      });
      s.style.display = cv ? "block" : "none";
      s.querySelector(".ccount").textContent = cv ? cv : "";
    });
    document.getElementById("vcount").textContent = total;
    document.querySelector(".empty").style.display = total ? "none" : "block";
    var b = document.getElementById("fbadge"), n = activeCount();
    b.textContent = n; b.classList.toggle("on", n > 0);
  }

  function syncChips() {
    document.querySelectorAll(".chip").forEach(function (c) {
      var g = c.dataset.g, v = c.dataset.v;
      if (g === "region") {
        if (v === "all") c.classList.toggle("active", F.region.length === 0);
        else c.classList.toggle("active", F.region.indexOf(v) >= 0);
      } else {
        c.classList.toggle("active", F[g] === v);
      }
    });
  }

  document.querySelectorAll(".more").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var g = btn.closest(".region-group");
      var gi = Array.prototype.indexOf.call(document.querySelectorAll(".region-group"), g);
      expanded[gi] = true;
      apply();
    });
  });

  document.getElementById("q").addEventListener("input", function () {
    F.q = this.value.trim().toLowerCase();
    F.qtoks = F.q.split(/\\s+/).filter(Boolean);  // 공백 단위 토큰 (AND 매칭)
    expanded = {};
    apply();
  });

  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      var g = chip.dataset.g, v = chip.dataset.v;
      expanded = {};
      if (g === "region") {
        if (v === "all") F.region = [];
        else {
          var i = F.region.indexOf(v);
          if (i >= 0) F.region.splice(i, 1); else F.region.push(v);
        }
      } else {
        F[g] = v;
      }
      syncChips();
      apply();
    });
  });

  var panel = document.getElementById("panel");
  document.getElementById("filterBtn").addEventListener("click", function () { panel.classList.toggle("open"); });
  document.getElementById("closeBtn").addEventListener("click", function () { panel.classList.remove("open"); });
  document.getElementById("resetBtn").addEventListener("click", function () {
    F = JSON.parse(JSON.stringify(DEF));
    document.getElementById("q").value = "";
    expanded = {};
    syncChips();
    apply();
  });

  apply();
</script>
</body></html>"""


if __name__ == "__main__":
    build()
