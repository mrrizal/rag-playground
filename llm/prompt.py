class PromptGenerator:
    def __init__(self):
        self.code_quality_prompt = """
        - Naming consistency
        - DRY and clean code principles
        - Appropriate use of design patterns
        - Violations of SOLID principles (SRP, OCP, LSP, ISP, DIP)
        - Opportunities for simplification or refactoring
        """

        self.base_header = "You are an expert software engineer specializing in Python. Please analyze the following code snippet and check for:"
        self.footer = "Provide your feedback in a concise manner."

    def generate_review_prompt(self, code_snippet: str) -> str:
        """
        Generates a prompt for code review based on coding style."""

        prompt = f"""
        {self.base_header.strip()}
        {self.code_quality_prompt.strip()}

        new code snippet:
        ```
        {code_snippet.strip()}
        ```

        {self.footer.strip()}
        """
        return prompt.strip()

    def extract_similar_snippets(self, similar_codes: dict) -> str:
        index_document = []
        for index, distance in enumerate(similar_codes['distances'][0]):
            if distance > 0.55:
                continue
            index_document.append(index)

        similar_code = ""
        for counter, index in enumerate(index_document):
            doc = similar_codes['documents'][0][index]
            similar_code += "\n\n- similar code snippet {}:\n".format(counter + 1)
            similar_code += f"```\n{doc.strip()}\n```"

        similar_code = similar_code.strip()
        if not similar_code:
            return ""
        return similar_code

    def generate_contextual_prompt(self, code_snippet: str, similar_codes: dict) -> str:
        """
        Generates a prompt that includes context from similar code snippets.
        """
        similary_code = self.extract_similar_snippets(similar_codes)
        if not similary_code:
            return self.generate_review_prompt(code_snippet)

        prompt = self.generate_review_prompt(code_snippet)
        prompt += " Also we found similar code snippett with existing codebase, here the similar codes:\n\n"
        prompt += similary_code
        prompt += "\n\nFocus on new code snippet, please analyze the duplicated code between the new code snippet and exisiting code snippets. Provide your feedback in a concise manner.\n\n"
        return prompt.strip()