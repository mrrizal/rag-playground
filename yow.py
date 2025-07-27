import ast

with open('./repo/django-exercise/product_service/views.py') as f:
    source = f.read()

try:
    ast.parse(source)
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
