import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 통합 분석", layout="wide")

# CSS를 통한 UI 보강
st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 95%; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 5px; }
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

# 시각적 스타일링 함수 (배경색 제거, 텍스트 중앙정렬, 합계행 시인성 강화)
def style_financial_df(df, diff_cols, text_cols, label_col='품목명'):
    if df.empty: return df
    
    num_cols = [c for c in df.columns if df[c].dtype != object and c != label_col]
    
    # 합계행 강조 함수 (진한 회색 배경 + 검은색 폰트)
    def highlight_total(row):
        if row.get(label_col) == '▶ 합계 (TOTAL)':
            return ['background-color: #B0BEC5 !important; color: #000000 !important; font-weight: 900 !important;'] * len(row)
        return [''] * len(row)
        
    styler = df.style.format("{:,.0f}", subset=num_cols)
    
    # 텍스트 열 중앙 정렬
    existing_text = [c for c in text_cols if c in df.columns]
    if existing_text:
        styler = styler.set_properties(subset=existing_text, **{'text-align': 'center'})
        
    # 숫자 열 우측 정렬
    if num_cols:
        styler = styler.set_properties(subset=num_cols, **{'text-align': 'right'})
        
    styler = styler.apply(highlight_total, axis=1)
                   
    # 증감 열 양수/음수 색상 적용
    existing_diff_cols = [c for c in diff_cols if c in df.columns]
    if existing_diff_cols:
        styler = styler.map(lambda x: 'color: #D32F2F; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 
                            else ('color: #1565C0; font-weight: bold;' if isinstance(x, (int, float)) and x < 0 else 'color: black'), 
                            subset=existing_diff_cols)
        
    return styler

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
