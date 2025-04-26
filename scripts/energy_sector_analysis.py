#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import os
import sys
from datetime import datetime

# 현재 스크립트 경로를 기준으로 상위 디렉토리를 sys.path에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# 필요한 모듈 임포트 
try:
    from src.stock_data import get_stock_data
    from src.indicators import add_all_indicators
    from src.signal import generate_trading_signal
    from src.config import set_ticker, config
except ImportError as e:
    print(f"필요한 모듈 임포트 실패: {e}")
    print("이 스크립트는 auto-stock-trading 프로젝트의 루트 디렉토리에서 실행해야 합니다.")
    sys.exit(1)

# 에너지 섹터 주식 및 ETF 정의 (Industry Group 추가)
ENERGY_SECTOR = {
    "에너지 (Energy)": {
        "industry_groups": {
            "석유 & 가스 탐사 및 생산 (Oil & Gas E&P)": ["XOM", "CVX", "COP", "EOG", "OXY", "PXD"],
            "석유 & 가스 장비 및 서비스 (Oil & Gas Equipment & Services)": ["SLB", "OIH"],
            "석유 & 가스 정제 및 마케팅 (Oil & Gas Refining & Marketing)": ["PSX", "VLO", "MPC"],
            "통합 에너지 ETF (Integrated Energy ETFs)": ["XLE", "VDE", "IYE", "FENY", "XOP"]
        },
        "stocks": ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PXD", "PSX", "VLO", "MPC"],
        "etfs": ["XLE", "VDE", "IYE", "FENY", "XOP", "OIH"]
    }
}

# 티커별 Industry Group 매핑 함수
def get_industry_group(ticker):
    """티커에 해당하는 Industry Group을 반환합니다."""
    for sector_name, sector_data in ENERGY_SECTOR.items():
        for group_name, tickers in sector_data.get("industry_groups", {}).items():
            if ticker in tickers:
                return group_name
    return "기타"

# 매매 가능성 계산 함수
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

def analyze_energy_sector(sector_data):
    """에너지 섹터 주식 및 ETF를 분석합니다."""
    results = []
    
    for sector_name, tickers in sector_data.items():
        print(f"\n=== {sector_name} 섹터 상세 분석 ===")
        
        # Industry Group별 결과를 저장할 딕셔너리
        group_results = {}
        for group_name in tickers.get("industry_groups", {}).keys():
            group_results[group_name] = []
        
        # 주식 분석
        print("\n🔹 대표 주식:")
        for ticker in tickers["stocks"]:
            try:
                print(f"\n분석 중: {ticker}")
                # 티커 설정
                set_ticker(ticker)
                
                # 주식 데이터 가져오기
                df = get_stock_data()
                if df is None:
                    print(f"❌ {ticker}: 데이터를 가져오는데 실패했습니다.")
                    continue
                
                # 지표 계산
                df = add_all_indicators(df)
                
                # 매매 신호 생성
                result = generate_trading_signal(df)
                
                if result and result.get("data"):
                    data = result["data"]
                    industry_group = get_industry_group(ticker)
                    
                    b_value = data.get("b_value", 0.5)
                    dev_percent = data.get("deviation_percent", 0)
                    
                    # 매수/매도 확률 계산
                    buy_probability, sell_probability = calculate_trading_probability(b_value, dev_percent)
                    
                    result_item = {
                        "sector": sector_name,
                        "industry_group": industry_group,
                        "type": "Stock",
                        "ticker": ticker,
                        "signal": data.get("signal", "N/A"),
                        "technical_signal": data.get("technical_signal", "N/A"),
                        "price": data.get("price", 0),
                        "ma25": data.get("ma25", 0),
                        "b_value": b_value,
                        "mfi": data.get("mfi", 0),
                        "deviation_percent": dev_percent,
                        "band_width": data.get("band_width", 0),
                        "buy_probability": buy_probability,
                        "sell_probability": sell_probability
                    }
                    
                    results.append(result_item)
                    if industry_group in group_results:
                        group_results[industry_group].append(result_item)
                    
                    # 포맷에 맞게 결과 출력
                    signal_text = data.get('signal', 'No Signal')
                    probability_text = ""
                    
                    if signal_text == "Hold":
                        probability_text = f"[매수 {buy_probability}% | 매도 {sell_probability}%]"
                    
                    print(f"✅ {ticker} [{industry_group}]: {signal_text} {probability_text}")
                    print(f"   가격: ${data.get('price', 0):.2f}, MA25: ${data.get('ma25', 0):.2f}")
                    print(f"   %B: {b_value:.2f}, MFI: {data.get('mfi', 0):.2f}")
                    print(f"   MA25 이격도: {dev_percent:.2f}%, 밴드폭: {data.get('band_width', 0):.2f}%")
                else:
                    print(f"❌ {ticker}: 분석 실패")
            except Exception as e:
                print(f"❌ {ticker} 분석 중 오류: {str(e)}")
        
        # ETF 분석
        print("\n🔹 관련 ETF:")
        for ticker in tickers["etfs"]:
            try:
                print(f"\n분석 중: {ticker}")
                # 티커 설정
                set_ticker(ticker)
                
                # 주식 데이터 가져오기
                df = get_stock_data()
                if df is None:
                    print(f"❌ {ticker}: 데이터를 가져오는데 실패했습니다.")
                    continue
                
                # 지표 계산
                df = add_all_indicators(df)
                
                # 매매 신호 생성
                result = generate_trading_signal(df)
                
                if result and result.get("data"):
                    data = result["data"]
                    industry_group = get_industry_group(ticker)
                    
                    b_value = data.get("b_value", 0.5)
                    dev_percent = data.get("deviation_percent", 0)
                    
                    # 매수/매도 확률 계산
                    buy_probability, sell_probability = calculate_trading_probability(b_value, dev_percent)
                    
                    result_item = {
                        "sector": sector_name,
                        "industry_group": industry_group,
                        "type": "ETF",
                        "ticker": ticker,
                        "signal": data.get("signal", "N/A"),
                        "technical_signal": data.get("technical_signal", "N/A"),
                        "price": data.get("price", 0),
                        "ma25": data.get("ma25", 0),
                        "b_value": b_value,
                        "mfi": data.get("mfi", 0),
                        "deviation_percent": dev_percent,
                        "band_width": data.get("band_width", 0),
                        "buy_probability": buy_probability,
                        "sell_probability": sell_probability
                    }
                    
                    results.append(result_item)
                    if industry_group in group_results:
                        group_results[industry_group].append(result_item)
                    
                    # 포맷에 맞게 결과 출력
                    signal_text = data.get('signal', 'No Signal')
                    probability_text = ""
                    
                    if signal_text == "Hold":
                        probability_text = f"[매수 {buy_probability}% | 매도 {sell_probability}%]"
                    
                    print(f"✅ {ticker} [{industry_group}]: {signal_text} {probability_text}")
                    print(f"   가격: ${data.get('price', 0):.2f}, MA25: ${data.get('ma25', 0):.2f}")
                    print(f"   %B: {b_value:.2f}, MFI: {data.get('mfi', 0):.2f}")
                    print(f"   MA25 이격도: {dev_percent:.2f}%, 밴드폭: {data.get('band_width', 0):.2f}%")
                else:
                    print(f"❌ {ticker}: 분석 실패")
            except Exception as e:
                print(f"❌ {ticker} 분석 중 오류: {str(e)}")
        
        # Industry Group별 분석 결과 출력
        print("\n🔹 Industry Group별 분석 결과:")
        for group_name, group_data in group_results.items():
            if group_data:
                avg_b_value = sum(item["b_value"] for item in group_data) / len(group_data)
                avg_deviation = sum(item["deviation_percent"] for item in group_data) / len(group_data)
                avg_buy_prob = sum(item["buy_probability"] for item in group_data) / len(group_data)
                avg_sell_prob = sum(item["sell_probability"] for item in group_data) / len(group_data)
                
                print(f"\n📊 {group_name} (종목 수: {len(group_data)}개)")
                print(f"   평균 %B: {avg_b_value:.2f}, 평균 이격도: {avg_deviation:.2f}%")
                print(f"   그룹 매수 확률: {avg_buy_prob:.0f}%, 그룹 매도 확률: {avg_sell_prob:.0f}%")
    
    return results

def save_results(results):
    """분석 결과를 CSV 파일로 저장합니다."""
    if not results:
        print("저장할 결과가 없습니다.")
        return
    
    # 결과를 DataFrame으로 변환
    df = pd.DataFrame(results)
    
    # 현재 날짜를 포함한 파일명 생성
    today = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"energy_sector_analysis_{today}.csv"
    
    # 결과 저장
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n분석 결과가 {filename}에 저장되었습니다.")
    
    # 매수/매도 신호 분석
    buy_signals = df[df['signal'].str.contains('Buy', na=False)]
    sell_signals = df[df['signal'].str.contains('Sell', na=False)]
    
    print("\n🔔 매수 신호 종목:")
    if len(buy_signals) > 0:
        for _, row in buy_signals.iterrows():
            print(f"{row['ticker']} ({row['type']}, {row['industry_group']}): {row['signal']}, B값: {row['b_value']:.2f}, MA25 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매수 신호 종목이 없습니다.")
    
    print("\n🔔 매도 신호 종목:")
    if len(sell_signals) > 0:
        for _, row in sell_signals.iterrows():
            print(f"{row['ticker']} ({row['type']}, {row['industry_group']}): {row['signal']}, B값: {row['b_value']:.2f}, MA25 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매도 신호 종목이 없습니다.")
    
    # Industry Group별 분석
    print("\n🔔 Industry Group별 분석:")
    groups = df['industry_group'].unique()
    for group in groups:
        group_df = df[df['industry_group'] == group]
        buy_count = len(group_df[group_df['signal'].str.contains('Buy', na=False)])
        sell_count = len(group_df[group_df['signal'].str.contains('Sell', na=False)])
        hold_count = len(group_df[group_df['signal'] == 'Hold'])
        
        avg_b_value = group_df['b_value'].mean()
        avg_deviation = group_df['deviation_percent'].mean()
        avg_buy_prob = group_df['buy_probability'].mean()
        avg_sell_prob = group_df['sell_probability'].mean()
        
        print(f"\n📊 {group} (종목 수: {len(group_df)}개)")
        print(f"   신호 분포: Buy {buy_count}개, Sell {sell_count}개, Hold {hold_count}개")
        print(f"   평균 %B: {avg_b_value:.2f}, 평균 이격도: {avg_deviation:.2f}%")
        print(f"   평균 매수 확률: {avg_buy_prob:.0f}%, 평균 매도 확률: {avg_sell_prob:.0f}%")
    
    # Hold 종목 매매 가능성 분석
    print("\n🔔 Hold 종목 매매 확률 분석:")
    
    hold_df = df[df['signal'] == 'Hold'].copy()
    hold_df['total_probability'] = hold_df['buy_probability'] + hold_df['sell_probability']
    
    # 매수 확률 상위 종목
    high_buy_prob = hold_df[hold_df['buy_probability'] >= 40].sort_values(by='buy_probability', ascending=False)
    if not high_buy_prob.empty:
        print("\n매수 확률 상위 종목:")
        for _, row in high_buy_prob.iterrows():
            print(f"{row['ticker']} ({row['type']}, {row['industry_group']}): 매수 확률 {row['buy_probability']:.0f}%, 매도 확률 {row['sell_probability']:.0f}%, B값: {row['b_value']:.2f}, 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매수 확률이 높은 종목이 없습니다.")
    
    # 매도 확률 상위 종목
    high_sell_prob = hold_df[hold_df['sell_probability'] >= 40].sort_values(by='sell_probability', ascending=False)
    if not high_sell_prob.empty:
        print("\n매도 확률 상위 종목:")
        for _, row in high_sell_prob.iterrows():
            print(f"{row['ticker']} ({row['type']}, {row['industry_group']}): 매도 확률 {row['sell_probability']:.0f}%, 매수 확률 {row['buy_probability']:.0f}%, B값: {row['b_value']:.2f}, 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매도 확률이 높은 종목이 없습니다.")
    
    # 시그널별 요약
    signal_summary = df['signal'].value_counts()
    print("\n🔔 시그널 요약:")
    for signal, count in signal_summary.items():
        print(f"{signal}: {count}개")
    
    # 매수/매도 확률 구간별 분포
    print("\n🔔 매수/매도 확률 분포:")
    buy_prob_bins = [0, 20, 40, 60, 80, 100]
    buy_prob_labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%']
    buy_prob_counts = pd.cut(hold_df['buy_probability'], bins=buy_prob_bins, labels=buy_prob_labels).value_counts().sort_index()
    
    sell_prob_bins = [0, 20, 40, 60, 80, 100]
    sell_prob_labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%']
    sell_prob_counts = pd.cut(hold_df['sell_probability'], bins=sell_prob_bins, labels=sell_prob_labels).value_counts().sort_index()
    
    print("매수 확률 분포:")
    for label, count in buy_prob_counts.items():
        print(f"   {label}: {count}개")
    
    print("매도 확률 분포:")
    for label, count in sell_prob_counts.items():
        print(f"   {label}: {count}개")

def main():
    """메인 함수"""
    print("에너지 섹터 주식 및 ETF 분석을 시작합니다...\n")
    
    try:
        # 에너지 섹터 주식 및 ETF 분석
        results = analyze_energy_sector(ENERGY_SECTOR)
        
        # 결과 저장
        save_results(results)
        
        print("\n에너지 섹터 분석이 완료되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 