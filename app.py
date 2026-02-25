import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 통합 분석", layout="wide")

st.title("⚖️ Financial Inventory Variance Analysis")
st.markdown("회계 결산 및 증감 분석을 위한 통합 보고서 시스템입니다.")

# 1. 데이터 전처리 함수 (매칭 신뢰도 강화)
def process_inventory_data(file):
    if file is None: return None
    try:
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None)
        else:
            df_raw = pd.read_excel(file, header=None)
        
        header_main = df_raw.iloc[0].ffill()
        header_sub = df_raw.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(header_main, header_sub):
            col_name = f"{m}_{s}".strip("_") if s != '' else str(m)
            new_cols.append(col_name)
        
        df = df_raw.iloc[2:].copy()
        df.columns = new_cols
        
        # 품목계정그룹 및 품목코드 정제 (누락 방지 핵심)
        df['품목계정그룹'] = df['품목계정그룹'].astype(str).str.strip().replace('제품(OEM)', '제품')
        df['품목코드'] = df['품목코드'].astype(str).str.strip()
        df['품목명'] = df['품목명'].astype(str).str.strip()
        
        # 유효 데이터 필터링
        df = df[df['품목코드'] != 'nan']
        
        # 숫자 변환
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"⚠️ {file.name} 처리 중 오류: {e}")
        return None

# 합계 행 추가 함수
def add_total_row(df, numeric_cols):
    if df.empty: return df
    total_row = df[numeric_cols].sum()
    summary = pd.DataFrame([total_row], columns=numeric_cols)
    summary['품목명'] = '▶ 합계 (TOTAL)'
    return pd.concat([df, summary], ignore_index=True)

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

# 3. 메인 로직 시작
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
if all(f is not None for f in files):
    d_curr_m = process_inventory_data(f_curr_m)
    d_prev_m = process_inventory_data(f_prev_m)
    d_curr_ytd = process_inventory_data(f_curr_ytd)
    d_prev_ytd = process_inventory_data(f_prev_ytd)
    d_prev_full = process_inventory_data(f_prev_full)

    # 전체 데이터 그룹화 및 병합 (누락 방지를 위해 모든 품목 취합)
    all_items = pd.concat([
        d_curr_m[['품목코드', '품목명', '단위', '품목계정그룹']],
        d_prev_m[['품목코드', '품목명', '단위', '품목계정그룹']],
        d_curr_ytd[['품목코드', '품목명', '단위', '품목계정그룹']]
    ]).drop_duplicates('품목코드')

    # 데이터 매칭
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

    # 공통 증감 계산
    comp_all['제조원가_YoY증감'] = comp_all['당기누적_생산출고'] - comp_all['전기동기_생산출고']
    comp_all['판매원가_YoY증감'] = comp_all['당기누적_판매출고'] - comp_all['전기동기_판매출고']
    comp_all['재고_전기말대비증감'] = comp_all['당월말_재고'] - comp_all['전기말_재고']

    # 계정별 버튼 UI
    groups = ['제품', '상품', '반제품', '원재료', '부재료']
    st.subheader("📋 계정별 세부 증감 분석")
    btn_cols = st.columns(len(groups))
    if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
    for i, group in enumerate(groups):
        if btn_cols[i].button(group, use_container_width=True):
            st.session_state.current_group = group
    
    target_group = st.session_state.current_group
    group_df = comp_all[comp_all['품목계정그룹'] == target_group]

    if not group_df.empty:
        t1, t2, t3 = st.tabs(["🏛️ 재무상태표(재고)", "💰 매출원가(판매)", "🛠️ 제조원가(생산)"])
        
        with t1:
            st.write(f"📌 {target_group} - 전기말 대비 재고 증감 (금액 큰 순)")
            view1 = group_df[['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_전기말대비증감']].sort_values('재고_전기말대비증감', ascending=False)
            st.dataframe(add_total_row(view1, ['전기말_재고', '당월말_재고', '재고_전기말대비증감']), use_container_width=True, hide_index=True)

        with t2:
            st.write(f"📌 {target_group} - 누적 판매원가 YoY 증감")
            view2 = group_df[['품목코드', '품목명', '전기동기_판매출고', '당기누적_판매출고', '판매원가_YoY증감']].sort_values('판매원가_YoY증감', ascending=False)
            st.dataframe(add_total_row(view2, ['전기동기_판매출고', '당기누적_판매출고', '판매원가_YoY증감']), use_container_width=True, hide_index=True)

        with t3:
            st.write(f"📌 {target_group} - 누적 제조원가 YoY 증감")
            view3 = group_df[['품목코드', '품목명', '전기동기_생산출고', '당기누적_생산출고', '제조원가_YoY증감']].sort_values('제조원가_YoY증감', ascending=False)
            st.dataframe(add_total_row(view3, ['전기동기_생산출고', '당기누적_생산출고', '제조원가_YoY증감']), use_container_width=True, hide_index=True)
    else:
        st.warning(f"'{target_group}' 계정에 데이터가 없습니다.")

    # 4. 총괄 요약 보고서 (하단 고정)
    st.divider()
    st.subheader("📑 계정별 총괄 요약 보고서 (Summary Report)")
    summary_data = comp_all.groupby('품목계정그룹').agg({
        '전기말_재고': 'sum',
        '당월말_재고': 'sum',
        '재고_전기말대비증감': 'sum',
        '당기누적_판매출고': 'sum',
        '판매원가_YoY증감': 'sum',
        '당기누적_생산출고': 'sum',
        '제조원가_YoY증감': 'sum'
    }).reset_index()
    
    # 합계 행 추가
    summary_report = add_total_row(summary_data, summary_data.columns[1:])
    summary_report.iloc[-1, 0] = '▶ 총 합계'
    
    st.table(summary_report.style.format("{:,.0f}", subset=summary_report.columns[1:]))

    # 전체 데이터 다운로드
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        comp_all.to_excel(writer, index=False, sheet_name='전체증감분석')
    st.download_button("📥 전체 분석 데이터(Excel) 다운로드", data=output.getvalue(), file_name=f"Inventory_Final_Report_{X}M.xlsx")

else:
    st.info("💡 사이드바의 5개 영역에 파일을 모두 업로드하면 정밀 분석이 시작됩니다.")
