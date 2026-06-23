#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TourAPI 자동 수집 테스트 — 아이랑 갈 만한 곳

keys.json의 TourAPI 키로 권역별 아이 관련 장소를 자동 수집해
places.json과 같은 형식으로 places_auto.json에 저장한다.
(수동 큐레이션 places.json은 건드리지 않음 — 자동 채우기가 되는지 확인용)

카테고리 분류 = API가 주는 contentTypeId + 장소 이름 기준.
(키워드로 카테고리를 정하지 않음 → '키즈뮤지엄=숙소' 같은 오분류 방지)

실행:  python3 fetch_places.py
"""

import json
import os
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
KEY = json.load(open(os.path.join(BASE, "keys.json")))["tour_api_key"]
API = "https://apis.data.go.kr/B551011/KorService2/searchKeyword2"

# 권역 = TourAPI areaCode 묶음
REGION_AREAS = {
    "수도권": [1, 2, 31],   # 서울·인천·경기
    "강원": [32],
    "충청": [3, 8, 33, 34],  # 대전·세종·충북·충남
    "전라": [5, 37, 38],     # 광주·전북·전남
    "경상": [6, 7, 9, 35, 36],  # 부산·대구·울산·경북·경남
    "제주": [39],
}

# 아이 관련 장소를 폭넓게 긁기 위한 검색어 (카테고리 분류용 아님 — 관련성만)
KEYWORDS = ["어린이", "키즈", "가족", "물놀이", "워터파크", "체험"]

# contentTypeId → 의미 (참고)
# 12 관광지 · 14 문화시설 · 15 축제공연 · 25 여행코스 · 28 레포츠 · 32 숙박 · 38 쇼핑 · 39 음식
CONTENTTYPE_NAME = {
    "12": "관광지", "14": "문화시설", "15": "축제공연", "25": "여행코스",
    "28": "레포츠", "32": "숙박", "38": "쇼핑", "39": "음식",
}

# 카테고리 판정용 이름 키워드 (위에서부터 우선순위)
WATER_WORDS = ["물놀이", "워터파크", "수영장", "해수욕", "해변", "계곡", "풀장"]
MUSEUM_WORDS = ["박물관", "과학관", "미술관", "천문대", "전시관", "사이언스", "기념관"]
ANIMAL_WORDS = ["동물원", "아쿠아", "수족관", "식물원", "목장", "농장", "곤충", "나비", "생태", "딸기"]
THEME_WORDS = ["테마파크", "놀이공원", "놀이동산", "에버랜드", "롯데월드", "키즈월드", "랜드"]
PLAY_WORDS = ["놀이터"]          # 순수 놀이터만
PARK_WORDS = ["공원"]            # 어린이공원·대공원·꿈공원·생태공원 등
CAMP_WORDS = ["캠핑", "글램핑", "오토캠"]
EDU_WORDS = ["체험", "도서관", "회관", "교육", "센터", "공방", "키즈카페"]

# 카테고리가 아니라 아예 제외할 contentTypeId (장소가 아님)
EXCLUDE_CONTENTTYPE = {"25", "39"}  # 25 여행코스 · 39 음식


def categorize(raw):
    """API가 준 contentTypeId + 이름으로 카테고리 판정. 제외 대상은 None."""
    cid = str(raw.get("contenttypeid", ""))
    name = raw.get("title", "")
    if cid in EXCLUDE_CONTENTTYPE:
        return None
    if cid == "32":                                  # 숙박
        return "숙소"
    if any(w in name for w in WATER_WORDS):
        return "물놀이터"
    if any(w in name for w in MUSEUM_WORDS):
        return "박물관·과학·전시"
    if any(w in name for w in ANIMAL_WORDS):
        return "동물·자연"
    if any(w in name for w in THEME_WORDS):
        return "테마파크·놀이공원"
    if any(w in name for w in PLAY_WORDS):   # 순수 놀이터
        return "놀이터"
    if any(w in name for w in PARK_WORDS):   # 공원류
        return "공원"
    if any(w in name for w in CAMP_WORDS):
        return "캠핑"
    if any(w in name for w in EDU_WORDS):
        return "체험·교육"
    return "액티비티"                                 # 그 외 관광지·레포츠 등


def fetch(area_code, keyword, rows=30):
    params = {
        "serviceKey": KEY, "MobileOS": "ETC", "MobileApp": "KidsGuide",
        "_type": "json", "numOfRows": rows, "pageNo": 1,
        "areaCode": area_code, "keyword": keyword,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
    except Exception as e:
        print(f"   ! 오류 area={area_code} kw={keyword}: {e}")
        return []
    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    if not items or items == "":
        return []
    item = items.get("item", [])
    return item if isinstance(item, list) else [item]


CATEGORIES = ["숙소", "놀이터", "공원", "물놀이터", "테마파크·놀이공원",
              "박물관·과학·전시", "동물·자연", "체험·교육", "캠핑", "액티비티"]


def to_place(region, cat, raw):
    return {
        "category": cat,
        "region": region,
        "name": raw.get("title", "").strip(),
        "area": raw.get("addr1", "").strip(),
        "desc": "(TourAPI 자동수집)",
        "indoor": False,
        "free": False,
        "_source": "tourapi",
        "_contenttypeid": str(raw.get("contenttypeid", "")),
        "_contentid": raw.get("contentid", ""),
        "_img": raw.get("firstimage", ""),
    }


def main():
    seen = set()
    collected = []
    for region, areas in REGION_AREAS.items():
        for kw in KEYWORDS:
            for area in areas:
                for raw in fetch(area, kw):
                    cid = raw.get("contentid")
                    if not cid or cid in seen:
                        continue
                    seen.add(cid)
                    cat = categorize(raw)
                    if cat is None:          # 여행코스·음식 등 장소 아님 → 제외
                        continue
                    collected.append(to_place(region, cat, raw))
        n = len([p for p in collected if p["region"] == region])
        print(f"  {region}: {n}곳 누적")

    out = os.path.join(BASE, "places_auto.json")
    json.dump({"places": collected}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ 총 {len(collected)}곳 자동수집 → places_auto.json")

    print("\n[카테고리별]")
    for cat in CATEGORIES:
        c = len([p for p in collected if p["category"] == cat])
        print(f"  {cat}: {c}곳")

    print("\n[contentTypeId 분포]")
    dist = {}
    for p in collected:
        dist[p["_contenttypeid"]] = dist.get(p["_contenttypeid"], 0) + 1
    for cid, c in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {cid} {CONTENTTYPE_NAME.get(cid,'?')}: {c}곳")

    print("\n[카테고리별 샘플]")
    for cat in CATEGORIES:
        sample = [p for p in collected if p["category"] == cat][:3]
        for p in sample:
            print(f"  · [{cat}] {p['name']} ({CONTENTTYPE_NAME.get(p['_contenttypeid'],'?')}) — {p['area'][:20]}")


if __name__ == "__main__":
    main()
