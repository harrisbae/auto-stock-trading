#!/bin/bash
# 다양한 ETF 및 채권 종목에 대한 주식 거래 신호 모니터링 스크립트
# 각 종목마다 구매가와 목표 수익률(10%)을 설정하여 즉시 분석을 실행합니다.
# 사용법: ./main.sh

# 추가 옵션 설정
# --tranche_count: 분할 매수 단계 설정 (기본값: 3단계)
# --stop_loss_percent: 손절 비율 설정 (기본값: 7%)
# --band_riding_detection: 밴드타기 감지 옵션 (밴드 상단에 연속 접촉 시 알림)
# --risk_management_level: 위험 관리 수준 설정 (low, medium, high)
# --use_mfi_filter: MFI 필터 적용 여부 (과매수/과매도 상태 기반 매매 신호 필터링)
# --force_notify: 매매 신호가 없어도 알림을 강제로 보냄

# 공통 옵션 설정
TRANCHE="--tranche_count 3"
STOP_LOSS="--stop_loss_percent 7"
BAND_RIDING="--band_riding_detection" 
RISK_MANAGEMENT="--risk_management_level medium"
MFI_FILTER="--use_mfi_filter"
FORCE_NOTIFY=""  # 기본적으로 비활성화

# 명령줄 인수 처리
for arg in "$@"; do
  case $arg in
    --force-notify|--force_notify)
      FORCE_NOTIFY="--force_notify"
      echo "알림 강제 전송 옵션이 활성화되었습니다."
      ;;
  esac
done

# 출력 포맷 개선을 위한 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 종목 정보 배열 정의 (티커/구매가/목표수익률)
declare -a STOCKS=(
    "GLD/304.00/10"      # S&P 500 ETF
 #   "SCHD/25.0587/10"    # 배당주 ETF
 #   "O/56.69/10"         # Realty Income Corporation (부동산 투자 신탁)
 #  "JEPQ/49.051/10"     # JPMorgan Nasdaq Equity Premium Income ETF
 #   "BIL/91.5077/10"     # SPDR Bloomberg 1-3 Month T-Bill ETF (단기 국채)
 #   "SGOV/100.58/10"     # iShares 0-3 Month Treasury Bond ETF (초단기 국채)
 #   "TLT/87.2767/10"     # iShares 20+ Year Treasury Bond ETF (장기 국채)
 #   "TLTW/23.1991/10"    # TLT Warrants (TLT 옵션)
)

# 종목 설명 배열 정의 (배열 순서는 STOCKS와 일치해야 함)
declare -a DESCRIPTIONS=(
    "GOLD ETF"
 #   "배당주 ETF"
 #   "부동산 투자 신탁"
 #   "JPMorgan Nasdaq Equity Premium Income ETF"
 #   "단기 국채"
 #   "초단기 국채"
 #   "장기 국채"
 #   "TLT 옵션"
)

# 포맷팅 함수 정의
print_header() {
    echo
    echo -e "${BOLD}${BLUE}=============================================================${NC}"
    echo -e "${BOLD}${BLUE}[분석 결과: $1 - $2]${NC}"
    echo -e "${BOLD}${BLUE}=============================================================${NC}"
}

print_footer() {
    echo -e "${BLUE}-------------------------------------------------------------${NC}"
    echo
}

print_signal() {
    local signal=$1
    
    if [[ "$signal" == *"Buy"* ]]; then
        echo -e "${BOLD}${GREEN}신호: $signal${NC}"
    elif [[ "$signal" == *"Sell"* ]]; then
        echo -e "${BOLD}${RED}신호: $signal${NC}"
    else
        echo -e "${BOLD}${YELLOW}신호: $signal${NC}"
    fi
}

print_details() {
    # 메시지를 보기 좋게 출력
    echo -e "${CYAN}[분석 실행 중...]${NC}"
    echo
    
    # 티커 정보만 사용하여 명령 실행
    python main.py --ticker "$1" $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT $MFI_FILTER $FORCE_NOTIFY
    
    # 출력 결과 여부에 관계없이 성공 상태로 반환
    return 0
}

# 스크립트 사용법 출력
print_usage() {
    echo -e "${BOLD}자동 주식 거래 신호 모니터링 스크립트 사용법${NC}"
    echo -e "사용법: $0 [옵션]"
    echo
    echo -e "옵션:"
    echo -e "  --force-notify, --force_notify\t매매 신호가 없어도 알림을 강제로 보냅니다."
    echo
}

# 도움말 요청 확인
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    print_usage
    exit 0
fi

# 종목별 분석 실행
for ((i=0; i<${#STOCKS[@]}; i++)); do
    STOCK_INFO=${STOCKS[$i]}
    DESCRIPTION=${DESCRIPTIONS[$i]}
    
    # 티커 심볼과 파라미터 분리
    TICKER=${STOCK_INFO%/*}  # / 앞부분(티커)만 추출
    
    # 포맷된 헤더 출력
    print_header "${DESCRIPTION}" "${TICKER}"
    
    # 분석 결과 출력
    print_details "$TICKER"
    
    # 포맷된 푸터 출력
    print_footer
done

echo -e "${BOLD}모든 종목 분석이 완료되었습니다.${NC}"