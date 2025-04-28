#!/usr/bin/env python
# 거래 신호 알림 메시지를 콘솔에 출력하는 스크립트

import pandas as pd
import numpy as np
import argparse
from datetime import datetime
import random

def print_formatted_message(ticker, signal, b_value, mfi, deviation_percent, current_price, purchase_price=None, current_gain=None):
    """
    거래 신호 알림 메시지를 콘솔에 출력합니다.
    """
    # 신호에 따른 이유 생성
    if signal == "Buy":
        reason = f"%B 값이 {b_value:.4f}로 하단 밴드에 접근하여 과매도 상태입니다."
        if mfi is not None:
            reason += f" MFI 값이 {mfi:.2f}로 과매도 상태를 확인해줍니다."
    elif signal == "Sell":
        reason = f"%B 값이 {b_value:.4f}로 상단 밴드에 접근하여 과매수 상태입니다."
        if mfi is not None:
            reason += f" MFI 값이 {mfi:.2f}로 과매수 상태를 확인해줍니다."
    else:  # Hold
        reason = f"%B 값이 {b_value:.4f}로 중립 구간에 있어 뚜렷한 매매 신호가 없습니다."
        if 0.4 < b_value < 0.6:
            reason += " 중심선 부근에서 횡보하고 있어 추세 방향성을 확인할 필요가 있습니다."
        if mfi is not None:
            reason += f" MFI 값도 {mfi:.2f}로 중립적인 상태입니다."

    # 포맷된 메시지 생성
    formatted_message = f"""
📈 *[{ticker} 거래 신호: {signal}]*
{reason}

*[주요 지표]*
• 현재 가격: ${current_price:.2f}"""

    if purchase_price is not None:
        formatted_message += f"\n• 구매 가격: ${purchase_price:.2f}"
        
    formatted_message += f"""
• %B 값: {b_value:.4f}
• 이격도: {deviation_percent:.2f}%"""

    if mfi is not None:
        formatted_message += f"\n• MFI: {mfi:.2f}"
        
    if current_gain is not None:
        formatted_message += f"\n• 현재 수익률: {current_gain:.2f}%"
    
    # 전략 조언 추가
    formatted_message += "\n\n*[전략 조언]*"
    
    # 신호에 따른 조언 추가
    advice_points = []
    if signal == "Buy":
        advice_points.append("☑️ 하단밴드 접근 시 분할 매수 전략 추천")
        advice_points.append("☑️ 첫 매수는 총 자금의 20-30%로 진입")
        if mfi is not None and mfi < 20:
            advice_points.append(f"☑️ MFI {mfi:.2f}로 과매도 상태, 반등 가능성 증가")
    elif signal == "Sell":
        advice_points.append("☑️ 상단밴드 접근 시 분할 매도 전략 추천")
        advice_points.append("☑️ 첫 매도는 보유 물량의 30-50%로 이익 실현")
        if mfi is not None and mfi > 80:
            advice_points.append(f"☑️ MFI {mfi:.2f}로 과매수 상태, 조정 가능성 증가")
    else:  # Hold
        if b_value > 0.6:
            advice_points.append("☑️ 중심선 위에서 횡보 중, 상승 추세 가능성 주시")
        elif b_value < 0.4:
            advice_points.append("☑️ 중심선 아래에서 횡보 중, 하락 추세 가능성 주시")
        else:
            advice_points.append("☑️ 중심선 부근에서 횡보 중, 추세 방향성 관찰 필요")
    
    # 조언 추가
    if advice_points:
        formatted_message += "\n" + "\n".join(advice_points)

    # 구분선 추가
    print("\n" + "=" * 80)
    print(f"[{ticker} 분석 결과 - 신호: {signal}]")
    print("=" * 80)
    print(formatted_message)
    print("-" * 80 + "\n")
    
    # HOLD가 아닌 경우만 알림 전송
    if signal != "Hold":
        print(f"{ticker} 알림 전송 성공! (신호: {signal})")
    else:
        print(f"{ticker}에 대한 알림 비활성화 (신호: Hold)")

def main():
    parser = argparse.ArgumentParser(description="거래 신호 알림 메시지를 콘솔에 출력합니다.")
    parser.add_argument("--ticker", required=True, help="분석할 주식 종목 티커 심볼")
    parser.add_argument("--purchase-price", type=float, help="구매 가격")
    parser.add_argument("--signal", choices=["Buy", "Sell", "Hold"], default="Hold", help="거래 신호")
    parser.add_argument("--b-value", type=float, default=random.uniform(0.3, 0.7), help="%B 값")
    parser.add_argument("--mfi", type=float, default=random.uniform(30, 70), help="MFI 값")
    parser.add_argument("--deviation-percent", type=float, default=random.uniform(-3, 3), help="이격도 (%)")
    parser.add_argument("--current-price", type=float, help="현재 가격")
    
    args = parser.parse_args()
    
    # 현재 가격이 제공되지 않은 경우, 구매 가격을 기준으로 계산
    current_price = args.current_price
    if current_price is None:
        if args.purchase_price:
            # 구매 가격에 랜덤한 수익률 적용
            gain_percent = random.uniform(-10, 20)
            current_price = args.purchase_price * (1 + gain_percent / 100)
        else:
            # 기본값 설정
            current_price = 100.0
    
    # 현재 수익률 계산
    current_gain = None
    if args.purchase_price:
        current_gain = ((current_price / args.purchase_price) - 1) * 100
    
    # 신호 결정 (인자로 제공된 경우 사용, 아니면 %B 값과 MFI 기반으로 결정)
    signal = args.signal
    if signal == "Hold" and not args.signal:
        b_value = args.b_value
        mfi = args.mfi
        
        if b_value <= 0.2 and mfi < 30:
            signal = "Buy"
        elif b_value >= 0.8 and mfi > 70:
            signal = "Sell"
    
    # 메시지 출력
    print_formatted_message(
        ticker=args.ticker,
        signal=signal,
        b_value=args.b_value,
        mfi=args.mfi,
        deviation_percent=args.deviation_percent,
        current_price=current_price,
        purchase_price=args.purchase_price,
        current_gain=current_gain
    )

if __name__ == "__main__":
    main() 