import time
import schedule
import argparse
from src.stock_data import get_stock_data
from src.indicators import add_all_indicators
from src.signal import generate_trading_signal
from src.notification import send_slack_message, send_slack_formatted_message
from src.config import set_ticker, set_webhook_url, set_target_params, DEFAULT_TICKER, config

"""
# 볼린저 밴드 기반 실전 매매 전략

## 기본 매매 전략
1. 하단밴드 터치 시 (%B < 0.2) 분할 매수 진입 
   - 첫 매수는 총 자금의 20-30%로 진입
   - MA25 대비 이격도 -15% 이상 시 매수 확률 증가

2. 상단밴드 터치 시 (%B > 0.8) 분할 매도 
   - MA25 대비 이격도 +10% 이상 시 매도 확률 증가
   - MFI 70 이상 동반 시 과매수 신호로 판단

3. 분할 매수 전략
   - 하단밴드 터치 시 20-30% 자금으로 첫 매수
   - 추가 하락 시 평균단가 낮추기
   - 중심선(MA25) 도달 시 50% 익절 고려
   - 중심선 돌파 확인 후 남은 물량 유지

4. 손절 전략
   - 돌파 매매의 경우: 밴드 상단선 아래로 내려올 때 손절
   - 하단 매수의 경우: 추가 하락으로 평균단가 낮추기
   - 진입가 대비 -7% 또는 %B 값이 0.2 미만으로 하락 시 손절 고려

5. 위험 관리
   - 분할 매매로 리스크 분산
   - 매수/매도 시점에 MFI 지표 병행 확인
   - 추세 변화 시 신속한 대응 (밴드 기울기 변화 주시)
   - 목표 수익률 도달 시 일부 이익 실현
"""

# 매매 가능성 계산 함수 추가
def calculate_trading_probability(b_value, dev_percent):
    """B값과 이격도를 기반으로 매수/매도 확률을 계산합니다."""
    buy_potential = 0
    sell_potential = 0
    
    # 매수 가능성 계산 - 모든 구간에 적용
    if b_value < 0.5:  # %B가 0.5보다 작을 때 매수 가능성 있음
        # 0.5에서 멀어질수록 확률 증가, 0일 때 최대
        buy_potential += (0.5 - b_value) * 200
    
    if dev_percent < 0:  # 음의 이격도일 때 매수 가능성 있음
        # 이격도가 더 낮을수록 매수 확률 증가
        buy_potential += min(abs(dev_percent) * 6, 100)
        
    # 매도 가능성 계산 - 모든 구간에 적용
    if b_value > 0.5:  # %B가 0.5보다 클 때 매도 가능성 있음
        # 0.5에서 멀어질수록 확률 증가, 1일 때 최대
        sell_potential += (b_value - 0.5) * 200
    
    if dev_percent > 0:  # 양의 이격도일 때 매도 가능성 있음
        # 이격도가 더 높을수록 매도 확률 증가
        sell_potential += min(dev_percent * 6, 100)
    
    # 가능성이 계산되었으면 평균내기
    if buy_potential > 0 and dev_percent < 0:
        buy_potential /= 2
    if sell_potential > 0 and dev_percent > 0:
        sell_potential /= 2
    
    buy_potential = min(100, max(0, buy_potential))
    sell_potential = min(100, max(0, sell_potential))
    
    return round(buy_potential), round(sell_potential)

# 분할 매수 전략 계산 함수 추가
def calculate_tranche_strategy(b_value, dev_percent, tranche_count=3):
    """
    분할 매수 전략을 계산합니다.
    
    Args:
        b_value (float): 볼린저 밴드 %B 값
        dev_percent (float): 이격도 (%)
        tranche_count (int): 분할 매수 단계 수
        
    Returns:
        dict: 분할 매수 전략 정보
    """
    result = {
        "current_tranche": 0,
        "allocation_percent": 0,
        "next_entry_price": None,
        "strategy_message": "",
        "exit_strategy": ""
    }
    
    # 현재 몇 번째 트랜치에 해당하는지 계산
    # 하단밴드 터치 상황
    if b_value <= 0.2:
        # 첫 번째 트랜치는 밴드 하단 터치 시 (20-30% 자금 투입)
        if b_value > 0.1:
            result["current_tranche"] = 1
            result["allocation_percent"] = 25  # 첫 매수는 25% 정도로 고정
            result["strategy_message"] = f"하단밴드 터치: 첫 매수 - 총 자금의 {result['allocation_percent']}% 매수 권장"
        # 추가 하락 시 평균단가 낮추기 (두 번째 트랜치)
        elif b_value > 0.05:
            result["current_tranche"] = 2
            result["allocation_percent"] = 35
            result["strategy_message"] = f"추가 하락: 두 번째 매수 - 총 자금의 {result['allocation_percent']}% 추가 매수로 평균단가 낮추기"
        # 급격한 하락 시 마지막 트랜치 (안전망 구축)
        else:
            result["current_tranche"] = 3
            result["allocation_percent"] = 40
            result["strategy_message"] = f"급격한 하락: 마지막 매수 - 총 자금의 {result['allocation_percent']}% 안전망 매수"
    # 매수 시점이 아닌 경우
    else:
        result["current_tranche"] = 0
    
    # 익절 전략 추가
    # MA25(중심선) 도달 시 50% 익절 고려
    if 0.45 <= b_value <= 0.55:
        result["exit_strategy"] = "MA25(중심선) 도달: 보유 물량의 50% 익절 고려"
    # 중심선 상향 돌파 시 남은 물량 유지
    elif 0.55 < b_value <= 0.7:
        result["exit_strategy"] = "중심선 상향 돌파: 남은 물량 유지하고 상단밴드 터치까지 홀딩"
    # 상단밴드 접근 시 매도 고려
    elif b_value > 0.7:
        result["exit_strategy"] = "상단밴드 접근: 남은 물량 전량 매도 검토"
    
    return result

# 밴드타기 감지 함수 추가
def detect_band_riding(df, lookback=5):
    """
    볼린저 밴드 상단에 연속 접촉하는 밴드타기 현상을 감지합니다.
    
    Args:
        df (DataFrame): 주가 데이터프레임
        lookback (int): 확인할 기간
        
    Returns:
        dict: 밴드타기 감지 결과
    """
    result = {
        "is_riding": False,
        "consecutive_days": 0,
        "strength": 0,
        "message": "",
        "is_strong_trend": False,
        "trend_message": ""
    }
    
    # 최근 데이터만 사용
    recent_df = df.tail(lookback).copy()
    
    # 상단 밴드 근처에 있는 날 확인 (%B > 0.8)
    upper_band_touches = recent_df[recent_df['%B'] > 0.8]
    result["consecutive_days"] = len(upper_band_touches)
    
    # 연속 3일 이상 상단 접촉 시 밴드타기로 간주
    if result["consecutive_days"] >= 3:
        result["is_riding"] = True
        
        # 밴드타기 강도 계산 (0-100)
        avg_b = upper_band_touches['%B'].mean()
        result["strength"] = round(min(100, (avg_b - 0.8) * 500))
        
        # 최근 볼륨 확인 (거래량 증가는 추세 강도 확인에 중요)
        volume_increase = False
        if 'Volume' in recent_df.columns:
            avg_volume = recent_df['Volume'].mean()
            recent_volume = recent_df['Volume'].iloc[-1]
            if recent_volume > avg_volume * 1.2:  # 20% 이상 거래량 증가
                volume_increase = True
        
        # 강한 상승 추세 확인
        price_trend = 0
        if len(recent_df) >= 3:
            price_diff = recent_df['Close'].pct_change().dropna()
            price_trend = sum(1 for x in price_diff if x > 0) / len(price_diff)
        
        # 기본 밴드타기 메시지 초기화
        result["message"] = f"밴드타기 감지: {result['consecutive_days']}일 연속 상단밴드 접촉 (강도: {result['strength']}%)"
        
        # 강한 상승 추세로 판단 (가격 상승일이 70% 이상이고 거래량 증가 또는 %B가 매우 높음)
        if (price_trend >= 0.7 and (volume_increase or avg_b > 0.9)):
            # 강한 상승 추세 감지 (거래량 증가 또는 %B 매우 높음)
            result["is_strong_trend"] = True
            result["trend_message"] = "강한 상승 추세 감지: 단순 상단 접촉만으로 매도하지 말고 추세 지속 관찰 권장"
            
            # 강한 추세일 때는 매도보다는 추세 추종 메시지
            result["message"] += f"\n- 강한 상승 추세 유지 중: 상단 접촉만으로 매도하지 말고 추세 모멘텀 활용"
            result["message"] += f"\n- 트레일링 스탑(Trailing Stop) 전략으로 이익 보호하며 추세 추종"
        else:
            result["message"] += f"\n- 상단밴드에 지속 접촉 시 밴드 타기 현상 주시"
            
            result["message"] += f"\n- 중심선(MA25) 아래로 돌파 시 잔여 물량 매도 고려"
    
    return result

# 위험 관리 수준에 따른 전략 조정 함수
def adjust_strategy_by_risk_level(strategy_type, risk_level="medium", volatility=None, 
                          band_slope=None, current_gain=None, target_gain=None):
    """
    위험 관리 수준에 따라 매매 전략을 조정합니다.
    
    Args:
        strategy_type (str): 전략 유형 (buy, sell, stop_loss, target_profit)
        risk_level (str): 위험 관리 수준 (low, medium, high)
        volatility (float, optional): 변동성 (%)
        band_slope (float, optional): 볼린저 밴드 기울기
        current_gain (float, optional): 현재 수익률 (%)
        target_gain (float, optional): 목표 수익률 (%)
        
    Returns:
        dict: 위험 관리 전략 정보
    """
    result = {}
    
    # 매수 전략 조정
    if strategy_type == "buy":
        # 위험 수준에 따른 자금 분배 설정
        if risk_level == "low":
            # 저위험: 더 많은 단계로 분할
            result["tranches"] = [20, 20, 20, 20, 20]  # 5단계, 한 번에 20%씩
        elif risk_level == "medium":
            # 중위험: 3단계로 분할
            result["tranches"] = [30, 35, 35]  # 3단계, 첫 단계 30%
        else:  # high
            # 고위험: 2단계로 분할
            result["tranches"] = [50, 50]  # 2단계, 한 번에 50%씩
        
        # 변동성에 따른 트랜치 비율 차별화
        if volatility is not None:
            if volatility > 30:  # 고변동성 (30% 초과)
                # 고변동성에서는 보수적으로 첫 단계 비율 감소
                first_allocation = result["tranches"][0]
                result["tranches"][0] = max(15, first_allocation - 15)  # 최소 15%로 감소
            elif volatility < 10:  # 저변동성 (10% 미만)
                # 저변동성에서는 첫 단계 비율 증가
                first_allocation = result["tranches"][0]
                result["tranches"][0] = min(60, first_allocation + 10)  # 최대 60%로 증가
        
        # 밴드 기울기가 하락하면 첫 단계 투자 비율 감소
        if band_slope is not None and band_slope < -0.1:
            result["tranches"][0] = max(15, result["tranches"][0] - 5)  # 최소 15%
    
    # 매도 전략 조정
    elif strategy_type == "sell":
        # 위험 수준에 따른 물량 배분 설정
        if risk_level == "low":
            # 저위험: 보수적 익절
            result["first_portion"] = 70  # 첫 매도에 70% 실현
            result["portions"] = [70, 30]  # 2단계 매도
        elif risk_level == "medium":
            # 중위험: 중간 익절
            result["first_portion"] = 60  # 첫 매도에 60% 실현
            result["portions"] = [60, 20, 20]  # 3단계 매도
        else:  # high
            # 고위험: 공격적 익절
            result["first_portion"] = 50  # 첫 매도에 50% 실현
            result["portions"] = [50, 20, 15, 15]  # 4단계 매도
    
    # 손절 전략 조정
    elif strategy_type == "stop_loss":
        # 위험 수준에 따른 손절 비율 설정
        if risk_level == "low":
            # 저위험: 보수적 손절
            result["percent"] = 5  # 5% 손절
        elif risk_level == "medium":
            # 중위험: 중간 손절
            result["percent"] = 7  # 7% 손절
        else:  # high
            # 고위험: 여유로운 손절
            result["percent"] = 10  # 10% 손절
        
        # 변동성 조정
        if volatility is not None:
            if volatility > 30:  # 초고변동성
                result["percent"] = min(7, result["percent"])  # 손절선 축소, 최대 7%
            elif volatility < 10:  # 저변동성
                result["percent"] = min(15, result["percent"] + 2)  # 손절선 확대
        
        # 밴드 기울기 조정
        if band_slope is not None:
            if band_slope < -0.2:  # 급격한 하락 추세
                result["percent"] = min(7, result["percent"])  # 손절선 축소, 최대 7%
    
    # 목표 수익률 조정
    elif strategy_type == "target_profit":
        # 위험 수준에 따른 목표 수익률 설정
        if risk_level == "low":
            # 저위험: 보수적 목표
            result["target_percent"] = 10  # 10% 목표
        elif risk_level == "medium":
            # 중위험: 중간 목표
            result["target_percent"] = 15  # 15% 목표
        else:  # high
            # 고위험: 공격적 목표
            result["target_percent"] = 20  # 20% 목표
        
        # 목표 수익률의 70%에서 일부 이익 실현
        result["partial_profit_at"] = 70  # 목표의 70%에서 부분 익절
    
    return result

# 원래 함수 이름과 호환성을 위한 alias 함수
def adjust_risk_management(risk_level, b_value, dev_percent, stop_loss_percent=7, is_breakout=False, mfi=None, 
                          band_slope=None, current_gain=None, target_gain=None):
    """
    위험 관리 수준에 따라 매매 전략을 조정합니다. (이전 버전 호환용)
    
    Args:
        risk_level (str): 위험 관리 수준 (low, medium, high)
        b_value (float): 볼린저 밴드 %B 값
        dev_percent (float): 이격도 (%)
        stop_loss_percent (float): 기본 손절 비율
        is_breakout (bool): 돌파 매매 여부
        mfi (float, optional): MFI(Money Flow Index) 값
        band_slope (float, optional): 볼린저 밴드 기울기
        current_gain (float, optional): 현재 수익률 (%)
        target_gain (float, optional): 목표 수익률 (%)
        
    Returns:
        dict: 위험 관리 전략 정보
    """
    result = {
        "adjusted_stop_loss": stop_loss_percent,
        "capital_risk_percent": 0,
        "strategy_message": "",
        "stop_loss_strategy": "",
        "risk_management": []
    }
    
    # 위험 수준에 따른 자본 위험 비율 설정
    if risk_level == "low":
        result["capital_risk_percent"] = 3
        result["adjusted_stop_loss"] = min(5, stop_loss_percent)
    elif risk_level == "medium":
        result["capital_risk_percent"] = 5
        result["adjusted_stop_loss"] = stop_loss_percent
    elif risk_level == "high":
        result["capital_risk_percent"] = 10
        result["adjusted_stop_loss"] = max(10, stop_loss_percent)
    
    # 매수/매도 상황에 따른 전략 메시지
    if b_value < 0.2:  # 매수 영역 (하단 매수)
        if risk_level == "low":
            result["strategy_message"] = f"저위험 전략: 총 자본의 {result['capital_risk_percent']}%만 투자, 손절: -{result['adjusted_stop_loss']}%"
        elif risk_level == "medium":
            result["strategy_message"] = f"중위험 전략: 분할 매수 활용, 총 자본의 {result['capital_risk_percent']}% 투자, 손절: -{result['adjusted_stop_loss']}%"
        else:
            result["strategy_message"] = f"고위험 전략: 적극적 진입, 총 자본의 {result['capital_risk_percent']}% 투자, 손절: -{result['adjusted_stop_loss']}%"
        
        # 하단 매수의 경우 손절 전략: 추가 하락 시 평균단가 낮추기
        result["stop_loss_strategy"] = "하단 매수 전략: 추가 하락 시 평균단가 낮추기 (손절보다는 추가 매수 통한 비용절감 추구)"
    
    elif b_value > 0.8:  # 매도 영역
        if risk_level == "low":
            result["strategy_message"] = f"저위험 전략: 보수적 이익실현, 90% 이상 매도"
        elif risk_level == "medium":
            result["strategy_message"] = f"중위험 전략: 70% 매도, 나머지는 트레일링 스탑으로 관리"
        else:
            result["strategy_message"] = f"고위험 전략: 50% 매도, 상승추세 유지 시 홀딩"
    
    # 돌파 매매의 경우 손절 전략: 밴드 상단선 아래로 내려올 때 손절
    if is_breakout:
        result["stop_loss_strategy"] = "돌파 매매 전략: 밴드 상단선 아래로 내려올 때 손절 (상단선 = %B < 0.8 지점)"
    elif 0.2 <= b_value <= 0.8 and not result["stop_loss_strategy"]:
        # 기본 손절 전략
        result["stop_loss_strategy"] = f"기본 손절 전략: 진입가 대비 -{result['adjusted_stop_loss']}% 손실 발생 시 손절 검토"
    
    # 위험 관리 전략 추가
    
    # 1. 분할 매매로 리스크 분산
    diversification_strategy = "분할 매매로 리스크 분산: "
    if b_value < 0.2:  # 매수 영역
        if risk_level == "low":
            diversification_strategy += "총 4-5회 나누어 진입, 한 번에 15-20% 자금만 투입"
        elif risk_level == "medium":
            diversification_strategy += "총 3회 나누어 진입, 한 번에 25-30% 자금 투입"
        else:
            diversification_strategy += "총 2회 나누어 진입, 한 번에 40-50% 자금 투입"
    elif b_value > 0.8:  # 매도 영역
        if risk_level == "low":
            diversification_strategy += "총 2회 나누어 90% 이상 매도, 첫 매도에 70% 실현"
        elif risk_level == "medium":
            diversification_strategy += "총 3회 나누어 70-80% 매도, 가격에 따라 분할 실현"
        else:
            diversification_strategy += "총 3-4회 나누어 50-70% 매도, 나머지는 추세 유지 시 홀딩"
    else:
        diversification_strategy += "진입/이탈 시 일시에 모든 자금을 투입/회수하지 않고 분할 매매 실행"
    
    result["risk_management"].append(diversification_strategy)
    
    # 2. MFI 지표 병행 확인
    mfi_strategy = "MFI 지표 병행 확인: "
    if mfi is not None:
        if b_value < 0.2 and mfi < 20:
            mfi_strategy += f"MFI({mfi:.1f})가 과매도 상태로 매수 신호 강화"
        elif b_value < 0.2 and mfi > 50:
            mfi_strategy += f"MFI({mfi:.1f})가 높아 가격 하락 속도 둔화 가능성, 매수 시점 재검토"
        elif b_value > 0.8 and mfi > 80:
            mfi_strategy += f"MFI({mfi:.1f})가 과매수 상태로 매도 신호 강화"
        elif b_value > 0.8 and mfi < 50:
            mfi_strategy += f"MFI({mfi:.1f})가 낮아 상승 가능성 있음, 매도 시점 재검토"
        else:
            mfi_strategy += f"현재 MFI({mfi:.1f}) 기준으로는 뚜렷한 신호 없음"
    else:
        if b_value < 0.2:
            mfi_strategy += "매수 전 반드시 MFI 20 이하인지 확인 (이상일 경우 매수 유보 검토)"
        elif b_value > 0.8:
            mfi_strategy += "매도 전 반드시 MFI 80 이상인지 확인 (이하일 경우 홀딩 검토)"
        else:
            mfi_strategy += "매수/매도 결정 시 MFI 확인으로 신호 강도 검증"
    
    result["risk_management"].append(mfi_strategy)
    
    # 3. 추세 변화 시 신속한 대응 (밴드 기울기 변화 주시)
    trend_strategy = "추세 변화 감지: "
    if band_slope is not None:
        if band_slope > 0.01:  # 밴드 기울기 상승
            trend_strategy += f"밴드 기울기 상승중(+{band_slope:.3f}), 상승 추세 확인"
            if b_value > 0.5:
                trend_strategy += " - 상승 모멘텀 활용 가능"
            elif b_value < 0.2:
                trend_strategy += " - 반등 시작 가능성 있음"
        elif band_slope < -0.01:  # 밴드 기울기 하락
            trend_strategy += f"밴드 기울기 하락중({band_slope:.3f}), 하락 추세 확인"
            if b_value < 0.5:
                trend_strategy += " - 하락 가속화 가능성 주의"
            elif b_value > 0.8:
                trend_strategy += " - 추세 전환 가능성 높음, 이익실현 고려"
        else:
            trend_strategy += "밴드 기울기 중립, 횡보장 가능성"
    else:
        trend_strategy += "밴드 기울기 변화 주시하여 추세 전환 조기 감지"
        if b_value < 0.2:
            trend_strategy += " - 하단밴드 기울기가 수평/상승으로 전환 시 매수 신호 강화"
        elif b_value > 0.8:
            trend_strategy += " - 상단밴드 기울기가 수평/하락으로 전환 시 매도 신호 강화"
    
    result["risk_management"].append(trend_strategy)
    
    # 4. 목표 수익률 도달 시 일부 이익 실현
    profit_strategy = "목표 수익률 관리: "
    if current_gain is not None and target_gain is not None:
        target_ratio = current_gain / target_gain if target_gain != 0 else 0
        if target_ratio >= 1:  # 목표 수익률 달성
            profit_strategy += f"목표 수익률({target_gain:.1f}%) 달성, 보유 물량의 "
            if risk_level == "low":
                profit_strategy += "80-90% 익절 권장"
            elif risk_level == "medium":
                profit_strategy += "50-70% 익절 후 나머지는 추가 상승에 대비"
            else:
                profit_strategy += "30-50% 익절 후 나머지는 추세 유지 여부에 따라 결정"
        elif target_ratio >= 0.7:  # 목표 수익률의 70% 이상 달성
            profit_strategy += f"목표 수익률의 {target_ratio*100:.1f}% 달성, 보유 물량의 "
            if risk_level == "low":
                profit_strategy += "50-60% 부분 익절 검토"
            elif risk_level == "medium":
                profit_strategy += "30-40% 부분 익절 검토"
            else:
                profit_strategy += "20-30% 부분 익절 검토"
        else:
            profit_strategy += f"현재 수익률 {current_gain:.1f}%, 목표 수익률({target_gain:.1f}%)의 {target_ratio*100:.1f}% 달성, 추세 유지 관찰"
    else:
        profit_strategy += "목표 수익률의 70% 도달 시 일부 익절, 100% 도달 시 위험 수준에 따라 50-90% 익절"
    
    result["risk_management"].append(profit_strategy)
    
    return result

def check_trading_signal(ticker=None, notify_method='json_body', tranche_count=3, stop_loss_percent=7, 
                        band_riding_detection=True, risk_management_level="medium"):
    """
    주식 데이터를 가져와 신호를 체크하고 필요시 알림을 보냅니다.
    
    Args:
        ticker (str, optional): 분석할 주식 종목 티커 심볼
        notify_method (str): Slack 알림 전송 방식
        tranche_count (int): 분할 매수 단계 수
        stop_loss_percent (float): 손절 비율
        band_riding_detection (bool): 밴드타기 감지 여부
        risk_management_level (str): 위험 관리 수준 (low, medium, high)
    """
    # 주식 종목 설정
    if ticker:
        current_ticker = set_ticker(ticker)
        print(f"분석할 주식 종목: {current_ticker}")
    
    # 주식 데이터 가져오기
    df = get_stock_data()
    if df is None:
        print("주식 데이터를 가져오는데 실패했습니다.")
        return
    
    # 지표 계산
    df = add_all_indicators(df)
    
    # 매매 신호 생성
    result = generate_trading_signal(df)
    
    # 기본 데이터 가져오기
    b_value = result["data"].get("b_value", 0.5)
    dev_percent = result["data"].get("deviation_percent", 0)
    
    # 추가 데이터 추출
    mfi = None
    if 'MFI' in df.columns:
        mfi = df['MFI'].iloc[-1]
        result["data"]["mfi"] = mfi
    
    # 밴드 기울기 계산
    band_slope = None
    if 'upperband' in df.columns and len(df) > 5:
        # 최근 5일간의 상단밴드 기울기 계산
        recent_upper = df['upperband'].tail(5).values
        if len(recent_upper) >= 2:
            band_slope = (recent_upper[-1] - recent_upper[0]) / (len(recent_upper) * recent_upper[0])
            result["data"]["band_slope"] = band_slope
    
    # 현재 수익률 및 목표 수익률 가져오기
    current_gain = None
    target_gain = None
    if hasattr(config, 'PURCHASE_PRICE') and config.PURCHASE_PRICE is not None:
        current_price = df['Close'].iloc[-1] if not df.empty else None
        if current_price is not None:
            current_gain = ((current_price / config.PURCHASE_PRICE) - 1) * 100
            result["data"]["current_gain"] = current_gain
            
        if hasattr(config, 'TARGET_GAIN_PERCENT'):
            target_gain = config.TARGET_GAIN_PERCENT
            result["data"]["target_gain"] = target_gain
    
    # 돌파 매매 여부 확인 (신호가 'Breakout_Buy'인 경우)
    is_breakout = result["data"]["signal"] == "Breakout_Buy" if "signal" in result["data"] else False
    
    # 추가 전략 계산
    tranche_strategy = calculate_tranche_strategy(b_value, dev_percent, tranche_count)
    risk_strategy = adjust_risk_management(
        risk_management_level, b_value, dev_percent, stop_loss_percent, is_breakout,
        mfi=mfi, band_slope=band_slope, current_gain=current_gain, target_gain=target_gain
    )
    
    # 밴드타기 감지 (옵션이 켜져 있을 경우)
    band_riding_info = {"is_riding": False, "message": ""}
    if band_riding_detection:
        band_riding_info = detect_band_riding(df)
    
    # Hold 신호일 경우 매수/매도 확률 계산
    if result["data"]["signal"] == "Hold":
        buy_prob, sell_prob = calculate_trading_probability(b_value, dev_percent)
        
        # 기존 메시지에 매수/매도 확률 정보 추가
        result["message"] += f"\n매수 확률: {buy_prob}%, 매도 확률: {sell_prob}%"
        
        # 데이터에도 확률 정보 추가
        result["data"]["buy_probability"] = buy_prob
        result["data"]["sell_probability"] = sell_prob
        
        # 실전 매매 전략 추천 메시지 추가
        if buy_prob >= 30:
            result["message"] += f"\n\n[매수 전략 추천]"
            result["message"] += f"\n- 현재 매수 확률 {buy_prob}%로 분할 매수 고려 가능"
            
            # 분할 매수 전략 정보 추가
            if tranche_strategy["current_tranche"] > 0:
                result["message"] += f"\n- {tranche_strategy['strategy_message']}"
            else:
                result["message"] += f"\n- 하단밴드 터치 시 총 자금의 20-30%로 첫 매수 진입 검토"
            
            # 위험 관리 전략 정보 추가
            result["message"] += f"\n- {risk_strategy['strategy_message']}"
            
            # 손절 전략 추가
            result["message"] += f"\n- {risk_strategy['stop_loss_strategy']}"
            
        elif sell_prob >= 30:
            result["message"] += f"\n\n[매도 전략 추천]"
            result["message"] += f"\n- 현재 매도 확률 {sell_prob}%로 분할 이익실현 고려"
            
            # 위험 관리 전략 정보 추가
            result["message"] += f"\n- {risk_strategy['strategy_message']}"
            
            # 밴드타기 감지 정보 추가
            if band_riding_info["is_riding"]:
                result["message"] += f"\n- {band_riding_info['message']}"
                
                # 강한 상승 추세에서는 매도 권장을 수정
                if band_riding_info["is_strong_trend"]:
                    result["message"] += f"\n- 강한 상승 추세 유지 중: 상단 접촉만으로 매도하지 말고 추세 모멘텀 활용"
                    result["message"] += f"\n- 트레일링 스탑(Trailing Stop) 전략으로 이익 보호하며 추세 추종"
            else:
                result["message"] += f"\n- 상단밴드에 지속 접촉 시 밴드 타기 현상 주시"
            
            result["message"] += f"\n- 중심선(MA25) 아래로 돌파 시 잔여 물량 매도 고려"
        
        # 익절 전략 정보 추가 (b_value가 0.45 이상일 때)
        if b_value >= 0.45 and tranche_strategy["exit_strategy"]:
            result["message"] += f"\n\n[익절 전략 추천]"
            result["message"] += f"\n- {tranche_strategy['exit_strategy']}"
    
    # 돌파 매매 신호인 경우 손절 전략 추가
    elif is_breakout:
        result["message"] += f"\n\n[돌파 매매 손절 전략]"
        result["message"] += f"\n- {risk_strategy['stop_loss_strategy']}"
    
    # 위험 관리 세부 전략 추가
    if risk_strategy["risk_management"]:
        result["message"] += f"\n\n[위험 관리 전략]"
        for strategy in risk_strategy["risk_management"]:
            result["message"] += f"\n- {strategy}"
    
    # 밴드타기 감지 정보 추가 (매수/매도 확률과 관계없이 밴드타기가 감지된 경우)
    if band_riding_detection and band_riding_info["is_riding"] and band_riding_info["message"] not in result["message"]:
        result["message"] += f"\n\n[밴드타기 감지]\n{band_riding_info['message']}"
        result["data"]["band_riding"] = band_riding_info
    
    # 분할 매수 및 위험 관리 데이터 추가
    result["data"]["tranche_strategy"] = tranche_strategy
    result["data"]["risk_management"] = risk_strategy
    
    # 결과 출력
    print(result["message"])
    
    # 알림을 보내야 하는 조건
    should_notify = False
    
    # 기술적 신호와 목표가 신호 확인
    if "technical_signal" in result["data"] and "target_signal" in result["data"]:
        # 기술적 신호가 Buy 또는 Sell이거나 목표가 신호가 Target_Reached인 경우 알림
        should_notify = (
            result["data"]["technical_signal"] in ["Buy", "Sell"] or  # 기술적 지표 기반 매수/매도 신호
            result["data"]["target_signal"] == "Target_Reached"  # 목표 수익률 달성
        )
    else:
        # 이전 버전 호환성을 위한 코드
        if "target_reached" in result["data"]:
            should_notify = (
                result["signal"] in ["Buy", "Sell", "Target_Reached"] or  # 매수/매도/목표수익률 신호
                result["data"]["target_reached"]  # 목표 수익률 달성
            )
        else:
            should_notify = result["signal"] in ["Buy", "Sell"]  # 매수/매도 신호만
    
    # 매수/매도 확률이 높은 경우에도 알림 (30% 이상)
    if result["data"]["signal"] == "Hold" and ("buy_probability" in result["data"] or "sell_probability" in result["data"]):
        buy_prob = result["data"].get("buy_probability", 0)
        sell_prob = result["data"].get("sell_probability", 0)
        if buy_prob >= 40 or sell_prob >= 40:
            should_notify = True
    
    # 밴드타기가 감지된 경우 알림
    if band_riding_detection and band_riding_info["is_riding"] and band_riding_info["strength"] > 50:
            should_notify = True
    
    # 조건에 맞으면 Slack 알림 전송
    if should_notify:
        send_slack_message(result["message"], method=notify_method)
    else:
        print("현재 특별한 신호 없음. Slack 알림을 보내지 않습니다.")
    
    return result

def run_scheduler(ticker=None, notify_method='json_body', tranche_count=3, stop_loss_percent=7, 
                 band_riding_detection=True, risk_management_level="medium"):
    """
    스케줄러를 설정하고 실행합니다.
    
    Args:
        ticker (str, optional): 분석할 주식 종목 티커 심볼
        notify_method (str): Slack 알림 전송 방식
        tranche_count (int): 분할 매수 단계 수
        stop_loss_percent (float): 손절 비율
        band_riding_detection (bool): 밴드타기 감지 여부
        risk_management_level (str): 위험 관리 수준 (low, medium, high)
    """
    # 주식 종목 설정 (스케줄링 전에 미리 설정)
    if ticker:
        current_ticker = set_ticker(ticker)
        print(f"분석할 주식 종목: {current_ticker}")
    
    # 메서드 전달을 위한 래퍼 함수
    def scheduled_check():
        # 설정된 파라미터를 재사용하여 호출
        check_trading_signal(
            notify_method=notify_method,
            tranche_count=tranche_count,
            stop_loss_percent=stop_loss_percent,
            band_riding_detection=band_riding_detection,
            risk_management_level=risk_management_level
        )
    
    # 평일 장 마감 후(한국 시간 기준 다음날 오전 6시) 매일 실행
    schedule.every().day.at("06:00").do(scheduled_check)
    
    print("주식 거래 신호 모니터링 시작...")
    print("매일 오전 6시에 자동으로 확인합니다.")
    if hasattr(config, 'PURCHASE_PRICE') and config.PURCHASE_PRICE is not None:
        target_price = config.PURCHASE_PRICE * (1 + config.TARGET_GAIN_PERCENT / 100)
        print(f"구매가: ${config.PURCHASE_PRICE:.2f}, 목표 수익률: {config.TARGET_GAIN_PERCENT:.2f}%")
        print(f"목표 가격: ${target_price:.2f}")
    
    # 분할 매수 및 위험 관리 정보 출력
    print(f"분할 매수 전략: 총 {tranche_count}단계")
    print(f"손절 비율: {stop_loss_percent}%")
    print(f"밴드타기 감지: {'활성화' if band_riding_detection else '비활성화'}")
    print(f"위험 관리 수준: {risk_management_level}")
    
    print("Ctrl+C를 눌러 종료할 수 있습니다.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")

def test_slack_notification(notify_method='json_body', use_blocks=False):
    """
    Slack 알림 전송을 테스트합니다.
    
    Args:
        notify_method (str): 알림 전송 방식 ('json_body' 또는 'payload_param')
        use_blocks (bool): 블록 형식 메시지 사용 여부
    """
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if use_blocks:
        # Slack 블록 형식의 메시지
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 주식 거래 알림 테스트",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*시간:* {current_time}\n*상태:* 테스트 메시지"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "이 메시지는 Slack 웹훅 연결 테스트를 위한 것입니다."
                }
            }
        ]
        
        success = send_slack_formatted_message(blocks, text="주식 거래 알림 테스트")
    else:
        # 일반 텍스트 메시지
        test_message = f"""
[테스트 알림]
이것은 Slack 웹훅 연결을 테스트하는 메시지입니다.
시간: {current_time}
"""
        success = send_slack_message(test_message, method=notify_method)
    
    if success:
        print("Slack 알림 전송 성공!")
    else:
        print("Slack 알림 전송 실패!")

def main():
    """명령행 인수 처리 및 실행"""
    parser = argparse.ArgumentParser(description='주식 거래 신호 모니터링 프로그램')
    
    # 주식 정보 관련 인수
    parser.add_argument('--stock-info', 
                        help='주식 정보 (형식: 티커/구매가/목표수익률%)')
    parser.add_argument('--ticker', 
                        help='주식 종목 티커 심볼')
    parser.add_argument('--purchase-price', type=float, 
                        help='구매 가격')
    parser.add_argument('--target-gain', type=float, 
                        help='목표 수익률 (%)')
    
    # Slack 웹훅 관련 인수
    parser.add_argument('--webhook-url', 
                        help='Slack 웹훅 URL')
    parser.add_argument('--notify-method', choices=['json_body', 'payload_param'], 
                        default='json_body', 
                        help='Slack 알림 전송 방식')
    
    # 실행 모드 관련 인수
    parser.add_argument('--now', action='store_true', 
                        help='지금 바로 확인하고 종료')
    parser.add_argument('--schedule', action='store_true', 
                        help='스케줄링된 방식으로 실행')
    parser.add_argument('--test-slack', action='store_true', 
                        help='Slack 웹훅 연결 테스트')
    parser.add_argument('--use-blocks', action='store_true', 
                        help='Slack 블록 형식 사용')
    
    # 새로운 전략 관련 인수
    parser.add_argument('--tranche', type=int, default=3,
                        help='분할 매수 단계 수 (기본값: 3)')
    parser.add_argument('--stop-loss', type=float, default=7, 
                        help='손절 비율 (%, 기본값: 7)')
    parser.add_argument('--band-riding', type=str, choices=['true', 'false'], default='true',
                        help='밴드타기 감지 여부 (기본값: true)')
    parser.add_argument('--risk-management', choices=['low', 'medium', 'high'], default='medium',
                        help='위험 관리 수준 (기본값: medium)')
    
    args = parser.parse_args()
    
    # 밴드타기 문자열을 불리언으로 변환
    band_riding_detection = args.band_riding.lower() == 'true'
    
    # Slack 웹훅 URL 설정 (입력된 경우)
    if args.webhook_url:
        set_webhook_url(args.webhook_url)
    
    # 주식 정보 파싱 (--stock-info 인수가 제공된 경우)
    if args.stock_info:
        parts = args.stock_info.split('/')
        if len(parts) >= 3:
            ticker = parts[0]
            purchase_price = float(parts[1])
            target_gain = float(parts[2])
            
            # 주식 정보 설정
            set_ticker(ticker)
            set_target_params(purchase_price, target_gain)
            print(f"주식 정보 설정: {ticker}, 구매가: ${purchase_price}, 목표 수익률: {target_gain}%")
    else:
        # 개별 인수로 주식 정보 설정
        if args.ticker:
            set_ticker(args.ticker)
        
        if args.purchase_price is not None and args.target_gain is not None:
            set_target_params(args.purchase_price, args.target_gain)
    
    # 실행 모드에 따라 다르게 처리
    if args.test_slack:
        # Slack 웹훅 테스트
        test_slack_notification(args.notify_method, args.use_blocks)
    elif args.now:
        # 즉시 확인
        check_trading_signal(
            notify_method=args.notify_method,
            tranche_count=args.tranche,
            stop_loss_percent=args.stop_loss,
            band_riding_detection=band_riding_detection,
            risk_management_level=args.risk_management
        )
    elif args.schedule:
        # 스케줄링된 방식으로 실행
        run_scheduler(
            notify_method=args.notify_method,
            tranche_count=args.tranche,
            stop_loss_percent=args.stop_loss,
            band_riding_detection=band_riding_detection,
            risk_management_level=args.risk_management
        )
    else:
        # 기본적으로 스케줄링 모드로 실행
        run_scheduler(
            notify_method=args.notify_method,
            tranche_count=args.tranche,
            stop_loss_percent=args.stop_loss,
            band_riding_detection=band_riding_detection,
            risk_management_level=args.risk_management
        )

if __name__ == "__main__":
    main() 