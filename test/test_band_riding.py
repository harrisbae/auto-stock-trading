import unittest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트할 모듈 import
from src.indicators import add_all_indicators
from main import detect_band_riding

class TestBandRiding(unittest.TestCase):
    """밴드타기 현상 감지 테스트 클래스"""
    
    def generate_band_riding_data(self, days=100, type='normal', strength='medium'):
        """밴드타기 패턴 데이터 생성 함수"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # 기본 가격 데이터 생성
        prices = []
        current_price = 100
        volatility = 5
        
        # 3단계: 초기 중립, 밴드타기 준비 상승, 밴드타기 현상
        for i in range(days):
            if i < days - 20:  # 초기 중립 구간
                change = np.random.normal(0, volatility/5)
            elif i < days - 10:  # 밴드타기 준비 상승 구간
                if type == 'normal':
                    change = np.random.normal(0.6, volatility/6)
                elif type == 'strong':
                    change = np.random.normal(1.0, volatility/5)
                elif type == 'weak':
                    change = np.random.normal(0.3, volatility/7)
            else:  # 밴드타기 현상 구간
                if type == 'normal':
                    if strength == 'medium':
                        change = np.random.normal(0.4, volatility/7)
                    elif strength == 'strong':
                        change = np.random.normal(0.6, volatility/6)
                    elif strength == 'weak':
                        change = np.random.normal(0.2, volatility/8)
                elif type == 'strong':
                    change = np.random.normal(0.8, volatility/5)
                elif type == 'weak':
                    change = np.random.normal(0.1, volatility/10)
            
            current_price = max(current_price + change, 1)
            prices.append(current_price)
        
        # 기본 데이터프레임 생성
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'Close': prices,
            'Volume': [np.random.normal(1000000, 200000) for _ in range(days)]
        }, index=dates)
        
        # 밴드타기 기간 거래량 조정
        if type == 'strong':
            for i in range(days - 10, days):
                df.loc[df.index[i], 'Volume'] = df.iloc[i-1]['Volume'] * (1 + np.random.uniform(0.1, 0.3))
        
        df_with_indicators = add_all_indicators(df)
        
        # 밴드타기 직접 감지될 수 있도록 %B 값 조정
        if type == 'normal' or type == 'strong':
            for i in range(5):
                idx = len(df_with_indicators) - 5 + i
                # UpperBand와 LowerBand, Close 값 조정으로 %B 값이 더 정확하게 계산되도록 함
                mean = df_with_indicators.loc[df_with_indicators.index[idx], 'MA25']
                std = df_with_indicators.loc[df_with_indicators.index[idx], 'STD']
                
                if type == 'normal':
                    # 중간 강도 밴드타기 (%B = 0.85~0.95)
                    target_b = 0.85 + (i * 0.02)
                    df_with_indicators.loc[df_with_indicators.index[idx], '%B'] = target_b
                    df_with_indicators.loc[df_with_indicators.index[idx], 'Close'] = mean + (target_b * 2 - 1) * 2 * std
                    
                    # 정상적인 볼륨(거래량) 설정 - 밴드타기는 있지만 추세가 강하지 않도록
                    # 거래량 감소시켜 강한 추세가 아니라고 판단되도록 함
                    df_with_indicators.loc[df_with_indicators.index[idx], 'Volume'] = df_with_indicators.iloc[idx-1]['Volume'] * 0.8
                    
                    # 가격 변화 패턴 랜덤화 - 일부 하락일 포함
                    if i % 2 == 0:
                        df_with_indicators.loc[df_with_indicators.index[idx], 'Close'] *= 0.99
                    
                elif type == 'strong':
                    # 강한 밴드타기 (%B = 0.9~1.0)
                    target_b = 0.9 + (i * 0.02)
                    df_with_indicators.loc[df_with_indicators.index[idx], '%B'] = target_b
                    df_with_indicators.loc[df_with_indicators.index[idx], 'Close'] = mean + (target_b * 2 - 1) * 2 * std
                
                # 강한 추세에서만 거래량 증가
                if type == 'strong' and i > 2:
                    df_with_indicators.loc[df_with_indicators.index[idx], 'Volume'] *= 1.5
        
        elif type == 'weak':
            # 약한 밴드타기: 상단밴드에 접촉하지 않도록 설정
            for i in range(5):
                idx = len(df_with_indicators) - 5 + i
                if i < 2:  # 앞의 2일은 0.7 정도로 설정
                    target_b = 0.5 + (i * 0.1)
                else:   # 나머지는 0.5 미만
                    target_b = 0.3 + (i * 0.02)
                    
                df_with_indicators.loc[df_with_indicators.index[idx], '%B'] = target_b
                
                mean = df_with_indicators.loc[df_with_indicators.index[idx], 'MA25']
                std = df_with_indicators.loc[df_with_indicators.index[idx], 'STD']
                df_with_indicators.loc[df_with_indicators.index[idx], 'Close'] = mean + (target_b * 2 - 1) * 2 * std
        
        return df_with_indicators
    
    def setUp(self):
        """테스트 데이터 준비"""
        # 다양한 밴드타기 패턴 데이터셋 생성
        self.normal_riding_data = self.generate_band_riding_data(type='normal', strength='medium')
        self.strong_riding_data = self.generate_band_riding_data(type='strong', strength='strong')
        self.weak_riding_data = self.generate_band_riding_data(type='weak', strength='weak')
        
        # 밴드타기가 아닌 일반 데이터 생성
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        prices = []
        current_price = 100
        
        for i in range(100):
            change = np.random.normal(0, 1)
            current_price = max(current_price + change, 1)
            prices.append(current_price)
        
        self.no_riding_data = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'Close': prices,
            'Volume': [np.random.normal(1000000, 200000) for _ in range(100)]
        }, index=dates)
        
        no_riding_with_indicators = add_all_indicators(self.no_riding_data)
        
        # 확실히 밴드타기가 없도록 %B 값 조정
        for i in range(10):
            idx = len(no_riding_with_indicators) - 10 + i
            target_b = 0.4 + (i * 0.02)
            no_riding_with_indicators.loc[no_riding_with_indicators.index[idx], '%B'] = target_b
            
            mean = no_riding_with_indicators.loc[no_riding_with_indicators.index[idx], 'MA25']
            std = no_riding_with_indicators.loc[no_riding_with_indicators.index[idx], 'STD']
            no_riding_with_indicators.loc[no_riding_with_indicators.index[idx], 'Close'] = mean + (target_b * 2 - 1) * 2 * std
        
        self.no_riding_data = no_riding_with_indicators
    
    def test_normal_band_riding_detection(self):
        """일반적인 밴드타기 감지 테스트"""
        # 일반 강도의 밴드타기 데이터 준비
        normal_data = self.normal_riding_data.copy()
        
        # 정확하게 강한 추세가 아니라고 판단되도록 추가 조정
        for i in range(5):
            idx = len(normal_data) - 5 + i
            # 거래량 감소
            normal_data.loc[normal_data.index[idx], 'Volume'] = normal_data.iloc[idx-1]['Volume'] * 0.5
            
            # 가격 등락 패턴 만들기 (강한 상승 추세가 아니도록)
            if i % 2 == 0:
                normal_data.loc[normal_data.index[idx], 'Close'] *= 0.98
        
        result = detect_band_riding(normal_data)
        
        # 밴드타기가 감지되어야 함
        self.assertTrue(result['is_riding'])
        
        # 3일 이상 연속으로 상단밴드 접촉
        self.assertGreaterEqual(result['consecutive_days'], 3)
        
        # 강도가 중간 정도여야 함 (20-70% 사이)
        self.assertGreaterEqual(result['strength'], 20)
        self.assertLessEqual(result['strength'], 70)
        
        # 일반 밴드타기는 강한 추세로 판단되지 않아야 함
        self.assertFalse(result['is_strong_trend'])
    
    def test_strong_band_riding_detection(self):
        """강한 밴드타기 감지 테스트"""
        # 강한 밴드타기 감지 테스트
        
        # 강한 추세를 위해 거래량과 %B 값 추가 조정
        strong_data = self.strong_riding_data.copy()
        
        # 마지막 5일 동안 거래량 추가 증가 및 %B 값 증가
        for i in range(5):
            idx = len(strong_data) - 5 + i
            strong_data.loc[strong_data.index[idx], 'Volume'] = strong_data.iloc[idx-1]['Volume'] * 1.5
            strong_data.loc[strong_data.index[idx], '%B'] = min(1.0, 0.9 + (i * 0.02))
            
            # 높은 %B 값에 맞게 Close 가격 조정
            mean = strong_data.loc[strong_data.index[idx], 'MA25']
            std = strong_data.loc[strong_data.index[idx], 'STD']
            b_value = strong_data.loc[strong_data.index[idx], '%B']
            strong_data.loc[strong_data.index[idx], 'Close'] = mean + (b_value * 2 - 1) * 2 * std
        
        # 가격이 지속적으로 상승하도록 조정
        price_diffs = strong_data['Close'].pct_change().dropna()
        positive_pct = sum(1 for x in price_diffs.tail(5) if x > 0) / 5
        
        # 추가 조정이 필요한 경우
        if positive_pct < 0.7:
            for i in range(4):
                idx = len(strong_data) - 5 + i
                next_idx = idx + 1
                if next_idx < len(strong_data):
                    strong_data.loc[strong_data.index[next_idx], 'Close'] = strong_data.iloc[idx]['Close'] * 1.02
        
        result = detect_band_riding(strong_data)
        
        # 밴드타기가 감지되어야 함
        self.assertTrue(result['is_riding'])
        
        # 3일 이상 연속으로 상단밴드 접촉
        self.assertGreaterEqual(result['consecutive_days'], 3)
        
        # 강도가 높아야 함 (70% 이상)
        self.assertGreaterEqual(result['strength'], 70)
    
    def test_weak_band_riding_detection(self):
        """약한 밴드타기 감지 테스트"""
        result = detect_band_riding(self.weak_riding_data)
        
        # 약한 밴드타기는 감지되지 않아야 함 (%B가 0.8 미만이므로)
        self.assertFalse(result['is_riding'])
        
        # 연속 일수가 적어야 함
        self.assertLess(result['consecutive_days'], 3)
    
    def test_no_band_riding(self):
        """밴드타기가 없는 데이터 테스트"""
        # 밴드타기가 없는 데이터 테스트
        result = detect_band_riding(self.no_riding_data)
        
        # 밴드타기가 감지되지 않아야 함
        self.assertFalse(result['is_riding'])
        
        # 연속 일수가 적어야 함
        self.assertLess(result['consecutive_days'], 3)
    
    def test_lookback_period(self):
        """조회 기간 변경 테스트"""
        # 조회 기간을 다르게 설정하여 테스트
        for lookback in [3, 5, 10]:
            result = detect_band_riding(self.normal_riding_data, lookback=lookback)
            
            # 조회 기간이 충분히 길면 밴드타기가 감지되어야 함
            if lookback >= 5:
                self.assertTrue(result['is_riding'])
            
            # 연속 일수는 조회 기간보다 작거나 같아야 함
            self.assertLessEqual(result['consecutive_days'], lookback)
    
    def test_trend_strength_detection(self):
        """추세 강도 감지 테스트"""
        # 거래량이 증가하는 강한 밴드타기 케이스
        strong_trend_data = self.strong_riding_data.copy()
        
        # 마지막 5일 동안 거래량 추가 증가 및 %B 값 증가
        for i in range(5):
            idx = len(strong_trend_data) - 5 + i
            strong_trend_data.loc[strong_trend_data.index[idx], 'Volume'] = strong_trend_data.iloc[idx-1]['Volume'] * 2.0
            strong_trend_data.loc[strong_trend_data.index[idx], '%B'] = 0.95
            
            # 높은 %B 값에 맞게 Close 가격 조정
            mean = strong_trend_data.loc[strong_trend_data.index[idx], 'MA25']
            std = strong_trend_data.loc[strong_trend_data.index[idx], 'STD']
            strong_trend_data.loc[strong_trend_data.index[idx], 'Close'] = mean + 0.9 * 2 * std
            
            # 가격이 지속 상승하도록 조정
            if i > 0:
                strong_trend_data.loc[strong_trend_data.index[idx], 'Close'] = strong_trend_data.iloc[idx-1]['Close'] * 1.03
        
        result = detect_band_riding(strong_trend_data)
        
        # 강한 추세가 감지되어야 함
        self.assertTrue(result['is_riding'])
        self.assertTrue(result['is_strong_trend'])
        
        # 추세 메시지가 있어야 함
        self.assertGreater(len(result['trend_message']), 0)
    
    def test_consecutive_days_requirement(self):
        """연속 일수 요구사항 테스트"""
        # 단 1-2일만 상단밴드에 닿는 데이터 생성
        temp_data = self.no_riding_data.copy()
        
        # 마지막 2일만 상단밴드에 닿게 조정 (%B 값이 0.8 이상)
        for i in range(2):
            idx = len(temp_data) - 2 + i
            temp_data.loc[temp_data.index[idx], '%B'] = 0.82
            
            # %B 값에 맞게 Close 가격 조정
            mean = temp_data.loc[temp_data.index[idx], 'MA25']
            std = temp_data.loc[temp_data.index[idx], 'STD']
            temp_data.loc[temp_data.index[idx], 'Close'] = mean + 0.64 * 2 * std
        
        # 나머지 날은 확실히 0.8 미만으로 설정
        for i in range(5):
            if i < 3:  # 앞의 3일
                idx = len(temp_data) - 5 + i
                temp_data.loc[temp_data.index[idx], '%B'] = 0.5
                
                # %B 값에 맞게 Close 가격 조정
                mean = temp_data.loc[temp_data.index[idx], 'MA25']
                std = temp_data.loc[temp_data.index[idx], 'STD']
                temp_data.loc[temp_data.index[idx], 'Close'] = mean
        
        result = detect_band_riding(temp_data)
        
        # 연속 2일은 밴드타기로 감지되지 않아야 함 (3일 이상 필요)
        self.assertFalse(result['is_riding'])
        self.assertEqual(result['consecutive_days'], 2)

if __name__ == '__main__':
    unittest.main() 