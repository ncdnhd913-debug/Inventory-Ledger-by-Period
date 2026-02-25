import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="재무 수불 분석 시스템", layout="wide")

st.title("⚖️ Financial Inventory Analysis (MoM & vs Year-End)")
st.markdown("""
본 시스템은 **전월 대비 실적(MoM)** 분석과 **전기말 대비 재고 잔액(B/S)** 변동 분석에 최적화되어 있습니다.
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

# 2. 사이드바: 4단계 파일 업로드
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
    
    # 세션 2: 누적 및 전기말 비교 (YTD & BS)
    st.subheader("📁 [누적/전기] 재무 분석 자료")
    file_curr_ytd = st.file_uploader(f"③ 당기 누적 (01~{target_month})", type=['csv', 'xlsx'])
    file_prev_full = st.file_uploader(f"④ 전기 전체 (전년 01~12월)", type=['csv', 'xlsx'])

    st.caption("※ 전년 동기 누적 데이터는 분석에서 제외되었습니다.")

# 3. 메인 분석 로직
files = [file_curr_m, file_prev_m, file_curr_ytd, file_prev_full]
if all(f is not None for f in files):
    # 데이터 로드
    df_m_curr = process_inventory_data(file_curr_m)
    df_m_prev = process_inventory_data(file_prev_m)
    df_ytd_curr = process_inventory_data(file_curr_ytd)
    df_prev_full = process_inventory_data(file_prev_full)

    # 품목계정그룹 버튼 UI
    groups = ['제품', '상품', '반제품', '원재료', '부재료']
    st.subheader("📋 품목계정그룹별 재무 대시보드")
    btn_cols = st.columns(len(groups))
    if 'current_group' not in st.session_state: st.session_state.current_group = '제품'
    for i, group in enumerate(groups):
        if btn_cols[i].button(group, use_container_width=True):
            st.session_state.current_group = group
    
    target_group = st.session_state.current_group

    # --- 데이터 병합 및 계산 ---
    # 1. 당월/전월 (MoM 실적용)
    m_curr_sub = df_m_curr[df_m_curr['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '판매출고_금액', '기말재고_금액']]
    m_curr_sub.columns = ['품목코드', '품목명', '단위', '당월_판매', '당월말_재고']
    
    m_prev_sub = df_m_prev[['품목코드', '판매출고_금액']]
    m_prev_sub.columns = ['품목코드', '전월_판매']

    # 2. 당기YTD (누적 정보 확인용)
    ytd_curr_sub = df_ytd_curr[['품목코드', '판매출고_금액', '입고계_금액']]
    ytd_curr_sub.columns = ['품목코드', '당기YTD_판매', '당기YTD_입고']

    # 3. 전기말 (BS 비교용)
    prev_full_sub = df_prev_full[['품목코드', '기말재고_금액']]
    prev_full_sub.columns = ['품목코드', '전기말_재고']

    # --- 최종 병합 ---
    comp_df = pd.merge(m_curr_sub, m_prev_sub, on='품목코드', how='left')
    comp_df = pd.merge(comp_df, ytd_curr_sub, on='품목코드', how='left')
    comp_df = pd.merge(comp_df, prev_full_sub, on='품목코드', how='left').fillna(0)

    # --- 분석 지표 계산 ---
    # PL: 전월 대비 판매 증감 (MoM)
    comp_df['MoM_판매증감'] = comp_df['당월_판매'] - comp_df['전월_판매']
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
        st.metric("당기 누적 판매(YTD)", f"{comp_df['당기YTD_판매'].sum():,.0f}")
    with c3:
        st.metric("현재 재고잔액", f"{comp_df['당월말_재고'].sum():,.0f}", 
                  delta=f"{comp_df['재고증감_vs전기말'].sum():,.0f} (vs 전기말)")

    # 상세 테이블 (주요 컬럼 위주 재배치)
    display_cols = [
        '품목코드', '품목명', '단위', 
        '당월_판매', '전월_판매', 'MoM_판매증감',
        '당기말_재고', '전기말_재고', '재고증감_vs전기말', 
        '당기YTD_판매', '당기YTD_입고'
    ]
    st.dataframe(comp_df[display_cols], use_container_width=True, hide_index=True)

    # 엑셀 다운로드
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        comp_df[display_cols].to_excel(writer, index=False, sheet_name='Comparison_Analysis')
    st.download_button(label="📥 분석 결과 다운로드", data=output.getvalue(), file_name=f"Financial_Analysis_{target_group}.xlsx")

else:
    st.info("💡 사이드바의 4개 파일 업로드 영역에 데이터를 모두 업로드해주세요.")
