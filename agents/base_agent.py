from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

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
            if self.llm is None:
                logger.error(f"LLM Manager not initialized for agent {self.config.name}")
                return False
                
            logger.info(f"Starting commit cycle for {self.config.name}")
            content = await self.generate_content()
            
            if not content:
                logger.warning(f"No content generated for {self.config.name}")
                return False
                
            commit_message = self.get_commit_message(content)
            logger.info(f"Generated commit message: {commit_message}")
            
            # Save files locally
            for filename, file_content in content.items():
                self.github.save_file(
                    repo_name=self.config.repo_name,
                    file_path=filename,
                    content=file_content
                )
                logger.debug(f"Saved file: {filename}")
            
            # Commit and push
            success = self.github.commit_and_push(
                repo_name=self.config.repo_name,
                message=commit_message
            )
            
            if success:
                self.last_commit_time = datetime.now()
                logger.info(f"Commit successful for {self.config.name}")
                return True
            else:
                logger.warning(f"Commit failed for {self.config.name}")
                return False
            
        except Exception as e:
            logger.error(f"Error in commit cycle for {self.config.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False