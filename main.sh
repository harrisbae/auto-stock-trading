#!/bin/bash
# 다양한 ETF 및 채권 종목에 대한 주식 거래 신호 모니터링 스크립트
# 각 종목마다 구매가와 목표 수익률(10%)을 설정하여 즉시 분석을 실행합니다.
# 사용법: ./main.sh

# 추가 옵션 설정
# --tranche: 분할 매수 단계 설정 (기본값: 3단계)
# --stop-loss: 손절 비율 설정 (기본값: 7%)
# --band-riding: 밴드타기 감지 옵션 (밴드 상단에 연속 접촉 시 알림)
# --risk-management: 위험 관리 수준 설정 (low, medium, high)

TRANCHE="--tranche=3"
STOP_LOSS="--stop-loss=7"
BAND_RIDING="--band-riding=true" 
RISK_MANAGEMENT="--risk-management=medium"

# S&P 500 ETF 분석
python main.py --now --stock-info SPY/508.62/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# 배당주 ETF 분석
python main.py --now --stock-info SCHD/25.0587/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# Realty Income Corporation (부동산 투자 신탁) 분석
python main.py --now --stock-info O/56.69/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# JPMorgan Nasdaq Equity Premium Income ETF 분석
python main.py --now --stock-info JEPQ/49.051/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# SPDR Bloomberg 1-3 Month T-Bill ETF (단기 국채) 분석
python main.py --now --stock-info BIL/91.5077/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# iShares 0-3 Month Treasury Bond ETF (초단기 국채) 분석
python main.py --now --stock-info SGOV/100.58/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# iShares 20+ Year Treasury Bond ETF (장기 국채) 분석
python main.py --now --stock-info TLT/87.2767/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT

# TLT Warrants (TLT 옵션) 분석 
python main.py --now --stock-info TLTW/23.1991/10 $TRANCHE $STOP_LOSS $BAND_RIDING $RISK_MANAGEMENT