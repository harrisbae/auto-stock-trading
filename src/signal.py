from src.config import (
    config,
    BUY_B_THRESHOLD, BUY_MFI_THRESHOLD,
    SELL_B_THRESHOLD, SELL_MFI_THRESHOLD,
    TICKER
)
import pandas as pd
import numpy as np
import sys

def generate_signal(df, use_mfi_filter=False):
    """
    Generate trading signals based on Bollinger Band %B and MFI indicators.
    
    Args:
        df (pandas.DataFrame): DataFrame with calculated indicators
        use_mfi_filter (bool): Whether to use MFI filter (filtering trading signals based on overbought/oversold conditions)
        
    Returns:
        tuple: (signal code, message)
    """
    if df is None or len(df) < 2:
        return "Hold", "데이터가 부족합니다."
    
    latest = df.iloc[-1]
    
    # Check required indicators
    required_indicators = ['%B']
    for indicator in required_indicators:
        if indicator not in latest:
            return "Hold", f"필수 지표({indicator})가 누락되었습니다."
    
    b_value = latest['%B']
    message_parts = []
    
    # Check MFI value (if available)
    mfi_value = None
    if 'MFI' in latest:
        mfi_value = latest['MFI']
    
    # Create data point
    data_point = {
        'date': df.index[-1],
        'close': latest['Close'] if 'Close' in latest else None,
        'b_value': b_value,
        'mfi': mfi_value,
        'upper_band': latest['UpperBand'] if 'UpperBand' in latest else None,
        'lower_band': latest['LowerBand'] if 'LowerBand' in latest else None,
        'use_mfi_filter': use_mfi_filter
    }
    
    # Buy signal (near lower band)
    if b_value <= 0.2:
        buy_signal = True
        
        # Apply MFI filter (if option enabled)
        if use_mfi_filter and mfi_value is not None:
            # Buy only when MFI is low (oversold condition)
            if mfi_value > 20:
                buy_signal = False  # Suppress buy signal if MFI is not low enough
                message_parts.append(f"%B 값 {b_value:.4f}가 하단밴드 근처에 있으나, MFI 필터({mfi_value:.2f})로 매수 신호 억제됨")
                return "Hold", ". ".join(message_parts)
        
        message_parts.append(f"%B 값 {b_value:.4f}가 하단밴드 근처에 위치")
        if mfi_value is not None:
            message_parts.append(f"MFI {mfi_value:.2f}")
            if mfi_value < 20:
                message_parts.append("과매도 상태로 반등 가능성 있음")
        
        return "Buy", ". ".join(message_parts)
    
    # Sell signal (near upper band)
    elif b_value >= 0.8:
        sell_signal = True
        
        # Apply MFI filter (if option enabled)
        if use_mfi_filter and mfi_value is not None:
            # Sell only when MFI is high (overbought condition)
            if mfi_value < 80:
                sell_signal = False  # Suppress sell signal if MFI is not high enough
                message_parts.append(f"%B 값 {b_value:.4f}가 상단밴드 근처에 있으나, MFI 필터({mfi_value:.2f})로 매도 신호 억제됨")
                return "Hold", ". ".join(message_parts)
        
        message_parts.append(f"%B 값 {b_value:.4f}가 상단밴드 근처에 위치")
        if mfi_value is not None:
            message_parts.append(f"MFI {mfi_value:.2f}")
            if mfi_value > 80:
                message_parts.append("과매수 상태로 조정 가능성 있음")
        
        return "Sell", ". ".join(message_parts)
    
    # Mid-band crossover (crossing the 0.5 baseline)
    prev_b = df.iloc[-2]['%B']
    if (prev_b < 0.5 and b_value >= 0.5) or (prev_b > 0.5 and b_value <= 0.5):
        message_parts.append(f"%B 값 {b_value:.4f}가 중심선을 교차")
        
        # Upward crossover
        if prev_b < 0.5 and b_value >= 0.5:
            # Additional condition: Stronger signal if MFI also shows uptrend
            if mfi_value is not None and mfi_value > 50:
                message_parts.append(f"MFI {mfi_value:.2f}가 상승 추세를 확인")
            return "Mid_Break_Up", ". ".join(message_parts)
        # Downward crossover
        else:
            # Additional condition: Stronger signal if MFI also shows downtrend
            if mfi_value is not None and mfi_value < 50:
                message_parts.append(f"MFI {mfi_value:.2f}가 하락 추세를 확인")
            return "Mid_Break_Down", ". ".join(message_parts)
    
    # No signal
    message_parts.append(f"%B 값 {b_value:.4f}에서 뚜렷한 신호 없음")
    if mfi_value is not None:
        message_parts.append(f"MFI {mfi_value:.2f}")
    
    return "Hold", ". ".join(message_parts)

def generate_target_signal(current_price, purchase_price, target_gain_percent):
    """
    Generate target price signals based on current price, purchase price, and target gain percentage.
    
    Args:
        current_price (float): Current price
        purchase_price (float): Purchase price
        target_gain_percent (float): Target gain percentage (%)
        
    Returns:
        tuple: (target price signal, current gain percentage (%))
    """
    # If purchase price is not set
    if purchase_price is None or target_gain_percent is None:
        return "No_Target", None
    
    # Calculate current gain percentage
    gain_percent = ((current_price - purchase_price) / purchase_price) * 100
    
    # Check if target gain percentage is reached
    if gain_percent >= target_gain_percent:
        return "Target_Reached", gain_percent
    else:
        return "Hold", gain_percent

def get_trading_advice(signal, b_value, mfi_value=None, dev_percent=None):
    """
    Generate additional advice based on trading signals.
    
    Args:
        signal (str): Trading signal
        b_value (float): %B value
        mfi_value (float, optional): MFI value
        dev_percent (float, optional): Deviation percentage (%)
        
    Returns:
        str: Trading advice message
    """
    advice = ""
    
    if signal == "Buy":
        advice += "☑️ 하단밴드 접근 시 분할 매수 전략 추천\n"
        advice += "☑️ 첫 매수는 총 자금의 20-30%로 진입\n"
        
        if dev_percent is not None:
            if dev_percent < -10:
                advice += f"☑️ 이격도 {dev_percent:.2f}%, 추가 하락 가능성 주의\n"
            elif dev_percent < -5:
                advice += f"☑️ 이격도 {dev_percent:.2f}%, 반등 가능성 있음\n"
        
        if mfi_value is not None:
            if mfi_value < 20:
                advice += f"☑️ MFI {mfi_value:.2f}, 과매도 상태로 반등 가능성 증가\n"
            elif mfi_value < 30:
                advice += f"☑️ MFI {mfi_value:.2f}, 매수 신호 강화\n"
        
    elif signal == "Sell":
        advice += "☑️ 상단밴드 접근 시 분할 매도 전략 추천\n"
        advice += "☑️ 첫 매도는 보유 물량의 30-50%로 이익 실현\n"
        
        if dev_percent is not None:
            if dev_percent > 10:
                advice += f"☑️ 이격도 {dev_percent:.2f}%, 과매수 상태, 조정 가능성 주의\n"
            elif dev_percent > 5:
                advice += f"☑️ 이격도 {dev_percent:.2f}%, 강한 상승 모멘텀\n"
        
        if mfi_value is not None:
            if mfi_value > 80:
                advice += f"☑️ MFI {mfi_value:.2f}, 과매수 상태로 조정 가능성 증가\n"
            elif mfi_value > 70:
                advice += f"☑️ MFI {mfi_value:.2f}, 매도 신호 강화\n"
    
    elif signal == "Hold":
        if b_value > 0.8:
            advice += "☑️ %B가 상단에 위치, 매도 시점 접근 중\n"
        elif b_value < 0.2:
            advice += "☑️ %B가 하단에 위치, 매수 시점 접근 중\n"
        elif 0.4 < b_value < 0.6:
            advice += "☑️ 중심선 근처에서 횡보 중, 추세 방향 관찰\n"
        
        if mfi_value is not None:
            if mfi_value > 70:
                advice += f"☑️ MFI {mfi_value:.2f}, 강한 상승 추세, 상단 돌파 가능성\n"
            elif mfi_value < 30:
                advice += f"☑️ MFI {mfi_value:.2f}, 강한 하락 추세, 하단 돌파 가능성\n"
    
    return advice

def generate_trading_signal(df, use_mfi_filter=False):
    """
    Generate trading signals based on BNF's Bollinger Band strategy.
    
    Args:
        df (pandas.DataFrame): Stock data including indicators
        use_mfi_filter (bool): Whether to use MFI filter (filtering trading signals based on overbought/oversold conditions)
        
    Returns:
        dict: Trading signal, message, and related data
    """
    # Initialize result structure
    result = {
        "signal": "Hold",
        "message": "",
        "reason": "",  # Add detailed reason for trading signal
        "data": {
            "params": {
                "use_mfi_filter": use_mfi_filter
            }
        }
    }
    
    # Verify data
    if df is None or df.empty or len(df) < 2:
        result["message"] = "유효한 데이터가 없습니다."
        result["reason"] = "신호 생성을 위한 충분한 데이터가 없습니다."
        return result
    
    # Generate technical signal
    tech_signal, tech_message = generate_signal(df, use_mfi_filter)
    
    # Extract basic data
    latest = df.iloc[-1]
    current_price = latest['Close'] if 'Close' in latest else None
    
    # Add MFI value
    mfi_value = latest['MFI'] if 'MFI' in latest and not pd.isna(latest['MFI']) else None
    
    # Add technical indicator data
    result["data"]["technical_signal"] = tech_signal
    result["data"]["b_value"] = latest['%B'] if '%B' in latest else None
    result["data"]["mfi"] = mfi_value
    
    # Calculate deviation percentage (based on MA25)
    if 'MA25' in latest and 'Close' in latest:
        dev_percent = ((latest['Close'] / latest['MA25']) - 1) * 100
        result["data"]["deviation_percent"] = dev_percent
    
    # Initialize target signal
    target_signal = "No_Target"
    target_message = ""
    
    # Generate target signal if purchase price and target gain are set
    if hasattr(config, 'PURCHASE_PRICE') and hasattr(config, 'TARGET_GAIN_PERCENT') and current_price is not None:
        purchase_price = config.PURCHASE_PRICE
        target_gain = config.TARGET_GAIN_PERCENT
        
        # Generate target signal
        if purchase_price is not None and target_gain is not None:
            target_signal, current_gain_percent = generate_target_signal(current_price, purchase_price, target_gain)
            
            # Calculate current gain percentage
            if current_gain_percent is not None:
                result["data"]["current_gain_percent"] = current_gain_percent
                # Set reason based on target gain achievement
                if target_signal == "Target_Reached":
                    result["reason"] = f"목표 수익률 {target_gain}%에 도달했습니다. 현재 수익률: {current_gain_percent:.2f}%"
    
    # Save target signal
    result["data"]["target_signal"] = target_signal
    
    # Determine final signal (priority: target reached > technical signal)
    if target_signal == "Target_Reached":
        result["signal"] = "Sell"  # Sell when target gain is reached
        result["message"] = f"🎯 목표 수익 달성: {target_message}"
    else:
        # Determine final signal based on technical signal
        result["signal"] = tech_signal
        
        # Set detailed reason for trading signal
        b_value = result["data"]["b_value"]
        dev_percent = result["data"].get("deviation_percent")
        
        # Compose messages and set reasons by signal type
        if tech_signal == "Buy":
            result["message"] = f"🔔 매수 신호: {tech_message}"
            
            # Set buy signal reasons
            reasons = []
            if b_value <= 0.05:
                reasons.append(f"%B 값이 {b_value:.4f}로 극도의 과매도 상태를 나타냅니다. 매우 강한 반등 가능성이 있습니다.")
            elif b_value <= 0.1:
                reasons.append(f"%B 값이 {b_value:.4f}로 강한 과매도 상태를 나타냅니다. 반등 가능성이 높습니다.")
            else:
                reasons.append(f"%B 값이 {b_value:.4f}로 하단밴드에 접근하여 과매도 상태를 나타냅니다.")
            
            if mfi_value is not None:
                if mfi_value < 10:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 극도의 과매도 상태를 나타내며, 강한 반등 신호를 제공합니다.")
                elif mfi_value < 20:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 강한 과매도 상태를 나타냅니다.")
                elif mfi_value < 30:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 과매도 상태를 확인합니다.")
                
                # Add MFI filter application info
                if use_mfi_filter:
                    if mfi_value <= BUY_MFI_THRESHOLD:
                        reasons.append(f"MFI 필터 ({mfi_value:.2f} <= {BUY_MFI_THRESHOLD})가 매수 신호를 강화합니다.")
                    result["message"] += f"\n💹 MFI 필터 활성화됨: {mfi_value:.2f} (임계값: {BUY_MFI_THRESHOLD})"
            
            if dev_percent is not None:
                if dev_percent < -15:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 상당히 낮아 반등 가능성이 매우 높습니다.")
                elif dev_percent < -10:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 크게 낮아 반등 가능성이 있습니다.")
                elif dev_percent < -5:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 낮습니다.")
            
            # Add volume information (if available)
            if 'Volume' in latest and 'Volume_Change' in latest and not pd.isna(latest['Volume_Change']):
                vol_change = latest['Volume_Change']
                if vol_change > 1.5:
                    reasons.append(f"거래량이 전일 대비 {vol_change:.2f}배 증가하여 매수 압력이 강화되었습니다.")
            
            result["reason"] = " ".join(reasons)
                
        elif tech_signal == "Sell":
            result["message"] = f"🔔 매도 신호: {tech_message}"
            
            # Set sell signal reasons
            reasons = []
            if b_value >= 0.95:
                reasons.append(f"%B 값이 {b_value:.4f}로 극도의 과매수 상태를 나타냅니다. 매우 강한 조정 가능성이 있습니다.")
            elif b_value >= 0.9:
                reasons.append(f"%B 값이 {b_value:.4f}로 강한 과매수 상태를 나타냅니다. 조정 가능성이 높습니다.")
            else:
                reasons.append(f"%B 값이 {b_value:.4f}로 상단밴드에 접근하여 과매수 상태를 나타냅니다.")
            
            if mfi_value is not None:
                if mfi_value > 90:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 극도의 과매수 상태를 나타내며, 강한 조정 신호를 제공합니다.")
                elif mfi_value > 80:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 강한 과매수 상태를 나타냅니다.")
                elif mfi_value > 70:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 과매수 상태를 확인합니다.")
                
                # Add MFI filter application info
                if use_mfi_filter:
                    if mfi_value >= SELL_MFI_THRESHOLD:
                        reasons.append(f"MFI 필터 ({mfi_value:.2f} >= {SELL_MFI_THRESHOLD})가 매도 신호를 강화합니다.")
                    result["message"] += f"\n💹 MFI 필터 활성화됨: {mfi_value:.2f} (임계값: {SELL_MFI_THRESHOLD})"
            
            if dev_percent is not None:
                if dev_percent > 15:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 상당히 높아 조정 가능성이 매우 높습니다.")
                elif dev_percent > 10:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 크게 높아 조정 가능성이 있습니다.")
                elif dev_percent > 5:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로, 20일 이동평균선보다 높습니다.")
            
            # Add volume information (if available)
            if 'Volume' in latest and 'Volume_Change' in latest and not pd.isna(latest['Volume_Change']):
                vol_change = latest['Volume_Change']
                if vol_change > 1.5:
                    reasons.append(f"거래량이 전일 대비 {vol_change:.2f}배 증가하여 매도 압력이 강화되었습니다.")
            
            result["reason"] = " ".join(reasons)
                
        elif tech_signal in ["Mid_Break_Up", "Mid_Break_Down"]:
            direction = "상향" if tech_signal == "Mid_Break_Up" else "하향"
            result["message"] = f"🔄 중심선 {direction} 돌파: {tech_message}"
            result["signal"] = "Hold"  # Treat midline crossover as Hold
            
            # Set midline crossover reasons
            if tech_signal == "Mid_Break_Up":
                reasons = [f"%B 값이 중심선(0.5)을 상향 돌파했습니다. 현재 값: {b_value:.4f}. 상승 추세로 전환 가능성이 있습니다."]
                
                if mfi_value is not None:
                    if mfi_value > 60:
                        reasons.append(f"MFI 값이 {mfi_value:.2f}로 강한 상승 추세를 확인합니다.")
                    elif mfi_value > 50:
                        reasons.append(f"MFI 값이 {mfi_value:.2f}로 상승 추세를 확인합니다.")
                
                if dev_percent is not None and dev_percent > 0:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로 20일 이동평균선보다 높아 상승 추세를 강화합니다.")
                
                # Check previous data for trend analysis
                if len(df) > 10:
                    prev_data = df.iloc[-10:-1]
                    if prev_data['%B'].mean() < 0.4:
                        reasons.append("이전 거래일의 평균 %B가 낮아 추세 반전에 대한 신뢰도가 높아집니다.")
                
                result["reason"] = " ".join(reasons)
            else:
                reasons = [f"%B 값이 중심선(0.5)을 하향 돌파했습니다. 현재 값: {b_value:.4f}. 하락 추세로 전환 가능성이 있습니다."]
                
                if mfi_value is not None:
                    if mfi_value < 40:
                        reasons.append(f"MFI 값이 {mfi_value:.2f}로 강한 하락 추세를 확인합니다.")
                    elif mfi_value < 50:
                        reasons.append(f"MFI 값이 {mfi_value:.2f}로 하락 추세를 확인합니다.")
                
                if dev_percent is not None and dev_percent < 0:
                    reasons.append(f"이격도가 {dev_percent:.2f}%로 20일 이동평균선보다 낮아 하락 추세를 강화합니다.")
                
                # Check previous data for trend analysis
                if len(df) > 10:
                    prev_data = df.iloc[-10:-1]
                    if prev_data['%B'].mean() > 0.6:
                        reasons.append("이전 거래일의 평균 %B가 높아 추세 반전에 대한 신뢰도가 높아집니다.")
                
                result["reason"] = " ".join(reasons)
        else:
            # Hold signal
            result["message"] = f"💤 관망 신호: {tech_message}"
            
            # Set hold signal reasons
            reasons = []
            if 0.3 <= b_value <= 0.7:
                reasons.append(f"%B 값이 {b_value:.4f}로 중심선 부근에 위치하여 특별한 신호가 없습니다.")
            elif b_value > 0.7:
                reasons.append(f"%B 값이 {b_value:.4f}로 상단으로 접근하고 있으나 아직 매도 신호는 아닙니다.")
            elif b_value < 0.3:
                reasons.append(f"%B 값이 {b_value:.4f}로 하단으로 접근하고 있으나 아직 매수 신호는 아닙니다.")
            
            if mfi_value is not None:
                if 40 <= mfi_value <= 60:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 중립 상태입니다.")
                elif mfi_value > 60:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 상승 추세에 있으나 과매수 상태는 아닙니다.")
                elif mfi_value < 40:
                    reasons.append(f"MFI 값이 {mfi_value:.2f}로 하락 추세에 있으나 과매도 상태는 아닙니다.")
            
            if use_mfi_filter:
                reasons.append("MFI 필터가 활성화되어 있어 강한 신호만 감지합니다.")
            
            result["reason"] = " ".join(reasons)
    
    # Generate trading advice based on signal
    if b_value is not None:
        result["data"]["advice"] = get_trading_advice(
            signal=result["signal"], 
            b_value=b_value, 
            mfi_value=mfi_value, 
            dev_percent=dev_percent
        )
    
    return result 