#!/bin/bash
# 다양한 ETF 및 채권 종목에 대한 주식 거래 신호 모니터링 스크립트
# 각 종목마다 구매가와 목표 수익률(10%)을 설정하여 즉시 분석을 실행합니다.
# 사용법: ./main.sh

# S&P 500 ETF 분석
python main.py --now --stock-info SPY/508.62/10

# 배당주 ETF 분석
python main.py --now --stock-info SCHD/25.0587/10

# Realty Income Corporation (부동산 투자 신탁) 분석
python main.py --now --stock-info O/56.69/10

# JPMorgan Nasdaq Equity Premium Income ETF 분석
python main.py --now --stock-info JEPQ/49.051/10

# SPDR Bloomberg 1-3 Month T-Bill ETF (단기 국채) 분석
python main.py --now --stock-info BIL/91.5077/10

# iShares 0-3 Month Treasury Bond ETF (초단기 국채) 분석
python main.py --now --stock-info SGOV/100.58/10

# iShares 20+ Year Treasury Bond ETF (장기 국채) 분석
python main.py --now --stock-info TLT/87.2767/10

# TLT Warrants (TLT 옵션) 분석 
python main.py --now --stock-info TLTW/23.1991/10