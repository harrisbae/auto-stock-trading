# MA Target Price Strategy Backtest Results

## Test Environment
- **Test Period**: 2022-05-31 ~ 2025-04-25 (1060 days)
- **Initial Capital**: $10,000.00
- **Target Security**: SPY (S&P 500 ETF)

## Strategy Description
This backtest analyzed trading strategies based on moving averages (MA) with a 5% target price range:

1. **MA20 5% Strategy**:
   - Buy Signal: Price falls below 5% under the 20-day moving average
   - Sell Signal: Price rises above 5% over the 20-day moving average

2. **MA25 5% Strategy**:
   - Buy Signal: Price falls below 5% under the 25-day moving average
   - Sell Signal: Price rises above 5% over the 25-day moving average

3. **Benchmark**: Simple Buy and Hold strategy

## Backtest Results

### 1. Final Portfolio Value
- **MA20 5% Strategy**: $12,474.30 (Profit: $2,474.30)
- **MA25 5% Strategy**: $9,879.76 (Profit: -$120.24)
- **Buy and Hold**: $13,932.35 (Profit: $3,932.35)

### 2. Annual Return
- **MA20 5% Strategy**: 7.91%
- **MA25 5% Strategy**: -0.42%
- **Buy and Hold**: 12.10%

### 3. Maximum Drawdown (MDD)
- **MA20 5% Strategy**: -6.33%
- **MA25 5% Strategy**: -18.88%
- **Buy and Hold**: -18.76%

### 4. Sharpe Ratio
- **MA20 5% Strategy**: 0.579
- **MA25 5% Strategy**: -0.122
- **Buy and Hold**: 0.609

### 5. Trading Activity
- **MA20 5% Strategy**: 17 trades (Average: 5.9 per year)
- **MA25 5% Strategy**: 19 trades (Average: 6.5 per year)

### 6. Strategy Differences
- **Signal Differences**: 133 occurrences (18.24% of trading days)
- **Days MA20 outperformed MA25**: 70 days (9.60%)
- **Days MA20 underperformed MA25**: 63 days (8.64%)

## Analysis and Conclusion

1. **Performance Comparison**:
   - MA20 5% strategy outperformed the MA25 5% strategy by 26.26%
   - MA20 5% strategy yielded positive returns, while MA25 5% strategy resulted in a slight loss
   - Both strategies underperformed the simple buy and hold strategy

2. **Risk Management**:
   - MA20 5% strategy demonstrated superior risk management with a significantly lower maximum drawdown (-6.33%)
   - MA25 5% strategy's maximum drawdown (-18.88%) was similar to the buy and hold strategy

3. **Efficiency**:
   - Risk-adjusted return (Sharpe ratio) of the MA20 5% strategy (0.579) was significantly better than the MA25 5% strategy (-0.122)
   - Buy and hold strategy had the highest Sharpe ratio (0.609)

4. **Practical Considerations**:
   - MA20 5% strategy had fewer trades than MA25 5% strategy (17 vs 19), making it more advantageous in terms of transaction costs
   - MA20 5% strategy is evaluated as a balanced strategy providing adequate returns with lower risk

5. **Conclusion**:
   - The buy and hold strategy achieved the highest returns as the market was generally bullish during the test period
   - However, the MA20 5% strategy was significantly superior in terms of risk management
   - In bear markets or markets with high volatility, the MA20 5% strategy could potentially be more effective
   - Strategy selection should be considered based on the investor's risk preference and market conditions 