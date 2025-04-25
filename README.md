# auto-stock-trading

# PLTR 실전 매매 자동화 + Slack 알림 시스템

## 1. 목표
- PLTR 주가를 모니터링하여 매수/매도 신호를 자동으로 감지
- 신호 발생 시 Slack 채널에 실시간 알림 전송

## 2. 시스템 구성도
```
[Yahoo Finance 데이터] --> [Python 분석] --> [매수/매도 신호 판단] --> [Slack 알림]
```

## 3. 필요한 준비물

| 항목 | 설명 |
|:---|:---|
| Slack 워크스페이스 | Slack 가입 및 워크스페이스 생성 |
| Slack 채널 | 알림 받을 채널 생성 (예: #trading-signal) |
| Incoming Webhook | Slack에서 Webhook URL 생성 |
| Python 3 환경 | 필요한 패키지는 requirements.txt 참조 |

## 4. 설치 및 설정 방법

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

## 5. 사용 방법

### 즉시 실행
현재 PLTR 주식의 매매 신호를 확인하려면:
```bash
python main.py --now
```

### 스케줄러 실행
매일 정해진 시간(기본값: 오전 6시)에 자동으로 신호를 확인하도록 설정:
```bash
python main.py --schedule
```

## 6. 프로젝트 구조
```
auto-stock-trading/
├── main.py                  # 메인 실행 파일
├── requirements.txt         # 필요한 패키지 목록
├── .env                     # 환경 변수 설정 (직접 생성 필요)
├── README.md                # 프로젝트 설명
└── src/                     # 소스 코드 디렉토리
    ├── __init__.py          # 패키지 초기화 파일
    ├── config.py            # 설정 파일
    ├── stock_data.py        # 주식 데이터 관련 기능
    ├── indicators.py        # 기술적 지표 계산 기능
    ├── signal.py            # 매매 신호 생성 기능
    └── notification.py      # Slack 알림 관련 기능
```

## 7. 커스터마이징

### 다른 주식으로 변경
`src/config.py` 파일에서 `TICKER` 값을 변경하여 다른 주식을 모니터링할 수 있습니다.

### 기술적 지표 변경
`src/config.py` 파일에서 다음 값들을 조정할 수 있습니다:
- MA_PERIOD: 이동평균선 기간
- BOLLINGER_BANDS_STD: 볼린저 밴드 표준편차
- MFI_PERIOD: MFI 계산 기간
- BUY_B_THRESHOLD, BUY_MFI_THRESHOLD: 매수 신호 임계값
- SELL_B_THRESHOLD, SELL_MFI_THRESHOLD: 매도 신호 임계값

### 스케줄링 시간 변경
`main.py` 파일의 `run_scheduler` 함수에서 `schedule.every().day.at("06:00")` 부분을 원하는 시간으로 변경하세요.

## 8. 참고사항
- Webhook URL은 외부 유출 금지
- Slack 무료 플랜에서도 충분히 운영 가능
- 주가 변동이 적을 때는 "Hold" 신호가 반복될 수 있음


