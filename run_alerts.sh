#!/bin/bash
# 다양한 ETF 및 채권 종목에 대한 주식 거래 신호 출력 스크립트
# format_output.py를 사용하여 알림 메시지를 생성하고 출력합니다.

# 종목 정보 배열 정의 (티커/구매가/목표수익률)
declare -a STOCKS=(
    "SPY/200.62/10"      # S&P 500 ETF
    "SCHD/25.0587/10"    # 배당주 ETF
    "O/56.69/10"         # Realty Income Corporation (부동산 투자 신탁)
    "JEPQ/49.051/10"     # JPMorgan Nasdaq Equity Premium Income ETF
    "BIL/91.5077/10"     # SPDR Bloomberg 1-3 Month T-Bill ETF (단기 국채)
    "SGOV/100.58/10"     # iShares 0-3 Month Treasury Bond ETF (초단기 국채)
    "TLT/87.2767/10"     # iShares 20+ Year Treasury Bond ETF (장기 국채)
    "TLTW/23.1991/10"    # TLT Warrants (TLT 옵션)
)

# 종목 설명 배열 정의 (배열 순서는 STOCKS와 일치해야 함)
declare -a DESCRIPTIONS=(
    "S&P 500 ETF"
    "배당주 ETF"
    "부동산 투자 신탁"
    "JPMorgan Nasdaq Equity Premium Income ETF"
    "단기 국채"
    "초단기 국채"
    "장기 국채"
    "TLT 옵션"
)

# 신호 유형 배열 (예시용)
declare -a SIGNALS=(
    "Hold"
    "Buy"
    "Hold"
    "Hold"
    "Sell"
    "Hold"
    "Hold"
    "Hold"
)

# %B 값 배열 (예시용)
declare -a B_VALUES=(
    "0.55"
    "0.15"
    "0.45"
    "0.60"
    "0.85"
    "0.40"
    "0.30"
    "0.65"
)

# MFI 값 배열 (예시용)
declare -a MFI_VALUES=(
    "52.4"
    "25.7"
    "48.3"
    "55.6"
    "82.1"
    "47.5"
    "38.9"
    "60.2"
)

# 이격도 배열 (예시용)
declare -a DEVIATION_VALUES=(
    "1.2"
    "-3.5"
    "-0.8"
    "2.1"
    "4.5"
    "-0.3"
    "-1.7"
    "2.8"
)

# 현재 가격 계산 함수
calculate_current_price() {
    local purchase_price=$1
    local deviation=$2
    
    # 이격도를 기반으로 현재 가격 계산
    local price=$(echo "$purchase_price * (1 + $deviation/100)" | bc -l)
    printf "%.2f" $price
}

# 종목별 분석 실행
for ((i=0; i<${#STOCKS[@]}; i++)); do
    STOCK_INFO=${STOCKS[$i]}
    DESCRIPTION=${DESCRIPTIONS[$i]}
    SIGNAL=${SIGNALS[$i]}
    B_VALUE=${B_VALUES[$i]}
    MFI_VALUE=${MFI_VALUES[$i]}
    DEVIATION=${DEVIATION_VALUES[$i]}
    
    # 티커 심볼과 파라미터 분리
    TICKER=${STOCK_INFO%/*}
    PRICE_TARGET=${STOCK_INFO#*/}
    PURCHASE_PRICE=${PRICE_TARGET%/*}
    TARGET=${PRICE_TARGET#*/}
    
    # 현재 가격 계산
    CURRENT_PRICE=$(calculate_current_price $PURCHASE_PRICE $DEVIATION)
    
    # 포맷된 출력 생성
    ./format_output.py \
      --ticker "$TICKER" \
      --purchase-price "$PURCHASE_PRICE" \
      --signal "$SIGNAL" \
      --b-value "$B_VALUE" \
      --mfi "$MFI_VALUE" \
      --deviation-percent "$DEVIATION" \
      --current-price "$CURRENT_PRICE"
done

echo "모든 종목 분석 결과 출력이 완료되었습니다." 