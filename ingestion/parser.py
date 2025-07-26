import os
import ast
import textwrap
from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field


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
    def __init__(self, repo_path: str):
        super().__init__(repo_path)
        # Track imports and class hierarchy across the file
        self.current_imports = {}
        self.current_from_imports = {}
        self.class_hierarchy = {}
        self.current_function_calls = set()
        self.current_attributes = set()
        self.current_exceptions = set()

    def extract_chunk_metadata(self, node, chunk_code, class_name=None, class_docstring=None, filepath=None) -> Dict:
        filename = filepath.split(os.sep)[-1] if filepath else None

        # Basic metadata (keeping your original structure)
        metadata = {
            "type": type(node).__name__,
            "name": getattr(node, "name", None),
            "code": chunk_code.strip(),
            "start_line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
            "docstring": ast.get_docstring(node),
            "class_name": class_name,
            "class_docstring": class_docstring,
            "method_name": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_function": isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)),
            "is_static": any(isinstance(d, ast.Name) and d.id == 'staticmethod' for d in getattr(node, "decorator_list", [])),
            "is_classmethod": any(isinstance(d, ast.Name) and d.id == 'classmethod' for d in getattr(node, "decorator_list", [])),
            "is_property": any(isinstance(d, ast.Name) and d.id == 'property' for d in getattr(node, "decorator_list", [])),
            "filepath": filepath if filepath else None,
            "filename": filename if filename else None
        }

        # Enhanced metadata for functions and methods
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metadata.update(self._extract_function_enhancements(node, class_name))

        # Enhanced metadata for classes
        elif isinstance(node, ast.ClassDef):
            metadata.update(self._extract_class_enhancements(node))

        return metadata

    def _extract_function_enhancements(self, node: ast.FunctionDef, class_name: Optional[str] = None) -> Dict[str, Any]:
        """Extract enhanced information for function/method nodes"""
        # Reset tracking for this function
        self.current_function_calls = set()
        self.current_attributes = set()
        self.current_exceptions = set()

        # Visit the function body to collect calls, attributes, etc.
        for stmt in node.body:
            self._visit_for_analysis(stmt)

        # Parse decorators
        decorators = self._parse_decorators(node.decorator_list)

        # Parse parameters
        parameters = self._parse_parameters(node.args)

        # Parse return annotation
        return_annotation = None
        if node.returns:
            return_annotation = self._get_annotation(node.returns)

        # Check if method overrides parent
        overrides_method = self._check_method_override(node.name, class_name)

        # Calculate complexity
        complexity_score = self._calculate_complexity(node)

        # Get imports used by this function
        imports_used = self._get_used_imports()

        return {
            "decorators": decorators,
            "parameters": parameters,
            "return_annotation": return_annotation,
            "calls_functions": list(self.current_function_calls),
            "accesses_attributes": list(self.current_attributes),
            "imports_used": list(imports_used),
            "raises_exceptions": list(self.current_exceptions),
            "overrides_method": overrides_method,
            "complexity_score": complexity_score,
        }

    def _extract_class_enhancements(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Extract enhanced information for class nodes"""
        # Get base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attribute_name(base))

        # Store class hierarchy
        self.class_hierarchy[node.name] = base_classes

        # Get class methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        return {
            "base_classes": base_classes,
            "methods": methods,
            "is_abstract": any("ABC" in base or "abstract" in base.lower() for base in base_classes)
        }

    def _visit_for_analysis(self, node):
        """Visit AST nodes to collect function calls, attributes, and exceptions"""
        if isinstance(node, ast.Call):
            func_name = self._get_call_name(node.func)
            if func_name:
                self.current_function_calls.add(func_name)

        elif isinstance(node, ast.Attribute):
            attr_name = self._get_attribute_name(node)
            if attr_name:
                self.current_attributes.add(attr_name)

        elif isinstance(node, ast.Raise):
            if node.exc:
                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                    self.current_exceptions.add(node.exc.func.id)
                elif isinstance(node.exc, ast.Name):
                    self.current_exceptions.add(node.exc.id)

        # Recursively visit child nodes
        for child in ast.iter_child_nodes(node):
            self._visit_for_analysis(child)

    def _parse_decorators(self, decorator_list: List[ast.expr]) -> List[str]:
        """Parse decorator information"""
        decorators = []
        for decorator in decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(self._get_attribute_name(decorator))
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(f"{decorator.func.id}()")
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(f"{self._get_attribute_name(decorator.func)}()")
        return decorators

    def _parse_parameters(self, args: ast.arguments) -> List[Dict[str, Any]]:
        """Parse function parameters"""
        parameters = []

        # Regular arguments
        for i, arg in enumerate(args.args):
            param_info = {
                'name': arg.arg,
                'type': self._get_annotation(arg.annotation) if arg.annotation else None,
                'default': None,
                'kind': 'positional'
            }

            # Check for default values
            default_offset = len(args.args) - len(args.defaults)
            if i >= default_offset:
                default_idx = i - default_offset
                param_info['default'] = self._get_default_value(args.defaults[default_idx])

            parameters.append(param_info)

        # *args
        if args.vararg:
            parameters.append({
                'name': f"*{args.vararg.arg}",
                'type': self._get_annotation(args.vararg.annotation) if args.vararg.annotation else None,
                'default': None,
                'kind': 'var_positional'
            })

        # **kwargs
        if args.kwarg:
            parameters.append({
                'name': f"**{args.kwarg.arg}",
                'type': self._get_annotation(args.kwarg.annotation) if args.kwarg.annotation else None,
                'default': None,
                'kind': 'var_keyword'
            })

        return parameters

    def _get_annotation(self, annotation: ast.expr) -> str:
        """Get string representation of type annotation"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return self._get_attribute_name(annotation)
        elif isinstance(annotation, ast.Subscript):
            value = self._get_annotation(annotation.value)
            slice_val = self._get_annotation(annotation.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        return ast.unparse(annotation) if hasattr(ast, 'unparse') else str(annotation)

    def _get_default_value(self, default: ast.expr) -> str:
        """Get string representation of default parameter value"""
        if isinstance(default, ast.Constant):
            return repr(default.value)
        elif isinstance(default, ast.Name):
            return default.id
        elif isinstance(default, ast.Attribute):
            return self._get_attribute_name(default)
        return ast.unparse(default) if hasattr(ast, 'unparse') else str(default)

    def _get_call_name(self, func: ast.expr) -> Optional[str]:
        """Get the name of a function call"""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return self._get_attribute_name(func)
        return None

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full name of an attribute access"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        elif isinstance(node.value, ast.Call):
            call_name = self._get_call_name(node.value.func)
            return f"{call_name}().{node.attr}" if call_name else f"<call>.{node.attr}"
        return f"<expr>.{node.attr}"

    def _check_method_override(self, method_name: str, class_name: Optional[str]) -> bool:
        """Check if a method overrides a parent method"""
        if not class_name or class_name not in self.class_hierarchy:
            return False

        base_classes = self.class_hierarchy[class_name]
        if not base_classes:
            return False

        # Check if method contains super() call (simple heuristic)
        return any('super()' in call for call in self.current_function_calls)

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _get_used_imports(self) -> Set[str]:
        """Get imports that are actually used by the current function"""
        used_imports = set()
        all_imports = {**self.current_imports, **self.current_from_imports}

        for call in self.current_function_calls:
            for imported_name, full_name in all_imports.items():
                if call.startswith(imported_name):
                    used_imports.add(full_name)

        for attr in self.current_attributes:
            for imported_name, full_name in all_imports.items():
                if attr.startswith(imported_name):
                    used_imports.add(full_name)

        return used_imports

    def _extract_imports(self, tree: ast.AST):
        """Extract import information from the AST"""
        self.current_imports = {}
        self.current_from_imports = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    self.current_imports[asname] = name

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    full_name = f"{module}.{name}" if module else name
                    self.current_from_imports[asname] = full_name

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

    def extract_methods_from_class(self, code: str, class_node: ast.ClassDef, filepath: str) -> List[Dict]:
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

                chunk = self.extract_chunk_metadata(
                    item,
                    method_code,
                    class_name=class_name,
                    class_docstring=class_docstring,
                    filepath=filepath
                )
                chunks.append(chunk)

        return chunks

    def chunk_python_code(self, code: str, max_chunk_size: int = 1000, filepath: str = None) -> List[Dict]:
        """
        Chunk Python code based on AST nodes (functions, classes, etc.)
        """
        tree = ast.parse(code)
        chunks = []

        # Extract imports first
        self._extract_imports(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # Get the source code for this node
                start_line = node.lineno
                end_line = node.end_lineno

                # Extract the actual code
                lines = code.split('\n')
                chunk_code = '\n'.join(lines[start_line-1:end_line])

                if isinstance(node, ast.ClassDef) and node.name == "Migration":
                    continue  # Skip Migration class

                if node.name in [
                    "__init__",
                    "__str__",
                    "__repr__",
                    "__call__"
                ]:
                    continue

                chunk = self.extract_chunk_metadata(node, chunk_code, filepath=filepath)
                chunks.append(chunk)

                if isinstance(node, ast.ClassDef):
                    # Extract methods from the class
                    class_chunks = self.extract_methods_from_class(
                        chunk_code,
                        node,
                        filepath=filepath
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
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    code = file.read()
                    file_chunks = self.chunk_python_code(code, filepath=file_path)
                    chunks.extend(file_chunks)
            except (UnicodeDecodeError, SyntaxError) as e:
                print(f"Warning: Could not parse {file_path}: {e}")
                continue
        return chunks
