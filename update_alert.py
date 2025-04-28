#!/usr/bin/env python
# main.py 파일에서 알림 출력 부분만 수정하는 스크립트

import re

# main.py 파일 읽기
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 알림 전송 부분 패턴 찾기
pattern = r"""        # 알림 필요시 전송
        if signal and signal != "Hold":
            success = send_slack_message\(formatted_message, method=notify_method\)
            if success:
                print\(f"{actual_ticker} 알림 전송 성공!"\)
            else:
                print\(f"{actual_ticker} 알림 전송 실패!"\)
        else:
            print\(f"{actual_ticker}에 대한 알림 조건 없음"\)"""

# 새 코드로 대체
replacement = """        # 모든 신호 유형에 대해 콘솔에 알림 메시지 출력
        print("\\n" + "=" * 80)
        print(f"[{actual_ticker} 분석 결과 - 신호: {signal}]")
        print("=" * 80)
        print(formatted_message)
        print("-" * 80 + "\\n")
        
        # Hold가 아닌 경우만 Slack으로 전송
        if signal and signal != "Hold":
            success = send_slack_message(formatted_message, method=notify_method)
            if success:
                print(f"{actual_ticker} 알림 전송 성공! (신호: {signal})")
            else:
                print(f"{actual_ticker} 알림 전송 실패! (신호: {signal})")
        else:
            print(f"{actual_ticker}에 대한 알림 비활성화 (신호: Hold)")"""

# 알림 전송 코드 교체
updated_content = re.sub(pattern, replacement, content)

# 결과 파일 저장
with open('main_updated.py', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("main_updated.py 파일이 생성되었습니다. 수정 전/후 내용을 비교해 보세요.")
print("문제가 없으면 다음 명령을 실행하여 원래 파일을 대체하세요:")
print("cp main_updated.py main.py") 