#!/bin/bash

# GICS 섹터 종목 분석 실행 스크립트

# 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# 환경 설정
cd "$PROJECT_ROOT"
if [ -d ".venv" ]; then
    echo "가상환경 활성화"
    source .venv/bin/activate
fi

# 실행 파일 확인
if [ ! -f "scripts/gics_sector_stocks.py" ]; then
    echo "오류: scripts/gics_sector_stocks.py 파일을 찾을 수 없습니다."
    exit 1
fi

# Slack Webhook 설정 확인
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "환경변수 SLACK_WEBHOOK_URL이 설정되지 않았습니다. 알림은 생략됩니다."
fi

echo "GICS 섹터 대표 종목 분석을 시작합니다..."
python scripts/gics_sector_stocks.py

echo "분석이 완료되었습니다." 