from app.gemini_reviewer import generate_review

sample_diff = """
diff --git a/app.py b/app.py
+def divide(a, b):
+    return a / b
"""

result = generate_review(sample_diff)
print(result)