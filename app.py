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
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Financial Inventory Variance Analysis")
st.markdown("회계 결산 및 재료비/매출원가 증감 분석을 위한 통합 시스템입니다.")

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

# 합계 행 데이터 생성 함수 (본문과 열 순서 동일하게 반환)
def get_totals(df, numeric_cols, label_col='품목명'):
    if df.empty: return pd.DataFrame()
    totals = df[numeric_cols].sum()
    total_data = {col: totals[col] for col in numeric_cols}
    total_data[label_col] = '▶ 합계 (TOTAL)'
    
    # 원본 df에 있는 나머지 텍스트 열은 빈칸 처리
    for col in df.columns:
        if col not in total_data:
            total_data[col] = ""
            
    total_df = pd.DataFrame([total_data])
    return total_df[df.columns] # 열 순서 강제 일치

# 시각적 스타일링 함수
def style_financial_df(df, diff_cols, text_cols, label_col='품목명', is_total=False):
    if df.empty: return df
    
    num_cols = [c for c in df.columns if df[c].dtype != object and c != label_col]
    styler = df.style.format("{:,.0f}", subset=num_cols)
    
    # 텍스트 열 중앙 정렬 / 숫자 열 우측 정렬
    existing_text = [c for c in text_cols if c in df.columns]
    if existing_text:
        styler = styler.set_properties(subset=existing_text, **{'text-align': 'center'})
    if num_cols:
        styler = styler.set_properties(subset=num_cols, **{'text-align': 'right'})
        
    # 합계 행인 경우 배경색 없이 글씨만 굵게
    if is_total:
        styler = styler.set_properties(**{'font-weight': 'bold !important'})
                   
    # 증감 열 양수/음수 색상 (양수: 빨강, 음수: 파랑)
    existing_diff_cols = [c for c in diff_cols if c in df.columns]
    if existing_diff_cols:
        styler = styler.map(lambda x: 'color: #D32F2F; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 
                            else ('color: #1565C0; font-weight: bold;' if isinstance(x, (int, float)) and x < 0 else 'color: black'), 
                            subset=existing_diff_cols)
    return styler

# 2-Step (그룹 -> 상세) 분석 렌더링 함수
def display_analysis_tab(df, target_cols, diff_cols, text_cols, tab_id):
    temp_df = df[target_cols].copy()
    num_cols = [c for c in temp_df.columns if temp_df[c].dtype != object and c != '분석그룹']
    
    # Step 1. 분석그룹별 요약
    st.markdown("#### 1️⃣ 품목 그룹별 차이 요약")
    st.caption("💡 '커스텀 그룹핑' 설정에 따라 묶인 그룹 단위의 원가/재고 변동입니다.")
    grp_summary = temp_df.groupby('분석그룹')[num_cols].sum().reset_index()
    if diff_cols: grp_summary = grp_summary.sort_values(diff_cols[0], ascending=False)
    
    # 본문 표 렌더링
    st.dataframe(style_financial_df(grp_summary, diff_cols, ['분석그룹'], label_col='분석그룹'), use_container_width=True, hide_index=True)
    # 합계 표 렌더링 (본문 아래 부착, 헤더 숨김 처리)
    grp_total = get_totals(grp_summary, num_cols, label_col='분석그룹')
    st.dataframe(style_financial_df(grp_total, diff_cols, ['분석그룹'], label_col='분석그룹', is_total=True), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Step 2. 상세 드릴다운
    st.markdown("#### 2️⃣ 그룹 하위 세부 품목 조회 (Drill-Down)")
    selected_grp = st.selectbox("📌 세부 내역을 확인할 품목 그룹을 선택하세요:", options=["전체 품목 보기"] + list(grp_summary['분석그룹'].unique()), key=tab_id)
    
    if selected_grp == "전체 품목 보기":
        detail_df = temp_df.drop(columns=['분석그룹'])
    else:
        detail_df = temp_df[temp_df['분석그룹'] == selected_grp].drop(columns=['분석그룹'])
        
    if diff_cols: detail_df = detail_df.sort_values(diff_cols[0], ascending=False)
        
    # 본문 표 렌더링
    st.dataframe(style_financial_df(detail_df, diff_cols, text_cols, label_col='품목명'), use_container_width=True, hide_index=True)
    # 합계 표 렌더링
    detail_total = get_totals(detail_df, num_cols, label_col='품목명')
    st.dataframe(style_financial_df(detail_total, diff_cols, text_cols, label_col='품목명', is_total=True), use_container_width=True, hide_index=True)

# 2. 사이드바 설정
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    X = st.selectbox("기준 월(X)", options=list(range(1, 13)), index=0)
    prev_X = X - 1 if X > 1 else 12
    st.divider()
    st.subheader("📁 1. 수불부 파일 업로드")
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
        all_items = pd.concat([d[['품목코드', '품목명', '단위', '품목계정그룹']] for d in dfs]).drop_duplicates('품목코드')
        
        # [커스텀 로직] 기본 분석그룹 = 품목명 첫단어(하이픈 기준)
        all_items['분석그룹'] = all_items['품목명'].apply(lambda x: str(x).split('-')[0].strip())
        
        # 엑셀 매핑 적용
        if f_mapping is not None:
            try:
                mapping_df = pd.read_csv(f_mapping) if f_mapping.name.endswith('.csv') else pd.read_excel(f_mapping)
                if '품목코드' in mapping_df.columns and '분석그룹' in mapping_df.columns:
                    mapping_df['품목코드'] = mapping_df['품목코드'].astype(str).str.strip()
                    mapping_dict = dict(zip(mapping_df['품목코드'], mapping_df['분석그룹']))
                    all_items['분석그룹'] = all_items['품목코드'].map(mapping_dict).fillna(all_items['분석그룹'])
            except Exception as e:
                st.sidebar.error(f"매핑 파일 오류: {e}")

        # 커스텀 에디터 UI
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

        # 데이터 병합
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
            
            # 1) 기말재고 차이분석
            with tabs[0]:
                view1 = group_df[(group_df['전기말_재고'] != 0) | (group_df['당월말_재고'] != 0)].copy()
                if not view1.empty:
                    view1 = view1[['분석그룹', '품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_증감']]
                    display_analysis_tab(view1, view1.columns.tolist(), ['재고_증감'], text_cols, "tab_inv")
                else: st.info("재고 변동 내역이 없습니다.")

            # 2) 매출원가 차이분석
            if target_group != '반제품':
                with tabs[1]:
                    view2 = group_df[(group_df['당기누적_판매출고'] != 0) | (group_df['전기동기_판매출고'] != 0) | (group_df['당월_판매출고'] != 0)].copy()
                    if not view2.empty:
                        view2 = view2[['분석그룹', '품목코드', '품목명', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']]
                        view2.columns = ['분석그룹', '품목코드', '품목명', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
                        display_analysis_tab(view2, view2.columns.tolist(), ['전기대비 차이증감', '전월대비 차이증감'], text_cols, "tab_cogs")

            # 3) 재료비 차이분석
            if target_group in ['원재료', '부재료']:
                with tabs[len(tab_names)-1]:
                    cost_label = "원재료비" if target_group == '원재료' else "부재료비"
                    view3 = group_df[(group_df['당기누적_생산출고'] != 0) | (group_df['전기동기_생산출고'] != 0) | (group_df['당월_생산출고'] != 0)].copy()
                    if not view3.empty:
                        view3 = view3[['분석그룹', '품목코드', '품목명', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']]
                        view3.columns = ['분석그룹', '품목코드', '품목명', f'당기누적_{cost_label}', f'전기누적_{cost_label}', '전기대비 차이증감', f'당월_{cost_label}', f'전월_{cost_label}', '전월대비 차이증감']
                        display_analysis_tab(view3, view3.columns.tolist(), ['전기대비 차이증감', '전월대비 차이증감'], text_cols, "tab_mat")
        else:
            st.warning(f"'{target_group}' 계정에 유효한 데이터가 없습니다.")

        # --- 총괄 요약 보고서 ---
        st.divider()
        st.subheader("📑 계정별 총괄 요약 보고서 (Summary Report)")
        
        summary_agg = comp_all.groupby('품목계정그룹').agg({
            '전기말_재고': 'sum', '당월말_재고': 'sum', '재고_증감': 'sum',
            '당기누적_판매출고': 'sum', '전기동기_판매출고': 'sum', '판매_YoY증감': 'sum',
            '당월_판매출고': 'sum', '전월_판매출고': 'sum', '판매_MoM증감': 'sum',
            '당기누적_생산출고': 'sum', '전기동기_생산출고': 'sum', '생산_YoY증감': 'sum',
            '당월_생산출고': 'sum', '전월_생산출고': 'sum', '생산_MoM증감': 'sum'
        }).reset_index()

        summary_agg['품목계정그룹'] = pd.Categorical(summary_agg['품목계정그룹'], categories=groups, ordered=True)
        summary_agg = summary_agg.sort_values('품목계정그룹')

        summary_tabs = st.tabs(["🏛️ 기말재고 총괄", "💰 매출원가 총괄", "🛠️ 재료비 총괄"])

        with summary_tabs[0]:
            sum_view1 = summary_agg[['품목계정그룹', '전기말_재고', '당월말_재고', '재고_증감']]
            st.dataframe(style_financial_df(sum_view1, ['재고_증감'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True)
            sum_view1_total = get_totals(sum_view1, sum_view1.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(sum_view1_total, ['재고_증감'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True)

        with summary_tabs[1]:
            s_view2 = summary_agg[summary_agg['품목계정그룹'] != '반제품']\
                [['품목계정그룹', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']]
            s_view2.columns = ['품목계정그룹', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
            st.dataframe(style_financial_df(s_view2, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True)
            s_view2_total = get_totals(s_view2, s_view2.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view2_total, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True)

        with summary_tabs[2]:
            s_view3 = summary_agg[summary_agg['품목계정그룹'].isin(['원재료', '부재료'])]\
                [['품목계정그룹', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']]
            s_view3.columns = ['품목계정그룹', '당기누적_재료비', '전기누적_재료비', '전기대비 차이증감', '당월_재료비', '전월_재료비', '전월대비 차이증감']
            st.dataframe(style_financial_df(s_view3, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹'), use_container_width=True, hide_index=True)
            s_view3_total = get_totals(s_view3, s_view3.columns[1:], label_col='품목계정그룹')
            st.dataframe(style_financial_df(s_view3_total, ['전기대비 차이증감', '전월대비 차이증감'], text_cols, label_col='품목계정그룹', is_total=True), use_container_width=True, hide_index=True)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            comp_all.to_excel(writer, index=False, sheet_name='종합분석')
        st.download_button("📥 전체 분석 데이터 다운로드", data=output.getvalue(), file_name=f"Inventory_Analysis_{X}M.xlsx")
else:
    st.info("💡 사이드바의 1번(수불부 5개 파일) 항목을 모두 업로드해주세요.")
