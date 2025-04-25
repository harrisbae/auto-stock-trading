import requests
from src.config import config, SLACK_WEBHOOK_URL

def send_slack_message(message, method='json_body'):
    """
    Slack 웹훅을 통해 메시지를 전송합니다.
    
    Args:
        message (str): 전송할 메시지
        method (str): 전송 방식 ('json_body' 또는 'payload_param')
        
    Returns:
        bool: 전송 성공 여부
    """
    webhook_url = config.WEBHOOK_URL
    
    # 디버깅 - 현재 설정된 웹훅 URL 확인 (민감한 정보이므로 일부만 표시)
    if webhook_url:
        masked_url = webhook_url[:15] + "..." + webhook_url[-5:] if len(webhook_url) > 25 else webhook_url
        print(f"웹훅 URL: {masked_url}")
    else:
        print("Slack Webhook URL이 설정되지 않았습니다. --webhook 옵션을 사용하여 설정하세요.")
        return False
    
    print(f"Slack에 메시지 전송 시도 중... (길이: {len(message)} 자, 방식: {method})")
    
    try:
        if method == 'json_body':
            # 방법 1: JSON 문자열을 본문으로 전송
            payload = {"text": message}
            response = requests.post(webhook_url, json=payload)
        else:
            # 방법 2: JSON 문자열을 payload 매개변수로 전송
            payload = {"payload": '{"text": "' + message.replace('"', '\\"').replace('\n', '\\n') + '"}'}
            response = requests.post(webhook_url, data=payload)
        
        print(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("Slack 메시지 전송 성공!")
            return True
        else:
            print(f"Slack 메시지 전송 실패: {response.text}")
            print("올바른 webhook URL인지 확인하고, Slack 워크스페이스 설정을 확인하세요.")
            return False
    except Exception as e:
        print(f"Slack 메시지 전송 중 오류 발생: {e}")
        print("인터넷 연결을 확인하고, URL 형식이 올바른지 확인하세요.")
        return False

def send_slack_formatted_message(blocks, text=""):
    """
    Slack 웹훅을 통해 포맷된 메시지(블록 형식)를 전송합니다.
    
    Args:
        blocks (list): Slack 블록 형식의 메시지
        text (str): 대체 텍스트 (알림 등에 표시)
        
    Returns:
        bool: 전송 성공 여부
    """
    webhook_url = config.WEBHOOK_URL
    
    if not webhook_url:
        print("Slack Webhook URL이 설정되지 않았습니다. --webhook 옵션을 사용하여 설정하세요.")
        return False
    
    payload = {
        "blocks": blocks
    }
    
    if text:
        payload["text"] = text
    
    try:
        print(f"Slack에 포맷된 메시지 전송 시도 중... (블록 수: {len(blocks)})")
        response = requests.post(webhook_url, json=payload)
        print(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("Slack 포맷된 메시지 전송 성공!")
            return True
        else:
            print(f"Slack 포맷된 메시지 전송 실패: {response.text}")
            return False
    except Exception as e:
        print(f"Slack 포맷된 메시지 전송 중 오류 발생: {e}")
        return False 