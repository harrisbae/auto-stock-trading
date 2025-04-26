import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Slack 관련 설정 - 환경 변수에서 로드
# 환경 변수에서 웹훅 URL 로드
raw_webhook_url = os.getenv('SLACK_WEBHOOK_URL', '')
if raw_webhook_url.startswith('ttps://'):
    SLACK_WEBHOOK_URL = 'h' + raw_webhook_url
else:
    SLACK_WEBHOOK_URL = raw_webhook_url

# % 같은 쓸데없는 문자 제거
if SLACK_WEBHOOK_URL and SLACK_WEBHOOK_URL[-1] == '%':
    SLACK_WEBHOOK_URL = SLACK_WEBHOOK_URL[:-1]

if SLACK_WEBHOOK_URL:
    print(f"설정된 Webhook URL: {SLACK_WEBHOOK_URL[:10]}...{SLACK_WEBHOOK_URL[-5:] if len(SLACK_WEBHOOK_URL) > 15 else ''}")
else:
    print("Webhook URL이 설정되지 않았습니다. 알림을 받으려면 다음 중 하나의 방법으로 설정하세요:")
    print("1. .env 파일에 SLACK_WEBHOOK_URL 환경 변수 추가")
    print("2. --webhook 옵션을 사용하여 실행 시 URL 제공")

# 설정 클래스
class Config:
    # 주식 관련 설정 (기본값)
    DEFAULT_TICKER = 'PLTR'
    TICKER = DEFAULT_TICKER  # 기본값으로 초기화, 외부에서 재설정 가능
    DATA_PERIOD = '6mo'
    DATA_INTERVAL = '1d'
    
    # 기술적 지표 설정
    MA_PERIOD = 20
    BOLLINGER_BANDS_STD = 2
    MFI_PERIOD = 14
    
    # 매매 신호 임계값
    BUY_B_THRESHOLD = 0.2
    BUY_MFI_THRESHOLD = 20
    SELL_B_THRESHOLD = 0.8
    SELL_MFI_THRESHOLD = 80  # 원래값으로 복원
    
    # Slack 웹훅 URL
    WEBHOOK_URL = SLACK_WEBHOOK_URL
    
    # 목표 수익률 관련 설정
    PURCHASE_PRICE = None  # 구매가
    TARGET_GAIN_PERCENT = None  # 목표 수익률 (%)

# 설정 객체 생성
config = Config()

# 기존 변수와의 호환성을 위한 전역 변수
DEFAULT_TICKER = config.DEFAULT_TICKER
TICKER = config.TICKER
DATA_PERIOD = config.DATA_PERIOD
DATA_INTERVAL = config.DATA_INTERVAL
MA_PERIOD = config.MA_PERIOD
BOLLINGER_BANDS_STD = config.BOLLINGER_BANDS_STD
MFI_PERIOD = config.MFI_PERIOD
BUY_B_THRESHOLD = config.BUY_B_THRESHOLD
BUY_MFI_THRESHOLD = config.BUY_MFI_THRESHOLD
SELL_B_THRESHOLD = config.SELL_B_THRESHOLD
SELL_MFI_THRESHOLD = config.SELL_MFI_THRESHOLD

# 티커 설정 함수
def set_ticker(ticker):
    """
    분석할 주식 종목 티커를 설정합니다.
    
    Args:
        ticker (str): 주식 티커 심볼 (예: 'AAPL', 'MSFT', 'PLTR' 등)
    """
    config.TICKER = ticker
    
    # 전역 변수도 업데이트
    global TICKER
    TICKER = ticker
    
    print(f"티커가 {ticker}로 설정되었습니다.")
    return ticker

# 구매가 및 목표 수익률 설정 함수
def set_target_params(purchase_price, target_gain_percent):
    """
    구매가 및 목표 수익률을 설정합니다.
    
    Args:
        purchase_price (float, None): 주식 구매 가격, None인 경우 초기화
        target_gain_percent (float, None): 목표 수익률 (%), None인 경우 초기화
    """
    if purchase_price is None:
        config.PURCHASE_PRICE = None
    else:
        config.PURCHASE_PRICE = float(purchase_price)
        
    if target_gain_percent is None:
        config.TARGET_GAIN_PERCENT = None
    else:
        config.TARGET_GAIN_PERCENT = float(target_gain_percent)
    
    if config.PURCHASE_PRICE is not None and config.TARGET_GAIN_PERCENT is not None:
        print(f"구매가: ${config.PURCHASE_PRICE:.2f}, 목표 수익률: {config.TARGET_GAIN_PERCENT:.2f}%")
        
        # 목표 가격 계산
        target_price = config.PURCHASE_PRICE * (1 + config.TARGET_GAIN_PERCENT / 100)
        print(f"목표 가격: ${target_price:.2f}")
    else:
        print("목표 매매 파라미터가 초기화되었습니다.")
    
    return config.PURCHASE_PRICE, config.TARGET_GAIN_PERCENT

# 웹훅 URL 설정 함수
def set_webhook_url(url):
    """
    Slack 웹훅 URL을 설정합니다.
    
    Args:
        url (str): Slack 웹훅 URL
    """
    # URL 형식 수정
    if url.startswith('ttps://'):
        url = 'h' + url
    
    # % 같은 쓸데없는 문자 제거
    if url and url[-1] == '%':
        url = url[:-1]
    
    config.WEBHOOK_URL = url
    
    # 전역 변수도 업데이트
    global SLACK_WEBHOOK_URL
    SLACK_WEBHOOK_URL = url
    
    print(f"Slack 웹훅 URL이 설정되었습니다.")
    return url 