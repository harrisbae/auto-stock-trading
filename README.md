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
- **기술적 지표 모니터링**: 
  - 볼린저 밴드 %B와 MFI 지표를 활용한 매수/매도 신호 생성
  - BNF의 볼린저 밴드 전략 기반 25일 이동평균선(MA25) 활용 매매 신호
- **목표 수익률 모니터링**: 설정한 구매가 기준 목표 수익률 달성 시 알림
- **Slack 알림**: 중요 신호 발생 시 Slack으로 실시간 알림
- **스케줄링**: 매일 정해진 시간에 자동으로 신호 확인 및 알림
- **다양한 종목 지원**: 명령줄 인자로 원하는 종목 지정 가능
- **분할 매수 전략**: 총 투자 자금을 여러 단계로 나누어 매수하는 전략
- **손절매 전략**: 투자 손실을 제한하기 위한 전략
- **밴드타기 현상 감지**: 주가가 볼린저 밴드의 상단에 연속적으로 접촉하며 상승하는 현상 감지
- **위험 관리 수준 설정**: 투자자의 위험 감수 성향에 따라 매매 전략을 조정

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

### 새로운 전략 옵션
```bash
# 분할 매수 전략 설정
python main.py --now --stock-info SPY/508.62/10 --tranche=5 --stop-loss=5 --risk-management=high
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
└── docs/                    # 문서 디렉토리
    ├── README.md            # 문서 개요
    └── bollinger_bands_strategy.md # 볼린저 밴드 전략 설명
```

## 8. 커스터마이징

### 기본 종목 변경
`src/config.py` 파일에서 `DEFAULT_TICKER` 값을 변경하여 기본 모니터링 종목을 변경할 수 있습니다.

### 기술적 지표 임계값 변경
`src/config.py` 파일에서 다음 값들을 조정할 수 있습니다:
- `BOLLINGER_BANDS_STD`: 볼린저 밴드 표준편차 (기본값: 2)
- `MFI_PERIOD`: MFI 계산 기간 (기본값: 14)
- `BUY_B_THRESHOLD`: 매수 신호 %B 임계값 (기본값: 0.2)
- `BUY_MFI_THRESHOLD`: 매수 신호 MFI 임계값 (기본값: 20)
- `SELL_B_THRESHOLD`: 매도 신호 %B 임계값 (기본값: 0.8)
- `SELL_MFI_THRESHOLD`: 매도 신호 MFI 임계값 (기본값: 80)

### 스케줄링 시간 변경
`main.py` 파일의 `run_scheduler` 함수에서 `schedule.every().day.at("06:00")` 부분을 원하는 시간으로 변경하세요.

## 9. 신호 종류 설명

프로그램은 다음과 같은 신호를 제공합니다:

1. **BNF 볼린저 밴드 전략 신호**: 25일 이동평균선(MA25)을 기준으로 다음 신호 생성
   - `Buy_Strong`: MA25 대비 20% 이상 하락하고 %B < 0.2 (급락 후 반등 매수 신호)
   - `Buy`: MA25 대비 15% 하락 후 소폭 반등, %B < 0.3, MFI < 30 (반등 시작 매수 신호)
   - `Sell`: MA25 대비 10% 이상 상승, %B > 0.8, MFI > 70 (과매수 매도 신호)
   - `Breakout_Buy`: 밴드 폭 축소(스퀴즈) 후 상단 돌파 시 매수 신호 (거래량 증가 동반)
   - `Hold`: 위 조건에 해당하지 않을 때

2. **목표가 신호**: 설정한 구매가 대비 목표 수익률 도달 여부
   - `Target_Reached`: 현재 가격이 목표 수익률을 달성했을 때
   - `Hold`: 목표 수익률에 도달하지 않았을 때

3. **최종 신호**: 위 두 신호를 종합한 최종 판단
   - 목표가 신호가 `Target_Reached`이면 최종 신호도 `Target_Reached`
   - 그렇지 않으면 BNF 전략 신호를 최종 신호로 사용

## 10. 참고사항
- Webhook URL은 외부 유출 금지 (.env 파일은 .gitignore에 포함됨)
- Slack 무료 플랜에서도 충분히 운영 가능
- 주가 변동이 적을 때는 "Hold" 신호가 반복될 수 있음
- 설정한 구매가가 현재 가격보다 높으면 수익률은 음수로 표시됨

## 11. BNF 볼린저 밴드 전략

[일본의 전설적 트레이더 BNF의 전략](docs/bollinger_bands_strategy.md)을 기반으로 매매 신호를 생성합니다:

- **MA25 활용**: 25일 이동평균선을 중심으로 한 볼린저 밴드 구성
- **이격도 활용**: MA25 대비 주가 이격도에 따른 매매 판단
  - 20~35% 하락 후 -15% 수준으로 반등 시 매수 포인트
  - 밴드 상단 돌파 시 돌파 매매
- **분할 매매**: 하단선 터치 시 일부 매수, 중심선 도달 시 일부 익절, 상단선 터치 시 남은 물량 정리
- **추세 판단**: 밴드 폭 축소 후 상단 돌파 시 강한 추세 예상

## 12. 분할 매수 전략 설명

분할 매수 전략은 총 투자 자금을 여러 단계로 나누어 매수하는 전략입니다. 이 전략을 통해 시장의 변동성에 대비하고 평균 매수 가격을 최적화할 수 있습니다.

- **기본 원칙**: 하단밴드 터치 시 첫 매수하고, 추가 하락 시 평균단가를 낮추는 전략
- **매수 단계**: 
  - **첫 매수**: 하단밴드 터치 시(%B ≤ 0.2) 총 자금의 20-30% 투입
  - **추가 매수**: 추가 하락 시(%B ≤ 0.1) 총 자금의 30-35% 추가 투입하여 평균단가 낮춤
  - **최종 매수**: 급락 시(%B ≤ 0.05) 총 자금의 35-40% 안전망 구축
- **익절 전략**:
  - **MA25(중심선) 도달 시**: 보유 물량의 50% 익절 고려
  - **중심선 돌파 시**: 남은 물량 유지하며 상단밴드 터치까지 홀딩
  - **상단밴드 접근 시**: 남은 물량 전량 매도 검토

## 13. 손절매 전략 설명

손절매 전략은 투자 손실을 제한하기 위한 전략입니다. 이 전략은 매매 유형에 따라 다르게 적용됩니다.

- **매매 유형별 손절 전략**:
  - **돌파 매매의 경우**: 밴드 상단선 아래로 내려올 때 손절 (상단선 = %B < 0.8 지점)
  - **하단 매수의 경우**: 추가 하락 시 손절보다는 평균단가 낮추기 전략 사용
    - 이는 손절이 아닌 비용절감 및 매수 기회로 활용하는 접근법

- **일반적인 손절 기준**:
  - 위험 수준에 따른 손절 비율 적용 (기본값: 7%)
  - 저위험: 5% 이내
  - 중위험: 7% 내외
  - 고위험: 10% 이상

- **손절 시점 판단**:
  - 돌파 매매: 볼린저 밴드 상단선 하향 돌파 시
  - 하단 매수: 진입가 대비 설정 비율 이상 하락 시 추가 매수 검토

## 14. 밴드타기 현상 설명

밴드타기 현상은 주가가 볼린저 밴드의 상단에 연속적으로 접촉하며 상승하는 현상입니다. 이는 강한 상승 추세를 의미하지만, 상황에 따라 다른 대응이 필요합니다.

- **밴드타기 감지 방법**:
  - 최근 5일 동안 %B 값이 0.8 이상인 날을 확인
  - 연속 3일 이상 상단밴드 접촉 시 밴드타기로 간주
  - 밴드타기 강도(0-100%)를 계산하여 대응 전략 차별화

- **강한 상승 추세에서의 대응**:
  - 가격 상승일이 70% 이상이고 거래량 증가 또는 %B가 0.9 이상일 때 강한 추세로 판단
  - 이 경우 단순 상단 접촉만으로 매도하지 않고 **추세를 지속적으로 관찰**
  - 트레일링 스탑(Trailing Stop) 전략으로 이익을 보호하며 추세 추종
  - 주가가 밴드 상단을 따라 상승하는 동안 추세 모멘텀 활용

- **일반적인 밴드타기에서의 대응**:
  - 강도 70% 이상: 조만간 추세 전환 가능성 높음 - 이익실현 고려
  - 강도 40-70%: 중간 강도 - 분할 매도 검토
  - 강도 40% 미만: 약한 밴드타기 - 주의 관찰

- **밴드타기 종료 신호**:
  - %B 값이 0.5 아래로 하락 (중심선 아래로 하락)
  - 거래량 급증 후 주가 하락

## 15. 위험 관리 전략 설명

위험 관리는 투자자의 자산을 보호하고 시장 변동성에 효과적으로 대응하기 위한 전략입니다. 다음 네 가지 주요 원칙을 기반으로 합니다.

- **분할 매매로 리스크 분산**:
  - 모든 자금을 한 번에 투입/회수하지 않고 여러 단계로 나누어 매매
  - 매수 시 위험 수준별 분할 전략:
    - 저위험: 총 4-5회 나누어 진입, 한 번에 15-20% 자금만 투입
    - 중위험: 총 3회 나누어 진입, 한 번에 25-30% 자금 투입
    - 고위험: 총 2회 나누어 진입, 한 번에 40-50% 자금 투입
  - 매도 시 위험 수준별 분할 전략:
    - 저위험: 총 2회 나누어 90% 이상 매도, 첫 매도에 70% 실현
    - 중위험: 총 3회 나누어 70-80% 매도, 가격에 따라 분할 실현
    - 고위험: 총 3-4회 나누어 50-70% 매도, 나머지는 추세 유지 시 홀딩

- **MFI 지표 병행 확인**:
  - 매수/매도 시점에 MFI(Money Flow Index) 지표를 함께 확인하여 신호 강도 검증
  - 매수 시 MFI 20 이하(과매도)면 매수 신호 강화, 50 이상이면 매수 시점 재검토
  - 매도 시 MFI 80 이상(과매수)이면 매도 신호 강화, 50 이하면 매도 시점 재검토
  - 볼린저 밴드와 MFI 지표가 일치할 때 신호 신뢰도 상승

- **추세 변화 시 신속한 대응 (밴드 기울기 변화 주시)**:
  - 볼린저 밴드의 기울기 변화를 지속적으로 모니터링하여 추세 전환 조기 감지
  - 상승 추세: 밴드 기울기가 상승 중일 때 (%B > 0.5이면 상승 모멘텀 활용)
  - 하락 추세: 밴드 기울기가 하락 중일 때 (%B < 0.5이면 하락 가속화 가능성 주의)
  - 횡보장: 밴드 기울기가 중립일 때 (추세 감소, 전환 가능성 고려)
  - 매수 최적 시점: 하단밴드 기울기가 수평/상승으로 전환될 때
  - 매도 최적 시점: 상단밴드 기울기가 수평/하락으로 전환될 때

- **목표 수익률 도달 시 일부 이익 실현**:
  - 목표 수익률의 70% 도달 시 일부 이익 실현 시작
  - 위험 수준별 익절 전략 (목표 수익률 100% 달성 시):
    - 저위험: 보유 물량의 80-90% 익절
    - 중위험: 보유 물량의 50-70% 익절 후 나머지는 추가 상승에 대비
    - 고위험: 보유 물량의 30-50% 익절 후 추세 유지 여부에 따라 결정
  - 부분 익절을 통해 원금을 보호하면서도 추가 상승에 따른 이익 가능성 유지

## 16. 라이센스

MIT License

## 17. 스케줄러 활용 방법

스케줄러를 사용하면 정해진 시간에 자동으로 주식 데이터를 분석하고 매매 신호를 확인할 수 있습니다.

### 기본 스케줄러 설정
```bash
# 기본 설정으로 스케줄러 실행 (기본 종목, 매일 오전 6시 실행)
python main.py --schedule
```

### 스케줄러 실행 옵션
```bash
# 특정 종목으로 스케줄러 실행
python main.py --schedule --ticker AAPL

# 분할 매수 전략과 함께 스케줄러 실행
python main.py --schedule --ticker TSLA --tranche=3 --risk-management=medium

# 목표 수익률 감시와 함께 스케줄러 실행
python main.py --schedule --stock-info NVDA/450.75/15

# 특정 시간에 스케줄러 실행 (오전 9시)
python main.py --schedule --schedule-time "09:00"

# 특정 시간에 특정 종목 분석 및 강제 알림 설정
python main.py --schedule --schedule-time "16:30" --ticker MSFT --force-notify
```

### 스케줄 시간 변경
스케줄 실행 시간을 변경하려면 `main.py` 파일의 `run_scheduler` 함수에서 다음 부분을 수정하세요:
```python
# 기본값: 매일 오전 6시 실행
schedule.every().day.at("06:00").do(job)

# 수정 예: 주중(월-금) 오전 9시와 오후 4시에 실행
schedule.every().monday.to.friday.at("09:00").do(job)
schedule.every().monday.to.friday.at("16:00").do(job)
```

### 스케줄러 실행 주기 정보
스케줄러는 기본적으로 **매일 1회** 지정된 시간(기본값: 오전 6시)에 실행됩니다. 스케줄러가 실행되면 다음 동작을 수행합니다:

1. 설정된 종목의 최신 주가 데이터를 가져옵니다.
2. 기술적 지표(볼린저 밴드, %B, MFI 등)를 계산합니다.
3. 매매 신호를 생성합니다.
4. 매수/매도 신호가 발생하면 Slack으로 알림을 전송합니다.
5. `force_notify` 옵션이 활성화된 경우 매매 신호가 없어도 일일 보고서를 전송합니다.

스케줄러는 설정된 시간 이후 계속 실행 상태를 유지하며, 다음 예정된 시간에 자동으로 작업을 수행합니다.

### 스케줄러 백그라운드 실행
Linux/macOS 환경에서 백그라운드로 스케줄러를 실행하는 방법:
```bash
# 기본 백그라운드 실행
nohup python main.py --schedule > trading_log.txt 2>&1 &

# 특정 종목과 시간 지정하여 백그라운드 실행
nohup python main.py --schedule --ticker AAPL --schedule-time "09:30" > apple_trading_log.txt 2>&1 &

# 여러 옵션을 적용하여 백그라운드 실행
nohup python main.py --schedule --ticker TSLA --schedule-time "10:00" --force-notify --tranche=5 > tesla_trading_log.txt 2>&1 &
```

Windows 환경에서 작업 스케줄러를 이용한 실행 방법:
1. 작업 스케줄러 열기
2. 기본 작업 만들기 선택
3. 트리거: 매일 또는 원하는 간격 설정
4. 동작: 프로그램 시작 선택, `python`과 인자로 `main.py --schedule` 입력

## 18. 언어 설정

이 프로그램은 한국어(ko)와 영어(en) 두 가지 언어를 지원합니다. 원하는 언어로 시스템 메시지와 알림을 받을 수 있습니다.

### 언어 설정 방법
1. **환경 변수로 설정**:
   `.env` 파일에 다음 설정을 추가하여 기본 언어를 설정할 수 있습니다:
   ```
   LANGUAGE=ko  # 한국어 (기본값)
   # 또는
   LANGUAGE=en  # 영어
   ```

2. **코드에서 설정**:
   언제든지 코드에서 직접 언어를 변경할 수 있습니다:
   ```python
   from src.config import set_language
   
   # 한국어로 설정
   set_language('ko')
   
   # 영어로 설정
   set_language('en')
   ```

3. **명령줄에서 설정**:
   ```bash
   # 영어로 실행
   python main.py --now --language en
   
   # 한국어로 실행
   python main.py --now --language ko
   ```

### 지원 기능
- 거래 신호 메시지
- 거래 이유 설명
- Slack 알림 메시지
- 콘솔 출력 메시지

기본 언어는 한국어(ko)로 설정되어 있습니다.

## 언어 설정 방법

이 애플리케이션은 한국어(기본값)와 영어를 지원합니다. 언어 설정 방법은 다음과 같습니다:

### 1. 명령줄 인자로 설정

프로그램 실행 시 `--language` 인자를 사용하여 언어를 설정할 수 있습니다.

```bash
# 영어로 설정
python main.py --ticker AAPL --language en

# 한국어로 설정
python main.py --ticker AAPL --language ko
```

### 2. 환경 변수로 설정

`.env` 파일에 `LANGUAGE` 환경 변수를 추가하여 기본 언어를 설정할 수 있습니다:

```
LANGUAGE=en  # 영어
```
또는
```
LANGUAGE=ko  # 한국어
```

### 3. 코드에서 직접 설정

`src/config.py` 파일에서 기본 언어를 변경할 수 있습니다:

```python
# .env에서 언어 설정 로드 (기본값 설정)
LANGUAGE = os.getenv('LANGUAGE', 'ko')  # 'ko'를 'en'으로 변경하면 영어가 기본값이 됩니다
```

프로그램에서 영어를 사용하면 모든 거래 신호, 메시지, 이유 등이 영어로 표시됩니다.


