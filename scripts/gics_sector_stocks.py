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

# GICS 섹터 11개와 대표 주식 및 ETF 정의
GICS_SECTORS = {
    "에너지 (Energy)": {
        "stocks": ["XOM", "CVX", "COP", "EOG", "SLB"],
        "etfs": ["XLE", "VDE", "IYE", "FENY"]
    },
    "소재 (Materials)": {
        "stocks": ["LIN", "APD", "ECL", "NEM", "FCX"],
        "etfs": ["XLB", "VAW", "IYM", "FMAT"]
    },
    "산업재 (Industrials)": {
        "stocks": ["UPS", "HON", "CAT", "GE", "BA"],
        "etfs": ["XLI", "VIS", "IYJ", "FIDU"]
    },
    "경기소비재 (Consumer Discretionary)": {
        "stocks": ["AMZN", "HD", "MCD", "NKE", "SBUX"],
        "etfs": ["XLY", "VCR", "IYC", "FDIS"]
    },
    "필수소비재 (Consumer Staples)": {
        "stocks": ["PG", "KO", "PEP", "WMT", "COST"],
        "etfs": ["XLP", "VDC", "IYK", "FSTA"]
    },
    "헬스케어 (Health Care)": {
        "stocks": ["JNJ", "UNH", "PFE", "MRK", "ABBV"],
        "etfs": ["XLV", "VHT", "IYH", "FHLC"]
    },
    "금융 (Financials)": {
        "stocks": ["JPM", "BAC", "WFC", "C", "GS"],
        "etfs": ["XLF", "VFH", "IYF", "FNCL"]
    },
    "정보기술 (Information Technology)": {
        "stocks": ["AAPL", "MSFT", "NVDA", "AVGO", "INTC"],
        "etfs": ["XLK", "VGT", "IYW", "FTEC"]
    },
    "통신서비스 (Communication Services)": {
        "stocks": ["GOOGL", "META", "NFLX", "T", "VZ"],
        "etfs": ["XLC", "VOX", "IYZ", "FCOM"]
    },
    "유틸리티 (Utilities)": {
        "stocks": ["NEE", "DUK", "SO", "D", "AEP"],
        "etfs": ["XLU", "VPU", "IDU", "FUTY"]
    },
    "부동산 (Real Estate)": {
        "stocks": ["AMT", "PLD", "CCI", "PSA", "EQIX"],
        "etfs": ["XLRE", "VNQ", "IYR", "FREL"]
    }
}

def analyze_sector_stocks(sector_data):
    """GICS 섹터별 주식 및 ETF를 분석합니다."""
    results = []
    
    for sector_name, tickers in sector_data.items():
        print(f"\n=== {sector_name} 섹터 분석 ===")
        
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
                    results.append({
                        "sector": sector_name,
                        "type": "Stock",
                        "ticker": ticker,
                        "signal": data.get("signal", "N/A"),
                        "technical_signal": data.get("technical_signal", "N/A"),
                        "price": data.get("price", 0),
                        "ma25": data.get("ma25", 0),
                        "b_value": data.get("b_value", 0),
                        "mfi": data.get("mfi", 0),
                        "deviation_percent": data.get("deviation_percent", 0),
                    })
                    print(f"✅ {ticker}: {data.get('signal', 'No Signal')}")
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
                    results.append({
                        "sector": sector_name,
                        "type": "ETF",
                        "ticker": ticker,
                        "signal": data.get("signal", "N/A"),
                        "technical_signal": data.get("technical_signal", "N/A"),
                        "price": data.get("price", 0),
                        "ma25": data.get("ma25", 0),
                        "b_value": data.get("b_value", 0),
                        "mfi": data.get("mfi", 0),
                        "deviation_percent": data.get("deviation_percent", 0),
                    })
                    print(f"✅ {ticker}: {data.get('signal', 'No Signal')}")
                else:
                    print(f"❌ {ticker}: 분석 실패")
            except Exception as e:
                print(f"❌ {ticker} 분석 중 오류: {str(e)}")
    
    return results

def save_results(results):
    """분석 결과를 CSV 파일로 저장합니다."""
    if not results:
        print("저장할 결과가 없습니다.")
        return
    
    # 결과를 DataFrame으로 변환
    df = pd.DataFrame(results)
    
    # 현재 날짜를 포함한 파일명 생성
    today = datetime.now().strftime("%Y%m%d")
    filename = f"gics_sector_analysis_{today}.csv"
    
    # 결과 저장
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n분석 결과가 {filename}에 저장되었습니다.")
    
    # 매수/매도 신호 분석
    buy_signals = df[df['signal'].str.contains('Buy', na=False)]
    sell_signals = df[df['signal'].str.contains('Sell', na=False)]
    
    print("\n🔔 매수 신호 종목:")
    if len(buy_signals) > 0:
        for i, row in buy_signals.iterrows():
            print(f"{row['ticker']} ({row['sector']}): {row['signal']}, B값: {row['b_value']:.2f}, MA25 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매수 신호 종목이 없습니다.")
    
    print("\n🔔 매도 신호 종목:")
    if len(sell_signals) > 0:
        for i, row in sell_signals.iterrows():
            print(f"{row['ticker']} ({row['sector']}): {row['signal']}, B값: {row['b_value']:.2f}, MA25 이격도: {row['deviation_percent']:.2f}%")
    else:
        print("매도 신호 종목이 없습니다.")
    
    # 시그널별 요약
    signal_summary = df['signal'].value_counts()
    print("\n🔔 시그널 요약:")
    for signal, count in signal_summary.items():
        print(f"{signal}: {count}개")

def main():
    """메인 함수"""
    print("GICS 11개 섹터 대표 주식 및 ETF 분석을 시작합니다...")
    
    try:
        # 섹터별 주식 및 ETF 분석
        results = analyze_sector_stocks(GICS_SECTORS)
        
        # 결과 저장
        save_results(results)
        
        print("\n분석이 완료되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 