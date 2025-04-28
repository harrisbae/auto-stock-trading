# SPY Strategy Comparison Analysis - Multiple Target Profits (5 Year Data)

## 1. Performance Summary

| Strategy | Total Return | Annual Return | Max Drawdown | Final Asset | Trade Count |
|------|----------|------------|---------|-----------|--------|
| Buy & Hold | 105.34% | 15.51% | 24.27% | $20534.22 | 1 |
| Bollinger (10% Target) | 28.65% | 5.18% | 10.61% | $12864.90 | 107 |
| Bollinger (30% Target) | 28.24% | 5.11% | 10.64% | $12824.01 | 111 |
| Bollinger (100% Target) | 28.24% | 5.11% | 10.64% | $12824.01 | 111 |

## 2. Strategy Parameters

### Common Parameters
- **Split Purchase Count**: 3
- **Stop Loss Percentage**: 7%
- **Band Riding Detection**: Yes
- **Risk Level**: medium

### Target Profit Variations
1. **Low Target (10%)**: Realize profits early, potentially missing large uptrends
2. **Medium Target (30%)**: Balance between quick profits and capturing trends
3. **High Target (100%)**: Hold positions for significant gains, potentially through downturns

## 3. Trading History Analysis

### Bollinger (10% Target)

**Target Profit**: 10%

**Total Trades**: 107
**Sell Reasons**:
- 익절: 31 times (62.0%)
- 밴드타기 매도: 16 times (32.0%)
- 목표 수익률 도달: 1 times (2.0%)
- 손절매: 2 times (4.0%)

### Bollinger (30% Target)

**Target Profit**: 30%

**Total Trades**: 111
**Sell Reasons**:
- 익절: 32 times (59.3%)
- 밴드타기 매도: 20 times (37.0%)
- 손절매: 2 times (3.7%)

### Bollinger (100% Target)

**Target Profit**: 100%

**Total Trades**: 111
**Sell Reasons**:
- 익절: 32 times (59.3%)
- 밴드타기 매도: 20 times (37.0%)
- 손절매: 2 times (3.7%)

## 4. Conclusion and Recommendations

### Performance Comparison

- **Buy & Hold** is the simplest strategy that performed well during the overall uptrend market.
- **Target Profit Strategies** show different trade-offs between capital preservation and upside potential.

### Recommended Strategy by Market Conditions

- **Bull Market**: Higher target profit (30-100%) to capture more upside
- **Bear Market**: Lower target profit (10%) with strict stop-loss to preserve capital
- **Sideways Market**: Medium target (30%) with band riding detection

### Risk vs. Reward

Setting a higher target profit seems to result in fewer trades and potentially higher returns in a strong bull market, but may expose the portfolio to larger drawdowns during market corrections. Lower targets realize profits earlier and might perform better in more volatile or range-bound markets.
