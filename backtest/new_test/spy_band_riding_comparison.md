# SPY Strategy Comparison Analysis - Band Riding Effect (5 Year Data)

## 1. Performance Summary

| Strategy | Total Return | Annual Return | Max Drawdown | Final Asset | Trade Count |
|------|----------|------------|---------|-----------|--------|
| Buy & Hold | 99.99% | 14.91% | 24.24% | $19998.89 | 1 |
| With Band Riding | 28.65% | 5.18% | 8.71% | $12864.90 | 107 |
| Without Band Riding | 26.75% | 4.87% | 8.83% | $12675.32 | 90 |
| With MFI Filter | 39.17% | 6.85% | 5.18% | $13917.28 | 22 |

## 2. Strategy Parameters

### Common Parameters
- **Split Purchase Count**: 3
- **Stop Loss Percentage**: 7%
- **Target Profit Percentage**: 10%
- **Risk Level**: medium

### Variable Parameters
- **Band Riding Detection**: True vs False
- **MFI Filter**: With MFI strategy uses stricter conditions (Buy: MFI < 20, Sell: MFI > 80)

## 3. Strategy Analysis

### With Band Riding
- **Total Trades**: 107
- **Buy Trades**: 57
- **Sell Trades**: 50

**Sell Reasons**:
- 익절: 31 times (62.0%)
- 밴드타기 매도: 16 times (32.0%)
- 목표 수익률 도달: 1 times (2.0%)
- 손절매: 2 times (4.0%)

### Without Band Riding
- **Total Trades**: 90
- **Buy Trades**: 57
- **Sell Trades**: 33

**Sell Reasons**:
- 익절: 31 times (93.9%)
- 손절매: 2 times (6.1%)

### With MFI Filter
- **Total Trades**: 22
- **Buy Trades**: 9
- **Sell Trades**: 13

**Sell Reasons**:
- 목표 수익률 도달: 3 times (23.1%)
- 밴드타기 매도: 9 times (69.2%)
- 손절매: 1 times (7.7%)

## 4. Key Differences

### Without Band Riding vs. With Band Riding
- **Return Difference**: -1.90% lower
- **Max Drawdown Difference**: 0.12% higher
- **Trade Count Difference**: 17 fewer trades

### With MFI Filter vs. With Band Riding
- **Return Difference**: 10.52% higher
- **Max Drawdown Difference**: 3.53% lower
- **Trade Count Difference**: 85 fewer trades

## 5. Conclusion

### MFI Filter Value

- **Positive Impact**: Strict MFI filtering (Buy < 20, Sell > 80) improves strategy performance
- Using strict MFI thresholds helped identify better entry and exit points

### Recommendation

- **Band Riding Detection**: Recommended as it improves performance
- **MFI Filter**: Recommended with strict thresholds (Buy < 20, Sell > 80)

The optimal strategy depends on specific market conditions and investor's risk tolerance. These results are based on historical data and may not predict future performance.