from src.config import (
    config,
    BUY_B_THRESHOLD, BUY_MFI_THRESHOLD,
    SELL_B_THRESHOLD, SELL_MFI_THRESHOLD,
    TICKER
)
import pandas as pd
import numpy as np

def generate_trading_signal(df):
    """
    기술적 지표를 기반으로 매매 신호를 생성합니다.
    
    Args:
        df (pandas.DataFrame): 지표가 포함된 주식 데이터
        
    Returns:
        dict: 신호 정보 (signal, data)
    """
    # 현재 사용 중인 티커 확인 (디버깅)
    print(f"신호 생성: 현재 설정된 티커 = {config.TICKER}")
    
    if df is None or df.empty:
        return {
            "signal": "Error",
            "data": None,
            "message": "데이터가 없습니다."
        }
    
    # 최신 데이터 가져오기
    latest = df.iloc[-1]
    
    # 기본 신호는 "Hold"
    signal = "Hold"
    technical_signal = "Hold"
    target_signal = "Hold"
    
    # NaN 값 체크
    b_value = latest['%B'] if not pd.isna(latest['%B']) else 0.5
    mfi_value = latest['MFI'] if not pd.isna(latest['MFI']) else 50
    
    # 기술적 지표 기반 신호 조건
    if b_value < config.BUY_B_THRESHOLD and mfi_value < config.BUY_MFI_THRESHOLD:
        technical_signal = "Buy"
    elif b_value > config.SELL_B_THRESHOLD and mfi_value > config.SELL_MFI_THRESHOLD:
        technical_signal = "Sell"
    
    # 목표 수익률 도달 확인
    target_reached = False
    target_message = ""
    current_gain_percent = 0
    
    if config.PURCHASE_PRICE is not None and config.TARGET_GAIN_PERCENT is not None:
        current_price = latest['Close']
        purchase_price = config.PURCHASE_PRICE
        target_gain = config.TARGET_GAIN_PERCENT
        
        # 현재 수익률 계산
        current_gain_percent = ((current_price - purchase_price) / purchase_price) * 100
        
        # 목표 가격 계산
        target_price = purchase_price * (1 + target_gain / 100)
        
        # 메시지에 수익률 정보 추가
        target_message = f"\n구매가: ${purchase_price:.2f}\n현재 수익률: {current_gain_percent:.2f}%\n목표 수익률: {target_gain:.2f}%\n목표 가격: ${target_price:.2f}"
        
        # 목표 수익률 도달 확인
        if current_gain_percent >= target_gain:
            target_reached = True
            target_signal = "Target_Reached"
            target_message += f"\n🎯 목표 수익률에 도달했습니다! (${current_price:.2f})"
    
    # 최종 신호 결정 (우선순위: 목표가 달성 > 기술적 지표)
    if target_signal == "Target_Reached":
        signal = "Target_Reached"
    else:
        signal = technical_signal
    
    # 신호 데이터 생성
    signal_data = {
        "ticker": config.TICKER,
        "price": latest['Close'],
        "b_value": b_value,
        "mfi": mfi_value,
        "signal": signal,
        "technical_signal": technical_signal,
        "target_signal": target_signal,
        "target_reached": target_reached,
        "current_gain_percent": current_gain_percent if config.PURCHASE_PRICE is not None else None
    }
    
    # 메시지 생성
    message = f"[{config.TICKER}]\n가격: ${latest['Close']:.2f}\n%B: {b_value:.2f}\nMFI: {mfi_value:.2f}\n기술적 신호: {technical_signal}\n목표가 신호: {target_signal}\n최종 신호: {signal}"
    
    # 목표 수익률 정보 추가
    if target_message:
        message += target_message
    
    return {
        "signal": signal,
        "data": signal_data,
        "message": message
    } 