import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 분석 시스템", layout="wide")

st.title("⚖️ Financial Inventory Analysis (Variance Report)")
st.markdown("회계 분석 목적에 최적화된 수불 증감 분석 도구입니다. 각 섹션에 맞는 파일을 업로드해 주세요.")

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

# 2. 사이드바: 분석 기준 및 동적 업로드 박스
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    
    # [수정 1] 기준 월 드롭박스 (1~12월)
    target_month_val = st.selectbox("기준 월(X)", options=list(range(1, 13)), index=0)
    X = target_month_val
    prev_X = X - 1 if X > 1 else 12
    
    st.divider()
    
    # [수정 2] 업로드 박스 설명 동적 수정
    st.subheader("📁 분석 파일 업로드")
    
    f_curr_m = st.file_uploader(f"(1) 당월 ({X}월)", type=['csv', 'xlsx'])
    
    f_prev_m = st.file_uploader(f"(2) 전월 ({prev_X}월)", type=['csv', 'xlsx'])
    
    f_curr_ytd = st.file_uploader(f"(3) 당기 누적 (1월~{X}월)", type=['csv', 'xlsx'])
    
    f_prev_ytd = st.file_uploader(f"(4) 전기 동기 누적 (전기 1월~{X}월)", type=['csv', 'xlsx'])
    
    f_prev_full = st.file_uploader(f"(5) 전기 전체 (전기 1월~12월)", type=['csv', 'xlsx'])

# 3. 메인 분석 로직
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
if all(f is not None for f in files):
    d_curr_m = process_inventory_data(f_curr_m)
    d_prev_m = process_inventory_data(f_prev_m)
    d_curr_ytd = process_inventory_data(f_curr_ytd)
    d_prev_ytd = process_inventory_data(f_prev_ytd)
    d_prev_full = process_inventory_data(f_prev_full)

    # 그룹 선택
    groups = ['제품', '상품', '반제품', '원재료', '부재료']
    st.subheader(f"📋 {st.session_state.get('current_group', '제품')} 계정 증감 분석")
    btn_cols = st.columns(len(groups))
    
    if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
    for i, group in enumerate(groups):
        if btn_cols[i].button(group, use_container_width=True):
            st.session_state.current_group = group
    
    target_group = st.session_state.current_group

    # 데이터 병합 (AF: 생산출고, AH: 판매출고, AJ: 기말재고)
    base = d_curr_m[d_curr_m['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '생산출고_금액', '판매출고_금액', '기말재고_금액']]
    base.columns = ['품목코드', '품목명', '단위', '당월_생산출고', '당월_판매출고', '당월말_재고']

    # 비교 데이터셋 구성
    prev_m = d_prev_m[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전월_생산출고', '판매출고_금액':'전월_판매출고'})
    curr_ytd = d_curr_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'당기누적_생산출고', '판매출고_금액':'당기누적_판매출고'})
    prev_ytd = d_prev_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전기동기_생산출고', '판매출고_금액':'전기동기_판매출고'})
    prev_full = d_prev_full[['품목코드', '기말재고_금액']].rename(columns={'기말재고_금액':'전기말_재고'})

    # 최종 병합
    comp = base.merge(prev_m, on='품목코드', how='left').merge(curr_ytd, on='품목코드', how='left')\
               .merge(prev_ytd, on='품목코드', how='left').merge(prev_full, on='품목코드', how='left').fillna(0)

    # 증감 계산
    comp['제조원가_YoY증감'] = comp['당기누적_생산출고'] - comp['전기동기_생산출고']
    comp['제조원가_MoM증감'] = comp['당월_생산출고'] - comp['전월_생산출고']
    comp['판매원가_YoY증감'] = comp['당기누적_판매출고'] - comp['전기동기_판매출고']
    comp['판매원가_MoM증감'] = comp['당월_판매출고'] - comp['전월_판매출고']
    comp['재고_전기말대비증감'] = comp['당월말_재고'] - comp['전기말_재고']

    # KPI 카드
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric(f"{X}월말 재고잔액", f"{comp['당월말_재고'].sum():,.0f}", f"{comp['재고_전기말대비증감'].sum():,.0f} (vs 전기말)")
    m2.metric("누적 판매원가(PL)", f"{comp['당기누적_판매출고'].sum():,.0f}", f"{comp['판매원가_YoY증감'].sum():,.0f} (vs 전년동기)")
    m3.metric("누적 제조원가(Cost)", f"{comp['당기누적_생산출고'].sum():,.0f}", f"{comp['제조원가_YoY증감'].sum():,.0f} (vs 전년동기)")

    # 상세 탭 (증감액 기준 내림차순 정렬 적용)
    t1, t2, t3 = st.tabs(["🏛️ 재무상태표(재고)", "💰 매출원가(판매)", "🛠️ 제조원가(생산)"])

    with t1:
        st.write("📌 **전기말 대비 재고 증감 순위** (자산 변동이 큰 품목부터)")
        bs_view = comp[['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_전기말대비증감']].sort_values(by='재고_전기말대비증감', ascending=False)
        st.dataframe(bs_view, use_container_width=True, hide_index=True)

    with t2:
        st.write("📌 **누적 판매원가 증감 순위** (전년 동기 대비 실적 변화 큰 품목)")
        pl_sales_view = comp[['품목코드', '품목명', '전기동기_판매출고', '당기누적_판매출고', '판매원가_YoY증감', '당월_판매출고', '판매원가_MoM증감']].sort_values(by='판매원가_YoY증감', ascending=False)
        st.dataframe(pl_sales_view, use_container_width=True, hide_index=True)

    with t3:
        st.write("📌 **누적 제조원가 증감 순위** (전년 동기 대비 투입 변화 큰 품목)")
        pl_cost_view = comp[['품목코드', '품목명', '전기동기_생산출고', '당기누적_생산출고', '제조원가_YoY증감', '당월_생산출고', '제조원가_MoM증감']].sort_values(by='제조원가_YoY증감', ascending=False)
        st.dataframe(pl_cost_view, use_container_width=True, hide_index=True)

    # 엑셀 내보내기
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        comp.sort_values(by='재고_전기말대비증감', ascending=False).to_excel(writer, index=False, sheet_name='종합증감분석')
    st.download_button("📥 종합 증감 분석 결과 다운로드", data=output.getvalue(), file_name=f"Inventory_Variance_{target_group}_{X}M.xlsx")

else:
    st.info(f"💡 사이드바의 설명을 참고하여 **{target_month_val}월 기준** 파일들을 업로드해 주세요.")
