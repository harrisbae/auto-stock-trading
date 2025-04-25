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
| Python 3 환경 | requests, pandas, numpy, yfinance 설치 필요 |


## 4. Slack Webhook 설정 방법

1. Slack 로그인
2. [Incoming Webhooks](https://slack.com/apps/A0F7XDUAZ-incoming-webhooks) 앱 추가
3. Webhook URL 생성 및 복사


## 5. Python 코드 (최종 버전)

```python
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Slack Webhook URL 입력
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/XXX/YYY/ZZZ'

# Slack 알림 함수
def send_slack_message(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print("Slack 메시지 전송 성공!")
    else:
        print("Slack 메시지 전송 실패:", response.text)

# MFI 계산 함수
def calculate_mfi(df, period=14):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    positive_flow = []
    negative_flow = []

    for i in range(1, len(typical_price)):
        if typical_price[i] > typical_price[i-1]:
            positive_flow.append(money_flow[i])
            negative_flow.append(0)
        else:
            positive_flow.append(0)
            negative_flow.append(money_flow[i])

    positive_mf = pd.Series(positive_flow).rolling(window=period).sum()
    negative_mf = pd.Series(negative_flow).rolling(window=period).sum()
    mfi = 100 * (positive_mf / (positive_mf + negative_mf))
    return mfi

# PLTR 데이터 다운로드 및 신호 생성
def check_trading_signal():
    ticker = 'PLTR'
    df = yf.download(ticker, period='6mo', interval='1d')

    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['UpperBand'] = df['MA20'] + (2 * df['STD'])
    df['LowerBand'] = df['MA20'] - (2 * df['STD'])
    df['%B'] = (df['Close'] - df['LowerBand']) / (df['UpperBand'] - df['LowerBand'])
    df['MFI'] = calculate_mfi(df)

    latest = df.iloc[-1]
    signal = "Hold"

    if latest['%B'] < 0.2 and latest['MFI'] < 20:
        signal = "Buy"
    elif latest['%B'] > 0.8 and latest['MFI'] > 80:
        signal = "Sell"

    message = f"[PLTR]\n가격: ${latest['Close']:.2f}\n%B: {latest['%B']:.2f}\nMFI: {latest['MFI']:.2f}\n신호: {signal}"

    if signal in ["Buy", "Sell"]:
        send_slack_message(message)
    else:
        print("현재 특별한 신호 없음.")

# 메인 실행
if __name__ == "__main__":
    check_trading_signal()
```


## 6. 스케줄링 (옵션)
- 이 스크립트를 매일 자동 실행하려면:
  - 윈도우: 작업 스케줄러 사용
  - 리눅스/맥: crontab 사용


## 7. 참고사항
- Webhook URL은 외부 유출 금지
- Slack 무료 플랜에서도 충분히 운영 가능
- 주가 변동이 적을 때는 "Hold" 신호가 반복될 수 있음


