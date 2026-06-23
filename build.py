#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이랑 갈 만한 곳 — 큐레이션 가이드 페이지 생성기

두 소스를 읽어 카테고리 → 권역(도)으로 그룹핑한 필터형 정적 페이지를 만든다.
  · places.json       = 손으로 고른 큐레이션 (정본, 우선)
  · places_auto.json  = TourAPI 자동수집 (후보, 사진 썸네일·'자동수집' 배지 표시)
이름이 겹치면 큐레이션이 이긴다(자동수집 중복 제거).

필터: 검색 · 권역 · 출처 · 실내/실외 · 무료/유료 · 계절
  · 기본 화면은 큐레이션만 (자동수집은 출처 필터로 펼침)
  · 권역별 8곳까지만 먼저 보이고 나머지는 '더보기'로 접힘
  · 자동수집분은 실내외·무료가 미확인('?') → 해당 필터를 켜면 제외

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


def norm(s):
    return re.sub(r"[\s()·]", "", unicodedata.normalize("NFC", s or "")).lower()


def naver_map_link(name):
    return "https://map.naver.com/p/search/" + urllib.parse.quote(name)


def tag(text, cls="tag"):
    return f'<span class="{cls}">{html.escape(text)}</span>'


def card_html(p):
    kind = p.get("_kind", "curated")
    is_auto = kind == "auto"
    raw_name = p.get("name", "?")
    raw_area = p.get("area", "")
    name = html.escape(raw_name)
    area = html.escape(raw_area)
    search = html.escape((raw_name + " " + raw_area).lower(), quote=True)

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

    return (
        f'<div class="card{" auto" if is_auto else ""}" '
        f'data-region="{html.escape(p.get("region",""))}" '
        f'data-indoor="{indoor}" data-free="{free}" '
        f'data-season="{html.escape(season_attr)}" data-source="{kind}" '
        f'data-search="{search}">'
        f"{thumb}"
        f'<div class="card-h"><span class="cname">{name}</span>'
        f'<span class="carea">{area}</span></div>'
        f"{desc_html}"
        f'<div class="ctags">{"".join(tags)}</div>'
        f'<a class="clink" href="{naver_map_link(raw_name)}" target="_blank">지도에서 보기 ↗</a>'
        f"</div>"
    )


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("places", [])


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
    places = curated + auto_dedup  # 큐레이션 우선(앞), 자동수집 뒤

    # 카테고리 점프 내비
    nav = ['<a class="navchip" href="#top">맨위</a>']

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
                f'<h3>{region} <span class="rcount"></span></h3>'
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

    page = (
        PAGE.replace("__NAV__", "\n".join(nav))
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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>아이랑 갈 만한 곳</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 960px;
         margin: 0 auto; padding: 24px 16px 60px; color: #1d1d1f; background: #fbfbfd; }
  h1 { font-size: 24px; margin: 0 0 2px; }
  .meta { color: #6e6e73; font-size: 13px; margin-bottom: 14px; }
  .muted { color: #86868b; font-weight: 400; font-size: 15px; }
  .filters { position: sticky; top: 0; background: rgba(251,251,253,.96);
             backdrop-filter: blur(8px); padding: 10px 0; border-bottom: 1px solid #eee;
             margin-bottom: 8px; z-index: 5; }
  .search { width: 100%; box-sizing: border-box; font-size: 15px; padding: 9px 13px;
            border: 1px solid #ddd; border-radius: 10px; background: #fff; margin-bottom: 8px; }
  .frow { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 4px 0; }
  .flabel { font-size: 12px; color: #86868b; width: 46px; flex: none; }
  .chip { font-size: 13px; padding: 4px 11px; border-radius: 999px; border: 1px solid #ddd;
          background: #fff; cursor: pointer; user-select: none; }
  .chip.active { background: #1d1d1f; color: #fff; border-color: #1d1d1f; }
  .resultbar { font-size: 13px; color: #6e6e73; margin: 6px 0 2px; }
  .resultbar b { color: #1d1d1f; }
  .nav { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 2px; }
  .navchip { font-size: 12px; padding: 3px 9px; border-radius: 999px; background: #eef0f2;
             color: #515154; text-decoration: none; }
  .navchip b { color: #1d1d1f; }
  section.cat { margin: 24px 0; scroll-margin-top: 130px; }
  h2 { font-size: 19px; margin: 0 0 6px; }
  h3 { font-size: 14px; color: #6e6e73; margin: 14px 0 8px; font-weight: 600; }
  .ccount, .rcount { font-size: 12px; color: #aeaeb2; font-weight: 500; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
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
  .clink { font-size: 13px; color: #0066cc; text-decoration: none; }
  .more { display: none; margin: 10px auto 0; font-size: 13px; padding: 6px 16px;
          border: 1px solid #ddd; border-radius: 999px; background: #fff; cursor: pointer; }
  .empty { color: #86868b; font-size: 14px; padding: 24px 0; display: none; }
  .note { color: #86868b; font-size: 12px; margin-top: 24px; line-height: 1.6; }
</style></head><body>
<a id="top"></a>
<h1>👨‍👩‍👧 아이랑 갈 만한 곳</h1>
<div class="meta">전국 권역별 가이드 · 총 <b>__TOTAL__</b>곳
  (★ 큐레이션 <b>__CUR__</b> · 🤖 자동수집 <b>__AUTO__</b>)</div>

<div class="filters">
  <input id="q" class="search" type="search" placeholder="🔍 이름·지역 검색 (예: 에버랜드, 제주)">
  <div class="frow"><span class="flabel">권역</span>
    <span class="chip active" data-g="region" data-v="all">전체</span>
    <span class="chip" data-g="region" data-v="수도권">수도권</span>
    <span class="chip" data-g="region" data-v="강원">강원</span>
    <span class="chip" data-g="region" data-v="충청">충청</span>
    <span class="chip" data-g="region" data-v="전라">전라</span>
    <span class="chip" data-g="region" data-v="경상">경상</span>
    <span class="chip" data-g="region" data-v="제주">제주</span>
  </div>
  <div class="frow"><span class="flabel">출처</span>
    <span class="chip" data-g="source" data-v="all">전체</span>
    <span class="chip active" data-g="source" data-v="curated">★ 큐레이션</span>
    <span class="chip" data-g="source" data-v="auto">🤖 자동수집</span>
  </div>
  <div class="frow"><span class="flabel">실내외</span>
    <span class="chip active" data-g="place" data-v="all">전체</span>
    <span class="chip" data-g="place" data-v="y">🏠 실내</span>
    <span class="chip" data-g="place" data-v="n">🌳 실외</span>
  </div>
  <div class="frow"><span class="flabel">비용</span>
    <span class="chip active" data-g="cost" data-v="all">전체</span>
    <span class="chip" data-g="cost" data-v="y">무료</span>
    <span class="chip" data-g="cost" data-v="n">유료</span>
  </div>
  <div class="frow"><span class="flabel">계절</span>
    <span class="chip active" data-g="season" data-v="all">전체</span>
    <span class="chip" data-g="season" data-v="봄">봄</span>
    <span class="chip" data-g="season" data-v="여름">여름</span>
    <span class="chip" data-g="season" data-v="가을">가을</span>
    <span class="chip" data-g="season" data-v="겨울">겨울</span>
  </div>
  <div class="resultbar">표시 <b id="vcount">0</b>곳 <span id="capnote"></span></div>
</div>

<div class="nav">__NAV__</div>

__SECTIONS__

<div class="empty">조건에 맞는 곳이 없어요. 검색어나 필터를 줄여보세요.</div>
<p class="note">※ ★ 큐레이션은 직접 검증한 곳, 🤖 자동수집은 공공데이터(TourAPI) 후보입니다(기본은 큐레이션만 표시).
자동수집분은 실내외·요금이 확인되지 않아 해당 필터를 켜면 제외됩니다.
운영시간·요금·물놀이장 개장은 방문 전 확인하세요.</p>

<script>
  var CAP = 8;
  var F = { region: [], source: "curated", place: "all", cost: "all", season: "all", q: "" };
  var expanded = {};

  function pass(card) {
    if (F.region.length && F.region.indexOf(card.dataset.region) < 0) return false;
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
    if (F.q && card.dataset.search.indexOf(F.q) < 0) return false;
    return true;
  }

  function apply() {
    var total = 0;
    var groups = document.querySelectorAll(".region-group");
    groups.forEach(function (g, gi) {
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
      var rc = g.querySelector(".rcount");
      if (rc) rc.textContent = vis ? vis : "";
      g.style.display = vis ? "block" : "none";
    });
    document.querySelectorAll("section.cat").forEach(function (s) {
      var cv = 0;
      s.querySelectorAll(".region-group").forEach(function (g) {
        if (g.style.display !== "none") cv += parseInt(g.querySelector(".rcount").textContent || "0", 10);
      });
      s.style.display = cv ? "block" : "none";
      var cc = s.querySelector(".ccount");
      if (cc) cc.textContent = cv ? cv : "";
    });
    document.getElementById("vcount").textContent = total;
    document.querySelector(".empty").style.display = total ? "none" : "block";
  }

  document.querySelectorAll(".more").forEach(function (btn, ignore) {
    btn.addEventListener("click", function () {
      var g = btn.closest(".region-group");
      var gi = Array.prototype.indexOf.call(document.querySelectorAll(".region-group"), g);
      expanded[gi] = true;
      apply();
    });
  });

  document.getElementById("q").addEventListener("input", function () {
    F.q = this.value.trim().toLowerCase();
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
        document.querySelectorAll('.chip[data-g="region"]').forEach(function (c) {
          if (c.dataset.v === "all") c.classList.toggle("active", F.region.length === 0);
          else c.classList.toggle("active", F.region.indexOf(c.dataset.v) >= 0);
        });
      } else {
        F[g] = v;
        document.querySelectorAll('.chip[data-g="' + g + '"]').forEach(function (c) {
          c.classList.toggle("active", c === chip);
        });
      }
      apply();
    });
  });

  apply();
</script>
</body></html>"""


if __name__ == "__main__":
    build()
