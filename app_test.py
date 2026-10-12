from pathlib import Path
import json

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# ==========================================
# 1. 기본 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
@st.cache_data(ttl=600)
def load_jeju_weather():
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": 33.4996,
        "longitude": 126.5312,
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "timezone": "Asia/Seoul"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()["current"]
    except (requests.RequestException, KeyError, ValueError):
        return None

# 관광지 위치 좌표 데이터 불러오기
@st.cache_data
def load_tourist_locations():
    locations = pd.read_csv(
        BASE_DIR / "제주_중심관광지.csv",
        encoding="utf-8-sig"
    )

    locations["mapX"] = pd.to_numeric(
        locations["mapX"], errors="coerce"
    )
    locations["mapY"] = pd.to_numeric(
        locations["mapY"], errors="coerce"
    )

    return (
        locations
        .dropna(subset=["hubTatsNm", "mapX", "mapY"])
        .drop_duplicates(subset=["hubTatsNm"])
    )

st.set_page_config(
    page_title="제주 숨은 여행지 찾기",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed"
)


@st.cache_data
def load_data():
    return pd.read_csv(
        BASE_DIR / "제주_자동차거리_TOP3_최종.csv",
        encoding="utf-8-sig"
    )


@st.cache_data
def load_routes():
    with open(
        BASE_DIR / "제주_TOP3_실제도로경로.geojson",
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


df = load_data()
route_data = load_routes()


# ==========================================
# 2. 디자인
# ==========================================

st.markdown("""
<style>
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(120deg, #087F8C, #12A89D);
        border-radius: 20px;
        padding: 35px;
        color: white;
        margin-bottom: 25px;
    }

    .hero-label {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 2px;
        opacity: 0.9;
    }

    .hero-title {
        font-size: clamp(28px, 5vw, 43px);
        font-weight: 800;
        margin: 12px 0;
    }

    .hero-desc {
        font-size: 16px;
        opacity: 0.95;
    }

    .section-title {
        font-size: 23px;
        font-weight: 800;
        margin: 25px 0 12px 0;
    }

    .result-card {
        background: #F0FAF8;
        border: 1px solid #C5EAE4;
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0 20px 0;
        color: #173D3B;
    }

    .result-label {
        font-size: 14px;
        color: #477A74;
        font-weight: 600;
    }

    .result-name {
        font-size: clamp(24px, 4vw, 34px);
        font-weight: 800;
        margin: 8px 0;
    }

    .result-desc {
        font-size: 14px;
        color: #527D78;
    }

    @media (max-width: 640px) {
        .hero {
            padding: 23px;
        }

        .block-container {
            padding-top: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 3. 서비스 소개
# ==========================================

st.markdown("""
<div class="hero">
    <div class="hero-label">JEJU SMART TRAVEL</div>
    <div class="hero-title">🌴 제주 숨은 여행지 찾기</div>
    <div class="hero-desc">
        관광수요와 실제 자동차 이동거리를 고려해
        가까운 대체 관광지를 추천합니다.
    </div>
</div>
""", unsafe_allow_html=True)
weather = load_jeju_weather()

if weather is not None:
    st.info(
        f"🌤️ 제주시 현재 날씨 | "
        f"기온 {weather['temperature_2m']}°C | "
        f"강수량 {weather['precipitation']}mm | "
        f"풍속 {weather['wind_speed_10m']}km/h"
    )
else:
    st.caption("현재 날씨 정보를 불러올 수 없습니다.")

# ==========================================
# 4. 출발 관광지 선택
# ==========================================

st.markdown(
    '<div class="section-title">📍 어디로 여행을 가시나요?</div>',
    unsafe_allow_html=True
)

options = sorted(
    df["출발관광지"].dropna().unique().tolist()
)

default_index = (
    options.index("함덕해수욕장")
    if "함덕해수욕장" in options
    else 0
)

selected = st.selectbox(
    "방문하려는 관광지를 선택하세요",
    options,
    index=default_index
)

# ==========================================
# 거리·수요 가중치 선택
# ==========================================

weight_choice = st.radio(
    "추천 기준을 선택하세요",
    [
        "⚖️ 균형 추천 (거리 50% · 수요 50%)",
        "🚗 거리 우선 (거리 60% · 수요 40%)",
        "🌿 수요 분산 우선 (거리 40% · 수요 60%)"
    ],
    horizontal=True
)

if "거리 우선" in weight_choice:
    distance_weight = 0.6
elif "수요 분산 우선" in weight_choice:
    distance_weight = 0.4
else:
    distance_weight = 0.5

# 선택한 출발 관광지의 추천 후보
candidates = df[
    df["출발관광지"] == selected
].copy()

# 선택한 가중치로 추천 점수 재계산
candidates["선택가중치점수"] = (
    candidates["거리점수_자동차"] * distance_weight
    + candidates["수요여유점수_자동차"] * (1 - distance_weight)
)

# 추천 점수가 높은 순서대로 정렬
candidates = candidates.sort_values(
    "선택가중치점수",
    ascending=False
)

# 가장 높은 점수의 관광지를 대표 추천지로 선택
result = candidates.iloc[0]
destination_type = str(result["카테고리 3단계"])
# 비가 올 때 야외 관광지 방문 주의 안내
outdoor_types = ["해수욕장", "폭포/계곡", "골프장", "오름"]

if weather is not None:
    if weather["precipitation"] > 0 and destination_type in outdoor_types:
        st.warning(
            "🌧️ 현재 제주시에서 비가 관측되고 있습니다. "
            "추천 관광지는 야외 관광지이므로 방문 전 "
            "현지 날씨와 운영·출입 상황을 확인해 주세요."
        )

# 선택된 추천 관광지의 위치 찾기
locations = load_tourist_locations()

# 출발 관광지의 위치 찾기
origin_location = locations[
    locations["hubTatsNm"] == str(selected)
]

if not origin_location.empty:
    origin_lat = float(origin_location.iloc[0]["mapY"])
    origin_lon = float(origin_location.iloc[0]["mapX"])
else:
    origin_lat = None
    origin_lon = None

destination_location = locations[
    locations["hubTatsNm"] == str(result["목적지명_정리"])
]

if not destination_location.empty:
    destination_lat = float(destination_location.iloc[0]["mapY"])
    destination_lon = float(destination_location.iloc[0]["mapX"])
else:
    destination_lat = None
    destination_lon = None

st.markdown("### 🏅 가중치별 추천 TOP3")

for rank, (_, candidate) in enumerate(
    candidates.head(3).iterrows(), start=1
):
    st.write(
        f"**{rank}위. {candidate['목적지명_정리']}** "
        f"｜자동차 {candidate['자동차거리_km']:.1f}km "
        f"｜약 {candidate['자동차시간_분']:.0f}분"
    )

st.caption(
    f"현재 출발지의 추천 후보는 총 {len(candidates)}개입니다. "
    "후보가 3개 미만이면 있는 후보만 표시합니다."
)

destination = str(result["목적지명_정리"])
distance = float(result["자동차거리_km"])
duration = float(result["자동차시간_분"])

origin_count = int(result["출발관광지_도착수"])
destination_count = int(result["관광객 도착 수"])


# ==========================================
# 5. 추천 결과
# ==========================================

st.markdown(
    '<div class="section-title">✨ 추천 여행지</div>',
    unsafe_allow_html=True
)

st.markdown(f"""
<div class="result-card">
    <div class="result-label">데이터 기반 대체 관광지 추천</div>
    <div class="result-name">🌿 {destination}</div>
    <div class="result-desc">
        {selected}에서 자동차로 이동할 수 있는
        추천 후보지입니다.
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "🚗 자동차 이동거리",
        f"{distance:.2f} km"
    )

with col2:
    st.metric(
        "⏱️ 예상 이동시간",
        f"{duration:.1f}분"
    )

st.caption(
    "이동거리와 시간은 분석 시점의 도로 경로 데이터 기준이며, "
    "실시간 교통상황은 반영하지 않습니다."
)


# ==========================================
# 6. 관광수요 비교
# ==========================================

st.markdown(
    '<div class="section-title">📊 관광수요 비교</div>',
    unsafe_allow_html=True
)

st.write(
    "기존 관광지와 추천 후보지의 관광객 도착 수를 비교해 보세요."
)

comparison = pd.DataFrame({
    "관광지": [selected, destination],
    "관광객 도착 수": [
        origin_count,
        destination_count
    ]
})

st.vega_lite_chart(
    comparison,
    {
        "mark": {
            "type": "bar",
            "cornerRadiusEnd": 6
        },
        "encoding": {
            "x": {
                "field": "관광객 도착 수",
                "type": "quantitative",
                "title": "관광객 도착 수"
            },
            "y": {
                "field": "관광지",
                "type": "nominal",
                "sort": [selected, destination],
                "title": None
            },
            "color": {
                "field": "관광지",
                "type": "nominal",
                "scale": {
                    "domain": [selected, destination],
                    "range": ["#2563EB", "#0D9488"]
                },
                "legend": None
            },
            "tooltip": [
                {
                    "field": "관광지",
                    "type": "nominal"
                },
                {
                    "field": "관광객 도착 수",
                    "type": "quantitative",
                    "format": ","
                }
            ]
        },
        "height": 170
    },
    use_container_width=True
)

count_col1, count_col2 = st.columns(2)

with count_col1:
    st.metric(
        f"기존 관광지 · {selected}",
        f"{origin_count:,}"
    )

with count_col2:
    st.metric(
        f"추천 관광지 · {destination}",
        f"{destination_count:,}"
    )

st.caption(
    "※ 도착 수는 분석에 사용한 관광지별 관측값입니다. "
    "실시간 혼잡도나 관광지 수용능력을 의미하지 않습니다."
)


# ==========================================
# 7. 실제 자동차 도로 경로 지도
# ==========================================

st.markdown(
    '<div class="section-title">🗺️ 실제 자동차 이동 경로</div>',
    unsafe_allow_html=True
)

# 기존에 정상 작동했던 출발지 기준 검색 방식 유지
selected_routes = []

for feature in route_data["features"]:
    props = feature.get("properties", {})

    if (
    props.get("출발관광지") == selected
    and props.get("목적지명_정리") == destination
):
        selected_routes.append(feature)

original_top1 = df[
    (df["출발관광지"] == selected)
    & (df["추천순위_자동차"] == 1)
]

route_is_valid = (
    bool(selected_routes)
    and not original_top1.empty
    and str(original_top1.iloc[0]["목적지명_정리"]) == destination
)

if selected_routes:
    route = selected_routes[0]
    coordinates = route["geometry"]["coordinates"]

    center_lat = (
        sum(p[1] for p in coordinates) / len(coordinates)
    )
    center_lon = (
        sum(p[0] for p in coordinates) / len(coordinates)
    )

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="OpenStreetMap",
        control_scale=True
    )

  
    # 파란색 자동차 도로 경로
    folium.GeoJson(
        route,
        name="자동차 이동 경로",
        style_function=lambda x: {
            "color": "#2563EB",
            "weight": 6,
            "opacity": 0.9
        }
    ).add_to(m)

    # 빨간색 출발지 핀
    folium.Marker(
        location=[
            coordinates[0][1],
            coordinates[0][0]
        ],
        popup=f"출발: {selected}",
        tooltip=f"출발: {selected}",
        icon=folium.Icon(
            color="red",
            icon="info-sign"
        )
    ).add_to(m)

    # 초록색 추천지 핀
    folium.Marker(
        location=[
            coordinates[-1][1],
            coordinates[-1][0]
        ],
        popup=f"추천: {destination}",
        tooltip=f"추천: {destination}",
        icon=folium.Icon(
            color="green",
            icon="ok-sign"
        )
    ).add_to(m)

    # 경로 전체 표시
    m.fit_bounds([
        [
            min(p[1] for p in coordinates),
            min(p[0] for p in coordinates)
        ],
        [
            max(p[1] for p in coordinates),
            max(p[0] for p in coordinates)
        ]
    ])

    st_folium(
        m,
        height=480,
        use_container_width=True,
        returned_objects=[]
    )

    st.caption(
        "🔴 출발 관광지 | 🟢 추천 관광지 | "
        "🔵 실제 자동차 도로 경로"
    )

else:
    if destination_lat is not None and destination_lon is not None:
        m = folium.Map(
            location=[destination_lat, destination_lon],
            zoom_start=13,
            tiles="OpenStreetMap"
        )

        folium.Marker(
            location=[destination_lat, destination_lon],
            popup=f"추천 관광지: {destination}",
            tooltip=destination,
            icon=folium.Icon(color="green")
        ).add_to(m)

        # 빨간색 출발 관광지 마커
        if origin_lat is not None and origin_lon is not None:
            folium.Marker(
                location=[origin_lat, origin_lon],
                popup=f"출발 관광지: {selected}",
                tooltip=f"출발: {selected}",
                icon=folium.Icon(color="red")
            ).add_to(m)

            # 출발지와 목적지가 모두 보이도록 지도 범위 조정
            m.fit_bounds([
                [origin_lat, origin_lon],
                [destination_lat, destination_lon]
            ])

        st_folium(
            m,
            height=480,
            use_container_width=True,
            returned_objects=[]
        )

        st.caption(
            "🟢 추천 관광지 위치입니다. "
            "해당 목적지의 실제 자동차 도로 경로는 아직 제공되지 않습니다."
        )
    else:
        st.warning(
            "추천 관광지의 위치 좌표를 찾지 못했습니다."
        )


# ==========================================
# 8. 서비스 설명
# ==========================================

st.divider()

st.markdown(
    "### 💡 이 서비스는 어떻게 추천하나요?"
)

st.write(
    "제주 관광수요 데이터를 바탕으로 수요 집중 지역을 분석하고, "
    "관광지별 도착 수와 실제 자동차 이동거리를 고려하여 "
    "상대적으로 수요가 낮은 대체 관광지 후보를 제시합니다."
)

with st.expander("분석 기준 및 이용 시 유의사항"):

    st.write(
        "• 자동차 이동거리 10km 이내 후보를 우선 검토하고, "
        "필요한 경우 최대 15km까지 확장했습니다."
    )

    st.write(
        "• 추천 결과는 데이터 기반 1차 후보지이며, "
        "실제 관광객 분산 효과를 검증한 결과는 아닙니다."
    )

    st.write(
        "• 관광지 운영 여부, 실시간 혼잡도, "
        "현장 수용능력 및 안전성은 별도로 확인해야 합니다."
    )

    st.write(
        "• 추천 점수는 모델 내부의 상대적 평가 지표이며, "
        "관광지의 절대적인 품질 점수가 아닙니다."
    )

st.caption(
    "2026 제주 관광 데이터 활용사례 공모전 | "
    "데이터 기반 관광수요 분산 추천 서비스"
)
