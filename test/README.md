# 볼린저 밴드 전략 테스트

이 폴더에는 볼린저 밴드 매매 전략의 다양한 측면을 테스트하기 위한 테스트 케이스가 포함되어 있습니다.

## 테스트 구성

1. **기본 볼린저 밴드 전략 테스트** (`test_bollinger_strategy.py`)
   - 볼린저 밴드 계산 검증
   - MFI 지표 계산 검증
   - 과매수/과매도 조건에서의 매수/매도 신호 테스트
   - 목표 수익률 도달 시 신호 발생 테스트

2. **스퀴즈 패턴 및 돌파 매수 테스트** (`test_squeeze_breakout.py`)
   - 밴드 폭 계산 및 스퀴즈 패턴 식별 테스트
   - 스퀴즈 후 상단 돌파 시 매수 신호 테스트
   - 거래량 증가 확인 테스트

3. **통합 테스트 러너** (`run_all_tests.py`)
   - 모든 테스트 케이스를 한 번에 실행하고 결과 보고

## 테스트 데이터

테스트에서는 다음과 같은 데이터 세트를 사용합니다:

1. **일반 데이터**: 랜덤하게 생성된 100일간의 주가 데이터
2. **과매수 데이터**: 마지막 5일간 지속적으로 상승하는 패턴
3. **과매도 데이터**: 마지막 5일간 지속적으로 하락하는 패턴
4. **스퀴즈 패턴 데이터**: 변동성 축소 후 상단 돌파하는 패턴

## 테스트 실행 방법

### 모든 테스트 실행
```bash
python test/run_all_tests.py
```

### 개별 테스트 실행
```bash
python test/test_bollinger_strategy.py
python test/test_squeeze_breakout.py
```

## 테스트 케이스 상세 설명

### 기본 볼린저 밴드 전략 테스트

1. **test_bollinger_bands_calculation**: 볼린저 밴드 계산이 올바르게 이루어지는지 검증
2. **test_mfi_calculation**: MFI 지표가 0~100 범위 내에서 계산되는지 검증
3. **test_buy_signal_oversold_condition**: 과매도 상태에서 매수 신호 발생 확인
4. **test_sell_signal_overbought_condition**: 과매수 상태에서 매도 신호 발생 확인
5. **test_hold_signal_normal_condition**: 일반 상태에서 홀드 신호 발생 확인
6. **test_target_reached_signal**: 목표 수익률 달성 시 신호 발생 확인

### 스퀴즈 패턴 및 돌파 매수 테스트

1. **test_band_width_calculation**: 밴드 폭 계산 검증
2. **test_breakout_buy_signal**: 스퀴즈 후 상단 돌파 매수 신호 발생 확인
3. **test_squeeze_pattern_identification**: 스퀴즈 패턴이 올바르게 식별되는지 검증

## 테스트 결과 해석

테스트가 성공적으로 완료되면 다음을 확인할 수 있습니다:

1. 볼린저 밴드와 관련 지표(%B, MFI)가 올바르게 계산됨
2. MA25 대비 이격도에 따른 매매 신호가 적절히 생성됨
3. 스퀴즈 패턴이 올바르게 감지되고 돌파 매수 신호가 발생함
4. 목표 수익률 도달 시 알림 신호가 정상적으로 생성됨 