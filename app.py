import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="회계 수불 증감 분석 시스템", layout="wide")

st.title("⚖️ Financial Inventory Analysis (Variance Report)")

# 1. 데이터 전처리 함수 (보강됨)
def process_inventory_data(file):
    if file is None: return None
    try:
        # 파일 읽기
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None)
        else:
            df_raw = pd.read_excel(file, header=None)
        
        # 헤더 결합 로직
        header_main = df_raw.iloc[0].ffill()
        header_sub = df_raw.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(header_main, header_sub):
            col_name = f"{m}_{s}".strip("_") if s != '' else str(m)
            new_cols.append(col_name)
        
        df = df_raw.iloc[2:].copy()
        df.columns = new_cols
        
        # 품목계정그룹 정제 (공백 제거 중요)
        df = df[df['품목계정그룹'].notna()]
        df['품목계정그룹'] = df['품목계정그룹'].astype(str).str.strip()
        df = df[df['품목계정그룹'] != '']
        
        # 이름 통일
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        
        # 숫자 변환
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"⚠️ {file.name} 처리 중 오류 발생: {e}")
        return None

# 2. 세션 상태 초기화 (메인 로직 실행 전)
if 'current_group' not in st.session_state:
    st.session_state.current_group = '원재료' # 기본값을 샘플에 많은 '원재료'로 설정

# 3. 사이드바: 분석 기준 및 파일 업로드
with st.sidebar:
    st.header("📅 분석 기준 설정")
    target_year = st.number_input("기준 년도", value=2026)
    X = st.selectbox("기준 월(X)", options=list(range(1, 13)), index=0)
    prev_X = X - 1 if X > 1 else 12
    
    st.divider()
    st.subheader("📁 분석 파일 업로드")
    f_curr_m = st.file_uploader(f"(1) 당월 ({X}월)", type=['csv', 'xlsx'])
    f_prev_m = st.file_uploader(f"(2) 전월 ({prev_X}월)", type=['csv', 'xlsx'])
    f_curr_ytd = st.file_uploader(f"(3) 당기 누적 (1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_ytd = st.file_uploader(f"(4) 전기 동기 누적 (전기 1월~{X}월)", type=['csv', 'xlsx'])
    f_prev_full = st.file_uploader(f"(5) 전기 전체 (전기 1월~12월)", type=['csv', 'xlsx'])

# 4. 메인 화면 로직
files = [f_curr_m, f_prev_m, f_curr_ytd, f_prev_ytd, f_prev_full]
file_names = ["당월", "전월", "당기누적", "전기동기누적", "전기전체"]

if all(f is not None for f in files):
    # 데이터 로드
    d_curr_m = process_inventory_data(f_curr_m)
    d_prev_m = process_inventory_data(f_prev_m)
    d_curr_ytd = process_inventory_data(f_curr_ytd)
    d_prev_ytd = process_inventory_data(f_prev_ytd)
    d_prev_full = process_inventory_data(f_prev_full)

    # 로드 성공 여부 최종 확인
    data_list = [d_curr_m, d_prev_m, d_curr_ytd, d_prev_ytd, d_prev_full]
    if any(d is None for d in data_list):
        st.error("일부 파일 로드에 실패했습니다. 컬럼 구성을 확인해주세요.")
    else:
        # 그룹 선택 버튼 UI
        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        st.subheader(f"📋 {st.session_state.current_group} 계정 증감 분석")
        btn_cols = st.columns(len(groups))
        
        for i, group in enumerate(groups):
            if btn_cols[i].button(group, use_container_width=True):
                st.session_state.current_group = group
        
        target_group = st.session_state.current_group

        # 데이터 병합 및 필터링
        base = d_curr_m[d_curr_m['품목계정그룹'] == target_group][['품목코드', '품목명', '단위', '생산출고_금액', '판매출고_금액', '기말재고_금액']]
        
        if base.empty:
            st.warning(f"🔔 현재 업로드된 데이터에 '{target_group}' 그룹에 해당하는 품목이 없습니다. 다른 버튼을 클릭해 보세요.")
            # 어떤 그룹들이 존재하는지 안내
            existing_groups = d_curr_m['품목계정그룹'].unique()
            st.info(f"현재 파일 내 품목군: {', '.join(existing_groups)}")
        else:
            base.columns = ['품목코드', '품목명', '단위', '당월_생산출고', '당월_판매출고', '당월말_재고']

            # 비교 데이터 구성
            prev_m = d_prev_m[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전월_생산출고', '판매출고_금액':'전월_판매출고'})
            curr_ytd = d_curr_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'당기누적_생산출고', '판매출고_금액':'당기누적_판매출고'})
            prev_ytd = d_prev_ytd[['품목코드', '생산출고_금액', '판매출고_금액']].rename(columns={'생산출고_금액':'전기동기_생산출고', '판매출고_금액':'전기동기_판매출고'})
            prev_full = d_prev_full[['품목코드', '기말재고_금액']].rename(columns={'기말재고_금액':'전기말_재고'})

            # 최종 병합
            comp = base.merge(prev_m, on='품목코드', how='left').merge(curr_ytd, on='품목코드', how='left')\
                       .merge(prev_ytd, on='품목코드', how='left').merge(prev_full, on='품목코드', how='left').fillna(0)

            # 증감 계산
            comp['제조원가_YoY증감'] = comp['당기누적_생산출고'] - comp['전기동기_생산출고']
            comp['판매원가_YoY증감'] = comp['당기누적_판매출고'] - comp['전기동기_판매출고']
            comp['재고_전기말대비증감'] = comp['당월말_재고'] - comp['전기말_재고']

            # KPI 카드
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric(f"{X}월말 재고잔액", f"{comp['당월말_재고'].sum():,.0f}", f"{comp['재고_전기말대비증감'].sum():,.0f} (vs 전기말)")
            m2.metric("누적 판매원가(PL)", f"{comp['당기누적_판매출고'].sum():,.0f}", f"{comp['판매원가_YoY증감'].sum():,.0f} (vs 전년동기)")
            m3.metric("누적 제조원가(Cost)", f"{comp['당기누적_생산출고'].sum():,.0f}", f"{comp['제조원가_YoY증감'].sum():,.0f} (vs 전년동기)")

            # 상세 탭
            t1, t2, t3 = st.tabs(["🏛️ 재무상태표(재고)", "💰 매출원가(판매)", "🛠️ 제조원가(생산)"])

            with t1:
                st.write("📌 **전기말 대비 재고 증감 순위**")
                bs_view = comp[['품목코드', '품목명', '전기말_재고', '당월말_재고', '재고_전기말대비증감']].sort_values(by='재고_전기말대비증감', ascending=False)
                st.dataframe(bs_view, use_container_width=True, hide_index=True)

            with t2:
                st.write("📌 **누적 판매원가 증감 순위** (전년 동기 대비)")
                pl_sales_view = comp[['품목코드', '품목명', '전기동기_판매출고', '당기누적_판매출고', '판매원가_YoY증감']].sort_values(by='판매원가_YoY증감', ascending=False)
                st.dataframe(pl_sales_view, use_container_width=True, hide_index=True)

            with t3:
                st.write("📌 **누적 제조원가 증감 순위** (전년 동기 대비)")
                pl_cost_view = comp[['품목코드', '품목명', '전기동기_생산출고', '당기누적_생산출고', '제조원가_YoY증감']].sort_values(by='제조원가_YoY증감', ascending=False)
                st.dataframe(pl_cost_view, use_container_width=True, hide_index=True)

            # 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                comp.sort_values(by='재고_전기말대비증감', ascending=False).to_excel(writer, index=False, sheet_name='종합증감분석')
            st.download_button("📥 종합 증감 분석 결과 다운로드", data=output.getvalue(), file_name=f"Inventory_Analysis_{X}M.xlsx")
else:
    # 파일 업로드 체크리스트 (사용자 안내용)
    st.info(f"💡 분석을 시작하려면 사이드바에 **{X}월 기준** 5개 파일을 모두 업로드해 주세요.")
    
    check_cols = st.columns(5)
    for i, (f, label) in enumerate(zip(files, file_names)):
        if f is not None:
            check_cols[i].success(f"✅ {label} 완료")
        else:
            check_cols[i].error(f"❌ {label} 대기")
