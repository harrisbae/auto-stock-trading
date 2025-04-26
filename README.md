# auto-stock-trading

# 주식 거래 자동화 신호 + Slack 알림 시스템

## 1. 목표
- 주식 데이터를 모니터링하여 기술적 지표 기반 매수/매도 신호를 자동으로 감지
- 목표 수익률 달성 시 알림 기능 제공
- 신호 발생 시 Slack 채널에 실시간 알림 전송

## 2. 시스템 구성도
```
[Yahoo Finance 데이터] --> [Python 분석] --> [매수/매도/목표가 신호 판단] --> [Slack 알림]
```

## 3. 주요 기능
- **기술적 지표 모니터링**: 볼린저 밴드 %B와 MFI 지표를 활용한 매수/매도 신호 생성
- **목표 수익률 모니터링**: 설정한 구매가 기준 목표 수익률 달성 시 알림
- **Slack 알림**: 중요 신호 발생 시 Slack으로 실시간 알림
- **스케줄링**: 매일 정해진 시간에 자동으로 신호 확인 및 알림
- **다양한 종목 지원**: 명령줄 인자로 원하는 종목 지정 가능

## 4. 필요한 준비물

| 항목 | 설명 |
|:---|:---|
| Slack 워크스페이스 | Slack 가입 및 워크스페이스 생성 |
| Slack 채널 | 알림 받을 채널 생성 (예: #trading-signal) |
| Incoming Webhook | Slack에서 Webhook URL 생성 |
| Python 3 환경 | 필요한 패키지는 requirements.txt 참조 |

## 5. 설치 및 설정 방법

1. 저장소 클론
   ```bash
   git clone https://github.com/yourusername/auto-stock-trading.git
   cd auto-stock-trading
   ```

2. 가상환경 생성 및 활성화 (선택사항)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. 필요한 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```

4. Slack Webhook URL 설정
   - Slack 앱 설정에서 [Incoming Webhooks](https://slack.com/apps/A0F7XDUAZ-incoming-webhooks) 앱 추가
   - Webhook URL 생성 및 복사
   - 프로젝트 루트 디렉토리에 `.env` 파일 생성하고 URL 설정
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
   ```

## 6. 사용 방법

### 기본 사용법
```bash
python main.py [--now | --schedule] [--ticker TICKER] [--webhook WEBHOOK_URL] [--test-slack] [--force-notify] [--notify-method METHOD] [--use-blocks] [--purchase-price PRICE] [--target-gain PERCENT] [--stock-info TICKER/PRICE/GAIN]
```

### 즉시 실행 예제
```bash
# 기본 종목(PLTR) 즉시 분석
python main.py --now

# 특정 종목(AAPL) 분석
python main.py --now --ticker AAPL

# 목표 수익률 설정 (AAPL 주식, 구매가 $150.5, 목표 수익률 10%)
python main.py --now --stock-info AAPL/150.5/10

# 강제 알림 전송
python main.py --now --ticker MSFT --force-notify
```

### 스케줄러 실행 예제
```bash
# 기본 종목으로 스케줄러 실행
python main.py --schedule

# 특정 종목으로 스케줄러 실행
python main.py --schedule --ticker TSLA

# 목표 수익률 감시와 함께 스케줄러 실행
python main.py --schedule --stock-info NVDA/450.75/15
```

### 기타 기능
```bash
# Slack 알림 테스트
python main.py --test-slack

# 블록 형식의 Slack 알림 테스트
python main.py --test-slack --use-blocks

# 웹훅 URL 직접 설정
python main.py --now --webhook https://hooks.slack.com/services/XXX/YYY/ZZZ
```

## 7. 프로젝트 구조
```
auto-stock-trading/
├── main.py                  # 메인 실행 파일
├── requirements.txt         # 필요한 패키지 목록
├── .env                     # 환경 변수 설정 (직접 생성 필요)
├── .gitignore               # Git 무시 파일 목록
├── README.md                # 프로젝트 설명
└── src/                     # 소스 코드 디렉토리
    ├── __init__.py          # 패키지 초기화 파일
    ├── config.py            # 설정 파일
    ├── stock_data.py        # 주식 데이터 관련 기능
    ├── indicators.py        # 기술적 지표 계산 기능
    ├── signal.py            # 매매 신호 생성 기능
    └── notification.py      # Slack 알림 관련 기능
```

## 8. 커스터마이징

### 기본 종목 변경
`src/config.py` 파일에서 `DEFAULT_TICKER` 값을 변경하여 기본 모니터링 종목을 변경할 수 있습니다.

### 기술적 지표 임계값 변경
`src/config.py` 파일에서 다음 값들을 조정할 수 있습니다:
- `MA_PERIOD`: 이동평균선 기간 (기본값: 20)
- `BOLLINGER_BANDS_STD`: 볼린저 밴드 표준편차 (기본값: 2)
- `MFI_PERIOD`: MFI 계산 기간 (기본값: 14)
- `BUY_B_THRESHOLD`: 매수 신호 %B 임계값 (기본값: 0.2)
- `BUY_MFI_THRESHOLD`: 매수 신호 MFI 임계값 (기본값: 20)
- `SELL_B_THRESHOLD`: 매도 신호 %B 임계값 (기본값: 0.8)
- `SELL_MFI_THRESHOLD`: 매도 신호 MFI 임계값 (기본값: 80)

### 스케줄링 시간 변경
`main.py` 파일의 `run_scheduler` 함수에서 `schedule.every().day.at("06:00")` 부분을 원하는 시간으로 변경하세요.

## 9. 신호 종류 설명

프로그램은 세 가지 신호를 제공합니다:

1. **기술적 신호**: %B와 MFI 지표를 기반으로 계산
   - `Buy`: %B가 매수 임계값보다 낮고 MFI가 매수 임계값보다 낮을 때
   - `Sell`: %B가 매도 임계값보다 높고 MFI가 매도 임계값보다 높을 때
   - `Hold`: 위 조건에 해당하지 않을 때

2. **목표가 신호**: 설정한 구매가 대비 목표 수익률 도달 여부
   - `Target_Reached`: 현재 가격이 목표 수익률을 달성했을 때
   - `Hold`: 목표 수익률에 도달하지 않았을 때

3. **최종 신호**: 위 두 신호를 종합한 최종 판단
   - 목표가 신호가 `Target_Reached`이면 최종 신호도 `Target_Reached`
   - 그렇지 않으면 기술적 신호를 최종 신호로 사용

## 10. 참고사항
- Webhook URL은 외부 유출 금지 (.env 파일은 .gitignore에 포함됨)
- Slack 무료 플랜에서도 충분히 운영 가능
- 주가 변동이 적을 때는 "Hold" 신호가 반복될 수 있음
- 설정한 구매가가 현재 가격보다 높으면 수익률은 음수로 표시됨


