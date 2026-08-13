import json
import time

# ==========================================
# 1. MAC 연산 및 핵심 유틸리티 함수
# ==========================================

def mac_operation(pattern, filter_matrix):
    """
    2차원 패턴과 필터 간의 순수 MAC (Multiply-Accumulate) 연산을 수행합니다.
    (가중치 합으로 나누지 않는 단순 위치별 곱의 누적 합)
    """
    size = len(pattern)
    score = 0.0
    for r in range(size):
        for c in range(size):
            score += pattern[r][c] * filter_matrix[r][c]
    return score

def measure_mac_performance(pattern, filter_matrix, runs=10):
    """
    I/O를 제외하고 pure MAC 연산 함수 호출 구간만 10회 측정하여 평균 시간(ms)을 반환합니다.
    """
    start_time = time.perf_counter()
    for _ in range(runs):
        _ = mac_operation(pattern, filter_matrix)
    end_time = time.perf_counter()
    
    avg_time_ms = ((end_time - start_time) / runs) * 1000.0
    return avg_time_ms

def normalize_label(label):
    """
    라벨 표준화 (정규화)
    '+', 'cross', 'Cross' -> 'Cross'
    'x', 'X'             -> 'X'
    """
    lbl_str = str(label).strip()
    if lbl_str in ['+', 'cross', 'Cross']:
        return 'Cross'
    elif lbl_str.lower() == 'x':
        return 'X'
    return lbl_str

def evaluate_scores_mode2(score_cross, score_x, epsilon=1e-9):
    """
    모드 2용: Cross 필터와 X 필터 점수를 비교하여 표준 라벨 판정
    abs(score_cross - score_x) < epsilon 일 경우 UNDECIDED 반환
    """
    diff = score_cross - score_x
    if abs(diff) < epsilon:
        return 'UNDECIDED'
    elif score_cross > score_x:
        return 'Cross'
    else:
        return 'X'


# ==========================================
# 2. 모드 1: 사용자 입력 (3x3)
# ==========================================

def get_3x3_matrix_input(prompt_name):
    """
    3x3 행렬을 공백 구분 형태로 입력받고 float 파싱 및 행/열 개수를 검증합니다.
    오류 발생 시 안내 문구를 출력하고 재입력을 유도합니다.
    """
    print(f"{prompt_name} (3줄 입력, 공백 구분)")
    while True:
        matrix = []
        valid = True
        for _ in range(3):
            try:
                line = input().strip()
                row = list(map(float, line.split()))
                if len(row) != 3:
                    print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
                    valid = False
                    break
                matrix.append(row)
            except ValueError:
                print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
                valid = False
                break
        
        if valid and len(matrix) == 3:
            return matrix
        print("처음부터 다시 입력해주세요.\n")

def run_mode_1():
    print("\n#----------------------------------------")
    print("# [1] 필터 입력")
    print("#----------------------------------------")
    filter_a = get_3x3_matrix_input("필터 A")
    print()
    filter_b = get_3x3_matrix_input("필터 B")

    print("\n#----------------------------------------")
    print("# [2] 패턴 입력")
    print("#----------------------------------------")
    pattern = get_3x3_matrix_input("패턴")

    # MAC 점수 계산
    score_a = mac_operation(pattern, filter_a)
    score_b = mac_operation(pattern, filter_b)

    # 연산 시간 측정 (최소 10회 반복 측정 평균)
    time_a = measure_mac_performance(pattern, filter_a, runs=10)
    time_b = measure_mac_performance(pattern, filter_b, runs=10)
    avg_time = (time_a + time_b) / 2.0

    print("\n#----------------------------------------")
    print("# [3] MAC 결과")
    print("#----------------------------------------")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/10회): {avg_time:.3f} ms")

    # 판정 (A / B / 판정 불가)
    diff = score_a - score_b
    if abs(diff) < 1e-9:
        print("판정: 판정 불가 (|A-B| < 1e-9)")
    elif score_a > score_b:
        print("판정: A")
    else:
        print("판정: B")


# ==========================================
# 3. 모드 2: data.json 분석
# ==========================================

def run_mode_2(json_file_path="data.json"):
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"오류: '{json_file_path}' 파일을 찾을 수 없습니다.")
        return
    except Exception as e:
        print(f"JSON 파일 읽기 오류: {e}")
        return

    filters_data = data.get("filters", {})
    patterns_data = data.get("patterns", {})

    print("\n#----------------------------------------")
    print("# [1] 필터 로드")
    print("#----------------------------------------")
    loaded_filters = {}
    for size_key, filter_pair in filters_data.items():
        cross_f = filter_pair.get("cross")
        x_f = filter_pair.get("x")
        loaded_filters[size_key] = {
            'Cross': cross_f,
            'X': x_f
        }
        print(f"확인, {size_key:<7} 필터 로드 완료 (Cross, X)")

    print("\n#----------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#----------------------------------------")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    fail_cases = []
    
    perf_records = {}

    for pat_key, pat_info in patterns_data.items():
        total_tests += 1
        print(f"- -- {pat_key} ---")

        # 1) 스키마 키 분석 (예: size_5_1 -> size_key='size_5', N=5)
        parts = pat_key.split('_')
        if len(parts) >= 2 and parts[1].isdigit():
            n_val = int(parts[1])
            size_key = f"size_{n_val}"
        else:
            n_val = None
            size_key = "unknown"

        # 필터 존재 여부 검증
        if size_key not in loaded_filters:
            print(f"FAIL (해당 크기의 필터 '{size_key}'를 찾을 수 없음)")
            failed_tests += 1
            fail_cases.append((pat_key, f"필터 '{size_key}' 없음"))
            continue

        pattern_matrix = pat_info.get("input", [])
        expected_raw = pat_info.get("expected", "")  # expected 필드 사용
        expected_norm = normalize_label(expected_raw)

        filter_cross = loaded_filters[size_key]['Cross']
        filter_x = loaded_filters[size_key]['X']

        # 2) 행/열 차원 및 크기 검증 (오류 발생 시 해당 케이스만 FAIL 처리)
        if not pattern_matrix or not isinstance(pattern_matrix, list):
            print("FAIL (패턴 데이터 형식 오류)")
            failed_tests += 1
            fail_cases.append((pat_key, "패턴 데이터 형식 오류"))
            continue

        n_rows = len(pattern_matrix)
        is_shape_valid = True
        for row in pattern_matrix:
            if not isinstance(row, list) or len(row) != n_rows:
                is_shape_valid = False
                break

        if not is_shape_valid or (n_val is not None and n_rows != n_val):
            print("FAIL (패턴 크기 불일치 또는 정방행렬 오류)")
            failed_tests += 1
            fail_cases.append((pat_key, "패턴 크기 불일치"))
            continue

        if len(filter_cross) != n_rows or len(filter_cross[0]) != n_rows:
            print(f"FAIL (패턴({n_rows}x{n_rows})과 필터 크기 불일치)")
            failed_tests += 1
            fail_cases.append((pat_key, "패턴과 필터 크기 불일치"))
            continue

        # 3) MAC 연산 수행
        score_cross = mac_operation(pattern_matrix, filter_cross)
        score_x = mac_operation(pattern_matrix, filter_x)

        # 연산 시간 측정 (I/O 제외, 10회 평균)
        t_cross = measure_mac_performance(pattern_matrix, filter_cross, runs=10)
        t_x = measure_mac_performance(pattern_matrix, filter_x, runs=10)
        avg_t = (t_cross + t_x) / 2.0
        perf_records[n_rows] = avg_t

        # 4) 판정 및 PASS/FAIL 결과 검증
        prediction = evaluate_scores_mode2(score_cross, score_x)

        if prediction == expected_norm:
            status = "PASS"
            passed_tests += 1
        else:
            status = "FAIL"
            failed_tests += 1
            if prediction == 'UNDECIDED':
                reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL"
            else:
                reason = f"판정 불일치({prediction} != {expected_norm})"
            fail_cases.append((pat_key, reason))

        print(f"Cross 점수: {score_cross}")
        print(f"X 점수:     {score_x}")
        print(f"판정: {prediction} | expected: {expected_norm} | {status}")

    print("\n#----------------------------------------")
    print("# [3] 성능 분석 (평균/10회)")
    print("#----------------------------------------")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수'}")
    print("-" * 40)
    
    # 3x3, 5x5, 13x13, 25x25 항목 포함
    sizes_to_report = [3, 5, 13, 25]
    for sz in sizes_to_report:
        ops = sz * sz
        if sz in perf_records:
            t_str = f"{perf_records[sz]:.3f}"
        else:
            # 3x3 등 json 패턴에 없는 크기는 기본 3x3 행렬 샘플로 10회 평균 측정
            dummy_mat = [[1.0] * sz for _ in range(sz)]
            t_val = measure_mac_performance(dummy_mat, dummy_mat, runs=10)
            t_str = f"{t_val:.3f}"
            
        print(f"{f'{sz}×{sz}':<10} {t_str:<15} {ops}")

    print("\n#----------------------------------------")
    print("# [4] 결과 요약")
    print("#----------------------------------------")
    print(f"총 테스트: {total_tests}개")
    print(f"통과: {passed_tests}개")
    print(f"실패: {failed_tests}개")

    if fail_cases:
        print("\n실패 케이스:")
        for case_id, reason in fail_cases:
            print(f"- {case_id}: {reason}")


# ==========================================
# 4. 메인 엔트리 포인트
# ==========================================

def main():
    print("=== Mini NPU Simulator ===")
    print("\n[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    
    choice = input("선택: ").strip()
    
    if choice == '1':
        run_mode_1()
    elif choice == '2':
        run_mode_2("data.json")
    else:
        print("올바른 모드를 선택해 주세요. (1 또는 2)")

if __name__ == "__main__":
    main()