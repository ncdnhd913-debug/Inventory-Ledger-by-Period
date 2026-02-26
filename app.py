import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(
    page_title="회계 수불 증감 통합 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# 커스텀 CSS - 모던 UI 디자인
# ============================================
st.markdown("""
<style>
    /* 전체 폰트 및 배경 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 100%;
    }
    
    /* 헤더 스타일 */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.85);
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 300;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fc 0%, #eef1f8 100%);
    }
    
    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.5rem;
    }
    
    .sidebar-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .sidebar-header h2 {
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
    }
    
    /* 파일 업로더 스타일 */
    .upload-section {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
    }
    
    .upload-section:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    .upload-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #374151;
        margin-bottom: 0.5rem;
    }
    
    .upload-number {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        text-align: center;
        line-height: 22px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    /* 메트릭 카드 */
    .metric-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        flex: 1;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    .metric-card .label {
        font-size: 0.85rem;
        color: #6b7280;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f2937;
    }
    
    .metric-card .delta {
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    .delta-positive { color: #dc2626; }
    .delta-negative { color: #2563eb; }
    
    /* 섹션 카드 */
    .section-card {
        background: white;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
    }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* 그룹 선택 버튼 */
    .group-btn-container {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    
    /* Streamlit 버튼 오버라이드 */
    .stButton > button {
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 500;
        border: 2px solid #e5e7eb;
        background: white;
        color: #374151;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        border-color: #667eea;
        color: #667eea;
        background: #f8f7ff;
    }
    
    .stButton > button:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
    }
    
    /* 선택된 버튼 스타일 */
    .selected-btn > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: #f8f9fc;
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        color: #6b7280;
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #667eea !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* 데이터프레임 스타일 */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    [data-testid="stDataFrame"] > div {
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    }
    
    /* 범례 뱃지 */
    .legend-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-right: 0.5rem;
    }
    
    .legend-yoy {
        background: #FEF9C3;
        color: #854d0e;
    }
    
    .legend-mom {
        background: #DBEAFE;
        color: #1e40af;
    }
    
    /* 다운로드 버튼 */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        font-weight: 600;
        border-radius: 10px;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
    }
    
    /* 정보 박스 */
    .info-box {
        background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        text-align: center;
    }
    
    .info-box p {
        color: #1e40af;
        font-size: 1rem;
        margin: 0;
    }
    
    .info-box .icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* 구분선 */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
        margin: 2rem 0;
    }
    
    /* 숨김 처리 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============================================
# 데이터 처리 함수
# ============================================
def process_inventory_data(file):
    """파일을 읽어 데이터프레임으로 변환"""
    if file is None:
        return None
    try:
        df_raw = pd.read_csv(file, header=None) if file.name.endswith('.csv') else pd.read_excel(file, header=None)
        header_main = df_raw.iloc[0].ffill()
        header_sub = df_raw.iloc[1].fillna('')
        new_cols = []
        for m, s in zip(header_main, header_sub):
            col_name = f"{m}_{s}".strip("_") if s != '' else str(m)
            new_cols.append(col_name)
        df = df_raw.iloc[2:].copy()
        df.columns = new_cols
        for col in ['품목계정그룹', '품목코드', '품목명']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        df = df[df['품목코드'] != 'nan']
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"⚠️ {file.name} 처리 중 오류: {e}")
        return None


def add_total_row(df, numeric_cols, label_col='품목명'):
    """합계 행 추가"""
    if df.empty:
        return df
    totals = df[numeric_cols].sum()
    total_data = {col: totals[col] for col in numeric_cols}
    total_data[label_col] = '📊 합계'
    for col in df.columns:
        if col not in total_data:
            total_data[col] = ""
    return pd.concat([df, pd.DataFrame([total_data])], ignore_index=True)


def style_financial_df(df, yoy_cols, mom_cols, diff_cols):
    """재무 데이터프레임 스타일링"""
    if df.empty:
        return df
    return df.style.format("{:,.0f}", subset=yoy_cols + mom_cols + diff_cols)\
        .set_properties(**{'background-color': '#FFFDE7', 'color': '#1f2937'}, subset=yoy_cols)\
        .set_properties(**{'background-color': '#EFF6FF', 'color': '#1f2937'}, subset=mom_cols)\
        .map(lambda x: 'color: #dc2626; font-weight: 600;' if x > 0 else ('color: #2563eb; font-weight: 600;' if x < 0 else 'color: #1f2937'), subset=diff_cols)


def format_currency(value):
    """통화 포맷팅"""
    if value >= 1e8:
        return f"{value/1e8:,.1f}억"
    elif value >= 1e4:
        return f"{value/1e4:,.0f}만"
    else:
        return f"{value:,.0f}"


# ============================================
# 사이드바
# ============================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h2>📅 분석 기준 설정</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        target_year = st.number_input("기준 년도", value=2026, min_value=2020, max_value=2030)
    with col2:
        X = st.selectbox("기준 월", options=list(range(1, 13)), index=0)
    
    prev_X = X - 1 if X > 1 else 12
    
    st.markdown("---")
    st.markdown("### 📁 데이터 파일 업로드")
    st.caption("분석에 필요한 5개 파일을 업로드해주세요")
    
    upload_configs = [
        (f"당월 ({X}월)", "curr_m"),
        (f"전월 ({prev_X}월)", "prev_m"),
        (f"당기 누적 (1~{X}월)", "curr_ytd"),
        (f"전기 동기 누적", "prev_ytd"),
        (f"전기 전체 (1~12월)", "prev_full")
    ]
    
    files = []
    for i, (label, key) in enumerate(upload_configs, 1):
        st.markdown(f"""
        <div class="upload-label">
            <span class="upload-number">{i}</span>{label}
        </div>
        """, unsafe_allow_html=True)
        f = st.file_uploader(f"파일 {i}", type=['csv', 'xlsx'], key=key, label_visibility="collapsed")
        files.append(f)
    
    f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full = files


# ============================================
# 메인 콘텐츠
# ============================================
# 헤더
st.markdown("""
<div class="main-header">
    <h1>📊 Financial Inventory Variance Analysis</h1>
    <p>회계 결산 및 제조/매출원가 증감 분석 시스템</p>
</div>
""", unsafe_allow_html=True)

# 파일 업로드 확인
if all(f is not None for f in files):
    dfs = [process_inventory_data(f) for f in files]
    d_curr_m, d_prev_m, d_curr_ytd, d_prev_ytd, d_prev_full = dfs
    
    if all(d is not None for d in dfs):
        # 데이터 병합
        all_items = pd.concat([d[['품목코드', '품목명', '단위', '품목계정그룹']] for d in dfs]).drop_duplicates('품목코드')
        
        comp_all = all_items.merge(d_curr_m[['품목코드', '생산출고_금액', '판매출고_금액', '기말재고_금액']], on='품목코드', how='left')\
                            .rename(columns={'생산출고_금액':'당월_생산출고', '판매출고_금액':'당월_판매출고', '기말재고_금액':'당월말_재고'})
        comp_all = comp_all.merge(d_prev_m[['품목코드', '생산출고_금액', '판매출고_금액']], on='품목코드', how='left')\
                            .rename(columns={'생산출고_금액':'전월_생산출고', '판매출고_금액':'전월_판매출고'})
        comp_all = comp_all.merge(d_curr_ytd[['품목코드', '생산출고_금액', '판매출고_금액']], on='품목코드', how='left')\
                            .rename(columns={'생산출고_금액':'당기누적_생산출고', '판매출고_금액':'당기누적_판매출고'})
        comp_all = comp_all.merge(d_prev_ytd[['품목코드', '생산출고_금액', '판매출고_금액']], on='품목코드', how='left')\
                            .rename(columns={'생산출고_금액':'전기동기_생산출고', '판매출고_금액':'전기동기_판매출고'})
        comp_all = comp_all.merge(d_prev_full[['품목코드', '기말재고_금액']], on='품목코드', how='left')\
                            .rename(columns={'기말재고_금액':'전기말_재고'}).fillna(0)
        
        # 차이 계산
        comp_all['재고_증감'] = comp_all['당월말_재고'] - comp_all['전기말_재고']
        comp_all['판매_YoY증감'] = comp_all['당기누적_판매출고'] - comp_all['전기동기_판매출고']
        comp_all['판매_MoM증감'] = comp_all['당월_판매출고'] - comp_all['전월_판매출고']
        comp_all['생산_YoY증감'] = comp_all['당기누적_생산출고'] - comp_all['전기동기_생산출고']
        comp_all['생산_MoM증감'] = comp_all['당월_생산출고'] - comp_all['전월_생산출고']
        
        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        
        # ========================================
        # 주요 지표 요약 카드
        # ========================================
        total_inv_curr = comp_all['당월말_재고'].sum()
        total_inv_prev = comp_all['전기말_재고'].sum()
        total_inv_diff = total_inv_curr - total_inv_prev
        total_sales_ytd = comp_all['당기누적_판매출고'].sum()
        total_sales_prev = comp_all['전기동기_판매출고'].sum()
        total_prod_ytd = comp_all['당기누적_생산출고'].sum()
        
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📈 핵심 지표 현황</div>', unsafe_allow_html=True)
        
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            delta_color = "delta-positive" if total_inv_diff > 0 else "delta-negative"
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">당월말 총재고</div>
                <div class="value">{format_currency(total_inv_curr)}</div>
                <div class="delta {delta_color}">전기대비 {format_currency(abs(total_inv_diff))} {'증가' if total_inv_diff > 0 else '감소'}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m2:
            sales_diff = total_sales_ytd - total_sales_prev
            delta_color = "delta-positive" if sales_diff > 0 else "delta-negative"
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">당기 매출원가 누적</div>
                <div class="value">{format_currency(total_sales_ytd)}</div>
                <div class="delta {delta_color}">YoY {format_currency(abs(sales_diff))} {'증가' if sales_diff > 0 else '감소'}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m3:
            prod_diff = total_prod_ytd - comp_all['전기동기_생산출고'].sum()
            delta_color = "delta-positive" if prod_diff > 0 else "delta-negative"
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">당기 제조원가 누적</div>
                <div class="value">{format_currency(total_prod_ytd)}</div>
                <div class="delta {delta_color}">YoY {format_currency(abs(prod_diff))} {'증가' if prod_diff > 0 else '감소'}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with m4:
            item_count = len(comp_all)
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">분석 품목 수</div>
                <div class="value">{item_count:,}개</div>
                <div class="delta" style="color: #6b7280;">{target_year}년 {X}월 기준</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ========================================
        # 계정별 상세 분석
        # ========================================
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 계정별 상세 차이 분석</div>', unsafe_allow_html=True)
        
        # 그룹 선택 버튼
        if 'current_group' not in st.session_state:
            st.session_state.current_group = '제품'
        
        btn_cols = st.columns(len(groups))
        for i, group in enumerate(groups):
            is_selected = st.session_state.current_group == group
            with btn_cols[i]:
                if is_selected:
                    st.markdown('<div class="selected-btn">', unsafe_allow_html=True)
                if st.button(f"📦 {group}" if group in ['제품', '상품'] else f"🔧 {group}" if group == '반제품' else f"🧱 {group}", 
                           key=f"btn_{group}", use_container_width=True):
                    st.session_state.current_group = group
                    st.rerun()
                if is_selected:
                    st.markdown('</div>', unsafe_allow_html=True)
        
        target_group = st.session_state.current_group
        group_df = comp_all[comp_all['품목계정그룹'] == target_group]
        
        if not group_df.empty:
            tab_names = ["🏛️ 기말재고 차이"]
            if target_group != '반제품':
                tab_names.append("💰 매출원가 차이")
            if target_group in ['원재료', '부재료']:
                tab_names.append("🛠️ 제조원가 차이")
            
            tabs = st.tabs(tab_names)
            
            text_align_cfg = {
                "품목코드": st.column_config.TextColumn("품목코드", width="medium"),
                "품목명": st.column_config.TextColumn("품목명", width="large"),
            }
            
            with tabs[0]:
                view1 = group_df[(group_df['전기말_재고'] != 0) | (group_df['당월말_재고'] != 0)][
                    ['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_증감']
                ].sort_values('재고_증감', ascending=False)
                
                if not view1.empty:
                    view1_total = add_total_row(view1, ['전기말_재고', '당월말_재고', '재고_증감'])
                    styled_view1 = view1_total.style.format("{:,.0f}", subset=['전기말_재고', '당월말_재고', '재고_증감'])\
                        .map(lambda x: 'color: #dc2626; font-weight: 600;' if x > 0 else ('color: #2563eb; font-weight: 600;' if x < 0 else 'color: #1f2937'), subset=['재고_증감'])
                    st.dataframe(styled_view1, use_container_width=True, hide_index=True, 
                               column_config=text_align_cfg, height=400)
            
            if target_group != '반제품':
                with tabs[1]:
                    st.markdown("""
                    <div style="margin-bottom: 1rem;">
                        <span class="legend-badge legend-yoy">🟡 전기(누적) 비교</span>
                        <span class="legend-badge legend-mom">🔵 전월(월간) 비교</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    view2 = group_df[(group_df['당기누적_판매출고'] != 0) | (group_df['전기동기_판매출고'] != 0) | (group_df['당월_판매출고'] != 0)]\
                        [['품목코드', '품목명', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']].copy()
                    view2.columns = ['품목코드', '품목명', '당기누적', '전기누적', 'YoY 증감', '당월', '전월', 'MoM 증감']
                    view2 = view2.sort_values('YoY 증감', ascending=False)
                    
                    view2_total = add_total_row(view2, view2.columns[2:].tolist())
                    styled_view2 = style_financial_df(view2_total, 
                                                      ['당기누적', '전기누적', 'YoY 증감'],
                                                      ['당월', '전월', 'MoM 증감'],
                                                      ['YoY 증감', 'MoM 증감'])
                    st.dataframe(styled_view2, use_container_width=True, hide_index=True, 
                               column_config=text_align_cfg, height=400)
            
            if target_group in ['원재료', '부재료']:
                with tabs[len(tab_names)-1]:
                    cost_label = "원재료비" if target_group == '원재료' else "부재료비"
                    
                    st.markdown(f"""
                    <div style="margin-bottom: 1rem;">
                        <span class="legend-badge legend-yoy">🟡 전기({cost_label} 누적)</span>
                        <span class="legend-badge legend-mom">🔵 전월({cost_label} 월간)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    view3 = group_df[(group_df['당기누적_생산출고'] != 0) | (group_df['전기동기_생산출고'] != 0) | (group_df['당월_생산출고'] != 0)]\
                        [['품목코드', '품목명', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']].copy()
                    view3.columns = ['품목코드', '품목명', '당기누적', '전기누적', 'YoY 증감', '당월', '전월', 'MoM 증감']
                    view3 = view3.sort_values('YoY 증감', ascending=False)
                    
                    view3_total = add_total_row(view3, view3.columns[2:].tolist())
                    styled_view3 = style_financial_df(view3_total, 
                                                      ['당기누적', '전기누적', 'YoY 증감'],
                                                      ['당월', '전월', 'MoM 증감'],
                                                      ['YoY 증감', 'MoM 증감'])
                    st.dataframe(styled_view3, use_container_width=True, hide_index=True, 
                               column_config=text_align_cfg, height=400)
        else:
            st.info(f"📭 '{target_group}' 계정에 해당하는 데이터가 없습니다.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ========================================
        # 계정별 총괄 요약
        # ========================================
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📑 계정별 총괄 요약</div>', unsafe_allow_html=True)
        
        summary_agg = comp_all.groupby('품목계정그룹').agg({
            '전기말_재고': 'sum', '당월말_재고': 'sum', '재고_증감': 'sum',
            '당기누적_판매출고': 'sum', '전기동기_판매출고': 'sum', '판매_YoY증감': 'sum',
            '당기누적_생산출고': 'sum', '전기동기_생산출고': 'sum', '생산_YoY증감': 'sum'
        }).reset_index()
        
        summary_agg['품목계정그룹'] = pd.Categorical(summary_agg['품목계정그룹'], categories=groups, ordered=True)
        summary_agg = summary_agg.sort_values('품목계정그룹')
        
        summary_tabs = st.tabs(["🏛️ 기말재고", "💰 매출원가", "🛠️ 제조원가"])
        
        summary_cfg = {"품목계정그룹": st.column_config.TextColumn("계정그룹", width="medium")}
        
        with summary_tabs[0]:
            sum_view1 = summary_agg[['품목계정그룹', '전기말_재고', '당월말_재고', '재고_증감']]
            sum_view1_total = add_total_row(sum_view1, sum_view1.columns[1:].tolist(), label_col='품목계정그룹')
            st.dataframe(
                sum_view1_total.style.format("{:,.0f}", subset=sum_view1.columns[1:].tolist())
                .map(lambda x: 'color: #dc2626; font-weight: 600;' if x > 0 else ('color: #2563eb; font-weight: 600;' if x < 0 else 'color: #1f2937'), subset=['재고_증감']),
                use_container_width=True, hide_index=True, column_config=summary_cfg
            )
        
        with summary_tabs[1]:
            sum_view2 = summary_agg[['품목계정그룹', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감']]
            sum_view2.columns = ['품목계정그룹', '당기누적', '전기동기', 'YoY 증감']
            sum_view2_total = add_total_row(sum_view2, sum_view2.columns[1:].tolist(), label_col='품목계정그룹')
            st.dataframe(
                sum_view2_total.style.format("{:,.0f}", subset=sum_view2.columns[1:].tolist())
                .map(lambda x: 'color: #dc2626; font-weight: 600;' if x > 0 else ('color: #2563eb; font-weight: 600;' if x < 0 else 'color: #1f2937'), subset=['YoY 증감']),
                use_container_width=True, hide_index=True, column_config=summary_cfg
            )
        
        with summary_tabs[2]:
            sum_view3 = summary_agg[['품목계정그룹', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감']]
            sum_view3.columns = ['품목계정그룹', '당기누적', '전기동기', 'YoY 증감']
            sum_view3_total = add_total_row(sum_view3, sum_view3.columns[1:].tolist(), label_col='품목계정그룹')
            st.dataframe(
                sum_view3_total.style.format("{:,.0f}", subset=sum_view3.columns[1:].tolist())
                .map(lambda x: 'color: #dc2626; font-weight: 600;' if x > 0 else ('color: #2563eb; font-weight: 600;' if x < 0 else 'color: #1f2937'), subset=['YoY 증감']),
                use_container_width=True, hide_index=True, column_config=summary_cfg
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ========================================
        # 다운로드 섹션
        # ========================================
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                comp_all.to_excel(writer, index=False, sheet_name='종합분석')
            
            st.download_button(
                label="📥 전체 분석 데이터 다운로드 (Excel)",
                data=output.getvalue(),
                file_name=f"Inventory_Analysis_{target_year}_{X}M.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # 파일 미업로드 상태
    st.markdown("""
    <div class="info-box">
        <div class="icon">📂</div>
        <p><strong>분석을 시작하려면 사이드바에서 5개의 파일을 모두 업로드해주세요.</strong></p>
        <p style="font-size: 0.9rem; color: #64748b; margin-top: 0.5rem;">
            당월, 전월, 당기 누적, 전기 동기 누적, 전기 전체 데이터가 필요합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 업로드 가이드
    st.markdown("---")
    st.markdown("### 📖 파일 업로드 가이드")
    
    guide_cols = st.columns(5)
    guides = [
        ("1️⃣", "당월 데이터", "분석 기준월의 수불 데이터"),
        ("2️⃣", "전월 데이터", "직전월의 수불 데이터"),
        ("3️⃣", "당기 누적", "당해연도 1월~기준월 누적"),
        ("4️⃣", "전기 동기", "전년도 동기간 누적"),
        ("5️⃣", "전기 전체", "전년도 연간 전체 데이터"),
    ]
    
    for col, (num, title, desc) in zip(guide_cols, guides):
        with col:
            st.markdown(f"""
            <div style="background: white; padding: 1rem; border-radius: 12px; text-align: center; 
                        border: 1px solid #e5e7eb; height: 120px;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{num}</div>
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 0.3rem;">{title}</div>
                <div style="font-size: 0.8rem; color: #6b7280;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
