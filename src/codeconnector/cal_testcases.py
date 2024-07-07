import json
import subprocess

def main():
    # Load the test cases from the JSON file
    try:
        with open('test_cases.json', 'r') as file:
            test_cases = json.load(file)
    except:
        return
    sum_cases = 0
    sum_funcs = len(test_cases)
    # Process each test case
    for test_case in test_cases:
        sum_cases += len(test_case["related_calls"])
    print('sum_cases:', sum_cases)
    print('sum_funcs:', sum_funcs)

if __name__ == "__main__":
    main()
