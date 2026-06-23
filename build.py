#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이랑 갈 만한 곳 — 큐레이션 가이드 페이지 생성기

places.json(엄선 데이터)를 읽어 카테고리 → 권역(도)으로 그룹핑한
필터형 정적 페이지(index.html)를 만든다.
필터: 권역 · 실내/실외 · 무료/유료 · 계절

실행:  python3 build.py   →  open index.html
데이터 추가/수정:  places.json 만 고치면 됨 (TourAPI 연동은 추후 자동 보강용)
"""

import json
import os
import html
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "places.json")
OUT = os.path.join(BASE, "index.html")

CATEGORIES = ["숙소", "놀이터", "공원", "물놀이터", "테마파크·놀이공원",
              "박물관·과학·전시", "동물·자연", "체험·교육", "캠핑", "액티비티"]
CAT_ICON = {"숙소": "🛏️", "놀이터": "🎠", "공원": "🌳", "물놀이터": "💦",
            "테마파크·놀이공원": "🎢", "박물관·과학·전시": "🔬", "동물·자연": "🦒",
            "체험·교육": "🎨", "캠핑": "⛺", "액티비티": "🎟️"}
CAT_SUB = {"숙소": "키즈 프렌들리", "놀이터": "순수 놀이터", "물놀이터": "여름 위주",
           "박물관·과학·전시": "실내·날씨무관", "캠핑": "키즈"}
REGIONS = ["수도권", "강원", "충청", "전라", "경상", "제주"]


def naver_map_link(name):
    return "https://map.naver.com/p/search/" + urllib.parse.quote(name)


def tag(text, cls="tag"):
    return f'<span class="{cls}">{html.escape(text)}</span>'


def card_html(p):
    name = html.escape(p.get("name", "?"))
    area = html.escape(p.get("area", ""))
    desc = html.escape(p.get("desc", ""))
    indoor = "y" if p.get("indoor") else "n"
    free = "y" if p.get("free") else "n"
    seasons = p.get("season", []) or []
    season_attr = ",".join(seasons)

    tags = []
    tags.append(tag("🏠 실내" if indoor == "y" else "🌳 실외", "tag place"))
    tags.append(tag("무료" if free == "y" else "유료", "tag cost"))
    for s in seasons:
        if s != "올시즌":
            tags.append(tag(s, "tag season"))
        else:
            tags.append(tag("사계절", "tag season"))
    if p.get("age"):
        tags.append(tag("👶 " + p["age"], "tag age"))
    for a in p.get("amenities", []):
        tags.append(tag(a, "tag amen"))

    return (
        f'<div class="card" data-region="{html.escape(p.get("region",""))}" '
        f'data-indoor="{indoor}" data-free="{free}" data-season="{html.escape(season_attr)}">'
        f'<div class="card-h"><span class="cname">{name}</span>'
        f'<span class="carea">{area}</span></div>'
        f'<div class="cdesc">{desc}</div>'
        f'<div class="ctags">{"".join(tags)}</div>'
        f'<a class="clink" href="{naver_map_link(p.get("name",""))}" target="_blank">지도에서 보기 ↗</a>'
        f"</div>"
    )


def build():
    with open(DATA, encoding="utf-8") as f:
        places = json.load(f)["places"]

    sections = []
    for cat in CATEGORIES:
        in_cat = [p for p in places if p.get("category") == cat]
        if not in_cat:
            continue
        groups = []
        for region in REGIONS:
            in_region = [p for p in in_cat if p.get("region") == region]
            if not in_region:
                continue
            cards = "\n".join(card_html(p) for p in in_region)
            groups.append(
                f'<div class="region-group" data-region="{region}">'
                f"<h3>{region}</h3>"
                f'<div class="cards">{cards}</div></div>'
            )
        sub = CAT_SUB.get(cat, "")
        sub_html = f' <span class="muted">({html.escape(sub)})</span>' if sub else ""
        sections.append(
            f'<section class="cat" data-cat="{html.escape(cat)}">'
            f'<h2>{CAT_ICON.get(cat,"")} {html.escape(cat)}{sub_html}</h2>'
            f'{"".join(groups)}</section>'
        )

    page = PAGE.replace("__SECTIONS__", "\n".join(sections)).replace(
        "__COUNT__", str(len(places))
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"✅ {len(places)}곳 → {OUT}")
    print("열기:  open index.html")


PAGE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>아이랑 갈 만한 곳</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 920px;
         margin: 28px auto; padding: 0 16px; color: #1d1d1f; background: #fbfbfd; }
  h1 { font-size: 24px; margin: 0 0 2px; }
  .meta { color: #6e6e73; font-size: 13px; margin-bottom: 18px; }
  .muted { color: #86868b; font-weight: 400; font-size: 15px; }
  .filters { position: sticky; top: 0; background: #fbfbfd; padding: 12px 0;
             border-bottom: 1px solid #eee; margin-bottom: 8px; z-index: 5; }
  .frow { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 4px 0; }
  .flabel { font-size: 12px; color: #86868b; width: 52px; flex: none; }
  .chip { font-size: 13px; padding: 4px 11px; border-radius: 999px; border: 1px solid #ddd;
          background: #fff; cursor: pointer; user-select: none; }
  .chip.active { background: #1d1d1f; color: #fff; border-color: #1d1d1f; }
  section.cat { margin: 26px 0; }
  h2 { font-size: 19px; margin: 0 0 6px; }
  h3 { font-size: 14px; color: #6e6e73; margin: 14px 0 8px; font-weight: 600; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
  .card { background: #fff; border-radius: 14px; padding: 14px 15px;
          box-shadow: 0 1px 3px rgba(0,0,0,.06); display: flex; flex-direction: column; }
  .card-h { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
  .cname { font-weight: 700; font-size: 15px; }
  .carea { font-size: 12px; color: #86868b; flex: none; }
  .cdesc { font-size: 13px; color: #3a3a3c; margin: 7px 0 10px; line-height: 1.5; flex: 1; }
  .ctags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
  .tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #f0f0f2; color: #515154; }
  .tag.place { background: #e6f0ff; color: #0040a0; }
  .tag.cost { background: #e3f6e9; color: #1a7f37; }
  .tag.season { background: #fff1e0; color: #9a5b00; }
  .clink { font-size: 13px; color: #0066cc; text-decoration: none; }
  .empty { color: #86868b; font-size: 14px; padding: 24px 0; display: none; }
  .note { color: #86868b; font-size: 12px; margin-top: 24px; line-height: 1.6; }
</style></head><body>
<h1>👨‍👩‍👧 아이랑 갈 만한 곳</h1>
<div class="meta">전국 권역별 큐레이션 가이드 · 총 <b>__COUNT__</b>곳</div>

<div class="filters">
  <div class="frow"><span class="flabel">권역</span>
    <span class="chip active" data-g="region" data-v="all">전체</span>
    <span class="chip" data-g="region" data-v="수도권">수도권</span>
    <span class="chip" data-g="region" data-v="강원">강원</span>
    <span class="chip" data-g="region" data-v="충청">충청</span>
    <span class="chip" data-g="region" data-v="전라">전라</span>
    <span class="chip" data-g="region" data-v="경상">경상</span>
    <span class="chip" data-g="region" data-v="제주">제주</span>
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
</div>

__SECTIONS__

<div class="empty">조건에 맞는 곳이 없어요. 필터를 줄여보세요.</div>
<p class="note">※ 큐레이션 가이드입니다. 운영시간·요금·물놀이장 개장은 방문 전 확인하세요.
공공데이터(TourAPI) 연동 시 더 많은 후보가 자동으로 채워집니다.</p>

<script>
  var F = { region: [], place: "all", cost: "all", season: "all" };
  function pass(card) {
    if (F.region.length && F.region.indexOf(card.dataset.region) < 0) return false;
    if (F.place  !== "all" && card.dataset.indoor !== F.place) return false;
    if (F.cost   !== "all" && card.dataset.free !== F.cost) return false;
    if (F.season !== "all") {
      var s = card.dataset.season;
      if (s) {
        var arr = s.split(",");
        if (arr.indexOf(F.season) < 0 && arr.indexOf("올시즌") < 0) return false;
      }
    }
    return true;
  }
  function apply() {
    document.querySelectorAll(".card").forEach(function (c) {
      c.style.display = pass(c) ? "flex" : "none";
    });
    var anyVisible = false;
    document.querySelectorAll(".region-group").forEach(function (g) {
      var vis = g.querySelectorAll('.card[style*="flex"]').length;
      g.style.display = vis ? "block" : "none";
    });
    document.querySelectorAll("section.cat").forEach(function (s) {
      var vis = s.querySelectorAll('.region-group[style*="block"]').length;
      s.style.display = vis ? "block" : "none";
      if (vis) anyVisible = true;
    });
    document.querySelector(".empty").style.display = anyVisible ? "none" : "block";
  }
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      var g = chip.dataset.g, v = chip.dataset.v;
      if (g === "region") {
        // 권역은 다중 선택: '전체'는 초기화, 나머지는 토글
        if (v === "all") {
          F.region = [];
        } else {
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
