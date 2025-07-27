import ast
import astor


class ASTNormalizer(ast.NodeTransformer):
    def __init__(self):
        self.var_counter = 0
        self.func_counter = 0
        self.var_names = {}
        self.func_names = {}

    def _get_var_name(self, name):
        if name not in self.var_names:
            self.var_counter += 1
            self.var_names[name] = f"var_{self.var_counter}"
        return self.var_names[name]

    def _get_func_name(self, name):
        if name not in self.func_names:
            self.func_counter += 1
            self.func_names[name] = f"func_{self.func_counter}"
        return self.func_names[name]

    def visit_FunctionDef(self, node):
        node.name = self._get_func_name(node.name)
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Load, ast.Store, ast.Del)):
            node.id = self._get_var_name(node.id)
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = "str_val"
        elif isinstance(node.value, (int, float)):
            node.value = 0
        return node


def normalize_code(code: str) -> str:
    tree = ast.parse(code)
    normalizer = ASTNormalizer()
    normalized_tree = normalizer.visit(tree)
    normalized_code = ast.unparse(normalized_tree) if hasattr(ast, "unparse") else astor.to_source(normalized_tree)
    return normalized_code.strip()
