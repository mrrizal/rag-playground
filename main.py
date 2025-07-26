import os
import argparse
from ingestion import (
    CloneService,
    PythonCodeParserService,
    ChromaDBIndexingService
)
from config import Config
from api import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk Python code from a Git repository.")
    parser.add_argument('--repo-url', type=str, help='URL of the Git repository to clone')
    parser.add_argument('--name', type=str, default='repo', help='Name of the cloned repository directory')
    parser.add_argument('--clone', action='store_true', help='Clone the repository before processing')
    parser.add_argument('--index', action='store_true', help='Index the parsed code chunks')
    parser.add_argument('--run-server', action='store_true', help='Run the FastAPI server')
    args = parser.parse_args()

    if args.clone and args.repo_url and args.name:
        clone_service = CloneService(args.repo_url, args.name)
        clone_service.clone_python_code()

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

    if args.run_server:
        import uvicorn
        uvicorn.run("api:app", reload=True, log_level="debug")
