import os
import ast
import json
import textwrap
import sys
import autopep8
import re


import ast
import os

class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self, target_function):
        self.target_function = target_function
        self.called_functions = set()
        self.inside_target_function = False

    def visit_FunctionDef(self, node):
        if node.name == self.target_function:
            self.inside_target_function = True
            self.generic_visit(node)
            self.inside_target_function = False
        else:
            self.generic_visit(node)

    def visit_Call(self, node):
        if self.inside_target_function:
            if isinstance(node.func, ast.Name):
                self.called_functions.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                self.called_functions.add(node.func.attr)
        self.generic_visit(node)

def find_functions_in_file(file_path, target_function):
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=file_path)

    visitor = FunctionCallVisitor(target_function)
    visitor.visit(tree)
    return visitor.called_functions

def search_project_for_function_calls(project_path, target_function):
    function_calls = {}

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                called_functions = find_functions_in_file(file_path, target_function)
                if called_functions:
                    function_calls[file_path] = called_functions

    return function_calls

def find_function_definitions(project_path):
    function_locations = {}

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            function_locations[node.name] = file_path

    return function_locations

def find_file_sign(target_function, project_path):
    #print('target_function:', target_function)
    #print('project_path:', project_path)
    target_function_list = target_function.split('.')
    prior_file = ''
    function_prior_calls = []
    if len(target_function_list) == 1: # 说明是全局函数
        target_function = target_function_list[0]
    else:
        target_function = target_function_list[-1]
        
    
    function_calls = search_project_for_function_calls(project_path, target_function)
    function_definitions = find_function_definitions(project_path)
    
    defined_calls = set()
    for file, calls in function_calls.items():
        #print(f"Function '{target_function}' in file '{file}' calls:")
        for call in calls:
            if call in function_definitions:
                #print(f"  - Function '{call}' defined in '{function_definitions[call]}'")
                defined_calls.add(function_definitions[call])
            #else:
                #print(f"  - Function '{call}' definition not found in project")
    #print('defined_calls:', defined_calls)
    return defined_calls
'''
if __name__ == "__main__":
    # 示例用法
    target_function = 'your_function'  # 替换为你要查找的函数名
    project_path = 'your_project_path'  # 替换为你的项目路径
    main(target_function, project_path)
'''

def extract_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    imports = ""
    import_pattern = re.compile(r'^\s*(import|from)\s+')

    for line in lines:
        if import_pattern.match(line):
            imports = imports + line.strip() + '\n'

    return imports
def parse_input(input_string):
    if 'None' in input_string:
        return [], []
    print(input_string)
    tests_part, files_part = input_string.strip().split(' (files: ')
    tests = [test.strip() for test in tests_part.replace('Tests: ', '').split(',')]
    files = [file.strip() for file in files_part[:-1].split(',') if file.strip().lower() != 'none']
    return tests, files

def extract_function_code(file_path, func_name):
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=file_path)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.unparse(node)
    return None

def extract_test_functions(test_code):
    # Remove any common leading whitespace from each line in the test_code
    lines = test_code.split('\n')
    min_indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            if min_indent is None or indent < min_indent:
                min_indent = indent
    
    dedented_code = '\n'.join(line[min_indent:] if line.strip() else line for line in lines)
    
    # Parse the dedented code
    #print(dedented_code)
    tree = ast.parse(dedented_code)
    test_functions = []

    def visit_node(node):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            test_functions.append(ast.unparse(node))
        for child in ast.iter_child_nodes(node):
            visit_node(child)

    visit_node(tree)
    
    return test_functions

def update_json(test_cases, json_file_path='test_cases.json'):
    try:
        if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        else:
            data = []
    except (json.JSONDecodeError, IOError):
        data = []

    for case in test_cases:
        func_name, func_code, func_path, related_calls, test_func = case['func_name'], case['func_code'], case['func_path'], case['related_calls'], case['test_func']
        
        record = next((item for item in data if item['test_func_name'] == func_name), None)
        
        if record:
            if test_func not in record['test_cases']:
                record['test_cases'].append(test_func)
        else:
            data.append({
                "test_func_name": func_name,
                "test_code": func_code,
                "func_path": func_path,
                "related_calls": related_calls,
                "test_cases": [test_func]
            })
    
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def process_file(file_path, project_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    parts = content.split('"""!!!')[1:]  # 分离出包含测试函数的部分
    import_string = content.split('"""!!!')[0] + '\n'
    #print(import_string)
    for part in parts:
        try:
            input_string, test_code = part.split('!!!"""')
            input_string = input_string.strip()
            #test_code = import_string + test_code
            test_code = textwrap.dedent(test_code.strip())

            if input_string[:5] != 'Tests':
                continue
            
            tests, files = parse_input(input_string)
            
            if not tests or not files:
                continue
            
            test_cases = []
            func_path = ''
            for test_func in tests:
                related_calls = list(find_file_sign(test_func, project_path))
                func_code = None
                for file in files:
                    func_code = extract_function_code(file, test_func.split('.')[-1])
                    if func_code:
                        func_code = extract_imports(file) + '\n' + func_code
                        func_path = file
                        break
                
                if not func_code:
                    continue
                
                test_functions = extract_test_functions(autopep8.fix_code(test_code))
                for test_func_code in test_functions:
                    test_cases.append({
                        "func_name": test_func,
                        "func_code": func_code,
                        "func_path": func_path,
                        "related_calls": related_calls,
                        "test_func": import_string + test_func_code
                    })
            
            if test_cases:
                update_json(test_cases)
        except Exception as e:
            print(f"Error processing part: {e}")
            continue

def main(folder_path, project_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                print(file)
                process_file(os.path.join(root, file), project_path)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python json_test.py <test_file_path> <project_path>")
    else:
        folder_path = sys.argv[1]  # 替换为实际的文件夹路径
        project_path = sys.argv[2]
        main(folder_path, project_path)
