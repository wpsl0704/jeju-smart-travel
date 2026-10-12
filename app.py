from pathlib import Path
import json

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


# ==========================================
# 1. 기본 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="제주 숨은 여행지 찾기",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed"
)


@st.cache_data
def load_data():
    return pd.read_csv(
        BASE_DIR / "제주_자동차거리_TOP1_최종.csv",
        encoding="utf-8-sig"
    )


@st.cache_data
def load_routes():
    with open(
        BASE_DIR / "제주_자동차TOP1_28쌍_실제도로경로.geojson",
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

result = df[
    df["출발관광지"] == selected
].iloc[0]

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

    if props.get("출발관광지") == selected:
        selected_routes.append(feature)

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
    st.warning(
        "선택한 관광지의 자동차 경로를 찾을 수 없습니다."
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