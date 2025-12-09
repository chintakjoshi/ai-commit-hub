from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        self.state_manager = None  # Will be set by app
        self.last_commit_time = None
        self.retry_count = 0
        self.max_retries = 3
        
    @abstractmethod
    async def generate_content(self) -> Dict[str, str]:
        """Generate content for commit"""
        pass
    
    @abstractmethod
    def get_commit_message(self, content: Dict[str, str]) -> str:
        """Generate commit message based on content"""
        pass
    
    def validate_content(self, content: Dict[str, str]) -> bool:
        """Validate generated content before committing"""
        if not content:
            logger.warning(f"Empty content generated for {self.config.name}")
            return False
        
        # Check if files are within limits
        num_files = len(content)
        if num_files < self.config.min_files_per_commit:
            logger.warning(f"Too few files generated: {num_files} < {self.config.min_files_per_commit}")
            return False
        
        if num_files > self.config.max_files_per_commit:
            logger.warning(f"Too many files generated: {num_files} > {self.config.max_files_per_commit}")
            return False
        
        # Check if content is not empty
        for filename, file_content in content.items():
            if not file_content or len(file_content.strip()) < 50:
                logger.warning(f"File {filename} has insufficient content")
                return False
        
        return True
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def generate_content_with_retry(self) -> Dict[str, str]:
        """Generate content with retry logic"""
        logger.debug(f"Generating content for {self.config.name} (attempt {self.retry_count + 1})")
        content = await self.generate_content()
        
        if not self.validate_content(content):
            raise ValueError("Content validation failed")
        
        return content
    
    async def execute_commit_cycle(self):
        """Full cycle: generate content, commit, push"""
        start_time = datetime.now()
        
        try:
            if self.llm is None:
                logger.error(f"LLM Manager not initialized for agent {self.config.name}")
                return False
            
            logger.info(f"Starting commit cycle for {self.config.name}")
            
            # Generate content with retry
            try:
                content = await self.generate_content_with_retry()
            except Exception as e:
                logger.error(f"Failed to generate valid content after retries: {e}")
                return False
            
            if not content:
                logger.warning(f"No content generated for {self.config.name}")
                return False
            
            # Generate commit message
            commit_message = self.get_commit_message(content)
            logger.info(f"Generated commit message: {commit_message}")
            
            # Check for duplicate content if state manager is available
            if self.state_manager:
                # Extract title from content for deduplication
                title = self._extract_title_from_content(content)
                if title and self.state_manager.is_title_used(self.config.name, title):
                    logger.warning(f"Title '{title}' was recently used, regenerating...")
                    # Could retry here, but for now just continue
            
            # Save files locally
            saved_files = []
            for filename, file_content in content.items():
                try:
                    self.github.save_file(
                        repo_name=self.config.repo_name,
                        file_path=filename,
                        content=file_content
                    )
                    saved_files.append(filename)
                    logger.debug(f"Saved file: {filename}")
                except Exception as e:
                    logger.error(f"Failed to save file {filename}: {e}")
                    # Clean up saved files
                    self._cleanup_failed_commit(saved_files)
                    return False
            
            # Commit and push
            try:
                success = self.github.commit_and_push(
                    repo_name=self.config.repo_name,
                    message=commit_message
                )
            except Exception as e:
                logger.error(f"Failed to commit/push: {e}")
                success = False
            
            # Record in state
            if self.state_manager:
                self.state_manager.record_commit(
                    agent_id=f"{self.config.name}_{self.config.repo_name}",
                    repo_name=self.config.repo_name,
                    commit_message=commit_message,
                    success=success,
                    files_count=len(content)
                )
                
                # Record title if successful
                if success:
                    title = self._extract_title_from_content(content)
                    if title:
                        self.state_manager.record_generated_title(
                            agent_id=self.config.name,
                            title=title,
                            metadata={'type': self.config.content_type}
                        )
            
            if success:
                self.last_commit_time = datetime.now()
                duration = (self.last_commit_time - start_time).total_seconds()
                logger.info(f"✓ Commit successful for {self.config.name} ({duration:.1f}s)")
                self.retry_count = 0  # Reset retry count on success
                return True
            else:
                logger.warning(f"✗ Commit failed for {self.config.name}")
                self.retry_count += 1
                return False
            
        except Exception as e:
            logger.error(f"Error in commit cycle for {self.config.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.retry_count += 1
            return False
    
    def _extract_title_from_content(self, content: Dict[str, str]) -> Optional[str]:
        """Extract title from content for deduplication"""
        # Try to extract from JSON files first
        for filename, file_content in content.items():
            if filename.endswith('.json'):
                try:
                    data = json.loads(file_content)
                    if 'title' in data:
                        return data['title']
                except:
                    pass
        
        # Try to extract from markdown files
        for filename, file_content in content.items():
            if filename.endswith('.md'):
                lines = file_content.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        return line[2:].strip()
        
        return None
    
    def _cleanup_failed_commit(self, saved_files: list):
        """Clean up files from a failed commit"""
        logger.info(f"Cleaning up {len(saved_files)} files from failed commit")
        for filename in saved_files:
            try:
                # Implementation depends on your file system structure
                # Could delete files or revert changes
                pass
            except Exception as e:
                logger.error(f"Error cleaning up file {filename}: {e}")
    
    def get_agent_id(self) -> str:
        """Get unique agent identifier"""
        return f"{self.config.name}_{self.config.repo_name}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent"""
        return {
            'name': self.config.name,
            'repo': self.config.repo_name,
            'type': self.config.content_type,
            'active': self.config.is_active,
            'last_commit': self.last_commit_time.isoformat() if self.last_commit_time else None,
            'retry_count': self.retry_count
        }