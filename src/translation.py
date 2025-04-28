import os
from src.config import config, LANGUAGE

# 번역 사전
translations = {
    'ko': {
        'trading_signal': {
            'Buy': '매수',
            'Sell': '매도',
            'Hold': '관망',
            'Watch': '관찰',
            'MID_BREAK_UP': '중앙선 상향돌파'
        },
        'messages': {
            'signal_detected': '거래 신호 감지',
            'current_price': '현재 가격',
            'purchase_price': '구매 가격',
            'b_value': '%B 값',
            'deviation': '이격도',
            'mfi': 'MFI',
            'current_gain': '현재 수익률',
            'strategy_advice': '전략 조언',
            'risk_management': '위험 관리 전략',
            'stop_loss_price': '손절 가격',
            'band_riding_detected': '밴드타기 감지',
            'strong_trend': '강한 상승 추세',
            'band_riding_warning': '밴드타기 현상이 감지되었으나 강한 추세는 아닙니다. 부분 매도를 고려하세요.',
            'sell_with_strong_trend': '매도 신호가 발생했으나, 강한 상승 추세로 판단됩니다. 트레일링 스탑을 고려하세요.'
        },
        'reasons': {
            'buy_signal': '매수 신호: %B({b_value:.4f})가 하단밴드 근처에 위치',
            'sell_signal': '매도 신호: %B({b_value:.4f})가 상단밴드 근처에 위치',
            'watch_signal': '관망 신호',
            'watch_above_mid': '%B({b_value:.4f})가 중심선 위에 위치하여 상승 추세 관찰 중',
            'watch_below_mid': '%B({b_value:.4f})가 중심선 아래에 위치하여 하락 추세 관찰 중',
            'mfi_oversold': 'MFI({mfi_value:.2f})가 과매도 상태',
            'mfi_overbought': 'MFI({mfi_value:.2f})가 과매수 상태',
            'mfi_not_overbought': 'MFI({mfi_value:.2f})가 과매수 상태가 아니어서 매도 신호가 억제됨',
            'mfi_not_oversold': 'MFI({mfi_value:.2f})가 과매도 상태가 아니어서 매수 신호가 억제됨',
            'negative_deviation': '이격도({dev_percent:.2f}%)가 음수',
            'positive_deviation': '이격도({dev_percent:.2f}%)가 양수',
            'general_reason': '매매 신호는 %B 값, 이격도, MFI 지표를 종합적으로 분석한 결과입니다.'
        }
    },
    'en': {
        'trading_signal': {
            'Buy': 'Buy',
            'Sell': 'Sell',
            'Hold': 'Hold',
            'Watch': 'Watch',
            'MID_BREAK_UP': 'Mid-line Breakout'
        },
        'messages': {
            'signal_detected': 'Trading Signal Detected',
            'current_price': 'Current Price',
            'purchase_price': 'Purchase Price',
            'b_value': '%B Value',
            'deviation': 'Deviation',
            'mfi': 'MFI',
            'current_gain': 'Current Gain',
            'strategy_advice': 'Strategy Advice',
            'risk_management': 'Risk Management Strategy',
            'stop_loss_price': 'Stop Loss Price',
            'band_riding_detected': 'Band Riding Detected',
            'strong_trend': 'Strong Upward Trend',
            'band_riding_warning': 'Band riding detected but not a strong trend. Consider partial selling.',
            'sell_with_strong_trend': 'Sell signal detected, but trend is strong. Consider using trailing stop.'
        },
        'reasons': {
            'buy_signal': 'Buy signal: %B({b_value:.4f}) is near the lower band',
            'sell_signal': 'Sell signal: %B({b_value:.4f}) is near the upper band',
            'watch_signal': 'Watch signal',
            'watch_above_mid': '%B({b_value:.4f}) is above the mid-line, watching upward trend',
            'watch_below_mid': '%B({b_value:.4f}) is below the mid-line, watching downward trend',
            'mfi_oversold': 'MFI({mfi_value:.2f}) is in oversold condition',
            'mfi_overbought': 'MFI({mfi_value:.2f}) is in overbought condition',
            'mfi_not_overbought': 'MFI({mfi_value:.2f}) is not overbought, sell signal suppressed',
            'mfi_not_oversold': 'MFI({mfi_value:.2f}) is not oversold, buy signal suppressed',
            'negative_deviation': 'Deviation({dev_percent:.2f}%) is negative',
            'positive_deviation': 'Deviation({dev_percent:.2f}%) is positive',
            'general_reason': 'Trading signal is based on comprehensive analysis of %B value, deviation, and MFI indicators.'
        }
    }
}

def get_translation(key, category='messages', **kwargs):
    """
    지정된 키에 대한 번역된 텍스트를 반환합니다.
    
    Args:
        key (str): 번역할 키
        category (str): 번역 카테고리 ('messages', 'trading_signal', 'reasons')
        **kwargs: 번역 문자열에 포맷팅할 변수들
        
    Returns:
        str: 번역된 텍스트
    """
    lang = config.LANGUAGE
    
    # 지원되지 않는 언어인 경우 영어로 대체
    if lang not in translations:
        lang = 'en'
    
    # 카테고리가 존재하는지 확인
    if category not in translations[lang]:
        # 카테고리가 없으면 키를 그대로 반환
        print(f"번역 카테고리를 찾을 수 없음: {category}")
        return key
    
    # 키가 존재하는지 확인
    if key not in translations[lang][category]:
        # 키가 없으면 키를 그대로 반환
        print(f"번역 키를 찾을 수 없음: {key}")
        return key
    
    # 번역된 텍스트 가져오기
    translated_text = translations[lang][category][key]
    
    # 포맷 변수가 있으면 적용
    if kwargs:
        try:
            translated_text = translated_text.format(**kwargs)
        except KeyError as e:
            print(f"번역 포맷 에러: {e}")
    
    return translated_text

def translate_signal(signal):
    """
    거래 신호를 번역합니다.
    
    Args:
        signal (str): 거래 신호 (Buy, Sell, Hold, Watch 등)
        
    Returns:
        str: 번역된 거래 신호
    """
    return get_translation(signal, category='trading_signal')

def translate_reason(reason_key, **kwargs):
    """
    거래 이유를 번역합니다.
    
    Args:
        reason_key (str): 이유 키
        **kwargs: 포맷팅할 변수들
        
    Returns:
        str: 번역된 이유 텍스트
    """
    return get_translation(reason_key, category='reasons', **kwargs) 