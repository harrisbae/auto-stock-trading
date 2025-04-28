import unittest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트할 모듈 import
from src.indicators import calculate_bollinger_bands, calculate_mfi, add_all_indicators
from src.signal import generate_trading_signal
from main import calculate_trading_probability, calculate_tranche_strategy, detect_band_riding

class TestBollingerStrategyCases(unittest.TestCase):
    """볼린저 밴드 전략 다양한 시나리오 테스트 클래스"""
    
    def generate_test_data(self, days=100, base_price=100, volatility=5, trend='neutral'):
        """테스트용 데이터 생성 함수"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # 트렌드에 따라 가격 생성 로직 변경
        prices = []
        current_price = base_price
        
        for i in range(days):
            # 기본값 설정
            change = 0
            
            if trend == 'neutral':
                # 중립 추세: 랜덤 변동
                change = np.random.normal(0, volatility/100)
            elif trend == 'uptrend':
                # 상승 추세: 약간의 상승 바이어스
                change = np.random.normal(0.15, volatility/100)
            elif trend == 'downtrend':
                # 하락 추세: 약간의 하락 바이어스
                change = np.random.normal(-0.15, volatility/100)
            elif trend == 'V_recovery':
                # V자 반등: 하락 후 상승
                if i < days // 2:
                    change = np.random.normal(-0.3, volatility/100)
                else:
                    change = np.random.normal(0.4, volatility/100)
            elif trend == 'collapse':
                # 급락: 안정적이다가 후반부에 급락
                if i < days // 2:
                    change = np.random.normal(0.05, volatility/100)
                else:
                    change = np.random.normal(-1.0, volatility/100)
            elif trend == 'sideways':
                # 횡보: 작은 변동성의 랜덤 변화 (중립보다 더 좁은 범위)
                change = np.random.normal(0, volatility/200)
            elif trend == 'band_riding':
                # 밴드타기: 상단 밴드에 연속 접촉하는 패턴
                change = np.random.normal(0.1, volatility/100)
            elif trend == 'overbought':
                # 과매수: 강한 상승 후 높은 수준 유지
                change = np.random.normal(0.2, volatility/100)
            elif trend == 'oversold':
                # 과매도: 강한 하락 후 낮은 수준 유지
                change = np.random.normal(-0.2, volatility/100)
            
            current_price = max(current_price + change, 1)  # 가격이 0 이하로 내려가지 않도록
            prices.append(current_price)
        
        # 기본 데이터프레임 생성
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'Close': prices,
            'Volume': [np.random.normal(1000000, 200000) for _ in range(days)]
        }, index=dates)
        
        # 특별한 패턴 추가 (예: 과매수/과매도)
        if trend == 'overbought':
            # 마지막 5일간 지속적 상승
            for i in range(5):
                idx = len(df) - 5 + i
                df.loc[df.index[idx], 'Close'] = df.iloc[idx-1]['Close'] * 1.03
                df.loc[df.index[idx], 'High'] = df.iloc[idx]['Close'] * 1.02
                df.loc[df.index[idx], 'Low'] = df.iloc[idx-1]['Close'] * 1.01
                df.loc[df.index[idx], 'Open'] = df.iloc[idx-1]['Close'] * 1.02
                df.loc[df.index[idx], 'Volume'] = df.iloc[idx-1]['Volume'] * 1.2
                
        elif trend == 'oversold':
            # 마지막 5일간 지속적 하락
            for i in range(5):
                idx = len(df) - 5 + i
                df.loc[df.index[idx], 'Close'] = df.iloc[idx-1]['Close'] * 0.97
                df.loc[df.index[idx], 'High'] = df.iloc[idx-1]['Close'] * 0.99
                df.loc[df.index[idx], 'Low'] = df.iloc[idx]['Close'] * 0.98
                df.loc[df.index[idx], 'Open'] = df.iloc[idx-1]['Close'] * 0.98
                df.loc[df.index[idx], 'Volume'] = df.iloc[idx-1]['Volume'] * 1.3
        
        return df
    
    def setUp(self):
        """테스트 케이스별 데이터 준비"""
        # 다양한 시나리오별 데이터셋 생성
        self.neutral_data = add_all_indicators(self.generate_test_data(trend='neutral'))
        self.uptrend_data = add_all_indicators(self.generate_test_data(trend='uptrend'))
        self.downtrend_data = add_all_indicators(self.generate_test_data(trend='downtrend'))
        self.v_recovery_data = add_all_indicators(self.generate_test_data(trend='V_recovery'))
        self.collapse_data = add_all_indicators(self.generate_test_data(trend='collapse'))
        self.sideways_data = add_all_indicators(self.generate_test_data(trend='sideways'))
        self.overbought_data = add_all_indicators(self.generate_test_data(trend='overbought'))
        self.oversold_data = add_all_indicators(self.generate_test_data(trend='oversold'))
        self.band_riding_data = add_all_indicators(self.generate_test_data(trend='band_riding'))
    
    def test_neutral_market(self):
        """중립 시장 상태에서의 신호 테스트"""
        result = generate_trading_signal(self.neutral_data)
        
        # 테스트 확인을 위한 진단 출력
        latest = self.neutral_data.iloc[-1]
        print(f"중립 시장 테스트 - 마지막 %B 값: {latest['%B']}")
        print(f"중립 시장 테스트 - 생성된 신호: {result['signal']}")
        
        # 중립 시장에서는 대체로 Hold 신호가 발생해야 함
        self.assertEqual(result['signal'], 'Hold')
        
        # 추가로 확률값 확인
        latest = self.neutral_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 중립 시장에서는 매수/매도 확률이 낮아야 함
        self.assertLess(buy_prob, 50)
        self.assertLess(sell_prob, 50)
    
    def test_uptrend_market(self):
        """상승 추세 시장에서의 신호 테스트"""
        result = generate_trading_signal(self.uptrend_data)
        
        # 상승 추세에서는 홀드 또는 매도 신호가 발생할 수 있음
        self.assertIn(result['signal'], ['Hold', 'Sell'])
        
        # 추가로 확률값 확인
        latest = self.uptrend_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 상승 추세에서는 매도 확률이 매수 확률보다 높아야 함
        self.assertGreater(sell_prob, buy_prob)
    
    def test_downtrend_market(self):
        """하락 추세 시장에서의 신호 테스트"""
        result = generate_trading_signal(self.downtrend_data)
        
        # 하락 추세에서는 홀드 또는 매수 신호가 발생할 수 있음
        self.assertIn(result['signal'], ['Hold', 'Buy', 'Buy_Strong'])
        
        # 추가로 확률값 확인
        latest = self.downtrend_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 하락 추세에서는 매수 확률이 매도 확률보다 높아야 함
        self.assertGreater(buy_prob, sell_prob)
    
    def test_v_recovery_market(self):
        """V자 반등 시장에서의 신호 테스트"""
        result = generate_trading_signal(self.v_recovery_data)
        
        # V자 반등 패턴에서는 신호가 다양할 수 있으나, 데이터가 말기 상승 패턴이면 Hold나 매도 신호가 나올 수 있음
        self.assertIn(result['signal'], ['Hold', 'Buy', 'Buy_Strong', 'Sell'])
        
        # 추세 분석을 위해 최근 데이터 확인
        recent_data = self.v_recovery_data.tail(10)
        price_changes = recent_data['Close'].pct_change().dropna()
        
        # 최근 데이터에서 상승 추세가 명확하게 있어야 함
        rising_days = sum(1 for x in price_changes if x > 0)
        self.assertGreaterEqual(rising_days, len(price_changes) * 0.6)  # 최소 60%는 상승일이어야 함
    
    def test_collapse_market(self):
        """급락 시장에서의 신호 테스트"""
        result = generate_trading_signal(self.collapse_data)
        
        # 급락 시장에서는 일반적으로 매수 신호가 발생
        self.assertIn(result['signal'], ['Buy', 'Buy_Strong'])
        
        # 추가로 확률값 확인
        latest = self.collapse_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 급락 시장에서는 매수 확률이 높아야 함
        self.assertGreater(buy_prob, 50)
        self.assertLess(sell_prob, 30)
        
        # 이격도가 충분히 낮은지 확인
        self.assertLess(deviation, -10)  # 최소 10% 이상 이격되어 있어야 함
    
    def test_overbought_condition(self):
        """과매수 상태에서의 신호 테스트"""
        result = generate_trading_signal(self.overbought_data)
        
        # 과매수 상태에서는 매도 신호가 발생해야 함
        self.assertEqual(result['signal'], 'Sell')
        
        # 추가로 확률값 확인
        latest = self.overbought_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 과매수 상태에서는 매도 확률이 매우 높아야 함
        self.assertGreater(sell_prob, 70)
        self.assertLess(buy_prob, 20)
        
        # %B 값이 상단밴드 근처인지 확인
        self.assertGreater(b_value, 0.8)
    
    def test_oversold_condition(self):
        """과매도 상태에서의 신호 테스트"""
        result = generate_trading_signal(self.oversold_data)
        
        # 과매도 상태에서는 매수 신호가 발생해야 함
        self.assertIn(result['signal'], ['Buy', 'Buy_Strong'])
        
        # 추가로 확률값 확인
        latest = self.oversold_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 과매도 상태에서는 매수 확률이 매우 높아야 함
        self.assertGreater(buy_prob, 70)
        self.assertLess(sell_prob, 20)
        
        # %B 값이 하단밴드 근처인지 확인
        self.assertLess(b_value, 0.2)
    
    def test_band_riding_detection(self):
        """밴드타기 현상 감지 테스트"""
        # 밴드타기 감지 함수 테스트
        band_riding_result = detect_band_riding(self.band_riding_data, lookback=10)
        
        # 밴드타기 감지 결과 확인
        self.assertTrue(band_riding_result['is_riding'])
        self.assertGreaterEqual(band_riding_result['consecutive_days'], 3)
        self.assertGreater(band_riding_result['strength'], 0)
        
        # 신호 확인
        result = generate_trading_signal(self.band_riding_data)
        
        # 밴드타기 현상에서는 대개 매도 신호가 발생
        self.assertEqual(result['signal'], 'Sell')
    
    def test_sideways_market(self):
        """횡보 시장에서의 신호 테스트"""
        result = generate_trading_signal(self.sideways_data)
        
        # 테스트 확인을 위한 진단 출력
        latest = self.sideways_data.iloc[-1]
        print(f"횡보 시장 테스트 - 마지막 %B 값: {latest['%B']}")
        print(f"횡보 시장 테스트 - 생성된 신호: {result['signal']}")
        
        # 횡보 시장에서는 일반적으로 Hold 신호가 발생
        self.assertEqual(result['signal'], 'Hold')
        
        # 추가로 확률값 확인
        latest = self.sideways_data.iloc[-1]
        b_value = latest['%B']
        deviation = ((latest['Close'] - latest['MA25']) / latest['MA25']) * 100
        buy_prob, sell_prob = calculate_trading_probability(b_value, deviation)
        
        # 횡보 시장에서는 매수/매도 확률이 모두 낮아야 함
        self.assertLess(buy_prob + sell_prob, 100)  # 두 확률의 합이 100 미만이어야 함
        
        # 이격도가 작아야 함
        self.assertLess(abs(deviation), 5)  # 이격도 절대값이 5% 미만이어야 함
    
    def test_tranche_strategy(self):
        """분할 매수 전략 테스트"""
        # 과매도 상태의 마지막 데이터로 분할 매수 전략 테스트
        latest_oversold = self.oversold_data.iloc[-1]
        b_value = latest_oversold['%B']
        deviation = ((latest_oversold['Close'] - latest_oversold['MA25']) / latest_oversold['MA25']) * 100
        
        # 분할 매수 전략 함수 호출
        tranche_result = calculate_tranche_strategy(b_value, deviation)
        
        # 과매도 상태이므로 분할 매수 단계가 활성화되어야 함
        self.assertGreater(tranche_result['current_tranche'], 0)
        # 자금 배분 비율이 설정되어야 함
        self.assertGreater(tranche_result['allocation_percent'], 0)
        # 전략 메시지가 비어있지 않아야 함
        self.assertGreater(len(tranche_result['strategy_message']), 0)
        
        # 과매수 상태에서는 익절 전략이 활성화되어야 함
        latest_overbought = self.overbought_data.iloc[-1]
        b_value_ob = latest_overbought['%B']
        deviation_ob = ((latest_overbought['Close'] - latest_overbought['MA25']) / latest_overbought['MA25']) * 100
        
        tranche_result_ob = calculate_tranche_strategy(b_value_ob, deviation_ob)
        
        # 과매수 상태이므로 분할 매수 단계는 비활성화되어야 함
        self.assertEqual(tranche_result_ob['current_tranche'], 0)
        # 익절 전략 메시지가 비어있지 않아야 함
        self.assertGreater(len(tranche_result_ob['exit_strategy']), 0)

if __name__ == '__main__':
    unittest.main() 