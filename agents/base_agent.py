from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class AgentConfig:
    name: str
    repo_name: str
    content_type: str
    commit_pattern: str
    is_active: bool = True
    max_files_per_commit: int = 3
    min_files_per_commit: int = 1

class BaseAgent(ABC):
    def __init__(self, config: AgentConfig, llm_manager, github_manager):
        self.config = config
        self.llm = llm_manager
        self.github = github_manager
        self.last_commit_time = None
        
    @abstractmethod
    async def generate_content(self) -> Dict[str, str]:
        """Generate content for commit"""
        pass
    
    @abstractmethod
    def get_commit_message(self, content: Dict[str, str]) -> str:
        """Generate commit message based on content"""
        pass
    
    async def execute_commit_cycle(self):
        """Full cycle: generate content, commit, push"""
        try:
            content = await self.generate_content()
            commit_message = self.get_commit_message(content)
            
            # Save files locally
            for filename, file_content in content.items():
                self.github.save_file(
                    repo_name=self.config.repo_name,
                    file_path=filename,
                    content=file_content
                )
            
            # Commit and push
            success = self.github.commit_and_push(
                repo_name=self.config.repo_name,
                message=commit_message
            )
            
            if success:
                self.last_commit_time = datetime.now()
                return True
            return False
            
        except Exception as e:
            print(f"Error in commit cycle for {self.config.name}: {e}")
            return False