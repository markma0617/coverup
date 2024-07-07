import json
import subprocess

def run_command(command):
    """Run a shell command and return its output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout



def main():
    # Load the test cases from the JSON file
    try:
        with open('test_cases.json', 'r') as file:
            test_cases = json.load(file)
    except:
        return

    # Process each test case
    for test_case in test_cases:
        if "related_code_trees" in test_case:
            continue
        test_case["related_code_trees"] = []
        for path in test_case["related_calls"]:
            command = f'python /home/ubuntu/Python_test/codetree/main.py {path}'
            output = run_command(command)
            test_case["related_code_trees"].append(output)

    # Save the updated test cases back to the JSON file
    with open('test_cases.json', 'w') as file:
        json.dump(test_cases, file, indent=4)

if __name__ == "__main__":
    main()
