import streamlit as st
import pandas as pd
import io

# 페이지 설정
st.set_page_config(page_title="월간 상세 수불 현황 분석", layout="wide")

st.title("📂 Monthly Detailed Inventory Movement Analysis")

# 1. 데이터 전처리 및 정제 함수
def process_inventory_data(file):
    try:
        # 파일 확장자에 따라 읽기 방식 결정
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None)
        else:
            df_raw = pd.read_excel(file, header=None)
        
        # 헤더 결합 (0행: 대분류, 1행: 수량/금액)
        header_main = df_raw.iloc[0].ffill()
        header_sub = df_raw.iloc[1].fillna('')
        
        new_cols = []
        for m, s in zip(header_main, header_sub):
            col_name = f"{m}_{s}".strip("_") if s != '' else str(m)
            new_cols.append(col_name)
        
        # 데이터 본체 추출 및 컬럼 지정
        df = df_raw.iloc[2:].copy()
        df.columns = new_cols
        
        # [정제 규칙 1] 품목계정그룹이 없는 행 제외
        df = df[df['품목계정그룹'].notna()]
        df = df[df['품목계정그룹'].astype(str).str.strip() != '']
        
        # [정제 규칙 2] '제품(OEM)'을 '제품'으로 변경
        df['품목계정그룹'] = df['품목계정그룹'].replace('제품(OEM)', '제품')
        
        # 숫자 데이터 변환 (콤마 제거 및 수치화)
        numeric_cols = [c for c in df.columns if '수량' in c or '금액' in c]
        for col in numeric_cols:
            if df[col].dtype == object:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            else:
                df[col] = df[col].fillna(0)
            
        return df
    except Exception as e:
        st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
        return None

# 2. 사이드바: 분석 월 세팅
with st.sidebar:
    st.header("📅 분석 기간 설정")
    selected_month = st.selectbox(
        "분석하고자 하는 월을 선택하세요",
        [f"{i}월" for i in range(1, 13)],
        index=0
    )
    
    st.info(f"💡 **안내:** 현재 화면은 **{selected_month}** 현황을 분석합니다. \nERP에서 추출한 상세 수불 데이터를 업로드해주세요.")
    uploaded_file = st.file_uploader(f"{selected_month} 수불부 파일 업로드", type=['csv', 'xlsx', 'xls'])

# 3. 메인 화면
if uploaded_file:
    df_processed = process_inventory_data(uploaded_file)
    
    if df_processed is not None:
        st.success(f"{selected_month} 데이터 로드 완료")
        
        # 요약 정보
        st.subheader(f"📌 {selected_month} 전체 수불 요약")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("기초금액 합계", f"{df_processed.get('기초재고_금액', pd.Series([0])).sum():,.0f}")
        k2.metric("입고금액 합계", f"{df_processed.get('입고계_금액', pd.Series([0])).sum():,.0f}")
        k3.metric("출고금액 합계", f"{df_processed.get('출고계_금액', pd.Series([0])).sum():,.0f}")
        k4.metric("기말금액 합계", f"{df_processed.get('기말재고_금액', pd.Series([0])).sum():,.0f}")
        
        st.divider()
        
        # 품목계정그룹별 조회 버튼
        st.subheader("📋 품목계정그룹별 세부 현황")
        groups = ['제품', '상품', '반제품', '원재료', '부재료']
        cols = st.columns(len(groups))
        
        if 'current_group' not in st.session_state:
            st.session_state.current_group = '제품'

        for i, group in enumerate(groups):
            if cols[i].button(group, use_container_width=True):
                st.session_state.current_group = group
        
        target_group = st.session_state.current_group
        st.markdown(f"### 🔍 {target_group} 상세 내역")
        
        group_df = df_processed[df_processed['품목계정그룹'].astype(str).str.strip() == target_group]
        
        if not group_df.empty:
            # 표시할 상세 컬럼 정의 (요청하신 순서)
            base_info = ['공장', '품목코드', '품목명', '단위']
            
            # 수불 항목 리스트
            detail_categories = [
                '기초재고', '생산입고', '구매입고', '외주입고', '기타입고', '재고이전입고', '실사입고', '입고계', 
                '기초+입고', '생산출고', '판매출고', '외주출고', '기타출고', '재고이전출고', '실사출고', '출고계', '기말재고'
            ]
            
            # 수량/금액 컬럼 생성
            target_cols = []
            for cat in detail_categories:
                target_cols.append(f"{cat}_수량")
                target_cols.append(f"{cat}_금액")
            
            # 1. 실제 데이터프레임에 존재하는 컬럼만 필터링
            existing_cols = [c for c in target_cols if c in group_df.columns]
            
            # 2. 모든 행의 값이 0인 컬럼은 제외 (데이터가 없는 컬럼 제외 로직)
            valid_detail_cols = []
            for c in existing_cols:
                if (group_df[c] != 0).any():
                    valid_detail_cols.append(c)
            
            display_cols = base_info + valid_detail_cols
            
            # 표 출력
            st.dataframe(group_df[display_cols], use_container_width=True, hide_index=True)
            
            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                group_df[display_cols].to_excel(writer, index=False, sheet_name=target_group)
            st.download_button(
                label=f"📥 {target_group} 내역 다운로드",
                data=output.getvalue(),
                file_name=f"{selected_month}_{target_group}_상세수불.xlsx"
            )
        else:
            st.warning(f"데이터 내에 '{target_group}' 그룹에 해당하는 항목이 없습니다.")

else:
    st.warning("왼쪽 사이드바에서 분석할 월을 선택하고 해당 월의 ERP 파일을 업로드하세요.")
