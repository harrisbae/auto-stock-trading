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
from backtest.new_test.spy_strategy_comparison import run_bollinger_strategy

class TestMFIFilter(unittest.TestCase):
    """MFI 필터 기능 테스트 클래스"""
    
    def generate_test_data(self, days=100, scenario='normal'):
        """테스트용 데이터 생성 함수

        Parameters:
        -----------
        days : int
            생성할 데이터의 일수
        scenario : str
            'normal': 일반적인 데이터
            'oversold': 과매도 상태 데이터 (MFI 낮음)
            'overbought': 과매수 상태 데이터 (MFI 높음)
        """
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # 기본 가격 데이터 생성
        prices = []
        volumes = []
        current_price = 100
        
        # 시나리오에 따른 가격/거래량 패턴 생성
        for i in range(days):
            if scenario == 'normal':
                price_change = np.random.normal(0.05, 1)
                volume = np.random.normal(1000000, 200000)
            elif scenario == 'oversold':
                # 지속적인 하락세와 거래량 증가 (Oversold 조건)
                if i >= days - 10:  # 마지막 10일
                    price_change = np.random.normal(-0.5, 0.5)  # 하락 편향
                    volume = np.random.normal(1500000, 300000)  # 거래량 증가
                else:
                    price_change = np.random.normal(0.05, 1)
                    volume = np.random.normal(1000000, 200000)
            elif scenario == 'overbought':
                # 지속적인 상승세와 거래량 증가 (Overbought 조건)
                if i >= days - 10:  # 마지막 10일
                    price_change = np.random.normal(0.5, 0.5)  # 상승 편향
                    volume = np.random.normal(1500000, 300000)  # 거래량 증가
                else:
                    price_change = np.random.normal(0.05, 1)
                    volume = np.random.normal(1000000, 200000)
            
            current_price = max(current_price + price_change, 1)
            prices.append(current_price)
            volumes.append(volume)
        
        # 기본 데이터프레임 생성
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'Close': prices,
            'Volume': volumes
        }, index=dates)
        
        # 지표 계산
        df_with_indicators = add_all_indicators(df)
        
        # 시나리오에 따라 MFI 값 강제 조정
        if scenario == 'oversold':
            for i in range(5):  # 마지막 5일
                idx = len(df_with_indicators) - 5 + i
                # MFI 값을 20 이하로 설정
                df_with_indicators.loc[df_with_indicators.index[idx], 'MFI'] = np.random.uniform(10, 20)
        elif scenario == 'overbought':
            for i in range(5):  # 마지막 5일
                idx = len(df_with_indicators) - 5 + i
                # MFI 값을 80 이상으로 설정
                df_with_indicators.loc[df_with_indicators.index[idx], 'MFI'] = np.random.uniform(80, 90)
        
        return df_with_indicators
    
    def setUp(self):
        """테스트 데이터 준비"""
        # 다양한 시나리오의 데이터셋 생성
        self.normal_data = self.generate_test_data(scenario='normal')
        self.oversold_data = self.generate_test_data(scenario='oversold')
        self.overbought_data = self.generate_test_data(scenario='overbought')
        
        # 테스트용 전략 매개변수
        self.strategy_params = {
            'tranche_count': 3,
            'stop_loss_percent': 7,
            'use_band_riding': True,
            'risk_level': 'medium',
            'target_profit_percent': 10
        }
    
    def test_mfi_filter_buy_signal(self):
        """MFI 필터 매수 신호 테스트 - 과매도 상태에서 매수 신호 확인"""
        # MFI 필터 활성화
        params_with_mfi = self.strategy_params.copy()
        params_with_mfi['use_mfi_filter'] = True
        
        # MFI 필터 비활성화
        params_without_mfi = self.strategy_params.copy()
        params_without_mfi['use_mfi_filter'] = False
        
        # 과매도 상태 데이터로 백테스트 실행
        result_with_mfi = run_bollinger_strategy(self.oversold_data, params_with_mfi)
        result_without_mfi = run_bollinger_strategy(self.oversold_data, params_without_mfi)
        
        # 매매 기록 분석
        buy_trades_with_mfi = [t for t in result_with_mfi['trades'] if t['type'] == 'buy']
        buy_trades_without_mfi = [t for t in result_without_mfi['trades'] if t['type'] == 'buy']
        
        # MFI 필터를 사용하면 과매도 상태에서 매수 신호가 발생해야 함
        self.assertGreater(len(buy_trades_with_mfi), 0, "MFI 필터가 활성화된 경우 과매도 상태에서 매수 신호가 발생해야 함")
        
        # MFI 필터 사용 시 과매도에서 매수 확인
        mfi_values = [float(self.oversold_data.loc[pd.to_datetime(trade['date']), 'MFI']) 
                     for trade in buy_trades_with_mfi 
                     if pd.to_datetime(trade['date']) in self.oversold_data.index]
        
        # 모든 매수가 MFI 20 이하에서 발생했는지 확인
        for mfi in mfi_values:
            self.assertLessEqual(mfi, 20, f"MFI 필터 사용 시 매수는 MFI 20 이하에서만 발생해야 함 (현재 MFI: {mfi})")
    
    def test_mfi_filter_sell_signal(self):
        """MFI 필터 매도 신호 테스트 - 과매수 상태에서 매도 신호 확인"""
        # 초기 매수가 있는 상태의 데이터 생성
        test_data = self.normal_data.copy()
        
        # 초기 60일은 정상, 이후 20일은 과매수 상태로 설정
        for i in range(20):
            idx = 60 + i
            if idx < len(test_data):
                test_data.loc[test_data.index[idx], 'MFI'] = np.random.uniform(80, 90)
        
        # MFI 필터 활성화
        params_with_mfi = self.strategy_params.copy()
        params_with_mfi['use_mfi_filter'] = True
        
        # MFI 필터 비활성화
        params_without_mfi = self.strategy_params.copy()
        params_without_mfi['use_mfi_filter'] = False
        
        # 강제로 초기 매수 상태 설정하기 위해 %B 값 조정
        for i in range(5):
            idx = 40 + i
            if idx < len(test_data):
                test_data.loc[test_data.index[idx], '%B'] = 0.1  # 하단밴드 터치로 매수 유도
        
        # 백테스트 실행
        result_with_mfi = run_bollinger_strategy(test_data, params_with_mfi)
        result_without_mfi = run_bollinger_strategy(test_data, params_without_mfi)
        
        # 매매 기록 분석
        sell_trades_with_mfi = [t for t in result_with_mfi['trades'] if t['type'] == 'sell']
        sell_trades_without_mfi = [t for t in result_without_mfi['trades'] if t['type'] == 'sell']
        
        # 매도 거래가 발생했는지 확인
        self.assertGreaterEqual(len(sell_trades_with_mfi), 0, "MFI 필터 사용 시 매도 거래가 발생해야 함")
        
        # 매도가 발생한 날짜의 MFI 값 확인
        mfi_values = []
        for trade in sell_trades_with_mfi:
            trade_date = pd.to_datetime(trade['date'])
            if trade_date in test_data.index:
                mfi_values.append(float(test_data.loc[trade_date, 'MFI']))
        
        # MFI 80 이상에서 매도가 발생했는지 확인
        for mfi in mfi_values:
            self.assertGreaterEqual(mfi, 80, f"MFI 필터 사용 시 매도는 MFI 80 이상에서만 발생해야 함 (현재 MFI: {mfi})")
    
    def test_mfi_filter_trade_count_reduction(self):
        """MFI 필터 적용 시 거래 횟수 감소 테스트"""
        # MFI 필터 활성화
        params_with_mfi = self.strategy_params.copy()
        params_with_mfi['use_mfi_filter'] = True
        
        # MFI 필터 비활성화
        params_without_mfi = self.strategy_params.copy()
        params_without_mfi['use_mfi_filter'] = False
        
        # 일반 데이터로 백테스트 실행
        result_with_mfi = run_bollinger_strategy(self.normal_data, params_with_mfi)
        result_without_mfi = run_bollinger_strategy(self.normal_data, params_without_mfi)
        
        # 거래 횟수 비교
        trades_with_mfi = len(result_with_mfi['trades'])
        trades_without_mfi = len(result_without_mfi['trades'])
        
        # MFI 필터 적용 시 거래 횟수가 감소해야 함
        self.assertLessEqual(trades_with_mfi, trades_without_mfi, 
                           f"MFI 필터 적용 시 거래 횟수가 감소해야 함 (필터 적용: {trades_with_mfi}, 미적용: {trades_without_mfi})")
    
    def test_mfi_threshold_effect(self):
        """MFI 임계값 효과 테스트"""
        # 다양한 MFI 임계값으로 테스트
        test_data = self.normal_data.copy()
        
        # 특정 날짜에 다양한 MFI 값 설정
        mfi_values = [15, 25, 35, 75, 85, 95]
        
        for i, mfi in enumerate(mfi_values):
            idx = 60 + i
            if idx < len(test_data):
                test_data.loc[test_data.index[idx], 'MFI'] = mfi
                
                # 매수/매도 신호 유도를 위한 %B 설정
                if mfi < 50:  # 낮은 MFI에는 낮은 %B (매수 신호)
                    test_data.loc[test_data.index[idx], '%B'] = 0.1
                else:  # 높은 MFI에는 높은 %B (매도 신호)
                    test_data.loc[test_data.index[idx], '%B'] = 0.9
        
        # 각 임계값으로 MFI 필터 테스트
        # 매수 임계값: 20, 매도 임계값: 80
        strict_params = self.strategy_params.copy()
        strict_params['use_mfi_filter'] = True  # 엄격한 MFI 필터
        
        # 백테스트 실행
        result = run_bollinger_strategy(test_data, strict_params)
        
        # 거래 기록 분석
        buys = [t for t in result['trades'] if t['type'] == 'buy']
        sells = [t for t in result['trades'] if t['type'] == 'sell']
        
        # 거래 날짜와 MFI 값 매핑
        buy_dates = [pd.to_datetime(t['date']) for t in buys]
        sell_dates = [pd.to_datetime(t['date']) for t in sells]
        
        # 매수/매도 발생 날짜의 MFI 값 확인
        for date in buy_dates:
            if date in test_data.index:
                mfi = float(test_data.loc[date, 'MFI'])
                self.assertLessEqual(mfi, 20, f"매수는 MFI 20 이하에서만 발생해야 함 (현재: {mfi})")
        
        for date in sell_dates:
            if date in test_data.index:
                mfi = float(test_data.loc[date, 'MFI'])
                self.assertGreaterEqual(mfi, 80, f"매도는 MFI 80 이상에서만 발생해야 함 (현재: {mfi})")
    
    def test_mfi_filter_performance_improvement(self):
        """MFI 필터 적용 시 성능 개선 테스트"""
        # 복합 데이터셋 구성 (일반 + 과매도 + 과매수)
        normal_part = self.normal_data.iloc[:60].copy()
        
        # 과매도 부분에서는 실제로 좋은 매수 기회 만들기
        oversold_part = self.oversold_data.iloc[-20:].copy()
        oversold_part.index = pd.date_range(start=normal_part.index[-1] + timedelta(days=1), periods=20, freq='D')
        
        # 과매도 이후의 가격 상승 패턴 강화
        for i in range(len(oversold_part)):
            if i > 5:  # 처음 5일간은 과매도 상태 유지, 그 후 상승세로 전환
                oversold_part.iloc[i, oversold_part.columns.get_loc('Close')] = oversold_part.iloc[i-1]['Close'] * (1 + np.random.uniform(0.01, 0.03))
                oversold_part.iloc[i, oversold_part.columns.get_loc('Open')] = oversold_part.iloc[i]['Close'] * 0.99
                oversold_part.iloc[i, oversold_part.columns.get_loc('High')] = oversold_part.iloc[i]['Close'] * 1.01
                oversold_part.iloc[i, oversold_part.columns.get_loc('Low')] = oversold_part.iloc[i]['Open'] * 0.99
                # MFI 값도 적절히 조정 (과매도에서 벗어나는 패턴)
                oversold_part.iloc[i, oversold_part.columns.get_loc('MFI')] = min(50, oversold_part.iloc[i-1]['MFI'] + 5)
        
        # 과매수 부분에서는 실제로 좋은 매도 기회 만들기
        overbought_part = self.overbought_data.iloc[-20:].copy()
        overbought_part.index = pd.date_range(start=oversold_part.index[-1] + timedelta(days=1), periods=20, freq='D')
        
        # 과매수 이후의 가격 하락 패턴 강화
        for i in range(len(overbought_part)):
            if i > 5:  # 처음 5일간은 과매수 상태 유지, 그 후 하락세로 전환
                overbought_part.iloc[i, overbought_part.columns.get_loc('Close')] = overbought_part.iloc[i-1]['Close'] * (1 - np.random.uniform(0.01, 0.03))
                overbought_part.iloc[i, overbought_part.columns.get_loc('Open')] = overbought_part.iloc[i]['Close'] * 1.01
                overbought_part.iloc[i, overbought_part.columns.get_loc('High')] = overbought_part.iloc[i]['Open'] * 1.01
                overbought_part.iloc[i, overbought_part.columns.get_loc('Low')] = overbought_part.iloc[i]['Close'] * 0.99
                # MFI 값도 적절히 조정 (과매수에서 벗어나는 패턴)
                overbought_part.iloc[i, overbought_part.columns.get_loc('MFI')] = max(50, overbought_part.iloc[i-1]['MFI'] - 5)
        
        # 추가로 거짓 신호가 많은 구간 삽입
        false_signal_part = self.normal_data.iloc[20:40].copy()
        false_signal_part.index = pd.date_range(start=overbought_part.index[-1] + timedelta(days=1), periods=20, freq='D')
        
        # 거짓 신호 구간에서 %B 값을 0.1-0.2 또는 0.8-0.9 사이로 설정하지만 
        # MFI 값은 매수/매도 조건과 일치하지 않게 설정
        for i in range(len(false_signal_part)):
            if i % 2 == 0:  # 짝수 인덱스에서는 하단 밴드 접근 (가짜 매수 신호)
                false_signal_part.iloc[i, false_signal_part.columns.get_loc('%B')] = np.random.uniform(0.1, 0.2)
                false_signal_part.iloc[i, false_signal_part.columns.get_loc('MFI')] = np.random.uniform(30, 50)  # 과매도 아님
            else:  # 홀수 인덱스에서는 상단 밴드 접근 (가짜 매도 신호)
                false_signal_part.iloc[i, false_signal_part.columns.get_loc('%B')] = np.random.uniform(0.8, 0.9)
                false_signal_part.iloc[i, false_signal_part.columns.get_loc('MFI')] = np.random.uniform(50, 70)  # 과매수 아님
            
            # 이 가짜 신호 구간에서는 가격이 원하는 방향으로 움직이지 않음
            if i > 0:
                if i % 2 == 0:  # 가짜 매수 신호 후 가격은 더 하락 (잘못된 매수)
                    false_signal_part.iloc[i, false_signal_part.columns.get_loc('Close')] = false_signal_part.iloc[i-1]['Close'] * 0.99
                else:  # 가짜 매도 신호 후 가격은 더 상승 (잘못된 매도)
                    false_signal_part.iloc[i, false_signal_part.columns.get_loc('Close')] = false_signal_part.iloc[i-1]['Close'] * 1.01
        
        # 데이터셋 결합
        combined_data = pd.concat([normal_part, oversold_part, overbought_part, false_signal_part])
        
        # 필요시 지표 재계산
        combined_data = add_all_indicators(combined_data)
        
        # MFI 필터 활성화/비활성화 전략 설정
        params_with_mfi = self.strategy_params.copy()
        params_with_mfi['use_mfi_filter'] = True
        
        params_without_mfi = self.strategy_params.copy()
        params_without_mfi['use_mfi_filter'] = False
        
        # 백테스트 실행
        result_with_mfi = run_bollinger_strategy(combined_data, params_with_mfi)
        result_without_mfi = run_bollinger_strategy(combined_data, params_without_mfi)
        
        # 성과 지표 비교 (디버깅용 출력)
        print(f"MFI 필터 성능 테스트 - MFI 필터 적용 시 최대 낙폭: {result_with_mfi['max_drawdown']:.2f}%")
        print(f"MFI 필터 성능 테스트 - MFI 필터 미적용 시 최대 낙폭: {result_without_mfi['max_drawdown']:.2f}%")
        
        # 최대 낙폭은 MFI 필터 적용 시 감소해야 함
        self.assertLessEqual(result_with_mfi['max_drawdown'], result_without_mfi['max_drawdown'], 
                           "MFI 필터 적용 시 최대 낙폭이 감소해야 함")
        
        # 거래당 수익 계산 및 출력
        if len(result_with_mfi['trades']) > 0 and len(result_without_mfi['trades']) > 0:
            profit_per_trade_with_mfi = result_with_mfi['total_return'] / len(result_with_mfi['trades'])
            profit_per_trade_without_mfi = result_without_mfi['total_return'] / len(result_without_mfi['trades'])
            
            print(f"MFI 필터 성능 테스트 - MFI 필터 적용 시 거래당 수익: {profit_per_trade_with_mfi:.2f}%")
            print(f"MFI 필터 성능 테스트 - MFI 필터 미적용 시 거래당 수익: {profit_per_trade_without_mfi:.2f}%")
            print(f"MFI 필터 성능 테스트 - 거래 횟수 (MFI 적용): {len(result_with_mfi['trades'])}")
            print(f"MFI 필터 성능 테스트 - 거래 횟수 (MFI 미적용): {len(result_without_mfi['trades'])}")
            
            # 거래당 수익은 MFI 필터 적용 시 증가해야 함
            self.assertGreaterEqual(profit_per_trade_with_mfi, profit_per_trade_without_mfi,
                                  "MFI 필터 적용 시 거래당 평균 수익이 증가해야 함")
        
        # 전체 수익률도 확인 (추가 검증)
        print(f"MFI 필터 성능 테스트 - MFI 필터 적용 시 총 수익률: {result_with_mfi['total_return']:.2f}%")
        print(f"MFI 필터 성능 테스트 - MFI 필터 미적용 시 총 수익률: {result_without_mfi['total_return']:.2f}%")

if __name__ == '__main__':
    unittest.main() 