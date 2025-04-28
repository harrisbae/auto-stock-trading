# Bollinger Bands Strategy Summary

## Bollinger Bands Indicator Overview
Bollinger Bands are indicators that visualize price volatility by drawing upper and lower bands using standard deviation around a moving average (MA) of the stock price. This system uses a 25-day moving average (MA25) and 2x standard deviation.

## %B Indicator
The %B indicator shows where the current price is positioned within the bands:
- 0 = Located at the lower band
- 0.5 = Located at the centerline (MA25)
- 1 = Located at the upper band
- Greater than 1 or less than 0 = Strong movement beyond the bands

## BNF Bollinger Bands Trading Strategy

### Buy Signal Types
1. **Buy_Strong (Strong Buy Signal)**
   - 20%+ decline from MA25
   - %B < 0.2 (oversold condition)
   - Buy at the point of rebound after a sharp decline

2. **Buy (Regular Buy Signal)**
   - 15% decline from MA25
   - %B < 0.3
   - MFI < 30 (capital outflow)
   - Buy at the point when the first rebound begins

3. **Breakout_Buy (Breakout Buy Signal)**
   - Upper band breakout after band squeeze
   - Accompanied by volume increase
   - Indicates the beginning of a strong uptrend

### Sell Signals
1. **Sell (Sell Signal)**
   - 10%+ rise from MA25
   - %B > 0.8 (overbought condition)
   - MFI > 70 (excessive capital inflow)
   - High probability of top formation

2. **Target_Reached (Target Price Reached)**
   - When target return compared to set purchase price is achieved

## Practical Trading Strategy

### Split Purchase Strategy
- First purchase with 20-30% of funds when touching the lower band
- Lower average cost on additional decline
- Consider 50% profit-taking when reaching the centerline (MA25)
- Maintain remaining position after confirming centerline breakout

### Stop-Loss Strategy
- For breakout trading: Stop loss when price falls below the upper band
- For lower band purchases: Lower average cost on additional decline

### Band Riding Phenomenon
- In strong uptrends, prices move along the upper band
- In this case, observe trend continuation rather than selling solely based on upper band touch

## Risk Management
- Risk distribution through split trading
- Concurrent verification with MFI indicator at buy/sell points
- Quick response to trend changes (monitor band slope changes)
- Partial profit realization when target return is reached

## Notification System
The system provides notifications via Slack under the following conditions:
- When technical buy/sell signals occur
- When target return is reached
- Upon forced notification request

## Indicator Threshold Settings
- BUY_B_THRESHOLD = 0.2
- BUY_MFI_THRESHOLD = 20
- SELL_B_THRESHOLD = 0.8
- SELL_MFI_THRESHOLD = 80 