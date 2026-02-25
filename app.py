import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="재무 통합 수불 분석 시스템", layout="wide")

st.title("⚖️ Comprehensive Financial Inventory Analysis")
st.markdown("""
본 시스템은 **월간(Monthly)** 및 **누적(YTD)** 데이터를 결합하여 전월 대비 실적과 전기말 대비 잔액 변동을 입체적으로 분석합니다.
""")

# 1. 데이터 전처리 함수
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
        
        # 정제 규칙
        df = df[df['품목계정그룹'].notna() & (df['품목계정그룹'].astype(str).str.strip() != '')]
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        
        # 숫자 변환
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            else:
                df[col] = df[col].fillna(0)
        return df
    except Exception as e:
        st.error(f"파일 처리 오류: {e}")
        return None

# 2. 사이드바: 5단계 파일 업로드 설계
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    target_month_val = st.slider("기준 월", 1, 12, 2)
    target_month = f"{target_month_val}월"
    prev_month = f"{target_month_val-1}월" if target_month_val > 1 else "12월(전기)"
    
    st.divider()
    
    # 세션 1: 월간 흐름 분석 (MoM)
    st.subheader("📁 [월간] 실적 분석 자료")
    file_curr_m = st.file_uploader(f"① 당월 ({target_month}) 1개월분", type=['csv', 'xlsx'])
    file_prev_m = st.file_uploader(f"② 전월 ({prev_month}) 1개월분", type=['csv', 'xlsx'])
    
    st.divider()
    
    # 세션 2: 누적/재무 상태 분석 (YTD & BS)
    st.subheader("📁 [누적] 재무 분석 자료")
    file_curr_ytd = st.file_uploader(f"③ 당기 누적 (01~{target_month})", type=['csv', 'xlsx'])
    file_prev_full = st.file_uploader(f"④ 전기 전체 (전년 01~12월)", type=['csv', 'xlsx'])
    file_prev_ytd = st.file_uploader(f"⑤ 전년 동기 누적 (전년 01~{target_month})", type=['csv', 'xlsx'])

# 3. 메인 분석 로직
files = [file_curr_m, file_prev_m, file_curr_ytd, file_prev_full, file_prev_ytd]
if all(f is not None for f in files):
    # 데이터 로드
    df_m_curr = process_inventory_data(file_curr_m)
    df_m_prev = process_inventory_data(file_prev_m)
    df_ytd_curr = process_inventory_data(file_curr_ytd)
    df_prev_full = process_inventory_data(file_prev_full)
    df_prev_ytd = process_inventory_data(file_prev_ytd)

    # 품목계정그룹 버튼 UI
    groups = ['제품', '상품', '반제품', '원재료', '부재료']
    st.subheader("📋 품목계정그룹별 통합 재무 대시보드")
    btn_cols = st.columns(len(groups))
    if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
    for i, group in enumerate(groups):
        if btn_cols[i].button(group, use_container_width=True):
            st.session_state.current_group = group
    
    target_group = st.session_state.current_group

    # --- 데이터 병합 및 계산 (품목코드 기준) ---
    # 1. 당월/전월 (MoM 실적용)
    m_curr_sub = df_m_curr[df_m_curr['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '판매출고_금액', '생산입고_금액', '기말재고_금액']]
    m_curr_sub.columns = ['품목코드', '품목명', '단위', '당월_판매', '당월_생산', '당월말_재고']
    
    m_prev_sub = df_m_prev[['품목코드', '판매출고_금액', '생산입고_금액', '기말재고_금액']]
    m_prev_sub.columns = ['품목코드', '전월_판매', '전월_생산', '전월말_재고']

    # 2. 당기YTD/전년YTD (YoY 실적용)
    ytd_curr_sub = df_ytd_curr[['품목코드', '판매출고_금액', '입고계_금액']]
    ytd_curr_sub.columns = ['품목코드', '당기YTD_판매', '당기YTD_입고']
    
    ytd_prev_sub = df_prev_ytd[['품목코드', '판매출고_금액', '입고계_금액']]
    ytd_prev_sub.columns = ['품목코드', '전년동기YTD_판매', '전년동기YTD_입고']

    # 3. 전기말 (BS 비교용)
    prev_full_sub = df_prev_full[['품목코드', '기말재고_금액']]
    prev_full_sub.columns = ['품목코드', '전기말_재고']

    # --- 최종 병합 ---
    comp_df = pd.merge(m_curr_sub, m_prev_sub, on='품목코드', how='left')
    comp_df = pd.merge(comp_df, ytd_curr_sub, on='품목코드', how='left')
    comp_df = pd.merge(comp_df, ytd_prev_sub, on='품목코드', how='left')
    comp_df = pd.merge(comp_df, prev_full_sub, on='품목코드', how='left').fillna(0)

    # --- 분석 지표 계산 ---
    # PL: 전월 대비 판매 증감 (MoM)
    comp_df['MoM_판매증감'] = comp_df['당월_판매'] - comp_df['전월_판매']
    # PL: 전년 동기 대비 누적 판매 증감 (YoY YTD)
    comp_df['YoY_YTD판매증감'] = comp_df['당기YTD_판매'] - comp_df['전년동기YTD_판매']
    # BS: 전기말 대비 재고 증감액
    comp_df['재고증감_vs전기말'] = comp_df['당월말_재고'] - comp_df['전기말_재고']

    # --- UI 출력 ---
    st.markdown(f"### 🔍 {target_group} 분석 결과")
    
    # 3단 KPI 카드
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(f"{target_month} 판매실적", f"{comp_df['당월_판매'].sum():,.0f}", 
                  delta=f"{comp_df['MoM_판매증감'].sum():,.0f} (vs 전월)")
    with c2:
        st.metric("당기 누적 판매(YTD)", f"{comp_df['당기YTD_판매'].sum():,.0f}", 
                  delta=f"{comp_df['YoY_YTD판매증감'].sum():,.0f} (vs 전년동기)")
    with c3:
        st.metric("현재 재고잔액", f"{comp_df['당월말_재고'].sum():,.0f}", 
                  delta=f"{comp_df['재고증감_vs전기말'].sum():,.0f} (vs 전기말)")

    # 상세 테이블
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # 엑셀 다운로드
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        comp_df.to_excel(writer, index=False, sheet_name='Financial_Comparison')
    st.download_button(label="📥 전체 분석 결과 다운로드", data=output.getvalue(), file_name=f"Comprehensive_Analysis_{target_group}.xlsx")

else:
    st.info("💡 사이드바의 모든 파일 업로드 영역(5개)에 데이터를 업로드하면 상세 분석이 시작됩니다.")
