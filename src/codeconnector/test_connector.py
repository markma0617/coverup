import ast
import astor
import builtins
import os

# 获取所有内置函数和类型
builtin_names = dir(builtins)

# 常见第三方库（可以根据需要扩展这个列表）
common_libraries = [
    'pytest', 'numpy', 'pandas', 'requests', 'sys', 'os', 'json', 're'
]

# 获取内置类型的方法
builtin_types = [int, float, str, list, dict, set, tuple, bool, complex]
builtin_methods = set()
for typ in builtin_types:
    builtin_methods.update(dir(typ))

class FunctionLocator(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.function_locations = {}

    def visit_FunctionDef(self, node):
        func_name = node.name
        self.function_locations[func_name] = self.file_path
        self.generic_visit(node)

def is_file_in_folder(abs_file_path, folder_path):
    folder_path = os.path.abspath(folder_path)
    abs_file_path = os.path.abspath(abs_file_path)
    common_prefix = os.path.commonpath([folder_path, abs_file_path])
    return common_prefix == folder_path

def build_function_index(project_path, exclude_path):
    function_locations = {}

    for root, _, files in os.walk(project_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not is_file_in_folder(file_path, exclude_path) and file.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                try:
                    tree = ast.parse(source_code)
                    locator = FunctionLocator(file_path)
                    locator.visit(tree)
                    function_locations.update(locator.function_locations)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

    return function_locations

class TestCaseAnnotator(ast.NodeVisitor):
    def __init__(self, file_path, function_locations):
        self.annotations = []
        self.file_path = file_path
        self.function_locations = function_locations
        self.method_comments = {}

    def visit_ClassDef(self, node):
        if node.name.startswith('Test'):
            combined_tests = set()
            combined_files = set()
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                    self.visit_FunctionDef(method, is_class=True)
                    if method.name in self.method_comments:
                        for comment in self.method_comments[method.name]:
                            tests, files = self._parse_comment(comment)
                            combined_tests.update(tests)
                            combined_files.update(files)
            if combined_tests:
                combined_tests_str = ', '.join(combined_tests)
                combined_files_str = ', '.join(combined_files)
                comment_str = f'!!!Tests: {combined_tests_str} (files: {combined_files_str})!!!'
                comment = ast.Expr(value=ast.Constant(value=comment_str))
                self.annotations.append((node, comment))
        self.generic_visit(node)

    def _parse_comment(self, comment):
        import re
        tests = re.findall(r'!!!Tests: (.*?) \(files: ', comment)[0].split(', ')
        files = re.findall(r'\(files: (.*?)\)!!!', comment)[0].split(', ')
        return set(tests), set(files)

    # 其他函数保持不变
    def visit_FunctionDef(self, node, is_class = False):
        if self._is_top_level_function(node) or is_class:
            if node.name.startswith('test_'):
                if self._has_tests_comment(node):
                    return  # 如果函数已经有 "Tests: ..." 注释，则跳过
                self.current_calls = set()
                self.generic_visit(node)
                project_calls = [call for call in self.current_calls if self._is_project_function(call)]
                if project_calls:
                    locations = []
                    for call in project_calls:
                        found = False
                        for func_name, location in self.function_locations.items():
                            if call.split('.')[0] + '.py' == os.path.basename(location) and call.split('.')[-1] == func_name:
                                locations.append(location)
                                found = True
                                break
                        if not found:
                            for func_name, location in self.function_locations.items():
                                if call.split('.')[-1] == func_name:
                                    locations.append(location)
                                    found = True
                                    break
                        if not found:
                            locations.append('None')
                    comment_str = f'!!!Tests: {", ".join(project_calls)} (files: {", ".join(locations)})!!!'
                    if not is_class: self.annotations.append((node, ast.Expr(value=ast.Constant(value=comment_str))))
                    if node.name not in self.method_comments:
                        self.method_comments[node.name] = set()
                    self.method_comments[node.name].add(comment_str)
                else:
                    comment_str = '!!!Tests: None!!!'
                    if not is_class: self.annotations.append((node, ast.Expr(value=ast.Constant(value=comment_str))))
                    if node.name not in self.method_comments:
                        self.method_comments[node.name] = set()
                    self.method_comments[node.name].add(comment_str)
            else:
                self.generic_visit(node)

    def visit_Call(self, node):
        if not hasattr(self, 'current_calls'):
            self.current_calls = set()
        func_name = self._get_full_name(node.func)
        if func_name:
            self.current_calls.add(func_name)
        self.generic_visit(node)

    def visit_With(self, node):
        if not hasattr(self, 'current_calls'):
            self.current_calls = set()
        for item in node.items:
            context_expr = item.context_expr
            if isinstance(context_expr, ast.Call):
                func_name = self._get_full_name(context_expr.func)
                if func_name:
                    self.current_calls.add(func_name)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if not hasattr(self, 'current_calls'):
            self.current_calls = set()
        if node.type and isinstance(node.type, ast.Call):
            func_name = self._get_full_name(node.type.func)
            if func_name:
                self.current_calls.add(func_name)
        self.generic_visit(node)

    def _get_full_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_full_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_full_name(node.func)
        return None

    def _is_project_function(self, func_name):
        parts = func_name.split('.')
        if not parts:
            return False
        if parts[0] in builtin_names or parts[0] in common_libraries:
            return False
        return True

    def _is_builtin_type(self, name):
        try:
            return isinstance(eval(name), tuple(builtin_types))
        except:
            return False

    def _has_tests_comment(self, node):
        for expr in node.body:
            if isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Constant) and isinstance(expr.value.value, str):
                if expr.value.value.startswith('!!!Tests:'):
                    return True
        return False

    def _is_top_level_function(self, node):
        return isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.Module)


def annotate_test_cases(file_path, function_locations):
    with open(file_path, 'r', encoding='utf-8') as file:
        source_code = file.read()
    if '!!!Tests:' in source_code:
        return
    tree = ast.parse(source_code)

    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    annotator = TestCaseAnnotator(file_path, function_locations)
    annotator.visit(tree)

    for node, comment in annotator.annotations:
        for body in (tree.body, *[n.body for n in ast.walk(tree) if hasattr(n, 'body')]):
            if node in body:
                index = body.index(node)
                body.insert(index, comment)
                break

    annotated_code = astor.to_source(tree)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(annotated_code)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python test_connector.py <test_file_path> <project_path>")
    else:
        test_file_path = sys.argv[1]
        project_path = sys.argv[2]
        exclude_path = test_file_path
        function_locations = build_function_index(project_path, exclude_path)
        for root, _, files in os.walk(test_file_path):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    try:
                        annotate_test_cases(os.path.join(root, file), function_locations)
                    except Exception as e:
                        print(f"Error processing file {file}: {e}")
