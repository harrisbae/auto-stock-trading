import time
import schedule
import argparse
from src.stock_data import get_stock_data
from src.indicators import add_all_indicators
from src.signal import generate_trading_signal
from src.notification import send_slack_message, send_slack_formatted_message
from src.config import set_ticker, set_webhook_url, set_target_params, DEFAULT_TICKER, config, set_language
from src.translation import get_translation, translate_signal, translate_reason

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
        "intensity": 0,  # 밴드 타기 강도 추가
        "trailing_stop_value": 0,  # 트레일링 스탑 값 추가
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
        
        # 밴드 타기 강도 계산 (추가 지표)
        # 상단 밴드 접촉 비율과 %B 평균값을 고려한 강도 측정
        touch_ratio = result["consecutive_days"] / lookback
        result["intensity"] = round(min(100, touch_ratio * 100 * avg_b))
        
        # 트레일링 스탑 값 계산 (현재 가격의 10%)
        if len(recent_df) > 0:
            current_price = recent_df['Close'].iloc[-1]
            result["trailing_stop_value"] = round(current_price * 0.9, 2)  # 10% 트레일링 스탑
        
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
        result["message"] = f"밴드타기 감지: {result['consecutive_days']}일 연속 상단밴드 접촉 (강도: {result['strength']}%, 강도지수: {result['intensity']})"
        
        # 강한 상승 추세로 판단 (가격 상승일이 70% 이상이고 거래량 증가 또는 %B가 매우 높음)
        if (price_trend >= 0.7 and (volume_increase or avg_b > 0.9)):
            # 강한 상승 추세 감지 (거래량 증가 또는 %B 매우 높음)
            result["is_strong_trend"] = True
            result["trend_message"] = "강한 상승 추세 감지: 단순 상단 접촉만으로 매도하지 말고 추세 지속 관찰 권장"
            
            # 강한 추세일 때는 매도보다는 추세 추종 메시지
            result["message"] += f"\n- 강한 상승 추세 유지 중: 상단 접촉만으로 매도하지 말고 추세 모멘텀 활용"
            result["message"] += f"\n- 트레일링 스탑(Trailing Stop) 전략으로 이익 보호하며 추세 추종 - 추천 스탑: ${result['trailing_stop_value']}"
        else:
            result["message"] += f"\n- 상단밴드에 지속 접촉 시 밴드 타기 현상 주시"
            result["message"] += f"\n- 트레일링 스탑 권장: ${result['trailing_stop_value']} (현재가의 90%)"
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
                        band_riding_detection=True, risk_management_level="medium", use_mfi_filter=False, force_notify=False):
    """
    주식 데이터를 가져와 신호를 체크하고 필요시 알림을 보냅니다.
    
    Args:
        ticker (str, optional): 분석할 주식 종목 티커 심볼
        notify_method (str): Slack 알림 전송 방식
        tranche_count (int): 분할 매수 단계 수
        stop_loss_percent (float): 손절 비율 (%)
        band_riding_detection (bool): 밴드타기 감지 여부
        risk_management_level (str): 위험 관리 수준 (low, medium, high)
        use_mfi_filter (bool): MFI 필터 사용 여부
        force_notify (bool): 매매 신호가 없어도 알림을 강제로 보냄
    """
    # 티커 정보 추출 및 설정
    actual_ticker = None
    if ticker:
        # ticker가 "SPY/508.62/10" 형태로 들어오는 경우 티커만 추출
        if '/' in ticker:
            parts = ticker.split('/')
            actual_ticker = parts[0].strip()  # 앞뒤 공백 제거
            
            # 디버깅: 분리된 티커 정보 출력
            print(f"티커 정보 파싱: {ticker} -> 티커={actual_ticker}, 가격={parts[1] if len(parts) > 1 else '없음'}")
            
            # 설정
            current_ticker = set_ticker(actual_ticker)
        else:
            actual_ticker = ticker.strip()  # 앞뒤 공백 제거
            current_ticker = set_ticker(actual_ticker)
    else:
        current_ticker = DEFAULT_TICKER
        actual_ticker = current_ticker
    
    # 티커 확인 (디버깅)
    print(f"분석 진행: ticker={ticker}, actual_ticker={actual_ticker}, current_ticker={current_ticker}")
    
    try:
        # 주식 데이터 가져오기 - 실제 티커 명시적 전달
        stock_data_raw = get_stock_data(actual_ticker)
        
        if stock_data_raw.empty:
            print(f"주식 데이터를 가져오는 데 실패했습니다. 종목: {actual_ticker}")
            return
        
        # 데이터 확인 (디버깅)
        print(f"데이터 로드 성공: {actual_ticker}, 행 수={len(stock_data_raw)}")
        
        # 기술적 지표 추가
        stock_data = add_all_indicators(stock_data_raw)
        
        # 거래 신호 생성
        trading_signal = generate_trading_signal(stock_data, use_mfi_filter=use_mfi_filter)
        
        # 거래 신호 결과
        signal = trading_signal['signal']
        message = trading_signal['message']
        
        # 나머지 파라미터 추가
        if 'params' not in trading_signal['data']:
            trading_signal['data']['params'] = {}
        
        trading_signal['data']['params'].update({
            'tranche_count': tranche_count,
            'stop_loss_percent': stop_loss_percent,
            'band_riding_detection': band_riding_detection,
            'risk_management_level': risk_management_level,
        })
        
        # 밴드타기 감지 (옵션에 따라 활성화)
        if band_riding_detection:
            band_riding_result = detect_band_riding(stock_data)
            
            if band_riding_result['is_riding']:
                trading_signal['data']['band_riding'] = band_riding_result
                
                # 밴드타기 메시지 추가
                message += f"\n\n[밴드타기 감지]\n{band_riding_result['message']}"
                
                if band_riding_result['is_strong_trend'] and band_riding_result['trend_message']:
                    message += f"\n{band_riding_result['trend_message']}"
                
                # 강한 상승 추세가 아닌 경우 매도 고려 메시지 추가
                if signal != "Sell" and not band_riding_result['is_strong_trend']:
                    message += "\n\n⚠️ 밴드타기 현상이 감지되었으나 강한 추세는 아닙니다. 부분 매도를 고려하세요."
                
                # 강한 추세로 판단되면 메시지 조정
                if signal == "Sell" and band_riding_result['is_strong_trend']:
                    message += "\n\n⚠️ 매도 신호가 발생했으나, 강한 상승 추세로 판단됩니다. 트레일링 스탑을 고려하세요."
                    # 신호를 Hold로 변경하지 않고 사용자 판단에 맡김
        
        # 위험 관리 전략 적용
        current_price = stock_data['Close'].iloc[-1]
        current_b_value = stock_data['%B'].iloc[-1]
        current_dev_percent = ((current_price / stock_data['MA25'].iloc[-1]) - 1) * 100
        
        # MFI 값 가져오기
        mfi_value = None
        if 'MFI' in stock_data.columns:
            mfi_value = stock_data['MFI'].iloc[-1]
        
        # 밴드 기울기 계산
        band_slope = None
        if len(stock_data) >= 5:
            recent_upper = stock_data['UpperBand'].iloc[-5:].values
            band_slope = (recent_upper[-1] - recent_upper[0]) / recent_upper[0] * 100
        
        # 현재 이득 계산
        current_gain = None
        if hasattr(config, 'PURCHASE_PRICE') and config.PURCHASE_PRICE is not None:
            current_gain = ((current_price / config.PURCHASE_PRICE) - 1) * 100
        
        # 목표 이득 설정
        target_gain = None
        if hasattr(config, 'TARGET_GAIN_PERCENT'):
            target_gain = config.TARGET_GAIN_PERCENT
        
        # 돌파 매매 확인 (중심선 위에서 신호가 발생한 경우)
        is_breakout = current_b_value > 0.5
        
        # 위험 관리 전략 계산
        risk_strategy = adjust_risk_management(
            risk_level=risk_management_level,
            b_value=current_b_value,
            dev_percent=current_dev_percent,
            stop_loss_percent=stop_loss_percent,
            is_breakout=is_breakout,
            mfi=mfi_value,
            band_slope=band_slope,
            current_gain=current_gain,
            target_gain=target_gain
        )
        
        # 위험 관리 전략을 데이터에 추가
        trading_signal['data']['risk_management'] = risk_strategy
        
        # 신호 근거 추가
        if trading_signal.get('reason') is None:
            # 기본 근거 메시지 설정
            if signal == "Buy":
                reason = f"매수 신호: %B({current_b_value:.4f})가 하단밴드 근처에 위치하고"
                if mfi_value is not None and mfi_value < 30:
                    reason += f", MFI({mfi_value:.2f})가 과매도 상태로"
                if current_dev_percent < 0:
                    reason += f", 이격도({current_dev_percent:.2f}%)가 음수"
                reason += "로 매수 포인트로 판단됩니다."
            elif signal == "Sell":
                reason = f"매도 신호: %B({current_b_value:.4f})가 상단밴드 근처에 위치하고"
                if mfi_value is not None and mfi_value > 70:
                    reason += f", MFI({mfi_value:.2f})가 과매수 상태로"
                if current_dev_percent > 0:
                    reason += f", 이격도({current_dev_percent:.2f}%)가 양수"
                reason += "로 매도 포인트로 판단됩니다."
            elif signal == "Watch":
                reason = "관망 신호: "
                if current_b_value > 0.5:
                    reason += f"%B({current_b_value:.4f})가 중심선 위에 위치하여 상승 추세 관찰 중"
                    if use_mfi_filter and mfi_value is not None and mfi_value < 70:
                        reason += f", MFI({mfi_value:.2f})가 과매수 상태가 아니어서 매도 신호가 억제됨"
                else:
                    reason += f"%B({current_b_value:.4f})가 중심선 아래에 위치하여 하락 추세 관찰 중"
                    if use_mfi_filter and mfi_value is not None and mfi_value > 30:
                        reason += f", MFI({mfi_value:.2f})가 과매도 상태가 아니어서 매수 신호가 억제됨"
            else:
                reason = "매매 신호는 %B 값, 이격도, MFI 지표를 종합적으로 분석한 결과입니다."
                
            trading_signal['reason'] = reason
        
        # 결과 출력
        print(message)
        
        # Slack 알림 전송
        formatted_message = f"""
📈 *[{actual_ticker} 거래 신호: {signal}]*
{trading_signal.get('reason', '매매 신호는 %B 값, 이격도, MFI 지표를 종합적으로 분석한 결과입니다.')}

*[주요 지표]*
• 현재 가격: ${current_price:.2f}"""

        if hasattr(config, 'PURCHASE_PRICE') and config.PURCHASE_PRICE is not None:
            formatted_message += f"\n• 구매 가격: ${config.PURCHASE_PRICE:.2f}"
            
        formatted_message += f"""
• %B 값: {current_b_value:.4f}
• 이격도: {current_dev_percent:.2f}%"""

        if mfi_value is not None:
            formatted_message += f"\n• MFI: {mfi_value:.2f}"
            
        if current_gain is not None:
            formatted_message += f"\n• 현재 수익률: {current_gain:.2f}%"
        
        formatted_message += "\n\n*[전략 조언]*"
        
        # 메시지에서 주요 조언 포인트 추출하여 불릿 포인트로 표시
        advice_points = []
        
        if current_b_value > 0.8:
            advice_points.append("☑️ 상단밴드 접근 시 분할 매도 전략 추천")
            advice_points.append(f"☑️ 첫 매도는 보유 물량의 {risk_strategy.get('first_portion', 30)}-50%로 이익 실현")
            if current_dev_percent > 10:
                advice_points.append(f"☑️ 이격도 {current_dev_percent:.2f}%로 과매수 상태, 조정 가능성 주의")
        elif current_b_value < 0.2:
            advice_points.append("☑️ 하단밴드 접근 시 분할 매수 전략 추천")
            advice_points.append(f"☑️ 첫 매수는 총 자금의 {risk_strategy.get('tranches', [25])[0]}% 권장")
            if current_dev_percent < -10:
                advice_points.append(f"☑️ 이격도 {current_dev_percent:.2f}%로 과매도 상태, 반등 가능성 주시")
        
        if mfi_value is not None:
            if mfi_value > 80 and current_b_value > 0.5:
                advice_points.append(f"☑️ MFI {mfi_value:.2f}로 매도 신호 보강")
            elif mfi_value < 20 and current_b_value < 0.5:
                advice_points.append(f"☑️ MFI {mfi_value:.2f}로 매수 신호 보강")
            elif (mfi_value > 80 and current_b_value < 0.5) or (mfi_value < 20 and current_b_value > 0.5):
                advice_points.append(f"☑️ MFI {mfi_value:.2f}와 %B {current_b_value:.2f} 간 배치, 신중한 접근 필요")
        
        # 추출된 조언 포인트를 메시지에 추가
        if advice_points:
            formatted_message += "\n" + "\n".join(advice_points)
        
        # 밴드타기 정보 추가
        if band_riding_detection and 'band_riding' in trading_signal['data']:
            br_result = trading_signal['data']['band_riding']
            formatted_message += f"\n\n*[밴드타기 감지]*"
            formatted_message += f"\n{br_result['message']}"
            
            if br_result['is_strong_trend'] and br_result['trend_message']:
                formatted_message += f"\n{br_result['trend_message']}"
            
            # 경고 메시지
            if signal == "Sell" and br_result['is_strong_trend']:
                formatted_message += "\n\n⚠️ 매도 신호가 발생했으나, 강한 상승 추세로 판단됩니다. 트레일링 스탑을 고려하세요."
        
        # 위험 관리 전략 정보 추가
        if 'risk_management' in trading_signal['data']:
            risk_msg = trading_signal['data']['risk_management'].get('strategy_message', '')
            if risk_msg:
                formatted_message += f"\n\n*[위험 관리 전략]*\n{risk_msg}"
            
            stop_price = trading_signal['data']['risk_management'].get('stop_loss_price')
            if stop_price:
                formatted_message += f"\n🛑 손절 가격: ${stop_price:.2f}"
        
        # 알림 필요시 전송
        if signal and signal != "Hold":
            success = send_slack_message(formatted_message, method=notify_method)
            if success:
                print(f"{actual_ticker} 알림 전송 성공!")
            else:
                print(f"{actual_ticker} 알림 전송 실패!")
        elif force_notify:
            # force_notify가 True일 경우 Hold 신호라도 알림 전송
            formatted_message = formatted_message.replace(f"*[{actual_ticker} 거래 신호: {signal}]*", f"*[{actual_ticker} 일일 보고서]*")
            formatted_message += "\n\n*[참고]*\n현재 특별한 매매 신호는 없으나, 일일 보고서로 전송됩니다."
            success = send_slack_message(formatted_message, method=notify_method)
            if success:
                print(f"{actual_ticker} 일일 보고서 알림 전송 성공!")
            else:
                print(f"{actual_ticker} 일일 보고서 알림 전송 실패!")
        else:
            print(f"{actual_ticker}에 대한 알림 조건 없음")
                
    except Exception as e:
        print(f"오류 발생: {actual_ticker} 분석 중 예외가 발생했습니다 - {str(e)}")

# 메인 실행 코드
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주식 거래 신호 체크 및 알림 전송")
    parser.add_argument("--ticker", type=str, help="분석할 주식 종목 티커 심볼")
    parser.add_argument("--notify_method", type=str, choices=['json_body', 'formatted_message'], default='json_body', help="알림 전송 방식")
    parser.add_argument("--tranche_count", type=int, default=3, help="분할 매수 단계 수")
    parser.add_argument("--stop_loss_percent", type=float, default=7, help="손절 비율 (%%)")
    parser.add_argument("--band_riding_detection", action='store_true', default=True, help="밴드타기 감지 여부")
    parser.add_argument("--risk_management_level", type=str, choices=['low', 'medium', 'high'], default="medium", help="위험 관리 수준")
    parser.add_argument("--use_mfi_filter", action='store_true', default=False, help="MFI 필터 사용 여부")
    parser.add_argument("--force_notify", action='store_true', default=False, help="매매 신호가 없어도 알림을 강제로 보냄")
    parser.add_argument("--language", type=str, choices=['ko', 'en'], default='ko', help="언어 설정 (ko: 한국어, en: 영어)")
    parser.add_argument("--now", action='store_true', help="지금 즉시 신호 체크")
    parser.add_argument("--schedule", action='store_true', help="스케줄러로 정기적 실행")
    parser.add_argument("--schedule-time", type=str, default="06:00", help="스케줄러 실행 시간 (HH:MM 형식, 기본값: 06:00)")

    args = parser.parse_args()
    
    # 언어 설정
    set_language(args.language)

    # 스케줄러 실행 함수
    def run_scheduler():
        """
        정해진 시간에 주기적으로 신호를 체크하고 알림을 전송하는 스케줄러를 실행합니다.
        기본적으로 매일 06:00 (서버 시간)에 실행됩니다.
        """
        print(f"스케줄러가 시작되었습니다. 매일 {args.schedule_time}에 {args.ticker if args.ticker else DEFAULT_TICKER} 종목을 분석합니다.")
        
        # 지정된 시간에 신호 체크 실행
        schedule.every().day.at(args.schedule_time).do(
            check_trading_signal,
            ticker=args.ticker,
            notify_method=args.notify_method,
            tranche_count=args.tranche_count,
            stop_loss_percent=args.stop_loss_percent,
            band_riding_detection=args.band_riding_detection,
            risk_management_level=args.risk_management_level,
            use_mfi_filter=args.use_mfi_filter,
            force_notify=args.force_notify
        )
        
        # 스케줄러 계속 실행
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인

    # 명령어에 따른 실행
    if args.schedule:
        # 스케줄러 모드로 실행
        run_scheduler()
    else:
        # 즉시 실행 모드
        check_trading_signal(
            ticker=args.ticker,
            notify_method=args.notify_method,
            tranche_count=args.tranche_count,
            stop_loss_percent=args.stop_loss_percent,
            band_riding_detection=args.band_riding_detection,
            risk_management_level=args.risk_management_level,
            use_mfi_filter=args.use_mfi_filter,
            force_notify=args.force_notify
        )
