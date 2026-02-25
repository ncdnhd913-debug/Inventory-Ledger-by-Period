import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 통합 분석", layout="wide")

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

        # 1번 요구사항: 한 행의 모든 수치 값이 0인 경우 제외
        num_cols_to_check = ['전기말_재고', '당월말_재고', '당기누적_판매출고', '전기동기_판매출고', '당기누적_생산출고', '전기동기_생산출고']
        group_df = group_df[(group_df[num_cols_to_check] != 0).any(axis=1)]

        if not group_df.empty:
            # 탭 구성 (제조원가는 원재료, 부재료만 노출)
            tab_names = ["🏛️ 기말재고 차이분석", "💰 매출원가 차이분석"]
            if target_group in ['원재료', '부재료']:
                tab_names.append("🛠️ 제조원가 차이분석")
            
            tabs = st.tabs(tab_names)
            
            with tabs[0]: # 기말재고 차이분석
                view1 = group_df[['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_증감']].sort_values('재고_증감', ascending=False)
                st.dataframe(add_total_row(view1, ['전기말_재고', '당월말_재고', '재고_증감']), use_container_width=True, hide_index=True)

            with tabs[1]: # 매출원가 차이분석
                view2 = group_df[['품목코드', '품목명', '당기누적_판매출고', '전기동기_판매출고', '판매_YoY증감', '당월_판매출고', '전월_판매출고', '판매_MoM증감']].copy()
                view2.columns = ['품목코드', '품목명', '당기누적_매출원가', '전기누적_매출원가', '전기대비 차이증감', '당월_매출원가', '전월_매출원가', '전월대비 차이증감']
                view2 = view2.sort_values('전기대비 차이증감', ascending=False)
                st.dataframe(add_total_row(view2, view2.columns[2:]), use_container_width=True, hide_index=True)

            if target_group in ['원재료', '부재료']:
                with tabs[2]: # 제조원가 차이분석
                    cost_label = "원재료비" if target_group == '원재료' else "부재료비"
                    view3 = group_df[['품목코드', '품목명', '당기누적_생산출고', '전기동기_생산출고', '생산_YoY증감', '당월_생산출고', '전월_생산출고', '생산_MoM증감']].copy()
                    view3.columns = ['품목코드', '품목명', f'당기누적_{cost_label}', f'전기누적_{cost_label}', '전기대비 차이증감', f'당월_{cost_label}', f'전월_{cost_label}', '전월대비 차이증감']
                    view3 = view3.sort_values('전기대비 차이증감', ascending=False)
                    st.dataframe(add_total_row(view3, view3.columns[2:]), use_container_width=True, hide_index=True)
        else:
            st.warning(f"'{target_group}' 계정에 유효한 데이터가 없습니다.")

        # 총괄 요약 보고서
        st.divider()
        st.subheader("📑 계정별 총괄 요약 보고서")
        summary_data = comp_all.groupby('품목계정그룹').agg({
            '전기말_재고': 'sum', '당월말_재고': 'sum', '재고_증감': 'sum',
            '당기누적_판매출고': 'sum', '판매_YoY증감': 'sum',
            '당기누적_생산출고': 'sum', '생산_YoY증감': 'sum'
        }).reset_index()
        summary_final = add_total_row(summary_data, summary_data.columns[1:], label_col='품목계정그룹')
        formatted_summary = summary_final.copy()
        for col in summary_final.columns[1:]:
            formatted_summary[col] = formatted_summary[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
        st.table(formatted_summary)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            comp_all.to_excel(writer, index=False, sheet_name='종합분석')
        st.download_button("📥 전체 분석 데이터 다운로드", data=output.getvalue(), file_name=f"Inventory_Analysis_{X}M.xlsx")
else:
    st.info("💡 사이드바의 5개 영역에 파일을 모두 업로드해주세요.")
