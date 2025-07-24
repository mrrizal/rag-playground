import os
from git import Repo
from config import Config

class CloneService:
    def __init__(self, repo_url: str, name: str = 'repo'):
        self.repo_url = repo_url
        self.name = name

    def clone_python_code(self):
        print(f"Cloning repository from {self.repo_url} into {Config.REPO_BASE_DIR}/{self.name}")
        if not os.path.exists(Config.REPO_BASE_DIR):
            os.makedirs(Config.REPO_BASE_DIR)

        repo_dir = os.path.join(Config.REPO_BASE_DIR, self.name)

        if not os.path.exists(repo_dir):
            Repo.clone_from(self.repo_url, repo_dir)

        print(f"Repository cloned into {repo_dir}")