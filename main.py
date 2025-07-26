import os
import argparse
from ingestion import (
    CloneService,
    PythonCodeParserService,
    ChromaDBIndexingService
)
from config import Config
from pprint import pprint
from llm.prompt import PromptGenerator


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk Python code from a Git repository.")
    parser.add_argument('--repo-url', type=str, help='URL of the Git repository to clone')
    parser.add_argument('--name', type=str, default='repo', help='Name of the cloned repository directory')
    parser.add_argument('--clone', action='store_true', help='Clone the repository before processing')
    parser.add_argument('--parse', action='store_true', help='Parse the Python code after cloning')
    parser.add_argument('--index', action='store_true', help='Index the parsed code chunks')
    parser.add_argument('--query', action='store_true', help='Query the indexed code chunks')
    args = parser.parse_args()

    if args.clone and args.repo_url and args.name:
        clone_service = CloneService(args.repo_url, args.name)
        clone_service.clone_python_code()

    if args.parse and args.name:
        repo_path = os.path.join(Config.REPO_BASE_DIR, args.name)
        if os.path.exists(repo_path):
            parser_service = PythonCodeParserService(repo_path)
            chunks = parser_service.parse_code()
            pprint(chunks)
            exit(0)
        else:
            print(f"Repository {repo_path} does not exist. Please clone it first.")

    if args.index and args.name:
        repo_path = os.path.join(Config.REPO_BASE_DIR, args.name)
        if os.path.exists(repo_path):
            parser_service = PythonCodeParserService(repo_path)
            chunks = parser_service.parse_code()
            if not chunks:
                print("No code chunks found to embed.")
                exit(0)
            indexing_service = ChromaDBIndexingService()
            indexing_service.index_chunks(chunks)
            print(f"Embedded {len(chunks)} code chunks.")
        else:
            print(f"Repository {repo_path} does not exist. Please clone and parse it first.")

    if args.query:
        indexing_service = ChromaDBIndexingService()
        prompt_generator = PromptGenerator()
        code_snippet = """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        n_variant = len(serializer.data['variants'])
        message = f"success create 1 product with {n_variant} variants"
        if n_variant <= 1:
            message = f"success create 1 product with {n_variant} variant"
        """
        # # query = """
        # # try:
        # #     created_at_gte = to_indonesia_timezone(
        # #         f'{created_at_gte}T00:00:00', datetime_format)
        # #     queryset = queryset.filter(created_at__gte=created_at_gte)
        # # except ValueError:
        # #     return Response(empty_result)
        # # """
        # # query = """
        # # @api_view(["GET", "POST"])
        # # def user_list_create(request):
        # #     if request.method == "GET":
        # #         return Response(users)

        # #     elif request.method == "POST":
        # #         name = request.data.get("name")
        # #         email = request.data.get("email")

        # #         if not name or not email:
        # #             return Response(
        # #                 {"error": "Name and email are required."},
        # #                 status=status.HTTP_400_BAD_REQUEST
        # #             )

        # #         user = {"id": len(users) + 1, "name": name, "email": email}
        # #         users.append(user)
        # #         return Response(user, status=status.HTTP_201_CREATED)
        # # """

        results = indexing_service.query_code(code_snippet, n_results=5)
        prompt = prompt_generator.generate_code_duplication_check_prompt(code_snippet, results)
        print(prompt)

        # # pprint(summary_lines)
