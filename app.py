import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- FRED API Key (필요시 입력) ---
FRED_API_KEY = "" 

st.set_page_config(page_title="역발상 매매 판단 컨트롤 타워 v4.5", layout="wide")

# 스타일 커스텀 (v4.2 고유의 깔끔한 테마와 인베스팅 스타일 레이아웃 결합)
st.markdown("""
<style>
    .main-title { font-size: 30px; font-weight: bold; color: #00FFBB; margin-bottom: 5px; }
    .sub-title { font-size: 14px; color: #888888; margin-bottom: 25px; }
    .section-title { font-size: 22px; font-weight: bold; color: #ffffff; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #00FFBB; padding-left: 10px; }
    .box-title { font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 10px; }
    .stAlert p { font-size: 16px !important; font-weight: bold !important; }
    
    /* 인베스팅닷컴 스타일 기간별 수익률 격자 박스 */
    .return-box {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
    }
    .return-title { font-size: 12px; color: #848e9c; margin-bottom: 5px; }
    .return-value { font-size: 16px; font-weight: bold; }
    .pos-val { color: #ff4a5a; }
    .neg-val { color: #28a745; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🦅 역발상 판독기 실전 매매 컨트롤 타워 v4.5</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">v4.2의 이상적인 화면 순서를 기반으로 NFCI·RSI 툴팁 설명 및 국내 지수와 기간별 수익률 레이아웃을 완벽 통합한 버전</div>', unsafe_allow_html=True)

# --- 💡 지표별 마우스 오버(툴팁)용 도움말 텍스트 정의 ---
help_bb = "미국 개인투자자협회(AAII) 낙관론(Bull)과 비관론(Bear)의 차이 값입니다.\n• 5점(광기): +30% 이상 | 4점(과열): +20% ~ +30% | 3점(중립): -20% ~ +20% | 2점(불안): -30% ~ -20% | 1점(공포): -30% 미만 *매수타이밍 good*"
help_pc = "하락 배팅 푸트옵션과 상승 배팅 콜옵션의 비율입니다.\n• 5점(광기): 0.4 이하 | 4점(과열): 0.4~0.5 | 3점(중립): 0.5 ~ 1.0 | 2점(불안): 1.0 ~ 1.2 | 1점(공포): 1.2 이상"
help_margin = "주식 신용융자(Margin Debt)의 전년대비 증가율입니다.\n• 5점(광기): +40% 이상 | 4점(과열): +20% ~ +40% | 3점(중립): -20% ~ +20% | 2점(불안): -30% ~ -20% | 1점(공포): -30% 미만"
help_vix = "S&P 500 옵션 기반 변동성(공포) 지수입니다.\n• 5점(광기): 15 이하 | 4점(과열): 15 ~ 20 | 3점(중립): 20 ~ 30 | 2점(불안): 30 ~ 40 | 1점(공포): 40 이상"
help_hy = "부실 기업 채권 금리와 국채 금리의 차이입니다.\n• 5점(광기): 3% 이하 | 4점(과열): 박스권 하단(3% ~ 3.5%) | 3점(중립): 3% ~ 5% 박스권 | 2점(불안): 5% 돌파 상승세 | 1점(공포): 5% 이상 폭등 후 하락 전환(진바닥) *7%이상 추가매수 금지*"
help_nfci = "시카고 연준 발표 주간 전국금융상황지수입니다.\n• 0 이상(양수): 금융 시스템 스트레스 및 신용 경색 위험 고조\n• 0 이하(음수): 유동성이 풍부하고 리스크가 낮은 안정적 중기 투자 환경"
help_rsi = "최근 14일간 주가 상승/하락 압력의 강도를 나타내는 단기 기술적 지표입니다.\n• 70 이상: 탐욕 구간 (과매수 단기 고점)\n• 30 이하: 투매 완료 구간 (과매도 기술적 바닥) *숫자가 작을수록 금융안정*"

# --- 데이터 로드 (정확한 수익률 계산을 위해 5년 데이터 패치) ---
@st.cache_data(ttl=14400)
def load_v45_data():
    tickers = {
        "SP500": "SPY", "NASDAQ": "QQQ", "SOXX": "SOXX", "SCHD": "SCHD",
        "GOLD": "GC=F", "FINANCIAL": "XLF", "ENERGY": "XLE",
        "DXY": "DX-Y.NYB", "USD_KRW": "KRW=X", "VIX": "^VIX",
        "QQQ": "QQQ", "QLD": "QLD",
        "KOSPI": "^KS11", "KOSDAQ": "^KQ11"  # 국내 지수 라인업 추가
    }
    yf_raw = {}
    for name, tk in tickers.items():
        df = yf.download(tk, period="5y", interval="1d")
        if not df.empty: yf_raw[name] = df
    return yf_raw

with st.spinner("글로벌 및 국내 금융 시장 데이터를 동기화하는 중..."):
    yf_data = load_v45_data()

if "SP500" in yf_data and "VIX" in yf_data:
    # ---------------------------------------------------------
    # 🛠️ 사이드바 조작 영역 (NFCI, RSI 수동 컨트롤러 툴팁 장착)
    # ---------------------------------------------------------
    st.sidebar.markdown("### ⚙️ 역발상 지표 수동 입력 및 검증")
    
    bb_spread_input = st.sidebar.slider("Bull/Bear Spread (%)", min_value=-50, max_value=50, value=-15, step=1, help=help_bb)
    if bb_spread_input >= 30: bb_score, bb_status = 5, "광기 🔴"
    elif bb_spread_input >= 20: bb_score, bb_status = 4, "과열 🟠"
    elif bb_spread_input >= -20: bb_score, bb_status = 3, "중립 🟡"
    elif bb_spread_input >= -30: bb_score, bb_status = 2, "불안 🔵"
    else: bb_score, bb_status = 1, "공포 🟢"

    facing_pc_ratio_input = st.sidebar.slider("Put/Call Ratio", min_value=0.3, max_value=2.0, value=0.8, step=0.05, help=help_pc)
    if facing_pc_ratio_input <= 0.4: pc_score, pc_status = 5, "광기 🔴"
    elif facing_pc_ratio_input <= 0.5: pc_score, pc_status = 4, "과열 🟠"
    elif facing_pc_ratio_input <= 1.0: pc_score, pc_status = 3, "중립 🟡"
    elif facing_pc_ratio_input <= 1.2: pc_score, pc_status = 2, "불안 🔵"
    else: pc_score, pc_status = 1, "공포 🟢"

    margin_debt_input = st.sidebar.slider("Margin Debt 전년대비 증가율 (%)", min_value=-40, max_value=60, value=5, step=5, help=help_margin)
    if margin_debt_input >= 40: margin_score, margin_status = 5, "광기 🔴"
    elif margin_debt_input >= 20: margin_score, margin_status = 4, "과열 🟠"
    elif margin_debt_input >= -20: margin_score, margin_status = 3, "중립 🟡"
    elif margin_debt_input >= -30: margin_score, margin_status = 2, "불안 🔵"
    else: margin_score, margin_status = 1, "공포 🟢"

    vix_curr = (yf_data["VIX"]['Close'].iloc[:, 0] if isinstance(yf_data["VIX"]['Close'], pd.DataFrame) else yf_data["VIX"]['Close']).iloc[-1]
    if vix_curr <= 15: vix_score, vix_status = 5, "광기 🔴"
    elif vix_curr <= 20: vix_score, vix_status = 4, "과열 🟠"
    elif vix_curr <= 30: vix_score, vix_status = 3, "중립 🟡"
    elif vix_curr <= 40: vix_score, vix_status = 2, "불안 🔵"
    else: vix_score, vix_status = 1, "공포 🟢"

    hy_input = st.sidebar.slider("High-Yield Spread (%)", min_value=2.0, max_value=10.0, value=3.4, step=0.1, help=help_hy)
    if hy_input <= 3.0: hy_score, hy_status = 5, "광기 🔴"
    elif hy_input <= 3.5: hy_score, hy_status = 4, "과열 🟠"
    elif hy_input <= 5.0: hy_score, hy_status = 3, "중립 🟡"
    elif hy_input <= 6.0: hy_score, hy_status = 2, "불안 🔵"
    else: hy_score, hy_status = 1, "공포 🟢"

    # [요구사항 1] 사이드바 내 NFCI, RSI 조작 시 물음표 아이콘 마우스 오버 툴팁 작동 지정
    nfci_input = st.sidebar.slider("NFCI (전국금융상황지수)", min_value=-1.0, max_value=3.0, value=-0.5, step=0.1, help=help_nfci)
    rsi_input = st.sidebar.slider("RSI (초단기 상대강도지수)", min_value=10, max_value=90, value=50, step=1, help=help_rsi)

    total_score = (bb_score + pc_score + margin_score + vix_score + hy_score) / 5

    # ---------------------------------------------------------
    # 🎯 [화면순서 복원 - 섹션 1]: 종합 계기판 & 테이블 결론
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">📊 1. 역발상 판독기 메인 컨트롤 패널</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1.1, 1.9])
    
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = total_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "종합 심리 판정", 'font': {'size': 16, 'color': "white"}},
            gauge = {
                'axis': {'range': [1, 5]}, 'bar': {'color': "#ffffff", 'thickness': 0.18},
                'steps': [
                    {'range': [1, 1.8], 'color': '#10B981'}, {'range': [1.8, 2.6], 'color': '#3B82F6'},
                    {'range': [2.6, 3.4], 'color': '#FBBF24'}, {'range': [3.4, 4.2], 'color': '#F97316'},
                    {'range': [4.2, 5.0], 'color': '#EF4444'}
                ],
            }
        ))
        fig_gauge.update_layout(template="plotly_dark", height=240, margin=dict(l=15,r=15,t=30,b=15))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        score_df = pd.DataFrame({
            "💡 역발상 핵심 지표": [
                "Bull/Bear Spread (주간)", "Put/Call Ratio (일간)", 
                "Margin Debt 증가율 (월간)", "VIX 공포지수 (자동)", "High-Yield 스프레드 (자동)"
            ],
            "현재 수치": [f"{bb_spread_input}%", f"{facing_pc_ratio_input}", f"{margin_debt_input}%", f"{vix_curr:.2f}", f"{hy_input}%"],
            "판단 구간": [bb_status, pc_status, margin_status, vix_status, hy_status],
            "배정 점수": [f"{bb_score} / 5", f"{pc_score} / 5", f"{margin_score} / 5", f"{vix_score} / 5", f"{hy_score} / 5"]
        })
        st.table(score_df.set_index("역발상 핵심 지표 (💡마우스 올리면 기준 팝업)"))


    
    # ---------------------------------------------------------
    # 📐 [화면순서 복원 - 섹션 2]: 멀티 자산 장기 이격도 및 섹터별 상세 추세 레이더
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">📐 2. 멀티 자산 장기 이격도 및 섹터별 상세 추세 레이더</div>', unsafe_allow_html=True)
    
    # [요구사항 2] 기존 v4.2 항목에 코스피(KOSPI)와 코스닥(KOSDAQ)을 완벽 추가 편입
    assets = {
        "S&P 500": {"key": "SP500", "color": "#3B82F6"},       
        "나스닥": {"key": "NASDAQ", "color": "#00AAFF"},       
        "필라델피아 반도체 (SOXX)": {"key": "SOXX", "color": "#00FFBB"}, 
        "코스피 (KOSPI)": {"key": "KOSPI", "color": "#FFCC00"},     
        "코스닥 (KOSDAQ)": {"key": "KOSDAQ", "color": "#FF9900"},   
        "금융 섹터 (XLF)": {"key": "FINANCIAL", "color": "#A855F7"},
        "에너지 섹터 (XLE)": {"key": "ENERGY", "color": "#EF4444"},
        "SCHD (배당)": {"key": "SCHD", "color": "#10B981"},       
        "금 (안전자산)": {"key": "GOLD", "color": "#FBBF24"}
    }

    names = []
    deviations = []
    colors = []
    alerts_info = []

    for name, info in assets.items():
        df = yf_data[info["key"]].copy()
        close = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        df['SMA200'] = close.rolling(window=200).mean()
        
        curr_p = close.iloc[-1]
        sma200_curr = df['SMA200'].iloc[-1]
        sma200_prev = df['SMA200'].iloc[-5]
        
        ma_ratio = (curr_p / sma200_curr) * 100
        ma_ratio_prev = (close.iloc[-5] / df['SMA200'].iloc[-5]) * 100 if len(close) > 5 else ma_ratio
        dev = ((curr_p - sma200_curr) / sma200_curr) * 100
        
        names.append(name)
        deviations.append(dev)
        colors.append(info["color"])
        
        status_msg = []
        if dev >= 15.0: status_msg.append("⚠️ 이격도 15% 이상: 단기 과열")
        if ma_ratio <= 30.0 and ma_ratio > ma_ratio_prev: status_msg.append("🔥 이평선 비중 바닥 탈출: [역발상 매수 타이밍]")
            
        if status_msg: alerts_info.append(f"**[{name}]** " + " / ".join(status_msg))

    fig_dev = go.Figure()
    fig_dev.add_trace(go.Bar(
        x=names, y=deviations, marker_color=colors,
        text=[f"{d:.2f}%" for d in deviations], textposition='auto'
    ))
    fig_dev.add_hline(y=15.0, line_dash="dash", line_color="red", annotation_text="단기 과열 기준 (15%)")
    fig_dev.add_hline(y=0.0, line_color="white", line_width=1)
    fig_dev.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=20, b=20))
    
    c_graph, c_msg = st.columns([2.2, 1])
    with c_graph:
        st.plotly_chart(fig_dev, use_container_width=True)
    with c_msg:
        st.markdown("#### 🚨 특이사항 진단 가이드")
        if alerts_info:
            for alert in alerts_info: st.error(alert)
        else:
            st.info("현재 특이 과열 및 역발상 시그널이 발동한 자산이 없습니다.")

    # 📊 섹터별 세부 추적 차트 컨텐츠 영역
    st.markdown("#### 🔍 섹터별 장기 추세선 및 기간별 수익률 실시간 조회")
    selected_asset = st.selectbox("추세를 추적할 자산(섹터)을 선택하세요:", list(assets.keys()))
    
    if selected_asset:
        target_key = assets[selected_asset]["key"]
        df_trend = yf_data[target_key].copy()
        close_trend = df_trend['Close'].iloc[:, 0] if isinstance(df_trend['Close'], pd.DataFrame) else df_trend['Close']
        
        df_trend['SMA200'] = close_trend.rolling(window=200).mean()
        df_trend['SMA20%'] = close_trend.rolling(window=20).mean() # 20일 이동평균선 기본 탑재
        
        df_chart = df_trend.iloc[-252:]
        close_chart = close_trend.iloc[-252:]
        
        fig_selected = go.Figure()
        fig_selected.add_trace(go.Scatter(x=df_chart.index, y=close_chart, name="현재 종가", line=dict(color="#00FFBB", width=2.5)))
        fig_selected.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20%'], name="20일 이동평균선", line=dict(color="#00AAFF", width=1.5)))
        fig_selected.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA200'], name="200일 이동평균선", line=dict(color="#FF5555", width=1.5, dash="dash")))
        fig_selected.update_layout(template="plotly_dark", height=280, title=f"📈 {selected_asset} 실시간 흐름 (종가 + 20일선 + 200일선)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_selected, use_container_width=True)

        # [요구사항 2-하단] 인베스팅 스타일의 기간별 실시간 수익률 격자 레이아웃 전면 배치
        st.markdown("##### 📊 최근 기간별 실시간 누적 수익률 스냅샷")
        curr_val = close_trend.iloc[-1]
        
        def get_return(days_ago):
            target_date = df_trend.index[-1] - timedelta(days=days_ago)
            idx = df_trend.index.get_indexer([target_date], method='pad')[0]
            past_val = close_trend.iloc[idx]
            return ((curr_val - past_val) / past_val) * 100

        ret_1d = ((curr_val - close_trend.iloc[-2]) / close_trend.iloc[-2]) * 100
        ret_1w = get_return(7)
        ret_1m = get_return(30)
        ret_3m = get_return(90)
        ret_6m = get_return(180)
        ret_1y = get_return(365)
        
        c_r1, c_r2, c_r3, c_r4, c_r5, c_r6 = st.columns(6)
        periods = [("1일", ret_1d), ("1주", ret_1w), ("1달", ret_1m), ("3달", ret_3m), ("6달", ret_6m), ("1년", ret_1y)]
        cols = [c_r1, c_r2, c_r3, c_r4, c_r5, c_r6]
        
        for col, (p_title, p_val) in zip(cols, periods):
            with col:
                val_class = "pos-val" if p_val >= 0 else "neg-val"
                sign = "+" if p_val >= 0 else ""
                st.markdown(f"""
                <div class="return-box">
                    <div class="return-title">{p_title}</div>
                    <div class="return-value {val_class}">{sign}{p_val:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 📉 [화면순서 복원 - 섹션 3]: 기계적 하락장 분할 매수 대응 시트 (MDD)
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">📉 3. 기계적 하락장 분할 매수 대응 시트 (MDD)</div>', unsafe_allow_html=True)
    
    mdd_targets = {
        "나스닥 (QQQ)": {"key": "QQQ", "threshold": -9.0},
        "S&P 500 지수": {"key": "SP500", "threshold": -8.0},
        "레버리지 (QLD)": {"key": "QLD", "threshold": -20.0},
        "배당성장 (SCHD)": {"key": "SCHD", "threshold": -9.0}
    }

    mdd_results = []
    for name, info in mdd_targets.items():
        df_mdd = yf_data[info["key"]].copy()
        close_mdd = df_mdd['Close'].iloc[:, 0] if isinstance(df_mdd['Close'], pd.DataFrame) else df_mdd['Close']
        
        highest_p = close_mdd.iloc[-252:].max() 
        current_p = close_mdd.iloc[-1]
        drop_rate = ((current_p - highest_p) / highest_p) * 100
        
        action_signal = "⚖️ 비중 유지 / 대기"
        if drop_rate <= info["threshold"]: action_signal = "🔥 고점 대비 기준 이하 돌파! 적극 매수 가동"
            
        mdd_results.append({
            "대응 자산 목록": name,
            "1년 최고가": f"${highest_p:,.2f}" if "SP500" not in info["key"] else f"{highest_p:,.2f}pt",
            "현재가": f"${current_p:,.2f}" if "SP500" not in info["key"] else f"{current_p:,.2f}pt",
            "고점 대비 현재 낙폭": f"{drop_rate:.2f}%",
            "지정 매수 기준선": f"{info['threshold']:.1f}% 이하",
            "실전 액션 판단": action_signal
        })

    mdd_df = pd.DataFrame(mdd_results)
    st.table(mdd_df.set_index("대응 자산 목록"))

    # ---------------------------------------------------------
    # 💵 [화면순서 복원 - 섹션 4]: 글로벌 달러지수 vs 한국 원달러 환율 디커플링 분석
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">💵 4. 글로벌 달러지수 vs 국내 환율 디커플링 레이어</div>', unsafe_allow_html=True)
    
    dxy_latest = (yf_data["DXY"]['Close'].iloc[:, 0] if isinstance(yf_data["DXY"]['Close'], pd.DataFrame) else yf_data["DXY"]['Close']).iloc[-1]
    krw_latest = (yf_data["USD_KRW"]['Close'].iloc[:, 0] if isinstance(yf_data["USD_KRW"]['Close'], pd.DataFrame) else yf_data["USD_KRW"]['Close']).iloc[-1]
    
    c_fx1, c_fx2 = st.columns([1, 2])
    with c_fx1:
        st.metric(label="글로벌 달러 인덱스 (DXY)", value=f"{dxy_latest:.2f}",
                  delta="증시 호재 환경 (100 이하)" if dxy_latest < 100 else "증시 유동성 압박 환경 (100 이상)",
                  delta_color="normal" if dxy_latest < 100 else "inverse")
        st.metric(label="원/달러 환율 (KRW)", value=f"{krw_latest:,.1f} 원")
        
    with c_fx2:
        fig_fx = make_subplots(specs=[[{"secondary_y": True}]])
        fig_fx.add_trace(go.Scatter(x=yf_data["DXY"].index[-252:], y=yf_data["DXY"]['Close'].iloc[-252:,0] if isinstance(yf_data["DXY"]['Close'], pd.DataFrame) else yf_data["DXY"]['Close'].iloc[-252:], name="달러 지수 (DXY)", line=dict(color='#00FFBB', width=2)), secondary_y=False)
        fig_fx.add_trace(go.Scatter(x=yf_data["USD_KRW"].index[-252:], y=yf_data["USD_KRW"]['Close'].iloc[-252:,0] if isinstance(yf_data["USD_KRW"]['Close'], pd.DataFrame) else yf_data["USD_KRW"]['Close'].iloc[-252:], name="원/달러 환율 (KRW)", line=dict(color='#FF5555', width=1.5, dash='dot')), secondary_y=True)
        fig_fx.update_layout(template="plotly_dark", height=220, margin=dict(l=10,r=10,t=10,b=10), showlegend=True)
        st.plotly_chart(fig_fx, use_container_width=True)

    # ---------------------------------------------------------
    # 🏦 [화면순서 복원 - 섹션 5]: 실시간 지수 우측 하단 스냅샷
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">📊 5. 실시간 국내외 주요 지수 요약 스냅샷</div>', unsafe_allow_html=True)
    c_sp, c_nas, c_kos, c_kdq = st.columns(4)
    
    with c_sp:
        sp_v = (yf_data["SP500"]['Close'].iloc[:, 0] if isinstance(yf_data["SP500"]['Close'], pd.DataFrame) else yf_data["SP500"]['Close']).iloc[-1]
        st.metric("S&P 500 지수", f"{sp_v:,.2f} pt")
    with c_nas:
        nas_v = (yf_data["NASDAQ"]['Close'].iloc[:, 0] if isinstance(yf_data["NASDAQ"]['Close'], pd.DataFrame) else yf_data["NASDAQ"]['Close']).iloc[-1]
        st.metric("나스닥 종합 지수", f"{nas_v:,.2f} pt")
    with c_kos:
        kos_v = (yf_data["KOSPI"]['Close'].iloc[:, 0] if isinstance(yf_data["KOSPI"]['Close'], pd.DataFrame) else yf_data["KOSPI"]['Close']).iloc[-1]
        st.metric("코스피 지수 (KOSPI)", f"{kos_v:,.2f} pt")
    with c_kdq:
        kdq_v = (yf_data["KOSDAQ"]['Close'].iloc[:, 0] if isinstance(yf_data["KOSDAQ"]['Close'], pd.DataFrame) else yf_data["KOSDAQ"]['Close']).iloc[-1]
        st.metric("코스닥 지수 (KOSDAQ)", f"{kdq_v:,.2f} pt")

else:
    st.error("데이터 동기화 실패")  
