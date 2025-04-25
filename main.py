import time
import schedule
import argparse
from src.stock_data import get_stock_data
from src.indicators import add_all_indicators
from src.signal import generate_trading_signal
from src.notification import send_slack_message, send_slack_formatted_message
from src.config import set_ticker, set_webhook_url, set_target_params, DEFAULT_TICKER, config

def check_trading_signal(ticker=None, notify_method='json_body'):
    """
    주식 데이터를 가져와 신호를 체크하고 필요시 알림을 보냅니다.
    
    Args:
        ticker (str, optional): 분석할 주식 종목 티커 심볼
        notify_method (str): Slack 알림 전송 방식
    """
    # 주식 종목 설정
    if ticker:
        current_ticker = set_ticker(ticker)
        print(f"분석할 주식 종목: {current_ticker}")
    
    # 주식 데이터 가져오기
    df = get_stock_data()
    if df is None:
        print("주식 데이터를 가져오는데 실패했습니다.")
        return
    
    # 지표 계산
    df = add_all_indicators(df)
    
    # 매매 신호 생성
    result = generate_trading_signal(df)
    
    # 결과 출력
    print(result["message"])
    
    # 알림을 보내야 하는 조건
    should_notify = False
    
    # 기술적 신호와 목표가 신호 확인
    if "technical_signal" in result["data"] and "target_signal" in result["data"]:
        # 기술적 신호가 Buy 또는 Sell이거나 목표가 신호가 Target_Reached인 경우 알림
        should_notify = (
            result["data"]["technical_signal"] in ["Buy", "Sell"] or  # 기술적 지표 기반 매수/매도 신호
            result["data"]["target_signal"] == "Target_Reached"  # 목표 수익률 달성
        )
    else:
        # 이전 버전 호환성을 위한 코드
        if "target_reached" in result["data"]:
            should_notify = (
                result["signal"] in ["Buy", "Sell", "Target_Reached"] or  # 매수/매도/목표수익률 신호
                result["data"]["target_reached"]  # 목표 수익률 달성
            )
        else:
            should_notify = result["signal"] in ["Buy", "Sell"]  # 매수/매도 신호만
    
    # 조건에 맞으면 Slack 알림 전송
    if should_notify:
        send_slack_message(result["message"], method=notify_method)
    else:
        print("현재 특별한 신호 없음. Slack 알림을 보내지 않습니다.")

def run_scheduler(ticker=None, notify_method='json_body'):
    """
    스케줄러를 설정하고 실행합니다.
    
    Args:
        ticker (str, optional): 분석할 주식 종목 티커 심볼
        notify_method (str): Slack 알림 전송 방식
    """
    # 주식 종목 설정 (스케줄링 전에 미리 설정)
    if ticker:
        current_ticker = set_ticker(ticker)
        print(f"분석할 주식 종목: {current_ticker}")
    
    # 메서드 전달을 위한 래퍼 함수
    def scheduled_check():
        # 설정된 파라미터를 재사용하여 호출
        check_trading_signal(notify_method=notify_method)
    
    # 평일 장 마감 후(한국 시간 기준 다음날 오전 6시) 매일 실행
    schedule.every().day.at("06:00").do(scheduled_check)
    
    print("주식 거래 신호 모니터링 시작...")
    print("매일 오전 6시에 자동으로 확인합니다.")
    if hasattr(config, 'PURCHASE_PRICE') and config.PURCHASE_PRICE is not None:
        target_price = config.PURCHASE_PRICE * (1 + config.TARGET_GAIN_PERCENT / 100)
        print(f"구매가: ${config.PURCHASE_PRICE:.2f}, 목표 수익률: {config.TARGET_GAIN_PERCENT:.2f}%")
        print(f"목표 가격: ${target_price:.2f}")
    
    print("Ctrl+C를 눌러 종료할 수 있습니다.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")

def test_slack_notification(notify_method='json_body', use_blocks=False):
    """
    Slack 알림 전송을 테스트합니다.
    
    Args:
        notify_method (str): 알림 전송 방식 ('json_body' 또는 'payload_param')
        use_blocks (bool): 블록 형식 메시지 사용 여부
    """
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if use_blocks:
        # Slack 블록 형식의 메시지
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 주식 거래 알림 테스트",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*시간:* {current_time}\n*상태:* 테스트 메시지"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "이 메시지는 Slack 웹훅 연결 테스트를 위한 것입니다."
                }
            }
        ]
        
        success = send_slack_formatted_message(blocks, text="주식 거래 알림 테스트")
    else:
        # 일반 텍스트 메시지
        test_message = f"""
[테스트 알림]
이것은 Slack 웹훅 연결을 테스트하는 메시지입니다.
시간: {current_time}
"""
        success = send_slack_message(test_message, method=notify_method)
    
    if success:
        print("테스트 메시지가 성공적으로 전송되었습니다!")
    else:
        print("테스트 메시지 전송에 실패했습니다.")
        print("1. 올바른 Webhook URL을 사용했는지 확인하세요.")
        print("2. 인터넷 연결을 확인하세요.")
        print("3. Slack 채널과 웹훅 설정을 확인하세요.")

def main():
    """
    명령줄 인자를 처리하고 적절한 기능을 실행합니다.
    """
    parser = argparse.ArgumentParser(description="자동 주식 거래 신호 모니터링 시스템")
    parser.add_argument("--now", action="store_true", help="즉시 실행")
    parser.add_argument("--schedule", action="store_true", help="스케줄러 실행")
    parser.add_argument("--ticker", type=str, default=None, 
                        help=f"분석할 주식 종목 티커 심볼 (기본값: {DEFAULT_TICKER})")
    parser.add_argument("--webhook", type=str, default=None,
                        help="Slack 웹훅 URL (필수: 알림을 받으려면 설정해야 함)")
    parser.add_argument("--test-slack", action="store_true",
                        help="Slack 알림 전송을 테스트합니다.")
    parser.add_argument("--force-notify", action="store_true",
                        help="신호와 상관없이 알림을 강제로 전송합니다.")
    parser.add_argument("--notify-method", type=str, choices=['json_body', 'payload_param'], 
                        default='json_body', help="Slack 알림 전송 방식 (기본값: json_body)")
    parser.add_argument("--use-blocks", action="store_true",
                        help="Slack 블록 형식의 메시지를 사용합니다.")
    # 구매가 및 목표 수익률 인자 추가
    parser.add_argument("--purchase-price", type=float, default=None,
                        help="주식 구매 가격")
    parser.add_argument("--target-gain", type=float, default=None,
                        help="목표 수익률 (%%)")
    # 종목/구매가/목표수익률 한번에 입력받는 인자 추가
    parser.add_argument("--stock-info", type=str, default=None,
                        help="종목/구매가/목표수익률 형식으로 입력 (예: AAPL/150.5/10)")
    
    args = parser.parse_args()
    
    # 웹훅 URL 설정
    if args.webhook:
        set_webhook_url(args.webhook)
    
    # 종목 설정 (--stock-info 인자가 있으면 그것을 우선 사용)
    ticker = None
    if args.stock_info:
        try:
            stock_info_parts = args.stock_info.split('/')
            if len(stock_info_parts) >= 3:
                ticker = stock_info_parts[0].strip()
                purchase_price = float(stock_info_parts[1].strip())
                target_gain = float(stock_info_parts[2].strip())
                
                # 종목 및 목표 파라미터 설정
                set_ticker(ticker)
                set_target_params(purchase_price, target_gain)
            else:
                print("ERROR: --stock-info 인자 형식이 잘못되었습니다. '종목/구매가/목표수익률' 형식으로 입력하세요.")
                return
        except Exception as e:
            print(f"ERROR: --stock-info 인자 처리 중 오류 발생: {e}")
            return
    else:
        # 개별 인자 처리
        ticker = args.ticker
        
        # 구매가 및 목표 수익률이 모두 제공된 경우에만 설정
        if args.purchase_price is not None and args.target_gain is not None:
            set_target_params(args.purchase_price, args.target_gain)
    
    # Slack 알림 테스트
    if args.test_slack:
        print("Slack 알림 테스트를 실행합니다...")
        test_slack_notification(args.notify_method, args.use_blocks)
        return
    
    if args.now:
        print("즉시 주식 거래 신호를 확인합니다...")
        check_trading_signal(ticker, args.notify_method)
        
        # 강제 알림 옵션이 활성화된 경우
        if args.force_notify:
            print("강제 알림 전송...")
            if args.use_blocks:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📊 {ticker or DEFAULT_TICKER} 주식 분석 완료",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*시간:* {current_time}\n*강제 알림:* 주식 분석이 완료되었습니다."
                        }
                    }
                ]
                send_slack_formatted_message(blocks, text=f"{ticker or DEFAULT_TICKER} 주식 분석 완료")
            else:
                send_slack_message(f"[강제 알림] {ticker or DEFAULT_TICKER} 주식을 분석했습니다.", method=args.notify_method)
    elif args.schedule:
        run_scheduler(ticker, args.notify_method)
    else:
        print("사용법: python main.py [--now | --schedule] [--ticker TICKER] [--webhook WEBHOOK_URL] [--test-slack] [--force-notify] [--notify-method METHOD] [--use-blocks] [--purchase-price PRICE] [--target-gain PERCENT] [--stock-info TICKER/PRICE/GAIN]")
        print("\n기본 옵션:")
        print("  --now: 즉시 실행")
        print("  --schedule: 스케줄러 실행")
        print(f"  --ticker: 분석할 주식 종목 티커 심볼 (기본값: {DEFAULT_TICKER})")
        print("  --webhook: Slack 웹훅 URL")
        print("  --test-slack: Slack 알림 전송 테스트")
        print("  --force-notify: 신호와 상관없이 알림을 강제로 전송")
        print("  --notify-method: Slack 알림 전송 방식 (json_body 또는 payload_param)")
        print("  --use-blocks: Slack 블록 형식의 메시지 사용")
        print("  --purchase-price: 주식 구매 가격")
        print("  --target-gain: 목표 수익률 (%)")
        print("  --stock-info: 종목/구매가/목표수익률 형식으로 입력 (예: AAPL/150.5/10)")
        
        print("\n사용 예제:")
        print("  1. 즉시 실행 예제:")
        print("     - 기본 종목 즉시 실행: python main.py --now")
        print("     - 특정 종목 즉시 실행: python main.py --now --ticker AAPL")
        print("     - 종목, 구매가, 목표 수익률 설정: python main.py --now --stock-info AAPL/150.5/10")
        print("     - 강제 알림과 함께 실행: python main.py --now --ticker MSFT --force-notify")
        
        print("\n  2. 스케줄러 실행 예제:")
        print("     - 기본 종목으로 스케줄러 실행: python main.py --schedule")
        print("     - 특정 종목으로 스케줄러 실행: python main.py --schedule --ticker TSLA")
        print("     - 목표 수익률 감시와 함께 스케줄러 실행: python main.py --schedule --stock-info NVDA/450.75/15")
        
        print("\n  3. 기타 유용한 예제:")
        print("     - Slack 알림 테스트: python main.py --test-slack")
        print("     - 블록 형식 Slack 알림 테스트: python main.py --test-slack --use-blocks")
        print("     - 다른 알림 방식 사용: python main.py --now --ticker AAPL --notify-method payload_param")
        print("     - Webhook URL 직접 설정: python main.py --now --webhook https://hooks.slack.com/services/XXX/YYY/ZZZ")

if __name__ == "__main__":
    main() 