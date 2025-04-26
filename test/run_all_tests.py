import unittest
import sys
import os
import time

# 테스트 시작 시간
start_time = time.time()

# 테스트 디렉토리 경로 설정
test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(test_dir)

# 프로젝트 루트 디렉토리를 시스템 경로에 추가
sys.path.append(project_dir)

# 테스트를 로드하기 위한 테스트 로더 생성
loader = unittest.TestLoader()

# 모든 테스트 케이스 로드
test_suite = loader.discover(test_dir, pattern="test_*.py")

# 테스트 실행기 생성
runner = unittest.TextTestRunner(verbosity=2)

# 전체 테스트 개수 계산
test_count = 0
for suite in test_suite:
    for test_case in suite:
        test_count += test_case.countTestCases()

print(f"==== 볼린저 밴드 전략 테스트 시작 ==== (총 {test_count}개 테스트 케이스)")
print(f"테스트 파일 목록:")
test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
for file in sorted(test_files):
    print(f"- {file}")
print("="*40)

# 테스트 실행
result = runner.run(test_suite)

# 테스트 종료 시간 및 실행 시간 계산
end_time = time.time()
execution_time = end_time - start_time

# 테스트 결과 출력
print("\n==== 볼린저 밴드 전략 테스트 결과 ====")
print(f"실행 시간: {execution_time:.2f}초")
print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
print(f"실패: {len(result.failures)}개")
print(f"에러: {len(result.errors)}개")
print("="*40)

# 실패 또는 에러가 있을 경우 출력
if result.failures or result.errors:
    print("\n==== 실패한 테스트 상세 정보 ====")
    
    if result.failures:
        print("\n--- 실패 테스트 ---")
        for i, (test, error) in enumerate(result.failures, 1):
            print(f"\n{i}. {test}")
            print("-" * 70)
            print(error)
    
    if result.errors:
        print("\n--- 에러 테스트 ---")
        for i, (test, error) in enumerate(result.errors, 1):
            print(f"\n{i}. {test}")
            print("-" * 70)
            print(error)

# 종료 코드 설정 (실패나 에러가 있으면 1, 그렇지 않으면 0)
sys.exit(1 if result.failures or result.errors else 0) 