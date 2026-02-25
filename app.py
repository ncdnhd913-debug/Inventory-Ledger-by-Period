import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="재무 누적 수불 분석 시스템", layout="wide")

st.title("⚖️ Financial Inventory Analysis (YTD Basis)")
st.markdown("""
이 시스템은 **누적(YTD) 수불부**를 기반으로 재무상태표(잔액)와 손익계산서(누적 흐름)를 입체적으로 분석합니다.
""")

# 1. 데이터 전처리 함수 (상세 수불 항목 17개 반영 및 정제)
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

# 2. 사이드바: 3단계 누적 파일 업로드
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("당기 기준 년도", value=2026)
    target_month = st.selectbox("기준 월", [f"{i}월" for i in range(1, 13)], index=1) # 2월 기본
    
    st.divider()
    st.subheader("📁 누적 수불 자료 업로드")
    
    # 1. 당기 누적 (1월 ~ 기준월)
    file_curr_ytd = st.file_uploader(f"1. 당기 누적 (01월~{target_month})", type=['csv', 'xlsx'])
    # 2. 전기 전체 (전년 01월 ~ 12월)
    file_prev_full = st.file_uploader(f"2. 전기 전체 (전년 01월~12월)", type=['csv', 'xlsx'])
    # 3. 전년 동기 누적 (전년 01월 ~ 전년 기준월)
    file_prev_ytd = st.file_uploader(f"3. 전년 동기 누적 (전년 01월~{target_month})", type=['csv', 'xlsx'])

    st.caption("※ 모든 파일은 해당 기간의 '누적 수불부'여야 정확한 분석이 가능합니다.")

# 3. 메인 로직
if file_curr_ytd and file_prev_full and file_prev_ytd:
    df_curr = process_inventory_data(file_curr_ytd)
    df_prev_full = process_inventory_data(file_prev_full)
    df_prev_ytd = process_inventory_data(file_prev_ytd)

    if all(v is not None for v in [df_curr, df_prev_full, df_prev_ytd]):
        
        # 품목계정그룹별 조회 버튼
        st.subheader("📋 품목계정그룹별 재무 분석")
        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        btn_cols = st.columns(len(groups))
        
        if 'current_group' not in st.session_state:
            st.session_state.current_group = '제품'
        for i, group in enumerate(groups):
            if btn_cols[i].button(group, use_container_width=True):
                st.session_state.current_group = group
        
        target_group = st.session_state.current_group
        
        # --- 데이터 병합 및 비교 계산 ---
        # A. 당기 누적 기준 (BS 기말잔액 + PL 당기 실적)
        base_df = df_curr[df_curr['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '기말재고_금액', '판매출고_금액', '입고계_금액', '생산입고_금액']]
        base_df.columns = ['품목코드', '품목명', '단위', '당기말_재고', '당기_누적판매', '당기_누적입고', '당기_누적생산']
        
        # B. 전기말 잔액 (BS 비교용: 전기말 12월 기말재고)
        prev_full_sub = df_prev_full[['품목코드', '기말재고_금액']]
        prev_full_sub.columns = ['품목코드', '전기말_재고']
        
        # C. 전년 동기 실적 (PL 비교용: 작년 같은 기간 누적 판매/입고)
        prev_ytd_sub = df_prev_ytd[['품목코드', '판매출고_금액', '입고계_금액']]
        prev_ytd_sub.columns = ['품목코드', '전년동기_누적판매', '전년동기_누적입고']
        
        # 최종 병합
        comp_df = pd.merge(base_df, prev_full_sub, on='품목코드', how='left')
        comp_df = pd.merge(comp_df, prev_ytd_sub, on='품목코드', how='left').fillna(0)
        
        # --- 계산 컬럼 ---
        # 1. 재무상태표(BS) 관점: 전기말 대비 재고 증감
        comp_df['BS_재고증감액'] = comp_df['당기말_재고'] - comp_df['전기말_재고']
        
        # 2. 손익계산서(PL) 관점: 전년 동기 대비 누적 판매 실적 증감
        comp_df['PL_판매실적증감'] = comp_df['당기_누적판매'] - comp_df['전년동기_누적판매']

        # --- 대시보드 출력 ---
        st.markdown(f"### 🔍 {target_group} 재무 비교 (YTD)")
        
        # 요약 지표 카드
        m1, m2, m3 = st.columns(3)
        m1.metric("당기말 재고총액", f"{comp_df['당기말_재고'].sum():,.0f}", 
                  delta=f"{comp_df['BS_재고증감액'].sum():,.0f} (vs 전기말)")
        m2.metric("당기 누적 판매액", f"{comp_df['당기_누적판매'].sum():,.0f}", 
                  delta=f"{comp_df['PL_판매실적증감'].sum():,.0f} (vs 전년동기)")
        m3.metric("전기말 재고총액", f"{comp_df['전기말_재고'].sum():,.0f}")

        # 상세 테이블 (가독성을 위해 정렬 및 선택)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        
        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            comp_df.to_excel(writer, index=False, sheet_name='YTD_Financial_Analysis')
        st.download_button(label="📥 YTD 분석 결과 다운로드", data=output.getvalue(), file_name=f"YTD_Analysis_{target_group}.xlsx")

else:
    st.warning("💡 **당기 누적**, **전기 전체(12월)**, **전년 동기 누적** 3개 파일을 업로드해 주세요.")
