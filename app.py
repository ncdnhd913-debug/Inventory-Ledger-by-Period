import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="재무 비교 수불 분석 시스템", layout="wide")

st.title("📊 Financial Inventory Comparison Analysis")
st.markdown("""
이 시스템은 **당월**, **전년 동월**, **전기말** 데이터를 비교하여 재고 자산의 변동을 분석합니다.
""")

# 1. 데이터 전처리 함수 (기존 로직 유지 + 필수 컬럼 선별)
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

# 2. 사이드바: 3단계 파일 업로드
with st.sidebar:
    st.header("📅 분석 기간 설정")
    target_year = st.number_input("기준 년도", value=2024)
    target_month = st.selectbox("기준 월", [f"{i}월" for i in range(1, 13)], index=4) # 기본 5월
    
    st.divider()
    st.subheader("📁 파일 업로드 안내")
    
    # 1. 당월
    file_curr = st.file_uploader(f"1. 당월 ({target_year}년 {target_month}) 파일", type=['csv', 'xlsx'])
    # 2. 전년 동월
    file_prev_month = st.file_uploader(f"2. 전년 동월 ({target_year-1}년 {target_month}) 파일", type=['csv', 'xlsx'])
    # 3. 전기말
    file_prev_year = st.file_uploader(f"3. 전기말 ({target_year-1}년 12월) 파일", type=['csv', 'xlsx'])

# 3. 메인 로직
if file_curr and file_prev_month and file_prev_year:
    df_curr = process_inventory_data(file_curr)
    df_prev_m = process_inventory_data(file_prev_month)
    df_prev_y = process_inventory_data(file_prev_year)

    if df_curr is not None and df_prev_m is not None and df_prev_y is not None:
        
        # 품목계정그룹별 조회 버튼
        st.subheader("📋 품목계정그룹별 비교 분석")
        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        cols = st.columns(len(groups))
        
        if 'current_group' not in st.session_state:
            st.session_state.current_group = '제품'
        for i, group in enumerate(groups):
            if cols[i].button(group, use_container_width=True):
                st.session_state.current_group = group
        
        target_group = st.session_state.current_group
        
        # 데이터 병합 (품목코드 기준)
        # 당월 기준 데이터 준비
        base_df = df_curr[df_curr['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '기말재고_금액', '판매출고_금액', '입고계_금액']]
        base_df.columns = ['품목코드', '품목명', '단위', '당월_기말금액', '당월_판매금액', '당월_입고금액']
        
        # 전년 동월 데이터 병합 (손익 비교용)
        prev_m_sub = df_prev_m[['품목코드', '판매출고_금액', '입고계_금액']]
        prev_m_sub.columns = ['품목코드', '전년동월_판매금액', '전년동월_입고금액']
        
        # 전기말 데이터 병합 (재무상태 비교용)
        prev_y_sub = df_prev_y[['품목코드', '기말재고_금액']]
        prev_y_sub.columns = ['품목코드', '전기말_재고금액']
        
        # 최종 비교 테이블 구성
        comp_df = pd.merge(base_df, prev_m_sub, on='품목코드', how='left')
        comp_df = pd.merge(comp_df, prev_y_sub, on='품목코드', how='left').fillna(0)
        
        # 계산 컬럼 생성
        # 1. 전기말 대비 재고 증감 (BS 관점)
        comp_df['전기말대비_증감액'] = comp_df['당월_기말금액'] - comp_df['전기말_재고금액']
        
        # 2. 전년동월 대비 판매(출고) 증감 (PL 관점)
        comp_df['전년동월대비_판매증감'] = comp_df['당월_판매금액'] - comp_df['전년동월_판매금액']

        # UI 출력
        st.markdown(f"### 🔍 {target_group} 재무 비교 내역")
        
        # 요약 지표 카드
        m1, m2, m3 = st.columns(3)
        m1.metric("당월 기말재고 총액", f"{comp_df['당월_기말금액'].sum():,.0f}", 
                  delta=f"{comp_df['전기말대비_증감액'].sum():,.0f} (vs 전기말)")
        m2.metric("당월 판매(출고) 총액", f"{comp_df['당월_판매금액'].sum():,.0f}", 
                  delta=f"{comp_df['전년동월대비_판매증감'].sum():,.0f} (vs 전년동월)")
        m3.metric("전기말 재고 총액", f"{comp_df['전기말_재고금액'].sum():,.0f}")

        # 상세 비교 표
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        
        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            comp_df.to_excel(writer, index=False, sheet_name='재무비교분석')
        st.download_button(label="📥 비교 분석 결과 다운로드", data=output.getvalue(), file_name=f"Financial_Comparison_{target_group}.xlsx")

else:
    st.info("💡 분석을 시작하려면 사이드바에 **당월**, **전년 동월**, **전기말** 3개의 파일을 모두 업로드해주세요.")
