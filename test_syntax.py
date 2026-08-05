import py_compile
import os

file_path = r"D:\desktop\virtualenv.worktrees\asma_backend-1\accounts\models.py"
try:
    py_compile.compile(file_path, doraise=True)
    print("models.py: Syntax is valid")
except Exception as e:
    print(f"models.py: Syntax error - {e}")