import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 분석 시스템", layout="wide")

st.title("📊 Accounting Inventory Variance Analysis")
st.markdown("제조원가(생산출고) 및 매출원가(판매출고)의 변동 원인과 재무상태표(BS) 재고 증감을 분석합니다.")

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
        
        # 정제 및 숫자 변환
        df = df[df['품목계정그룹'].notna() & (df['품목계정그룹'].astype(str).str.strip() != '')]
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"파일 처리 오류 ({file.name}): {e}")
        return None

# 2. 사이드바: 5단계 파일 업로드
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    target_month_val = st.slider("기준 월", 1, 12, 2)
    target_month = f"{target_month_val}월"
    prev_month = f"{target_month_val-1}월" if target_month_val > 1 else "12월(전기)"
    
    st.divider()
    st.subheader("📁 분석 파일 업로드")
    f_curr_m = st.file_uploader(f"① 당월 ({target_month}) 1개월", type=['csv', 'xlsx'])
    f_prev_m = st.file_uploader(f"② 전월 ({prev_month}) 1개월", type=['csv', 'xlsx'])
    f_curr_ytd = st.file_uploader(f"③ 당기 누적 (01~{target_month})", type=['csv', 'xlsx'])
    f_prev_ytd = st.file_uploader(f"④ 전기 동기 누적 (전년 01~{target_month})", type=['csv', 'xlsx'])
    f_prev_full = st.file_uploader(f"⑤ 전기 전체 (전년 12월 기말)", type=['csv', 'xlsx'])

# 3. 메인 분석
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
if all(f is not None for f in files):
    # 데이터 로드
    d_curr_m = process_inventory_data(f_curr_m)
    d_prev_m = process_inventory_data(f_prev_m)
    d_curr_ytd = process_inventory_data(f_curr_ytd)
    d_prev_ytd = process_inventory_data(f_prev_ytd)
    d_prev_full = process_inventory_data(f_prev_full)

    # 그룹 선택 버튼
    groups = ['제품', '상품', '반제품', '원재료', '부재료']
    st.subheader("📋 품목계정그룹별 원가/재고 분석")
    btn_cols = st.columns(len(groups))
    if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
    for i, group in enumerate(groups):
        if btn_cols[i].button(group, use_container_width=True):
            st.session_state.current_group = group
    
    target_group = st.session_state.current_group

    # --- 데이터 병합 및 계산 ---
    # 당월 기준 데이터 준비 (AF: 생산출고, AH: 판매출고, AJ: 기말재고)
    base = d_curr_m[d_curr_m['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '생산출고_금액', '판매출고_금액', '기말재고_금액']]
    base.columns = ['품목코드', '품목명', '단위', '당월_생산출고', '당월_판매출고', '당월말_재고']

    # 비교용 서브 데이터셋 구성
    prev_m = d_prev_m[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전월_생산출고', '판매출고_금액':'전월_판매출고'})
    curr_ytd = d_curr_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'당기누적_생산출고', '판매출고_금액':'당기누적_판매출고'})
    prev_ytd = d_prev_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전기동기_생산출고', '판매출고_금액':'전기동기_판매출고'})
    prev_full = d_prev_full[['품목코드', '기말재고_금액']].rename(columns={'기말재고_금액':'전기말_재고'})

    # 병합
    comp = base.merge(prev_m, on='품목코드', how='left').merge(curr_ytd, on='품목코드', how='left')\
               .merge(prev_ytd, on='품목코드', how='left').merge(prev_full, on='품목코드', how='left').fillna(0)

    # --- 증감액 계산 ---
    # 1. 원가/비용 변동 (AF, AH)
    comp['생산출고_YoY증감'] = comp['당기누적_생산출고'] - comp['전기동기_생산출고']
    comp['판매출고_YoY증감'] = comp['당기누적_판매출고'] - comp['전기동기_판매출고']
    comp['판매출고_MoM증감'] = comp['당월_판매출고'] - comp['전월_판매출고']

    # 2. 재무상태표 재고 변동 (AJ)
    comp['재고_전기말대비증감'] = comp['당월말_재고'] - comp['전기말_재고']

    # --- 분석 리포트 출력 ---
    st.markdown(f"### 🔍 {target_group} 심층 분석")
    
    # 상단 요약 카드 (BS 및 PL 핵심 지표)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("현재 재고잔액", f"{comp['당월말_재고'].sum():,.0f}", f"{comp['재고_전기말대비증감'].sum():,.0f} (vs 전기말)")
    with c2:
        st.metric("당기 누적 판매원가", f"{comp['당기누적_판매출고'].sum():,.0f}", f"{comp['판매출고_YoY증감'].sum():,.0f} (vs 전년동기)")
    with c3:
        st.metric("당기 누적 제조원가(생산)", f"{comp['당기누적_생산출고'].sum():,.0f}", f"{comp['생산출고_YoY증감'].sum():,.0f} (vs 전년동기)")

    # 탭 구분
    t1, t2, t3 = st.tabs(["📊 재무상태표(재고잔액) 분석", "📈 매출원가(판매) 분석", "🏭 제조원가(생산) 분석"])

    with t1:
        st.write("전기말 대비 재고 증감액이 큰 품목 순위입니다.")
        # 절대값이 아닌 실제 증감액 기준으로 정렬하여 '급증' 품목 우선 표기
        bs_df = comp[['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_전기말대비증감']].sort_values(by='재고_전기말대비증감', ascending=False)
        st.dataframe(bs_df, use_container_width=True, hide_index=True)

    with t2:
        st.write("누적 판매원가(COGS) 변동 순위입니다. (전년 동기 대비)")
        pl_sales_df = comp[['품목코드', '품목명', '전기동기_판매출고', '당기누적_판매출고', '판매출고_YoY증감', '당월_판매출고', '판매출고_MoM증감']].sort_values(by='판매출고_YoY증감', ascending=False)
        st.dataframe(pl_sales_df, use_container_width=True, hide_index=True)

    with t3:
        st.write("제조원가(투입/출고) 변동 순위입니다. (전년 동기 대비)")
        pl_cost_df = comp[['품목코드', '품목명', '전기동기_생산출고', '당기누적_생산출고', '생산출고_YoY증감']].sort_values(by='생산출고_YoY증감', ascending=False)
        st.dataframe(pl_cost_df, use_container_width=True, hide_index=True)

    # 엑셀 다운로드
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        comp.sort_values(by='재고_전기말대비증감', ascending=False).to_excel(writer, index=False, sheet_name='전체분석결과')
    st.download_button(label="📥 전체 증감 분석결과 다운로드", data=output.getvalue(), file_name=f"Variance_Analysis_{target_group}.xlsx")

else:
    st.info("💡 사이드바의 5개 영역에 모든 파일을 업로드하면 회계 분석이 시작됩니다.")
