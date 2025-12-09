import os
from github import Github, GithubException
import git
from typing import Optional, List
from pathlib import Path
from config.settings import settings
import shutil

class GitHubManager:
    def __init__(self):
        self.token = settings.github_token
        self.username = settings.github_username
        self.base_path = Path(settings.repo_base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize GitHub API
        self.gh = Github(self.token)
        self.user = self.gh.get_user()
    
    def create_repo(self, repo_name: str, description: str = "", private: bool = False) -> bool:
        """Create a new GitHub repository"""
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=description,
                private=private,
                auto_init=False
            )
            
            # Clone locally
            local_path = self.base_path / repo_name
            if local_path.exists():
                shutil.rmtree(local_path)
            
            repo_url = f"https://{self.token}:x-oauth-basic@github.com/{self.username}/{repo_name}.git"
            git.Repo.clone_from(repo_url, local_path)
            
            return True
            
        except GithubException as e:
            if e.status == 422:  # Repository already exists
                print(f"Repository {repo_name} already exists")
                return True
            print(f"Error creating repo: {e}")
            return False
    
    def save_file(self, repo_name: str, file_path: str, content: str):
        """Save file to local repository"""
        repo_path = self.base_path / repo_name
        file_full_path = repo_path / file_path
        
        # Create directories if they don't exist
        file_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def commit_and_push(self, repo_name: str, message: str) -> bool:
        """Commit and push changes to GitHub"""
        try:
            repo_path = self.base_path / repo_name
            if not repo_path.exists():
                print(f"Repository {repo_name} not found locally")
                return False
            
            repo = git.Repo(repo_path)
            
            # Add all changes
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                print(f"No changes to commit in {repo_name}")
                return False
            
            # Commit
            repo.git.commit('-m', message)
            
            # Push
            origin = repo.remote(name='origin')
            origin.push()
            
            print(f"Successfully committed and pushed to {repo_name}")
            return True
            
        except Exception as e:
            print(f"Error in commit/push: {e}")
            return False
    
    def get_repo_list(self) -> List[str]:
        """Get list of repositories"""
        return [repo.name for repo in self.user.get_repos()]