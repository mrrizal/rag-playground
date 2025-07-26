import textwrap

class PromptGenerator:
    def __init__(self):
        self.code_quality_prompt = (
            "- Naming consistency\n"
            "- DRY and clean code principles\n"
            "- Appropriate use of design patterns\n"
            "- Violations of SOLID principles (SRP, OCP, LSP, ISP, DIP)\n"
            "- Opportunities for simplification or refactoring"
        )
        self.base_header = "You are an expert software engineer specializing in Python. Please analyze the following code snippet and check for:"
        self.footer = "Provide your feedback in a concise manner."

    def generate_review_prompt(self, code_snippet: str) -> str:
        prompt = f"""{self.base_header}
{self.code_quality_prompt}
new code snippet:
```
{code_snippet.strip()}
```
{self.footer}"""
        return prompt

    def extract_similar_snippets(self, similar_codes: dict) -> str:
        index_document = []
        for index, distance in enumerate(similar_codes['distances'][0]):
            if distance > 0.55:
                continue
            index_document.append(index)

        similar_code = ""
        for counter, index in enumerate(index_document):
            doc = similar_codes['documents'][0][index]
            similar_code += f"- similar code snippet {counter + 1}:\n"
            if len(doc) > 500:
                doc = doc[:500] + "..."
            similar_code += f"```\n{doc.strip()}\n```\n\n"

        return similar_code.strip()

    def generate_code_duplication_check_prompt(self, code_snippet: str, similar_codes: dict) -> str:
        similar_code = self.extract_similar_snippets(similar_codes)
        if not code_snippet.strip():
            return ""

        if not similar_code:
            return self.generate_review_prompt(code_snippet)

        prompt = f"""We found similar code snippet(s) in the existing codebase.
new code snippet:
```
{code_snippet.strip()}
```

existing code snippets:

{similar_code}
Focus on the new code snippet. Please analyze duplicated logic and suggest improvements. Provide your feedback in a concise manner."""

        return prompt