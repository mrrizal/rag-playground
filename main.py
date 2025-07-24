import os
import argparse
from ingest import (
    CloneService,
    PythonCodeParserService,
    REPO_BASE_DIR
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk Python code from a Git repository.")
    parser.add_argument('--repo-url', type=str, help='URL of the Git repository to clone')
    parser.add_argument('--name', type=str, default='repo', help='Name of the cloned repository directory')
    parser.add_argument('--clone', action='store_true', help='Clone the repository before processing')
    parser.add_argument('--parse', action='store_true', help='Parse the Python code after cloning')
    args = parser.parse_args()

    if args.clone and args.repo_url and args.name:
        clone_service = CloneService(args.repo_url, args.name)
        clone_service.clone_python_code()

    if args.parse and args.name:
        repo_path = os.path.join(REPO_BASE_DIR, args.name)
        if os.path.exists(repo_path):
            parser_service = PythonCodeParserService(repo_path)
            chunks = parser_service.parse_code()
            for chunk in chunks:
                print(f"Chunk: {chunk['name']} ({chunk['type']})")
                print(f"Code:\n{chunk['code']}\n")
        else:
            print(f"Repository {repo_path} does not exist. Please clone it first.")
