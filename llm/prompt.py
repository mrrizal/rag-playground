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

    def generate_coding_style_prompt(self, code_snippet: str) -> str:
        prompt = f"""##### Instruction:
{self.base_header}
{self.code_quality_prompt}

##### Code Snippet:
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
            similar_code += f"[Code {counter + 1}]\n"
            if len(doc) > 1000:
                doc = doc[:1000] + "..."
            similar_code += f"```\n{doc.strip()}\n```\n\n"

        return similar_code.strip()

    def generate_code_duplication_check_prompt(self, code_snippet: str, similar_codes: dict) -> str:
        if not code_snippet.strip():
            return ""

        similar_code = self.extract_similar_snippets(similar_codes)
        if not similar_code:
            return ""

        prompt = f"""You are a code reviewer AI specialized in Python. Your task is to identify if the `target_code` has duplicated or similar logic with any of the `reference_code_list`.

##### Target Code:
```python
{code_snippet.strip()}
```

##### Reference Code List:
{similar_code}

##### Task:
Analyze the target code and check for duplication or similar logic from the reference code list.
- Point out any overlap or copy-paste behavior.
- Suggest refactoring if needed.
- Keep your response short, concise, and in bullet points.
"""
        return prompt

    def generate_summary_prompt(self, coding_style_result, duplication_check_result) -> str:
        prompt = f"""
You are a senior software engineer reviewing the following two LLM-generated code review results:

1. **Duplication Report**: Reviews code for repeated or redundant logic.
2. **Style Report**: Reviews naming, formatting, structure, and clean code principles.

Your task is to:
- Merge both results into a single, cohesive summary.
- Avoid repeating identical or overly verbose points.
- Highlight the most critical issues and recommend improvements.
- Use clear, concise language in markdown format.
- give a final summary of the overall code quality.

Here are the two results:

### Duplication Result:
{duplication_check_result}

### Style Result:
{coding_style_result}
"""
        return prompt.strip()
