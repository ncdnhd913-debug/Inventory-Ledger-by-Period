import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 통합 분석", layout="wide")

# CSS를 통한 UI 및 정렬 보강
st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 95%; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 5px; }
    /* 테이블 헤더 가운데 정렬 강제 (Streamlit 버전별 상이할 수 있음) */
    th { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Financial Inventory Variance Analysis")
st.markdown("회계 결산 및 제조/매출원가 증감 분석을 위한 통합 시스템입니다.")

# 1. 데이터 전처리 함수
def process_inventory_data(file):
    if file is None: return None
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

# 합계 행 추가 함수
def add_total_row(df, numeric_cols, label_col='품목명'):
    if df.empty: return df
    totals = df[numeric_cols].sum()
    total_data = {col: totals[col] for col in numeric_cols}
    total_data[label_col] = '▶ 합계 (TOTAL)'
    for col in df.columns:
        if col not in total_data:
            total_data[col] = ""
    return pd.concat([df, pd.DataFrame([total_data])], ignore_index=True)

# 시각적 스타일링 함수 (연한 색상 및 가운데 정렬 추가)
def style_financial_df(df, yoy_cols, mom_cols, diff_cols, text_cols):
    if df.empty: return df
    
    return df.style.format("{:,.0f}", subset=[c for c in df.columns if c not in text_cols and df[c].dtype != object])\
        .set_properties(**{'text-align': 'center'}, subset=text_cols)\
        .set_properties(**{'background-color': '#FFFDE7', 'color': 'black'}, subset=yoy_cols)\
        .set_properties(**{'background-color': '#F1F8FF', 'color': 'black'}, subset=mom_cols)\
        .map(lambda x: 'color: #D32F2F; font-weight: bold;' if x > 0 else ('color: #1976D2; font-weight: bold;' if x < 0 else 'color: black'), subset=diff_cols)

# 2. 사이드바 설정
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    X = st.selectbox("기준 월(X)", options=list(range(1, 13)), index=0)
    prev_X = X - 1 if X > 1 else 12
    st.divider()
    st.subheader("📁 파일 업로드")
    f_curr_m = st.file_uploader(f"(1) 당월 ({X}월)", type=['csv', 'xlsx'])
    f_prev_m = st.file_uploader(f"(2) 전월 ({prev_X}월)", type=['csv', 'xlsx'])
    f_curr_ytd = st.file_uploader(f"(3) 당기 누적 (1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_ytd = st.file_uploader(f"(4) 전기 동기 누적 (전기 1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_full = st.file_uploader(f"(5) 전기 전체 (전기 1월~12월)", type=['csv', 'xlsx'])

# 3. 메인 로직
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
if all(f is not None for f in files):
    dfs = [process_inventory_data(f) for f in files]
    d_curr_m, d_prev_m, d_curr_ytd, d_prev_ytd, d_prev_full = dfs

    if all(d is not None for d in dfs):
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

        comp_all['재고_증감'] = comp_all['당월말_재고'] - comp_all['전기말_재고']
        comp_all['판매_YoY증감'] = comp_all['당기누적_판매출고'] - comp_all['전기동기_판매출고']
        comp_all['판매_MoM증감'] = comp_all['당월_판매출고'] - comp_all['전월_판매출고']
        comp_all['생산_YoY증감'] = comp_all['당기누적_생산출고'] - comp_all['전기동기_생산출고']
        comp_all['생산_MoM증감'] = comp_all['당월_생산출고'] - comp_all['전월_생산출고']

        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        st.subheader("📋 계정별 상세 차이 분석")
        btn_cols = st.columns(len(groups))
        if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
        for i, group in enumerate(groups):
            if btn_cols[i].button(group, use_container_width=True):
                st.session_state.current_group = group
        
        target_group = st.session_state.current_group
        group_df = comp_all[comp_all['품목계정그룹'] == target_group]
        text_info_cols = ['품목코드', '품목명', '단위']

        if not group_df.empty:
            tab_names = ["🏛️ 기말재고 차이분석"]
            if target_group != '반제품': tab_names.append("💰 매출원가 차이분석")
            if target_group in ['원재료', '부재료']: tab_names.append("🛠️ 제조원가 차이분석")
            
            tabs = st.tabs(tab_names)
            
            # 1) 기말재고
            with tabs[0]:
                view1 = group_df[(group_df['전기말_재고'] != 0) | (group_df['당월말_재고'] != 0)][['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_증감']].sort_values('재고_증감', ascending=False)
                if not view1.empty:
                    view1_total = add_total_row(view1, ['전기말_재고', '당월말_재고', '재고_증감'])
                    styled_view1 = style_financial_df(view1_total, ['전기말_재고'], ['당월말_재고'], ['재고_증감'], ['품목코드', '품목명'])
                    st.dataframe(styled_view1, use_container_width=True, hide_index=True)
                else: st.info("재고 변동 내역이 없습니다.")

            # 2) 매출원가
            if target_group != '반제품':
                with tabs[1]:
                    view2 = group_df[(group_df['당기누적_판매출고'] != 0) | (group_df['전기동기_판매출고'] != 0) | (group_df['당월_판매출고'] != 0)]\
                        [['품목코드', '품목명', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']].copy()
                    view2.columns = ['품목코드', '품목명', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
                    view2 = view2.sort_values('전기대비 차이증감', ascending=False)
                    st.markdown("<small>🟡 **전기(누적)** | 🔵 **전월(월간)**</small>", unsafe_allow_html=True)
                    view2_total = add_total_row(view2, view2.columns[2:])
                    styled_view2 = style_financial_df(view2_total, 
                                                      ['당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감'],
                                                      ['당월_매출원가', '전월_매출원가', '전월대비 차이증감'],
                                                      ['전기대비 차이증감', '전월대비 차이증감'], ['품목코드', '품목명'])
                    st.dataframe(styled_view2, use_container_width=True, hide_index=True)

            # 3) 제조원가
            if target_group in ['원재료', '부재료']:
                with tabs[len(tab_names)-1]:
                    cost_label = "원재료비" if target_group == '원재료' else "부재료비"
                    view3 = group_df[(group_df['당기누적_생산출고'] != 0) | (group_df['전기동기_생산출고'] != 0) | (group_df['당월_생산출고'] != 0)]\
                        [['품목코드', '품목명', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']].copy()
                    view3.columns = ['품목코드', '품목명', f'당기누적_{cost_label}', f'전기누적_{cost_label}', '전기대비 차이증감', f'당월_{cost_label}', f'전월_{cost_label}', '전월대비 차이증감']
                    view3 = view3.sort_values('전기대비 차이증감', ascending=False)
                    st.markdown(f"<small>🟡 **전기({cost_label} 누적)** | 🔵 **전월({cost_label} 월간)**</small>", unsafe_allow_html=True)
                    view3_total = add_total_row(view3, view3.columns[2:])
                    styled_view3 = style_financial_df(view3_total, 
                                                      [f'당기누적_{cost_label}', f'전기누적_{cost_label}', '전기대비 차이증감'],
                                                      [f'당월_{cost_label}', f'전월_{cost_label}', '전월대비 차이증감'],
                                                      ['전기대비 차이증감', '전월대비 차이증감'], ['품목코드', '품목명'])
                    st.dataframe(styled_view3, use_container_width=True, hide_index=True)
        else:
            st.warning(f"'{target_group}' 계정에 유효한 데이터가 없습니다.")

        # --- 총괄 요약 보고서 (재구조화) ---
        st.divider()
        st.subheader("📑 계정별 총괄 요약 보고서 (Summary Report)")
        
        # 기본 집계
        summary_base = comp_all.groupby('품목계정그룹').agg({
            '전기말_재고': 'sum', '당월말_재고': 'sum', '재고_증감': 'sum',
            '당기누적_판매출고': 'sum', '전기동기_판매출고': 'sum', '판매_YoY증감': 'sum',
            '당기누적_생산출고': 'sum', '전기동기_생산출고': 'sum', '생산_YoY증감': 'sum'
        }).reset_index()

        # 순서 정렬 (제품 > 상품 > 반제품 > 원재료 > 부재료)
        sort_map = {'제품': 0, '상품': 1, '반제품': 2, '원재료': 3, '부재료': 4}
        summary_base['sort_key'] = summary_base['품목계정그룹'].map(sort_map)
        summary_base = summary_base.sort_values('sort_key').drop('sort_key', axis=1)

        sum_tabs = st.tabs(["🏛️ 기말재고 요약", "💰 매출원가 요약", "🛠️ 제조원가 요약"])
        
        with sum_tabs[0]:
            s_view1 = summary_base[['품목계정그룹', '전기말_재고', '당월말_재고', '재고_증감']]
            s_view1_total = add_total_row(s_view1, ['전기말_재고', '당월말_재고', '재고_증감'], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view1_total, ['전기말_재고'], ['당월말_재고'], ['재고_증감'], ['품목계정그룹']), use_container_width=True, hide_index=True)

        with sum_tabs[1]:
            # 반제품 제외 실적
            s_view2 = summary_base[summary_base['품목계정그룹'] != '반제품'][['품목계정그룹', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감']]
            s_view2.columns = ['품목계정그룹', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감']
            s_view2_total = add_total_row(s_view2, s_view2.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view2_total, ['당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감'], [], ['전기대비 차이증감'], ['품목계정그룹']), use_container_width=True, hide_index=True)

        with sum_tabs[2]:
            # 원재료, 부재료만 포함
            s_view3 = summary_base[summary_base['품목계정그룹'].isin(['원재료', '부재료'])][['품목계정그룹', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감']]
            s_view3.columns = ['품목계정그룹', '당기누적 제조원가', '전기누적 제조원가', '전기대비 차이증감']
            s_view3_total = add_total_row(s_view3, s_view3.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view3_total, ['당기누적 제조원가', '전기누적 제조원가', '전기대비 차이증감'], [], ['전기대비 차이증감'], ['품목계정그룹']), use_container_width=True, hide_index=True)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            comp_all.to_excel(writer, index=False, sheet_name='종합분석')
        st.download_button("📥 전체 분석 데이터 다운로드", data=output.getvalue(), file_name=f"Inventory_Analysis_{X}M.xlsx")
else:
    st.info("💡 사이드바의 5개 영역에 파일을 모두 업로드해주세요.")
