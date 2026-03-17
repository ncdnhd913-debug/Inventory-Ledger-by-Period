import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 통합 분석", layout="wide")

# CSS를 통한 UI 보강: 표 헤더 강제 중앙 정렬 및 여백 조정
st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 95%; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 5px; }
    /* 테이블 헤더 및 인덱스 중앙 정렬 */
    [data-testid="stDataFrame"] th { text-align: center !important; }
    /* 분리된 합계 표가 본문 표와 이어져 보이도록 마진 축소 */
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0rem; }
    /* 합계표 하단 테두리 추가 */
    div[data-testid="stDataFrame"] table { border-bottom: 1px solid #e6e9ef !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📦 Financial Inventory Variance Analysis")
st.markdown("기말재고 및 재료비/매출원가 증감 분석을 위한 통합 시스템입니다.")

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
        
        for col in ['품목계정그룹', '품목코드', '품목명', '단위']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace('nan', '')
                
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        df = df[df['품목코드'] != '']
        
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"⚠️ {file.name} 처리 중 오류: {e}")
        return None

# 합계 행 분리 반환 함수
def get_totals(df, numeric_cols, label_col='품목명'):
    if df.empty: return pd.DataFrame()
    totals = df[numeric_cols].sum()
    total_data = {col: totals[col] for col in numeric_cols}
    total_data[label_col] = '▶ 합계 (TOTAL)'
    for col in df.columns:
        if col not in total_data:
            total_data[col] = ""
    total_df = pd.DataFrame([total_data])
    return total_df[df.columns]

# 시각적 스타일링 함수
def style_financial_df(df, diff_cols, text_cols, label_col='품목명', is_total=False):
    if df.empty: return df
    
    num_cols = [c for c in df.columns if df[c].dtype != object and c != label_col]
    styler = df.style.format("{:,.0f}", subset=num_cols)
    
    existing_text = [c for c in text_cols if c in df.columns]
    if existing_text:
        styler = styler.set_properties(subset=existing_text, **{'text-align': 'center'})
    if num_cols:
        styler = styler.set_properties(subset=num_cols, **{'text-align': 'right'})
        
    if is_total:
        styler = styler.set_properties(**{'font-weight': 'bold !important'})
                   
    existing_diff_cols = [c for c in diff_cols if c in df.columns]
    if existing_diff_cols:
        styler = styler.map(lambda x: 'color: #D32F2F; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 
                            else ('color: #1565C0; font-weight: bold;' if isinstance(x, (int, float)) and x < 0 else 'color: black'), 
                            subset=existing_diff_cols)
    return styler

# 공통 Column Config 생성기
def get_column_config(df_columns, text_cols):
    config = {}
    for col in df_columns:
        if col in text_cols:
            if col == '품목명':
                config[col] = st.column_config.TextColumn(col, width="large")
            else:
                config[col] = st.column_config.TextColumn(col, width="medium")
        else:
             config[col] = st.column_config.NumberColumn(col, width="medium")
    return config

# 2-Step 분석 렌더링 함수
def display_analysis_tab(df, target_cols, diff_cols, text_cols, tab_id):
    temp_df = df[target_cols].copy()
    num_cols = [c for c in temp_df.columns if temp_df[c].dtype != object and c != '분석그룹']
    
    st.markdown("#### 1️⃣ 품목 그룹별 차이 요약")
    st.caption("💡 '커스텀 그룹핑' 설정에 따라 묶인 그룹 단위의 원가/재고 변동입니다.")
    grp_summary = temp_df.groupby('분석그룹')[num_cols].sum().reset_index()
    if diff_cols: grp_summary = grp_summary.sort_values(diff_cols[0], ascending=False)
    
    col_config_grp = get_column_config(grp_summary.columns, text_cols + ['분석그룹'])
    
    st.dataframe(style_financial_df(grp_summary, diff_cols, ['분석그룹'], label_col='분석그룹'), use_container_width=True, hide_index=True, column_config=col_config_grp)
    grp_total = get_totals(grp_summary, num_cols, label_col='분석그룹')
    st.dataframe(style_financial_df(grp_total, diff_cols, ['분석그룹'], label_col='분석그룹', is_total=True), use_container_width=True, hide_index=True, column_config=col_config_grp)
    
    st.divider()
    
    st.markdown("#### 2️⃣ 그룹 하위 세부 품목 조회 (Drill-Down)")
    selected_grp = st.selectbox("📌 세부 내역을 확인할 품목 그룹을 선택하세요:", options=["전체 품목 보기"] + list(grp_summary['분석그룹'].unique()), key=tab_id)
    
    if selected_grp == "전체 품목 보기":
        detail_df = temp_df.drop(columns=['분석그룹'])
    else:
        detail_df = temp_df[temp_df['분석그룹'] == selected_grp].drop(columns=['분석그룹'])
        
    if diff_cols: detail_df = detail_df.sort_values(diff_cols[0], ascending=False)
        
    col_config_dtl = get_column_config(detail_df.columns, text_cols)
        
    st.dataframe(style_financial_df(detail_df, diff_cols, text_cols, label_col='품목명'), use_container_width=True, hide_index=True, column_config=col_config_dtl)
    detail_total = get_totals(detail_df, num_cols, label_col='품목명')
    st.dataframe(style_financial_df(detail_total, diff_cols, text_cols, label_col='품목명', is_total=True), use_container_width=True, hide_index=True, column_config=col_config_dtl)

# 2. 사이드바 설정
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    X = st.selectbox("기준 월(X)", options=list(range(1, 13)), index=0)
    prev_X = X - 1 if X > 1 else 12
    st.divider()
    st.subheader("📁 1. 원가수불부(ERP10) 파일 업로드")
    st.caption("💡 '원가수불부' 메뉴에서 다운받은 실제원가수불(EXCEL) 자료를 업로드하세요.")
    f_curr_m = st.file_uploader(f"(1) 당월 ({X}월)", type=['csv', 'xlsx'])
    f_prev_m = st.file_uploader(f"(2) 전월 ({prev_X}월)", type=['csv', 'xlsx'])
    f_curr_ytd = st.file_uploader(f"(3) 당기 누적 (1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_ytd = st.file_uploader(f"(4) 전기 동기 누적 (전기 1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_full = st.file_uploader(f"(5) 전기 전체 (전기 1월~12월)", type=['csv', 'xlsx'])
    st.divider()
    st.subheader("⚙️ 2. 커스텀 매핑 파일 (선택)")
    f_mapping = st.file_uploader("품목 그룹핑 매핑 파일", type=['csv', 'xlsx'], help="품목코드와 분석그룹 열이 있는 파일을 올리시면 일괄 적용됩니다.")

# 3. 메인 로직
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
if all(f is not None for f in files):
    dfs = [process_inventory_data(f) for f in files]
    d_curr_m, d_prev_m, d_curr_ytd, d_prev_ytd, d_prev_full = dfs

    if all(d is not None for d in dfs):
        # 품목 마스터 취합
        all_items_list = []
        for d in dfs:
            if d is not None and not d.empty:
                cols = [c for c in ['품목코드', '품목명', '단위', '품목계정그룹'] if c in d.columns]
                if '품목코드' in cols:
                    all_items_list.append(d[cols])
        
        all_items = pd.concat(all_items_list).drop_duplicates('품목코드')
        
        for col in ['품목명', '단위', '품목계정그룹']:
            if col not in all_items.columns:
                all_items[col] = ""
            else:
                all_items[col] = all_items[col].fillna("")

        all_items['분석그룹'] = all_items['품목명'].apply(lambda x: str(x).split('-')[0].strip())
        
        if f_mapping is not None:
            try:
                mapping_df = pd.read_csv(f_mapping) if f_mapping.name.endswith('.csv') else pd.read_excel(f_mapping)
                if '품목코드' in mapping_df.columns and '분석그룹' in mapping_df.columns:
                    mapping_df['품목코드'] = mapping_df['품목코드'].astype(str).str.strip()
                    mapping_dict = dict(zip(mapping_df['품목코드'], mapping_df['분석그룹']))
                    all_items['분석그룹'] = all_items['품목코드'].map(mapping_dict).fillna(all_items['분석그룹'])
            except Exception as e:
                st.sidebar.error(f"매핑 파일 오류: {e}")

        with st.expander("🛠️ 품목 커스텀 그룹핑 설정 (직접 수정 가능)", expanded=False):
            st.info("아래 표의 **'분석그룹'** 열을 더블클릭하여 그룹명을 원하는 대로 수정할 수 있습니다. 수정한 내용을 다운로드해 사이드바에 업로드하면 다음 달에도 자동 반영됩니다.")
            col1, col2 = st.columns([8, 2])
            edited_items = st.data_editor(
                all_items[['품목계정그룹', '품목코드', '품목명', '분석그룹']],
                column_config={"분석그룹": st.column_config.TextColumn("분석그룹 (수정)", required=True)},
                use_container_width=True, hide_index=True
            )
            all_items['분석그룹'] = edited_items['분석그룹']
            
            with col2:
                out_map = io.BytesIO()
                with pd.ExcelWriter(out_map, engine='xlsxwriter') as writer:
                    all_items[['품목계정그룹', '품목코드', '품목명', '분석그룹']].to_excel(writer, index=False)
                st.download_button("📥 매핑 파일 저장(다운로드)", data=out_map.getvalue(), file_name="Item_Mapping.xlsx")

        # [핵심 수정] 병합 로직 재검토: 각 파일 중복 제거 및 타입 확인
        d_curr_m_unique = d_curr_m.drop_duplicates('품목코드') if d_curr_m is not None else pd.DataFrame()
        d_prev_m_unique = d_prev_m.drop_duplicates('품목코드') if d_prev_m is not None else pd.DataFrame()
        d_curr_ytd_unique = d_curr_ytd.drop_duplicates('품목코드') if d_curr_ytd is not None else pd.DataFrame()
        d_prev_ytd_unique = d_prev_ytd.drop_duplicates('품목코드') if d_prev_ytd is not None else pd.DataFrame()
        d_prev_full_unique = d_prev_full.drop_duplicates('품목코드') if d_prev_full is not None else pd.DataFrame()

        comp_all = all_items.copy()
        
        # 각 파일별 매칭. 존재하는 컬럼만 안전하게 조인
        if not d_curr_m_unique.empty:
            cols_to_use = [c for c in ['품목코드', '생산출고_금액', '판매출고_금액', '기말재고_금액'] if c in d_curr_m_unique.columns]
            comp_all = comp_all.merge(d_curr_m_unique[cols_to_use], on='품목코드', how='left')\
                                .rename(columns={'생산출고_금액':'당월_생산출고', '판매출고_금액':'당월_판매출고', '기말재고_금액':'당월말_재고'})
        
        if not d_prev_m_unique.empty:
            cols_to_use = [c for c in ['품목코드', '생산출고_금액', '판매출고_금액', '기말재고_금액'] if c in d_prev_m_unique.columns]
            comp_all = comp_all.merge(d_prev_m_unique[cols_to_use], on='품목코드', how='left')\
                                .rename(columns={'생산출고_금액':'전월_생산출고', '판매출고_금액':'전월_판매출고', '기말재고_금액':'전월말_재고'})
                                
        if not d_curr_ytd_unique.empty:
            cols_to_use = [c for c in ['품목코드', '생산출고_금액', '판매출고_금액'] if c in d_curr_ytd_unique.columns]
            comp_all = comp_all.merge(d_curr_ytd_unique[cols_to_use], on='품목코드', how='left')\
                                .rename(columns={'생산출고_금액':'당기누적_생산출고', '판매출고_금액':'당기누적_판매출고'})
                                
        if not d_prev_ytd_unique.empty:
            cols_to_use = [c for c in ['품목코드', '생산출고_금액', '판매출고_금액', '기말재고_금액'] if c in d_prev_ytd_unique.columns]
            comp_all = comp_all.merge(d_prev_ytd_unique[cols_to_use], on='품목코드', how='left')\
                                .rename(columns={'생산출고_금액':'전기동기_생산출고', '판매출고_금액':'전기동기_판매출고', '기말재고_금액':'전기동월말_재고'})
                                
        if not d_prev_full_unique.empty:
            cols_to_use = [c for c in ['품목코드', '기말재고_금액'] if c in d_prev_full_unique.columns]
            comp_all = comp_all.merge(d_prev_full_unique[cols_to_use], on='품목코드', how='left')\
                                .rename(columns={'기말재고_금액':'전기말_재고'})

        # 결측치를 0으로 채워 연산 누락 방지
        comp_all = comp_all.fillna(0)
        
        # 특정 파일에 해당 컬럼이 아예 없었을 경우를 대비한 안전 장치
        expected_num_cols = ['당월_생산출고', '당월_판매출고', '당월말_재고', '전월_생산출고', '전월_판매출고', '전월말_재고', 
                             '당기누적_생산출고', '당기누적_판매출고', '전기동기_생산출고', '전기동기_판매출고', '전기동월말_재고', '전기말_재고']
        for col in expected_num_cols:
            if col not in comp_all.columns:
                comp_all[col] = 0

        # 차이 계산
        comp_all['재고증감_vs전기말'] = comp_all['당월말_재고'] - comp_all['전기말_재고']
        comp_all['재고증감_vs전기동월'] = comp_all['당월말_재고'] - comp_all['전기동월말_재고']
        comp_all['재고증감_vs전월'] = comp_all['당월말_재고'] - comp_all['전월말_재고']
        
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
        
        text_cols = ['품목코드', '품목명', '단위', '품목계정그룹']

        if not group_df.empty:
            tab_names = ["🏛️ 기말재고 차이분석"]
            if target_group != '반제품': tab_names.append("💰 매출원가 차이분석")
            if target_group in ['원재료', '부재료']: tab_names.append("🛠️ 재료비 차이분석")
            
            tabs = st.tabs(tab_names)
            
            with tabs[0]:
                view1 = group_df[(group_df['전기말_재고'] != 0) | (group_df['전기동월말_재고'] != 0) | (group_df['전월말_재고'] != 0) | (group_df['당월말_재고'] != 0)].copy()
                if not view1.empty:
                    view1 = view1[['분석그룹', '품목코드', '품목명', '전기말_재고', '전기동월말_재고', '전월말_재고', '당월말_재고', '재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월']]
                    display_analysis_tab(view1, view1.columns.tolist(), ['재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월'], text_cols, "tab_inv")
                else: st.info("재고 변동 내역이 없습니다.")

            if target_group != '반제품':
                with tabs[1]:
                    view2 = group_df[(group_df['당기누적_판매출고'] != 0) | (group_df['전기동기_판매출고'] != 0) | (group_df['당월_판매출고'] != 0) | (group_df['전월_판매출고'] != 0)].copy()
                    if not view2.empty:
                        view2 = view2[['분석그룹', '품목코드', '품목명', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']]
                        view2.columns = ['분석그룹', '품목코드', '품목명', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
                        display_analysis_tab(view2, view2.columns.tolist(), ['전기대비 차이증감', '전월대비 차이증감'], text_cols, "tab_cogs")

            if target_group in ['원재료', '부재료']:
                with tabs[len(tab_names)-1]:
                    cost_label = "원재료비" if target_group == '원재료' else "부재료비"
                    view3 = group_df[(group_df['당기누적_생산출고'] != 0) | (group_df['전기동기_생산출고'] != 0) | (group_df['당월_생산출고'] != 0) | (group_df['전월_생산출고'] != 0)].copy()
                    if not view3.empty:
                        view3 = view3[['분석그룹', '품목코드', '품목명', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']]
                        view3.columns = ['분석그룹', '품목코드', '품목명', f'당기누적_{cost_label}', f'전기누적_{cost_label}', '전기대비 차이증감', f'당월_{cost_label}', f'전월_{cost_label}', '전월대비 차이증감']
                        display_analysis_tab(view3, view3.columns.tolist(), ['전기대비 차이증감', '전월대비 차이증감'], text_cols, "tab_mat")
        else:
            st.warning(f"'{target_group}' 계정에 유효한 데이터가 없습니다.")

        st.divider()
        st.subheader("📑 계정별 총괄 요약 보고서 (Summary Report)")
        
        summary_agg = comp_all.groupby('품목계정그룹').agg({
            '전기말_재고': 'sum', '전기동월말_재고': 'sum', '전월말_재고': 'sum', '당월말_재고': 'sum', 
            '재고증감_vs전기말': 'sum', '재고증감_vs전기동월': 'sum', '재고증감_vs전월': 'sum',
            '당기누적_판매출고': 'sum', '전기동기_판매출고': 'sum', '판매_YoY증감': 'sum',
            '당월_판매출고': 'sum', '전월_판매출고': 'sum', '판매_MoM증감': 'sum',
            '당기누적_생산출고': 'sum', '전기동기_생산출고': 'sum', '생산_YoY증감': 'sum',
            '당월_생산출고': 'sum', '전월_생산출고': 'sum', '생산_MoM증감': 'sum'
        }).reset_index()

        summary_agg['품목계정그룹'] = pd.Categorical(summary_agg['품목계정그룹'], categories=groups, ordered=True)
        summary_agg = summary_agg.sort_values('품목계정그룹')

        summary_tabs = st.tabs(["🏛️ 기말재고 총괄", "💰 매출원가 총괄", "🛠️ 재료비 총괄"])

        with summary_tabs[0]:
            sum_view1 = summary_agg[['품목계정그룹', '전기말_재고', '전기동월말_재고', '전월말_재고', '당월말_재고', '재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월']]
            col_cfg_sum1 = get_column_config(sum_view1.columns, text_cols)
            st.dataframe(style_financial_df(sum_view1, ['재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True, column_config=col_cfg_sum1)
            sum_view1_total = get_totals(sum_view1, sum_view1.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(sum_view1_total, ['재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True, column_config=col_cfg_sum1)

        with summary_tabs[1]:
            s_view2 = summary_agg[summary_agg['품목계정그룹'] != '반제품']\
                [['품목계정그룹', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']]
            s_view2.columns = ['품목계정그룹', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
            col_cfg_sum2 = get_column_config(s_view2.columns, text_cols)
            st.dataframe(style_financial_df(s_view2, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True, column_config=col_cfg_sum2)
            s_view2_total = get_totals(s_view2, s_view2.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view2_total, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True, column_config=col_cfg_sum2)

        with summary_tabs[2]:
            s_view3 = summary_agg[summary_agg['품목계정그룹'].isin(['원재료', '부재료'])]\
                [['품목계정그룹', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']]
            s_view3.columns = ['품목계정그룹', '당기누적_재료비', '전기누적_재료비', '전기대비 차이증감', '당월_재료비', '전월_재료비', '전월대비 차이증감']
            col_cfg_sum3 = get_column_config(s_view3.columns, text_cols)
            st.dataframe(style_financial_df(s_view3, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True, column_config=col_cfg_sum3)
            s_view3_total = get_totals(s_view3, s_view3.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view3_total, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True, column_config=col_cfg_sum3)

        # 엑셀 다운로드 (보고서 양식 맞춤)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_inv = summary_agg[['품목계정그룹', '전기말_재고', '전기동월말_재고', '전월말_재고', '당월말_재고', '재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월']].copy()
            export_inv = pd.concat([export_inv, get_totals(export_inv, export_inv.columns[1:], label_col='품목계정그룹')], ignore_index=True)
            export_inv.to_excel(writer, index=False, sheet_name='기말재고_총괄')

            export_cogs = summary_agg[summary_agg['품목계정그룹'] != '반제품'][['품목계정그룹', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']].copy()
            export_cogs.columns = ['품목계정그룹', '당기누적_매출원가', '전기누적_매출원가', '전기대비_차이증감', '당월_매출원가', '전월_매출원가', '전월대비_차이증감']
            export_cogs = pd.concat([export_cogs, get_totals(export_cogs, export_cogs.columns[1:], label_col='품목계정그룹')], ignore_index=True)
            export_cogs.to_excel(writer, index=False, sheet_name='매출원가_총괄')

            export_mat = summary_agg[summary_agg['품목계정그룹'].isin(['원재료', '부재료'])][['품목계정그룹', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']].copy()
            export_mat.columns = ['품목계정그룹', '당기누적_재료비', '전기누적_재료비', '전기대비_차이증감', '당월_재료비', '전월_재료비', '전월대비_차이증감']
            export_mat = pd.concat([export_mat, get_totals(export_mat, export_mat.columns[1:], label_col='품목계정그룹')], ignore_index=True)
            export_mat.to_excel(writer, index=False, sheet_name='재료비_총괄')

            export_detail = comp_all.copy()
            export_detail['품목계정그룹'] = pd.Categorical(export_detail['품목계정그룹'], categories=groups, ordered=True)
            export_detail = export_detail.sort_values(['품목계정그룹', '분석그룹', '품목코드'])
            
            export_detail = export_detail[(export_detail[['전기말_재고', '전기동월말_재고', '전월말_재고', '당월말_재고', '당기누적_판매출고', '전기동기_판매출고', '당월_판매출고', '전월_판매출고', '당기누적_생산출고', '전기동기_생산출고', '당월_생산출고', '전월_생산출고']] != 0).any(axis=1)]
            
            export_detail.rename(columns={
                '판매_YoY증감': '매출원가_전기대비증감', '판매_MoM증감': '매출원가_전월대비증감',
                '생산_YoY증감': '재료비_전기대비증감', '생산_MoM증감': '재료비_전월대비증감',
                '당기누적_판매출고': '당기누적_매출원가', '전기동기_판매출고': '전기누적_매출원가', '당월_판매출고': '당월_매출원가', '전월_판매출고': '전월_매출원가',
                '당기누적_생산출고': '당기누적_재료비', '전기동기_생산출고': '전기누적_재료비', '당월_생산출고': '당월_재료비', '전월_생산출고': '전월_재료비'
            }, inplace=True)
            
            detail_cols = ['분석그룹', '품목계정그룹', '품목코드', '품목명', '단위', 
                           '전기말_재고', '전기동월말_재고', '전월말_재고', '당월말_재고', '재고증감_vs전기말', '재고증감_vs전기동월', '재고증감_vs전월',
                           '당기누적_매출원가', '전기누적_매출원가', '매출원가_전기대비증감', '당월_매출원가', '전월_매출원가', '매출원가_전월대비증감',
                           '당기누적_재료비', '전기누적_재료비', '재료비_전기대비증감', '당월_재료비', '전월_재료비', '재료비_전월대비증감']
            
            export_detail[detail_cols].to_excel(writer, index=False, sheet_name='품목별_상세분석')

        st.download_button("📥 전체 분석 데이터 다운로드", data=output.getvalue(), file_name=f"Inventory_Analysis_{X}M.xlsx")
else:
    st.info("💡 사이드바의 1번(원가수불부 5개 파일) 항목을 모두 업로드해주세요.")
