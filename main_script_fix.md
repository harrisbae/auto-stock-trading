# 자동 주식 거래 신호 모니터링 스크립트 문제 해결

## 문제 상황
`main.sh` 스크립트 실행 시 발생하던 오류를 해결했습니다. 스크립트는 다양한 ETF 및 채권 종목에 대한 매매 신호를 모니터링하고 분석하는 기능을 담당하고 있었으나, 명령줄 인수 형식 불일치로 정상 실행되지 않았습니다.

## 문제 원인
스크립트에서 사용하던 명령줄 인수 형식이 `main.py` 파이썬 스크립트에서 실제로 지원하는 인수 형식과 달랐습니다.

### 주요 불일치 사항
1. **인수 형식의 차이**:
   - 원래 사용: `--tranche=3`, `--stop-loss=7`, `--band-riding=true`
   - 실제 지원: `--tranche_count 3`, `--stop_loss_percent 7`, `--band_riding_detection`

2. **미지원 인수 사용**:
   - `--now`, `--purchase-price`, `--target-gain` 등은 현재 `main.py`에서 지원되지 않음

## 해결 방법

### 1. 인수 이름 및 형식 변경
```diff
- TRANCHE="--tranche=3"
- STOP_LOSS="--stop-loss=7"
- BAND_RIDING="--band-riding=true" 
- RISK_MANAGEMENT="--risk-management=medium"
- MFI_FILTER="--mfi-filter=true"
+ TRANCHE="--tranche_count 3"
+ STOP_LOSS="--stop_loss_percent 7"
+ BAND_RIDING="--band_riding_detection" 
+ RISK_MANAGEMENT="--risk_management_level medium"
+ MFI_FILTER="--use_mfi_filter"
```

### 2. 명령 실행 부분 간소화
```diff
- # 명령 실행 및 모든 출력 표시
- python main.py --now \
-   --ticker "$1" \
-   --purchase-price "$2" \
-   --target-gain "$3" \
-   $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT $MFI_FILTER
+ # 티커 정보만 사용하여 명령 실행
+ python main.py --ticker "$1" $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT $MFI_FILTER
```

### 3. 불필요한 변수 제거
```diff
# 티커 심볼과 파라미터 분리
TICKER=${STOCK_INFO%/*}  # / 앞부분(티커)만 추출
- PRICE_TARGET=${STOCK_INFO#*/}  # / 뒷부분(가격/목표수익률)만 추출
- PRICE=${PRICE_TARGET%/*}  # 가격 추출
- TARGET=${PRICE_TARGET#*/}  # 목표수익률 추출

# 분석 결과 출력
- print_details "$TICKER" "$PRICE" "$TARGET"
+ print_details "$TICKER"
```

### 4. 강제 알림 옵션 추가
스크립트에 강제 알림 옵션을 추가하여 매매 신호가 없는 경우에도 알림을 받을 수 있는 기능을 구현했습니다.

```diff
+ # --force_notify: 매매 신호가 없어도 알림을 강제로 보냄
+
  # 공통 옵션 설정
  TRANCHE="--tranche_count 3"
  STOP_LOSS="--stop_loss_percent 7"
  BAND_RIDING="--band_riding_detection" 
  RISK_MANAGEMENT="--risk_management_level medium"
  MFI_FILTER="--use_mfi_filter"
+ FORCE_NOTIFY=""  # 기본적으로 비활성화
+ 
+ # 명령줄 인수 처리
+ for arg in "$@"; do
+   case $arg in
+     --force-notify)
+       FORCE_NOTIFY="--force_notify"
+       echo "알림 강제 전송 옵션이 활성화되었습니다."
+       ;;
+   esac
+ done
```

명령 실행 시 강제 알림 옵션을 전달하도록 수정:

```diff
  # 티커 정보만 사용하여 명령 실행
- python main.py --ticker "$1" $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT $MFI_FILTER
+ python main.py --ticker "$1" $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT $MFI_FILTER $FORCE_NOTIFY
```

또한 사용자 친화적인 도움말 기능을 추가했습니다:

```bash
# 스크립트 사용법 출력
print_usage() {
    echo -e "${BOLD}자동 주식 거래 신호 모니터링 스크립트 사용법${NC}"
    echo -e "사용법: $0 [옵션]"
    echo
    echo -e "옵션:"
    echo -e "  --force-notify\t매매 신호가 없어도 알림을 강제로 보냅니다."
    echo
}

# 도움말 요청 확인
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    print_usage
    exit 0
fi
```

## 수정 후 결과

스크립트가 성공적으로 실행되어 모든 종목에 대한 분석이 완료되었습니다. 주요 결과:

### BIL (단기 국채)
- **신호**: 매도 
- **원인**: %B 값 0.9311로 상단 밴드 접근, MFI 100.00으로 과매수 상태
- **밴드타기**: 5일 연속 상단밴드 접촉 (강도: 56%)
- **추천 전략**: 보유 물량의 30-50% 매도 및 중심선 하향 돌파 시 잔여 물량 매도 고려

### SGOV (초단기 국채)
- **신호**: 매도 
- **원인**: %B 값 0.9356로 상단 밴드 접근, MFI 94.48로 과매수 상태
- **밴드타기**: 5일 연속 상단밴드 접촉 (강도: 57%)
- **특이사항**: 강한 상승 추세 감지
- **추천 전략**: 트레일링 스탑 전략으로 이익 보호하며 추세 추종

### TLT (장기 국채)
- **신호**: 관망
- **MFI**: 27.44로 하락 추세 강함, 하단 돌파 가능성
- **추천 전략**: 추세 방향성 관찰 필요

### 기타 종목
- SPY, SCHD, O, JEPQ: 관망 신호로 뚜렷한 매매 신호 없음
- TLTW: 중심선 상향 돌파, MFI 22.11로 하락 추세 강함

## 결론

명령줄 인수 형식을 올바르게 수정함으로써, ETF 및 채권 종목에 대한 자동 모니터링 및 알림 시스템이 정상 작동하게 되었습니다. 특히 밴드타기 현상 감지 및 차별화된 전략 추천 기능이 제대로 작동하는 것을 확인했습니다.

추가적으로 구현한 강제 알림 옵션(`--force-notify`)을 통해 매매 신호가 없는 종목에 대해서도 필요 시 알림을 받을 수 있게 되어, 더욱 유연한 모니터링이 가능해졌습니다. 이 옵션은 다음과 같이 사용할 수 있습니다:

```bash
./main.sh --force-notify
``` 