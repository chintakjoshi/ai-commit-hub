import asyncio
import yaml
from pathlib import Path
from config.settings import settings
from managers.llm_manager import LLMManager
from managers.github_manager import GitHubManager
from managers.scheduler_manager import SchedulerManager
from agents.leetcode_agent import LeetCodeAgent
from agents.documentation_agent import DocumentationAgent
from agents.base_agent import AgentConfig

class AutoCommitterApp:
    def __init__(self):
        self.llm_manager = LLMManager()
        self.github_manager = GitHubManager()
        self.scheduler = SchedulerManager()
        self.agents = {}
    
    def load_agents_config(self, config_path: str = "config/agents_config.yaml"):
        """Load agent configurations from YAML file"""
        with open(config_path, 'r') as f:
            configs = yaml.safe_load(f)
        
        for agent_config in configs.get('agents', []):
            self._create_agent(agent_config)
    
    def _create_agent(self, config_data: dict):
        """Create agent instance based on configuration"""
        agent_config = AgentConfig(**config_data)
        
        # Create repository if it doesn't exist
        self.github_manager.create_repo(
            repo_name=agent_config.repo_name,
            description=f"Auto-generated {agent_config.content_type} repository"
        )
        
        # Instantiate the appropriate agent
        if agent_config.content_type == "leetcode":
            agent = LeetCodeAgent(
                config=agent_config,
                llm_manager=self.llm_manager,
                github_manager=self.github_manager
            )
        elif agent_config.content_type == "documentation":
            agent = DocumentationAgent(
                config=agent_config,
                llm_manager=self.llm_manager,
                github_manager=self.github_manager
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_config.content_type}")
        
        # Register with scheduler
        agent_id = f"{agent_config.name}_{agent_config.repo_name}"
        self.scheduler.register_agent(agent_id, agent)
        self.agents[agent_id] = agent
        
        # Schedule commits
        self.scheduler.schedule_daily_commits(agent_id)
        print(f"Created agent: {agent_id}")
    
    async def run_single_commit_cycle(self, agent_id: str = None):
        """Run a single commit cycle (for testing)"""
        if agent_id:
            agents_to_run = [agent_id]
        else:
            agents_to_run = list(self.agents.keys())
        
        for aid in agents_to_run:
            if aid in self.agents:
                success = await self.agents[aid].execute_commit_cycle()
                print(f"Commit cycle for {aid}: {'Success' if success else 'Failed'}")
    
    def run(self):
        """Main run loop"""
        print("Starting Auto-Committer Application...")
        print(f"Managing {len(self.agents)} agents")
        
        # Start the scheduler
        self.scheduler.start()
        
        try:
            # Keep the application running
            while True:
                # Check for user input to stop
                user_input = input("Enter 'stop' to quit: ")
                if user_input.lower() == 'stop':
                    break
                # You could add more commands here
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.scheduler.stop()

async def main():
    app = AutoCommitterApp()
    
    # Load agent configurations
    app.load_agents_config()
    
    # For testing: run a single commit cycle immediately
    # await app.run_single_commit_cycle()
    
    # Start the main application
    app.run()

if __name__ == "__main__":
    asyncio.run(main())