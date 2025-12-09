from agents.base_agent import BaseAgent, AgentConfig
from typing import Dict
import random

class DocumentationAgent(BaseAgent):
    def __init__(self, config: AgentConfig, llm_manager, github_manager):
        super().__init__(config, llm_manager, github_manager)
        self.docs_topics = [
            "API Documentation", "Tutorial", "How-to Guide",
            "Technical Deep Dive", "Best Practices", "Troubleshooting Guide",
            "Architecture Overview", "Getting Started Guide"
        ]
    
    async def generate_content(self) -> Dict[str, str]:
        """Generate documentation content"""
        
        topic = random.choice(self.docs_topics)
        tech_stack = random.choice([
            "Python", "JavaScript", "React", "Docker", "Kubernetes",
            "Machine Learning", "Web Development", "Data Science"
        ])
        
        prompt = f"""Create comprehensive documentation about {topic} for {tech_stack}.
        
        Include:
        1. Clear title and introduction
        2. Detailed explanations with examples
        3. Code snippets where applicable
        4. Diagrams or pseudo-code if helpful
        5. References and further reading
        
        Format as a well-structured markdown document."""
        
        content = await self.llm.generate_text(
            prompt=prompt,
            system_prompt="You are an expert technical writer.",
            temperature=0.5
        )
        
        filename = f"docs/{topic.lower().replace(' ', '_')}_{random.randint(100, 999)}.md"
        
        return {filename: content}
    
    def get_commit_message(self, content: Dict[str, str]) -> str:
        filename = list(content.keys())[0]
        return f"Add documentation: {filename}"