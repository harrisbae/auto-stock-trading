# Auto Stock Trading

자동화된 주식 거래 신호 모니터링 및 백테스팅 도구입니다.

## 개요

이 프로젝트는 다양한 기술적 지표를 기반으로 한 주식 거래 전략을 개발하고 백테스팅하기 위한 도구를 제공합니다. 주요 기능은 다음과 같습니다:

1. 실시간 주식 데이터 모니터링
2. 다양한 기술적 지표 기반 거래 신호 생성
3. 거래 전략 백테스팅
4. 성과 분석 및 시각화

## 설치 방법

```bash
git clone https://github.com/yourusername/auto-stock-trading.git
cd auto-stock-trading
pip install -r requirements.txt
```

## 사용 방법

### 실시간 거래 신호 모니터링

```bash
python main.py --ticker SPY --interval 1d
```

추가 옵션:
- `--webhook URL`: 슬랙 웹훅 URL 설정
- `--test-slack`: 슬랙 연결 테스트
- `--interval`: 데이터 조회 간격 (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo, 3mo)
- `--target`: 목표 수익률 설정 (기본값: 5%)

### 백테스팅 실행

다양한 백테스팅 스크립트를 제공합니다:

```bash
# 기본 백테스팅 (이동평균 기반)
python backtest_ma_strategy.py

# 부분 매매 전략 백테스팅 (다중 목표 수익률)
python backtest_target_partial_multi.py

# 볼린저 밴드 기반 백테스팅
python backtest_bollinger.py
```

## 주요 파일 구조

```
auto-stock-trading/
├── main.py                       # 메인 실행 파일
├── README.md                     # 프로젝트 설명
├── requirements.txt              # 필수 패키지 목록
├── src/
│   ├── config.py                 # 환경 설정
│   ├── trading_signal.py         # 거래 신호 생성 로직
│   └── utils.py                  # 유틸리티 함수
├── backtest_ma_strategy.py       # MA 전략 백테스팅
├── backtest_target_partial_multi.py  # 부분 매매 백테스팅
├── backtest_bollinger.py         # 볼린저 밴드 백테스팅
├── results/                      # 백테스팅 결과 그래프
│   └── *.png                     # 결과 그래프 파일
└── docs/                         # 백테스팅 결과 문서
    ├── README.md                     # 문서 개요
    ├── backtest_summary_all_strategies.md # 종합 결과 요약
    └── backtest_bollinger_bands.md   # 볼린저 밴드 전략 결과
```

## 백테스팅 전략

### 볼린저 밴드 전략
볼린저 밴드와 MFI 지표를 활용한 트레이딩 전략입니다. 자세한 내용은 [백테스팅 결과](docs/backtest_bollinger_bands.md)를 참조하세요.

### MA 전략
볼린저 밴드의 %B 지표를 기반으로 한 MA20과 MA25 전략입니다. 자세한 내용은 [백테스팅 결과](backtest_ma_results.md)를 참조하세요.

### 부분 매매 전략
목표 수익률(5%, 10%, 20%)에 따른 부분 매매 전략입니다. 자세한 내용은 [백테스팅 결과](backtest_target.md)를 참조하세요.

## 백테스팅 결과 문서

모든 백테스팅 전략의 결과를 종합적으로 분석하고 비교한 문서는 [docs 폴더](docs)에서 확인할 수 있습니다. 주요 문서는 다음과 같습니다:

- [종합 결과 요약](docs/backtest_summary_all_strategies.md) - 모든 전략의 성과 비교
- [볼린저 밴드 전략 결과](docs/backtest_bollinger_bands.md) - 볼린저 밴드 전략 상세 분석

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새로운 브랜치를 생성합니다: `git checkout -b feature/your-feature-name`
3. 변경사항을 커밋합니다: `git commit -m 'Add some feature'`
4. 포크한 저장소로 푸시합니다: `git push origin feature/your-feature-name`
5. Pull Request를 제출합니다.

## 라이센스

[MIT](LICENSE)


