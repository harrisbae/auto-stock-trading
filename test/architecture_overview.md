# 볼린저 밴드 트레이딩 시스템 아키텍처 개요

## 시스템 구조

본 프로젝트는 볼린저 밴드 기반의 주식 거래 신호 생성 시스템으로, 다음과 같은 주요 구성 요소로 이루어져 있습니다.

```
auto-stock-trading/
│
├── main.py                 # 메인 실행 파일
├── main.sh                 # 다중 종목 실행 스크립트
├── requirements.txt        # 의존성 목록
│
├── src/                    # 코어 소스 코드
│   ├── __init__.py
│   ├── config.py           # 설정 및 상수 정의
│   ├── signal.py           # 신호 생성 로직
│   ├── indicators.py       # 기술적 지표 계산
│   ├── stock_data.py       # 주식 데이터 처리
│   ├── slack_notifier.py   # Slack 알림 전송
│   └── utils.py            # 유틸리티 함수
│
├── test/                   # 테스트 코드
│   ├── test_mfi_filter.py       # MFI 필터 테스트
│   ├── test_band_riding.py      # 밴드타기 감지 테스트
│   ├── test_risk_management.py  # 위험 관리 테스트
│   ├── test_bollinger_strategy.py  # 기본 전략 테스트
│   └── run_all_tests.py         # 통합 테스트 실행
│
├── backtest/               # 백테스트 관련 코드
│   ├── results/                 # 백테스트 결과
│   │   └── spy_backtest_analysis.md  # SPY 백테스트 분석
│   │
│   └── new_test/               # 새로운 백테스트 모듈
│       └── spy_strategy_comparison.py  # 전략 비교 모듈
│
└── docs/                   # 문서
    ├── 볼린저밴드_전략_요약.md   # 전략 설명
    └── 시스템_종합요약_kr.md     # 시스템 요약
```

## 주요 컴포넌트 설명

### 1. 코어 로직 (src/)

#### `config.py`
- 전역 설정 및 상수 정의
- 매매 임계값 설정 (BUY_B_THRESHOLD, SELL_B_THRESHOLD 등)
- MFI 필터 임계값 설정 (BUY_MFI_THRESHOLD, SELL_MFI_THRESHOLD)

#### `signal.py`
- 핵심 거래 신호 생성 로직
- `generate_signal()`: 볼린저 밴드와 MFI 기반 신호 생성
- `generate_target_signal()`: 목표 수익률 기반 신호 생성
- `get_trading_advice()`: 매매 신호에 따른 조언 생성
- `generate_trading_signal()`: 통합 매매 신호 생성

#### `indicators.py`
- 기술적 지표 계산 함수
- 볼린저 밴드, MFI, 이동평균 등 계산
- `add_all_indicators()`: 모든 지표를 데이터프레임에 추가

#### `stock_data.py`
- Yahoo Finance API 연동
- 주식 데이터 다운로드 및 전처리
- 기간별 데이터 조회 기능

#### `slack_notifier.py`
- Slack Webhook을 통한 알림 전송
- 매매 신호, 차트 이미지 등 전송
- 알림 포맷팅 및 에러 처리

### 2. 메인 모듈

#### `main.py`
- 명령행 인수 처리
- 전략 설정 및 환경 구성
- 스케줄링 및 즉시 실행 모드 지원
- 다음 주요 기능 구현:
  - `detect_band_riding()`: 밴드타기 감지
  - `calculate_tranche_strategy()`: 트랜치 전략 계산
  - `adjust_strategy_by_risk_level()`: 위험 수준별 전략 조정

#### `main.sh`
- 다양한 종목에 대한 일괄 분석 실행
- 명령행 옵션 설정 (트랜치, 손절, MFI 필터 등)
- 결과 저장 및 로깅

### 3. 테스트 모듈 (test/)

#### `test_mfi_filter.py`
- MFI 필터 기능 테스트
- 과매수/과매도 상태 감지 정확성 검증
- 매매 신호 필터링 및 성과 개선 검증

#### `test_band_riding.py`
- 밴드타기 감지 기능 테스트
- 다양한 밴드타기 패턴(일반/강한/약한) 감지 검증
- 거래량 및 추세 강도 분석 검증

#### `test_risk_management.py`
- 위험 관리 전략 테스트
- 변동성 기반 트랜치 비율 조정 검증
- 손절매 전략 작동 여부 확인

#### `test_bollinger_strategy.py`
- 볼린저 밴드 기본 전략 테스트
- 매수/매도 신호 생성 검증
- 목표 수익률 도달 시 행동 검증

### 4. 백테스트 모듈 (backtest/)

#### `spy_strategy_comparison.py`
- 다양한 전략 설정으로 SPY 백테스트
- Buy & Hold 전략과 비교 분석
- 성과 지표 계산 및 시각화

## 핵심 로직 흐름

### 1. 거래 신호 생성 프로세스

```
데이터 수집 → 지표 계산 → 밴드타기 감지 → 신호 생성 → 위험 관리 적용 → 알림 전송
```

1. `stock_data.py`를 통해 Yahoo Finance에서 데이터 수집
2. `indicators.py`를 통해 볼린저 밴드, MFI 등 기술적 지표 계산
3. `main.py`의 `detect_band_riding()`으로 밴드타기 현상 감지
4. `signal.py`의 `generate_trading_signal()`로 매매 신호 생성
5. 위험 수준에 따라 `adjust_strategy_by_risk_level()`로 전략 조정
6. `slack_notifier.py`를 통해 Slack으로 신호 알림 전송

### 2. MFI 필터 적용 로직

```
%B 값 계산 → MFI 값 계산 → 임계값 비교 → 신호 필터링 → 최종 신호 결정
```

1. 볼린저 밴드 기반 %B 값 계산 (%B < 0.2: 매수 대상, %B > 0.8: 매도 대상)
2. MFI 값 계산 (과매수/과매도 상태 판별)
3. MFI 임계값과 비교 (MFI < 20: 과매도, MFI > 80: 과매수)
4. MFI 필터 기준에 맞지 않는 신호 제거
5. 최종 거래 신호 및 조언 생성

### 3. 밴드타기 감지 로직

```
연속 상단밴드 접촉 확인 → 거래량 증가 패턴 분석 → 추세 강도 계산 → 밴드타기 판정
```

1. `lookback` 기간 동안의 %B 값 분석
2. 연속적으로 상단밴드에 접촉하는 일수 계산
3. 거래량 증가 패턴 분석 (강한 추세 감지)
4. 상승일 비율 및 상승 강도 계산
5. 밴드타기 강도(일반/강한) 판정 및 메시지 생성

### 4. 위험 관리 및 트랜치 전략

```
변동성 계산 → 위험 수준 설정 → 트랜치 비율 조정 → 손절 전략 설정
```

1. 주가 변동성 계산
2. 사용자 지정 위험 수준(low/medium/high) 적용
3. 위험 수준과 변동성에 따른 트랜치 비율 조정
4. 손절매 전략 설정 및 적용

## 확장 및 통합 아키텍처

시스템은 다음과 같은 외부 서비스 및 도구와 통합됩니다:

1. **데이터 소스**: Yahoo Finance API
2. **알림 서비스**: Slack Webhook
3. **시각화**: Matplotlib (차트 생성)
4. **스케줄링**: 내장 스케줄러

## 기술 스택

- **언어**: Python 3.9+
- **데이터 처리**: pandas, numpy
- **금융 데이터**: yfinance
- **시각화**: matplotlib
- **통신**: requests (Slack API)
- **테스트**: unittest
- **문서화**: Markdown

## 설계 원칙

1. **모듈성**: 기능별로 분리된 모듈 구조로 유지보수 용이
2. **확장성**: 새로운 지표, 전략, 필터 쉽게 추가 가능
3. **테스트 가능성**: 각 기능에 대한 단위 테스트 지원
4. **구성 가능성**: 명령행 인수를 통한 다양한 설정 지원

## 향후 확장 방향

1. **머신러닝 통합**: 예측 모델 및 최적화 알고리즘 추가
2. **분산 처리**: 다수 종목 동시 분석을 위한 분산 시스템
3. **웹 대시보드**: 실시간 모니터링 및 설정 인터페이스
4. **알고리즘 다양화**: 추가적인 트레이딩 전략 및 지표 구현 