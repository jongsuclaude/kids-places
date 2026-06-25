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

# 카테고리별로 의미 있는 태그만 — 자명한 건 숨김
SHOW_PLACE = {"놀이터", "테마파크·놀이공원", "동물·자연", "체험·교육", "액티비티"}  # 실내외가 갈리는 곳
SHOW_COST = {"놀이터", "물놀이터", "박물관·과학·전시", "동물·자연", "체험·교육", "액티비티"}  # 무료/유료가 갈리는 곳
OBVIOUS_AGE = {"전연령", "전 연령", ""}  # 연령 태그 생략 대상


def norm(s):
    return re.sub(r"[\s()·]", "", unicodedata.normalize("NFC", s or "")).lower()


# 지도 검색을 방해하는 놀이터 설명 키워드(끝부분에서 제거)
_PLAYGROUND_DESC = re.compile(
    r"\s*(?:무장애\s*통합\s*놀이(?:터|시설)|무장애\s*놀이(?:터|시설)|통합\s*놀이터|"
    r"모험\s*놀이터|창의\s*놀이터|숲\s*놀이터|자연\s*놀이터|어린이\s*놀이(?:터|시설)|"
    r"놀이터|놀이시설)\s*$"
)


def map_query(name, area):
    # 괄호 별칭 제거 + 끝의 놀이터 설명 키워드 제거 + 지역 결합 → 네이버 지도에서 잡히게
    base = re.sub(r"\s*\([^)]*\)", "", name).strip()
    stripped = _PLAYGROUND_DESC.sub("", base).strip()
    if stripped:  # 전부 지워졌으면(이름 자체가 'OO놀이터') 원래 이름 사용
        base = stripped
    return (base + " " + (area or "")).strip()


def naver_map_link(query):
    return "https://map.naver.com/p/search/" + urllib.parse.quote(query)


# 제목 없는 단일 출처용 — URL에서 출처명 만들기
SOURCE_DOMAINS = {
    "i-rang.net": "아이랑넷", "mom-mom.net": "맘맘",
    "visitkorea.or.kr": "대한민국 구석구석",
    "seoul.go.kr": "서울시", "sejong.go.kr": "세종시", "daejeon.go.kr": "대전시",
    "chuncheon.go.kr": "춘천시", "taebaek.go.kr": "태백시", "hanam.go.kr": "하남시",
    "gunpo.go.kr": "군포시", "seongnam.go.kr": "성남시",
    "wjsangsang.or.kr": "원주 상상놀이터",
    "nate.com": "네이트뉴스", "nocutnews.co.kr": "노컷뉴스", "newsis.com": "뉴시스",
    "welfarehello.com": "웰로", "heraldcorp.com": "헤럴드경제", "khan.co.kr": "경향신문",
    "asiae.co.kr": "아시아경제", "sijung.co.kr": "시정일보", "jbnews.com": "중부매일",
    "lafent.com": "라펜트", "yeogi.com": "여기어때", "yanolja.com": "야놀자",
    "go.kr": "지자체·공공", "or.kr": "공공기관",
}


def source_title(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    for dom, label in SOURCE_DOMAINS.items():
        if host == dom or host.endswith("." + dom):
            return label
    return host or "정보 글"


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
        cat = p.get("category", "")
        if kind == "suggested":
            tags.append(tag("🙋 우리 추천", "tag sug"))
        else:
            tags.append(tag("★ 큐레이션", "tag cur"))
        if cat in SHOW_PLACE:
            tags.append(tag("🏠 실내" if indoor == "y" else "🌳 실외", "tag place"))
        if cat in SHOW_COST:
            tags.append(tag("무료" if free == "y" else "유료", "tag cost"))
        for s in seasons:
            if s and s != "올시즌":  # 사계절은 자명 → 생략
                tags.append(tag(s, "tag season"))
        age = p.get("age", "")
        if age not in OBVIOUS_AGE:
            tags.append(tag("👶 " + age, "tag age"))
        for a in p.get("amenities", []):
            tags.append(tag(a, "tag amen"))

    img = p.get("_img", "") if is_auto else ""
    thumb = (
        f'<img class="thumb" loading="lazy" src="{html.escape(img)}" alt="">'
        if img else ""
    )
    desc_html = f'<div class="cdesc">{desc}</div>' if desc else ""

    # 링크: 지도 + 정보 글(최대 3개). sources 배열 우선, 없으면 단일 source 하위호환
    map_url = naver_map_link(map_query(raw_name, raw_area))
    links = f'<a class="clink" href="{map_url}" target="_blank" rel="noopener">🗺️ 지도</a>'

    srcs = p.get("sources")
    if not srcs:
        s = (p.get("source") or "").strip()
        srcs = [{"url": s}] if s.startswith("http") else []
    srcs = [
        x for x in srcs
        if isinstance(x, dict) and str(x.get("url", "")).startswith("http")
    ][:3]
    # 제목 없거나 일반(정보 글)이면 URL에서 출처명 생성 → 1개여도 제목 노출
    for x in srcs:
        t = (x.get("title") or "").strip()
        if not t or t == "정보 글":
            x["title"] = source_title(x["url"])

    srclist_html = ""
    if srcs:
        label = "📄 정보 글" + (f" ({len(srcs)})" if len(srcs) > 1 else "")
        links += f'<button class="srcbtn" type="button">{label}</button>'
        items = "".join(
            f'<a class="clink src" href="{html.escape(x["url"], quote=True)}" '
            f'target="_blank" rel="noopener">📄 {html.escape(x.get("title") or "정보 글")}</a>'
            for x in srcs
        )
        srclist_html = f'<div class="srclist">{items}</div>'

    links += '<button class="reviewbtn" type="button">✍️ 평가</button>'
    links_html = f'<div class="clinks">{links}</div>{srclist_html}'

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
        f'<div class="reviewslot"></div>'
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
        p["_kind"] = "suggested" if p.get("src") == "suggested" else "curated"
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
            # 같은 시(area)끼리 묶이도록 정렬 (큐레이션·제보 먼저, 그다음 자동수집)
            in_region.sort(key=lambda p: (p.get("area", ""), 0 if p.get("_kind") != "auto" else 1))
            cards = "\n".join(card_html(p) for p in in_region)
            groups.append(
                f'<div class="region-group" data-region="{region}">'
                f'<h3 class="rhead"><span class="rchev">▸</span> '
                f'<span class="rlabel">{REGION_ICON.get(region,"")} {region}</span>'
                f' <span class="rcount"></span></h3>'
                f'<div class="cards">{cards}</div>'
                f'<button class="more" type="button">더보기</button>'
                f"</div>"
            )
        sub = CAT_SUB.get(cat, "")
        sub_html = f' <span class="muted">({html.escape(sub)})</span>' if sub else ""
        sections.append(
            f'<section class="cat" id="{cat_id}" data-cat="{html.escape(cat)}">'
            f'<h2 class="cathead"><span class="chev">▸</span> '
            f'{CAT_ICON.get(cat,"")} {html.escape(cat)}{sub_html}'
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
        chip_row("출처", "source", [("all", "전체", False), ("curated", "★ 큐레이션", True), ("suggested", "🙋 우리 추천", False), ("auto", "🤖 자동수집", False)]),
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
         margin: 0 auto; padding: 20px 16px 60px; color: #1d1d1f; background: #f5f5f7; }
  h1 { font-size: 23px; margin: 0 0 2px; }
  .meta { color: #6e6e73; font-size: 13px; margin-bottom: 12px; }
  .muted { color: #86868b; font-weight: 400; font-size: 15px; }

  /* 상단 고정바: 검색 + 필터버튼 */
  .topbar { position: sticky; top: 0; z-index: 20; background: rgba(245,245,247,.92);
            backdrop-filter: blur(10px); padding: 10px 0 8px;
            display: flex; gap: 8px; align-items: center; }
  .search { flex: 1; min-width: 0; box-sizing: border-box; font-size: 16px; padding: 10px 14px;
            border: 1px solid #ddd; border-radius: 12px; background: #fff; }
  .filter-toggle { flex: none; font-size: 14px; font-weight: 600; padding: 10px 14px;
                   border: 1px solid #ddd; border-radius: 12px; background: #fff; cursor: pointer;
                   display: flex; align-items: center; gap: 6px; }
  .fbadge { font-size: 11px; min-width: 17px; height: 17px; padding: 0 4px; box-sizing: border-box;
            border-radius: 999px; background: #1d6fd6; color: #fff; display: none;
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
  .chip.active { background: #1d6fd6; color: #fff; border-color: #1d6fd6; }
  .panel-actions { display: flex; gap: 8px; margin-top: 12px; }
  .pbtn { flex: 1; font-size: 14px; font-weight: 600; padding: 10px; border-radius: 10px;
          border: 1px solid #ddd; background: #fff; cursor: pointer; }
  .pbtn.primary { background: #1d6fd6; color: #fff; border-color: #1d6fd6; }

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
  .tag.sug { background: #e7f6ec; color: #1a7f37; }
  .tag.auto { background: #eef0f2; color: #8a8a8e; }
  .clinks { display: none; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
  .card.open .clinks { display: flex; }
  .card { cursor: pointer; }
  .clink { font-size: 13px; color: #0066cc; text-decoration: none; padding: 5px 10px;
           border: 1px solid #d6e4f5; border-radius: 8px; background: #f4f8fd; }
  .clink.src { color: #6b6b70; border-color: #e3e3e6; background: #f5f5f7; }
  .srcbtn { font-size: 13px; color: #6b6b70; padding: 5px 10px; border: 1px solid #e3e3e6;
            border-radius: 8px; background: #f5f5f7; cursor: pointer; }
  .srclist { display: none; flex-direction: column; gap: 6px; margin-top: 8px;
             padding-left: 2px; }
  .srclist.on { display: flex; }
  .card:not(.open) .srclist { display: none; }  /* 카드 닫히면 정보글도 숨김 */
  .srclist .clink.src { align-self: flex-start; }
  .more { display: none; margin: 12px auto 0; font-size: 13px; padding: 8px 18px;
          border: 1px solid #ddd; border-radius: 999px; background: #fff; cursor: pointer; }
  .empty { color: #86868b; font-size: 14px; padding: 24px 0; display: none; }
  .note { color: #86868b; font-size: 12px; margin-top: 24px; line-height: 1.6; }

  /* 평가(리뷰) UI — 기본 활성(통합) */
  .reviewbtn { display: none; font-size: 13px; color: #b8860b;
               padding: 5px 11px; border: 1px solid #f0e0b0; border-radius: 8px;
               background: #fffbf0; cursor: pointer; }
  body.edit-mode .reviewbtn { display: inline-block; }
  .reviewform { display: none; flex-direction: column; gap: 10px; margin-top: 10px;
                padding: 12px; border: 1px solid #eee; border-radius: 10px; background: #fafafa; }
  .reviewform.on { display: flex; }
  .card:not(.open) .reviewform { display: none; }  /* 카드 닫히면 평가도 숨김 */
  .rv-text { width: 100%; box-sizing: border-box; min-height: 70px; font-size: 14px;
             padding: 10px; border: 1px solid #ddd; border-radius: 8px; resize: vertical; }
  .rv-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
  .rv-upload { font-size: 13px; padding: 9px 12px; border: 1px solid #ddd; border-radius: 8px;
               background: #fff; cursor: pointer; white-space: nowrap; }
  .stars { display: inline-flex; gap: 3px; }
  .star { position: relative; color: #dcdce0; font-size: 27px; cursor: pointer; line-height: 1;
          width: 27px; text-align: center; }
  .star .fill { position: absolute; left: 0; top: 0; width: 0; overflow: hidden;
                color: #ffb300; pointer-events: none; }
  .rv-photos { display: flex; flex-wrap: wrap; gap: 12px; }
  .rv-thumb { position: relative; }
  .rv-thumb img { width: 56px; height: 56px; object-fit: cover; border-radius: 6px; display: block; }
  .rv-del { position: absolute; top: -7px; right: -7px; width: 20px; height: 20px; padding: 0;
            border: 0; border-radius: 50%; background: rgba(0,0,0,.72); color: #fff;
            font-size: 15px; line-height: 20px; text-align: center; cursor: pointer; }
  .rv-save { font-size: 14px; font-weight: 700; padding: 10px; border: 0; border-radius: 8px;
             background: #1d6fd6; color: #fff; cursor: pointer; }
  .rv-msg { font-size: 13px; color: #1a7f37; }

  /* 보기 토글 · 리스트뷰 · 아코디언 */
  .resultbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
  .viewtoggle { display: flex; gap: 4px; }
  .vbtn { font-size: 12px; padding: 5px 10px; border: 1px solid #ddd; border-radius: 8px;
          background: #fff; color: #515154; cursor: pointer; }
  .vbtn.active { background: #1d6fd6; color: #fff; border-color: #1d6fd6; }
  .cathead { cursor: pointer; user-select: none; display: flex; align-items: center; gap: 7px; }
  .chev { font-size: 12px; color: #aeaeb2; transition: transform .15s; }
  section.cat:not(.collapsed) > .cathead .chev { transform: rotate(90deg); }
  section.cat.collapsed .region-group,
  section.cat.collapsed .more { display: none !important; }
  .rhead { cursor: pointer; user-select: none; }
  .rchev { font-size: 11px; color: #aeaeb2; transition: transform .15s; display: inline-block; }
  .region-group:not(.rcollapsed) > .rhead .rchev { transform: rotate(90deg); }
  .region-group.rcollapsed > .cards,
  .region-group.rcollapsed > .more { display: none !important; }
  /* 리스트(compact) 뷰 */
  body.view-list .cards { grid-template-columns: 1fr; gap: 6px; }
  body.view-list .card { padding: 11px 13px; cursor: pointer; }
  body.view-list .thumb,
  body.view-list .cdesc { display: none; }
  body.view-list .card.open .cdesc { display: block; }
  body.view-list .ctags { margin: 6px 0 0; }

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
</style></head><body class="view-list">
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

<div class="resultbar">
  <span>표시 <b id="vcount">0</b>곳 / 전체 __TOTAL__곳</span>
  <span class="viewtoggle">
    <button id="expAll" class="vbtn" type="button">모두 펼치기</button>
    <button id="vList" class="vbtn active" type="button">📋 리스트</button>
    <button id="vCard" class="vbtn" type="button">🗂️ 카드</button>
  </span>
</div>
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
    if (F.source !== "all") { var ds = card.dataset.source; if (F.source === "curated") { if (ds !== "curated" && ds !== "suggested") return false; } else if (ds !== F.source) return false; }
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
    applyCollapse();
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

  document.querySelectorAll(".srcbtn").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var card = btn.closest(".card");
      var rf = card.querySelector(".reviewform");
      if (rf) rf.classList.remove("on");  // 평가 열려있으면 닫기(상호배타)
      var list = card.querySelector(".srclist");
      if (list) list.classList.toggle("on");
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

  // === 보기 토글 (리스트/카드) ===
  var body = document.body;
  function setView(v) {
    body.classList.toggle("view-list", v === "list");
    body.classList.toggle("view-card", v === "card");
    document.getElementById("vList").classList.toggle("active", v === "list");
    document.getElementById("vCard").classList.toggle("active", v === "card");
  }
  document.getElementById("vList").addEventListener("click", function () { setView("list"); });
  document.getElementById("vCard").addEventListener("click", function () { setView("card"); });

  // 리스트뷰에서 카드 탭 → 상세(설명·링크) 펼침
  document.querySelectorAll(".card").forEach(function (c) {
    c.addEventListener("click", function (e) {
      if (e.target.closest("a, button, .reviewslot")) return;
      var willOpen = !c.classList.contains("open");
      if (willOpen) {  // 새 카드 열 때 다른 열린 카드 닫기 (한 번에 하나)
        document.querySelectorAll(".card.open").forEach(function (o) {
          if (o === c) return;
          o.classList.remove("open");
          var orf = o.querySelector(".reviewform"); if (orf) orf.classList.remove("on");
          var osl = o.querySelector(".srclist"); if (osl) osl.classList.remove("on");
        });
      }
      c.classList.toggle("open");
      if (!c.classList.contains("open")) {  // 카드 닫으면 평가·정보글 닫기
        var rf = c.querySelector(".reviewform");
        if (rf) rf.classList.remove("on");
        var sl = c.querySelector(".srclist");
        if (sl) sl.classList.remove("on");
      }
    });
  });

  // === 카테고리 아코디언 (기본 접힘, 필터/검색 시 자동 펼침) ===
  var collapsed = {};
  document.querySelectorAll("section.cat").forEach(function (s) { collapsed[s.dataset.cat] = true; });
  var regionCollapsed = new Set();  // 권역 기본 접힘 — 카테고리 열면 권역 헤더만, 탭해야 카드 보임
  document.querySelectorAll(".region-group").forEach(function (g) { regionCollapsed.add(g); });
  function isFiltering() {
    return (F.qtoks && F.qtoks.length) || F.region.length || F.cat !== "all" ||
           F.place !== "all" || F.cost !== "all" || F.season !== "all";
  }
  function applyCollapse() {
    var filtering = isFiltering();
    document.querySelectorAll("section.cat").forEach(function (s) {
      var open = filtering || !collapsed[s.dataset.cat];
      s.classList.toggle("collapsed", !open);
    });
    document.querySelectorAll(".region-group").forEach(function (g) {
      var open = filtering || !regionCollapsed.has(g);
      g.classList.toggle("rcollapsed", !open);
    });
  }
  document.querySelectorAll(".cathead").forEach(function (h) {
    h.addEventListener("click", function () {
      var s = h.closest("section.cat");
      collapsed[s.dataset.cat] = !collapsed[s.dataset.cat];
      applyCollapse();
    });
  });
  document.querySelectorAll(".rhead").forEach(function (h) {
    h.addEventListener("click", function () {
      var g = h.closest(".region-group");
      if (regionCollapsed.has(g)) regionCollapsed.delete(g); else regionCollapsed.add(g);
      applyCollapse();
    });
  });
  document.querySelectorAll('.navchip[href^="#cat-"]').forEach(function (a) {
    a.addEventListener("click", function () {
      var s = document.querySelector(a.getAttribute("href"));
      if (s && s.dataset.cat) { collapsed[s.dataset.cat] = false; applyCollapse(); }
    });
  });
  var allOpen = false;
  document.getElementById("expAll").addEventListener("click", function () {
    allOpen = !allOpen;
    document.querySelectorAll("section.cat").forEach(function (s) { collapsed[s.dataset.cat] = !allOpen; });
    if (allOpen) regionCollapsed.clear();
    else document.querySelectorAll(".region-group").forEach(function (g) { regionCollapsed.add(g); });
    this.textContent = allOpen ? "모두 접기" : "모두 펼치기";
    applyCollapse();
  });

  // === 평가(리뷰) UI — 기본 활성(기존 사이트에 통합) ===
  // 에딧(평가) 모드 — 공개 기본 OFF. 우리 기기에서 ?edit=1 한 번 → localStorage에 저장돼 계속 유지.
  // 끄기: ?edit=0
  (function () {
    var q = location.search;
    try {
      if (/[?&]edit=0(&|$)/.test(q)) localStorage.removeItem("kp_edit");
      else if (/[?&]edit=1(&|$)/.test(q)) localStorage.setItem("kp_edit", "1");
      if (localStorage.getItem("kp_edit") === "1") document.body.classList.add("edit-mode");
    } catch (e) {
      if (/[?&]edit=1(&|$)/.test(q)) document.body.classList.add("edit-mode");
    }
  })();

  function updateStars(starsEl) {
    var r = parseFloat(starsEl.dataset.rating || "0");
    starsEl.querySelectorAll(".star").forEach(function (s, idx) {
      var i = idx + 1, w = (r >= i) ? 100 : (r >= i - 0.5 ? 50 : 0);
      s.querySelector(".fill").style.width = w + "%";
    });
  }
  function buildReviewForm() {
    var stars = "";
    for (var i = 1; i <= 5; i++) stars += '<span class="star" data-i="' + i + '">★<span class="fill">★</span></span>';
    return '<div class="reviewform">'
      + '<textarea class="rv-text" placeholder="다녀온 후기를 적어요 (날씨·아이 반응·머문 시간·꿀팁 등)"></textarea>'
      + '<div class="rv-row">'
      + '<label class="rv-upload">📷 사진 업로드<input type="file" accept="image/*" multiple hidden></label>'
      + '<span class="stars" data-rating="0">' + stars + '</span>'
      + '</div>'
      + '<div class="rv-photos"></div>'
      + '<button class="rv-save" type="button">저장</button>'
      + '<div class="rv-msg"></div>'
      + '</div>';
  }
  document.querySelectorAll(".reviewbtn").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var card = btn.closest(".card");
      var sl = card.querySelector(".srclist");
      if (sl) sl.classList.remove("on");  // 정보글 열려있으면 닫기(상호배타)
      var slot = card.querySelector(".reviewslot");
      var form = slot.querySelector(".reviewform");
      if (!form) {
        slot.innerHTML = buildReviewForm();
        form = slot.querySelector(".reviewform");
        var starsEl = form.querySelector(".stars");
        starsEl.querySelectorAll(".star").forEach(function (s) {
          s.addEventListener("click", function () {
            var i = parseInt(s.dataset.i, 10);
            var cur = parseFloat(starsEl.dataset.rating || "0");
            starsEl.dataset.rating = (cur === i) ? (i - 0.5) : i;  // 같은 별 다시 누르면 반개
            updateStars(starsEl);
          });
        });
        var fileInput = form.querySelector('input[type=file]');
        var photoBox = form.querySelector(".rv-photos");
        var selectedFiles = [];
        function renderPhotos() {
          photoBox.innerHTML = "";
          selectedFiles.forEach(function (f, idx) {
            var wrap = document.createElement("div"); wrap.className = "rv-thumb";
            var img = document.createElement("img"); img.src = URL.createObjectURL(f);
            var del = document.createElement("button");
            del.type = "button"; del.className = "rv-del"; del.textContent = "×";
            del.addEventListener("click", function (ev) {
              ev.stopPropagation(); selectedFiles.splice(idx, 1); renderPhotos();
            });
            wrap.appendChild(img); wrap.appendChild(del); photoBox.appendChild(wrap);
          });
        }
        fileInput.addEventListener("change", function () {
          Array.prototype.forEach.call(fileInput.files, function (f) { selectedFiles.push(f); });
          fileInput.value = "";  // 같은 파일 재선택 가능
          renderPhotos();
        });
        form.querySelector(".rv-save").addEventListener("click", function () {
          var rating = starsEl.dataset.rating || "0";
          form.querySelector(".rv-msg").textContent =
            "✅ (미리보기) 별점 " + rating + " · 사진 " + selectedFiles.length + "장 — 나스 연동 시 실제 저장됩니다.";
        });
      }
      form.classList.toggle("on");
    });
  });

  setView("list");
  apply();
</script>
</body></html>"""


if __name__ == "__main__":
    build()
