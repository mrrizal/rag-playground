import os
import ast
import textwrap
from abc import ABC, abstractmethod
from typing import List, Dict


class CodeParserService(ABC):
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    @abstractmethod
    def parse_code(self):
        """
        Abstract method to parse code.
        Should be implemented by subclasses.
        """
        pass


class PythonCodeParserService(CodeParserService):
    def extract_node_code(self, node, original_code: str) -> str:
        """Extract source code for a specific AST node with proper indentation"""
        lines = original_code.split('\n')
        start_line = node.lineno - 1
        end_line = node.end_lineno

        # Extract the lines
        node_lines = lines[start_line:end_line]

        # Remove common leading whitespace (dedent)
        dedented_code = textwrap.dedent('\n'.join(node_lines))

        return dedented_code

    def extract_methods_from_class(self, code: str, class_node: ast.ClassDef) -> List[Dict]:
        """
        Parse class code and extract each method as a separate chunk
        """
        chunks = []
        class_name = class_node.name
        class_docstring = ast.get_docstring(class_node)

        # Extract each method from the class
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_code = self.extract_node_code(item, code)

                if method_code.strip() == "":
                    continue

                chunks.append({
                    'type': 'method',
                    'name': item.name,
                    'class_name': class_name,
                    'method_name': item.name,
                    'code': method_code,
                    'docstring': ast.get_docstring(item),
                    'class_docstring': class_docstring,
                    'is_static': any(isinstance(d, ast.Name) and d.id == 'staticmethod'
                                for d in item.decorator_list),
                    'is_classmethod': any(isinstance(d, ast.Name) and d.id == 'classmethod'
                                        for d in item.decorator_list),
                    'is_property': any(isinstance(d, ast.Name) and d.id == 'property'
                                    for d in item.decorator_list),
                    'start_line': item.lineno,
                    'end_line': item.end_lineno
                })

        return chunks

    def chunk_python_code(self, code: str, max_chunk_size: int = 1000) -> List[Dict]:
        """
        Chunk Python code based on AST nodes (functions, classes, etc.)
        """
        tree = ast.parse(code)
        chunks = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # Get the source code for this node
                start_line = node.lineno
                end_line = node.end_lineno

                # Extract the actual code
                lines = code.split('\n')
                chunk_code = '\n'.join(lines[start_line-1:end_line])

                chunks.append({
                    'type': type(node).__name__,
                    'name': node.name,
                    'code': chunk_code,
                    'start_line': start_line,
                    'end_line': end_line,
                    'docstring': ast.get_docstring(node)
                })

                if isinstance(node, ast.ClassDef):
                    # Extract methods from the class
                    class_chunks = self.extract_methods_from_class(
                        chunk_code,
                        node
                    )
                    chunks.extend(class_chunks)

        return chunks

    def get_python_files(self, repo_path):
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    yield os.path.join(root, file)

    def parse_code(self):
        """
        Parse Python code in the repository and return chunks.
        """
        chunks = []
        for file_path in self.get_python_files(self.repo_path):
            with open(file_path, 'r') as file:
                code = file.read()
                file_chunks = self.chunk_python_code(code)
                chunks.extend(file_chunks)
        return chunks
