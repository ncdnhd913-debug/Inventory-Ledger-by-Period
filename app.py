import streamlit as st
import pandas as pd
import plotly.express as px
import io

# 페이지 설정
st.set_page_config(page_title="기간별 수불 분석 시스템", layout="wide")

st.title("📦 Periodic Inventory Ledger Analysis")
st.markdown("ERP에서 다운로드한 수불부 데이터를 업로드하여 품목군 및 기간별 현황을 확인하세요.")

# 1. 데이터 전처리 함수
def load_and_clean_data(file, year, month):
    try:
        # 데이터 읽기 (CSV/Excel 모두 대응 가능하도록 처리)
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None)
        else:
            df_raw = pd.read_excel(file, header=None)
        
        # 헤더 생성 (0행의 대분류와 1행의 소분류 결합)
        header_main = df_raw.iloc[0].ffill() # nan 값을 앞의 값으로 채움
        header_sub = df_raw.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(header_main, header_sub):
            col_name = f"{m}_{s}".strip("_") if s != '' else str(m)
            new_cols.append(col_name)
        
        # 데이터프레임 재구성
        df = df_raw.iloc[2:].copy()
        df.columns = new_cols
        
        # 수치형 데이터 변환 (콤마 제거 등)
        cols_to_fix = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
        df['년도'] = year
        df['월'] = month
        return df
    except Exception as e:
        st.error(f"파일 처리 오류 ({file.name}): {e}")
        return None

# 2. 사이드바 - 파일 업로드
with st.sidebar:
    st.header("📂 데이터 소스")
    uploaded_files = st.file_uploader("수불부 파일을 업로드하세요", accept_multiple_files=True, type=['csv', 'xlsx'])
    
    all_data = []
    if uploaded_files:
        for file in uploaded_files:
            with st.expander(f"설정: {file.name}"):
                y = st.selectbox("년도", [2024, 2025, 2026], index=1, key=f"y_{file.name}")
                m = st.selectbox("월", list(range(1, 13)), index=0, key=f"m_{file.name}")
                processed_df = load_and_clean_data(file, y, m)
                if processed_df is not None:
                    all_data.append(processed_df)

# 3. 데이터 분석 및 시각화
if all_data:
    df_combined = pd.concat(all_data, ignore_index=True)
    
    # 상단 필터
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_groups = st.multiselect("품목계정그룹", options=df_combined['품목계정그룹'].unique(), default=df_combined['품목계정그룹'].unique())
    with c2:
        selected_years = st.multiselect("조회 년도", options=sorted(df_combined['년도'].unique()), default=df_combined['년도'].unique())
    with c3:
        selected_months = st.multiselect("조회 월", options=sorted(df_combined['월'].unique()), default=df_combined['월'].unique())

    # 필터 적용
    mask = (df_combined['품목계정그룹'].isin(selected_groups)) & \
           (df_combined['년도'].isin(selected_years)) & \
           (df_combined['월'].isin(selected_months))
    df_final = df_combined[mask]

    # 주요 지표 (KPI)
    st.subheader("📌 요약 지표")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("기초재고 총액", f"{df_final['기초재고_금액'].sum():,.0f}")
    k2.metric("총 입고금액", f"{df_final['입고계_금액'].sum():,.0f}")
    k3.metric("총 출고금액", f"{df_final['출고계_금액'].sum():,.0f}")
    k4.metric("기말재고 총액", f"{df_final['기말재고_금액'].sum():,.0f}")

    # 차트 분석
    tab1, tab2 = st.tabs(["📊 시각화 분석", "📄 상세 데이터"])
    
    with tab1:
        # 그룹별 기말재고 비중
        fig_group = px.pie(df_final, values='기말재고_금액', names='품목계정그룹', title='품목계정그룹별 기말재고 비중')
        st.plotly_chart(fig_group, use_container_width=True)
        
        # 월별 입출고 추이
        df_monthly = df_final.groupby(['년도', '월'])[['입고계_금액', '출고계_금액']].sum().reset_index()
        df_monthly['Date'] = df_monthly['년도'].astype(str) + "-" + df_monthly['월'].astype(str).str.zfill(2)
        fig_trend = px.line(df_monthly, x='Date', y=['입고계_금액', '출고계_금액'], title='월별 입출고 추이 (금액 기준)', markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

    with tab2:
        # 원하는 컬럼만 선택하여 노출
        display_cols = ['년도', '월', '품목계정그룹', '품목코드', '품목명', '기초재고_수량', '입고계_수량', '출고계_수량', '기말재고_수량']
        st.dataframe(df_final[display_cols], use_container_width=True)
        
        # 엑셀 다운로드 기능
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='수불부_분석')
        st.download_button(label="📥 분석 결과 엑셀 다운로드", data=output.getvalue(), file_name="inventory_analysis.xlsx")

else:
    st.info("사이드바에서 ERP 엑셀 또는 CSV 파일을 업로드해주세요.")
