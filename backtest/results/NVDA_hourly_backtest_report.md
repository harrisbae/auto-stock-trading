# NVDA 시간 단위 백테스트 결과 요약

백테스트 기간: 2025-03-29 ~ 2025-04-28
데이터 포인트: 68개

![NVDA 백테스트 차트](NVDA_Default_Strategy_No_MFI_backtest.png)

## 전략별 성과

| 순위 | 전략 | 총 수익률 | 최대 낙폭 | 거래 횟수 | 승률 | 최종 자산 |
|------|------|-----------|-----------|-----------|------|----------|
| 1 | Default Strategy (No MFI) | -1.45% | 9.64% | 2 | 0.00% | $9854.80 |
| 2 | More Aggressive B Values | -1.45% | 9.64% | 2 | 0.00% | $9854.80 |
| 3 | Extreme B Values | -1.45% | 9.64% | 2 | 0.00% | $9854.80 |

## 최적 전략 파라미터

- **name**: Default Strategy (No MFI)
- **buy_b_threshold**: 0.2
- **sell_b_threshold**: 0.8
- **buy_mfi_threshold**: 20
- **sell_mfi_threshold**: 80
- **use_mfi_filter**: False

## 거래 기록

| 날짜 | 유형 | 가격 | 수량 | 거래액 |
|------|------|------|------|--------|
| 2025-04-16 13:30 | 매수 | $105.52 | 94 | $9918.88 |
| 2025-04-23 13:30 | 매도 | $104.18 | 94 | $9793.39 |

## 모든 전략의 차트

### Default Strategy (No MFI)

![Default Strategy (No MFI) 차트](NVDA_Default_Strategy_No_MFI_backtest.png)

### More Aggressive B Values

![More Aggressive B Values 차트](NVDA_More_Aggressive_B_Values_backtest.png)

### Extreme B Values

![Extreme B Values 차트](NVDA_Extreme_B_Values_backtest.png)

