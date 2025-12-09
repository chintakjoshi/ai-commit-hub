import asyncio
import yaml
import sys
import schedule
import threading
import time
from pathlib import Path
from datetime import datetime
from config.settings import settings
from managers.llm_manager import LLMManager
from managers.github_manager import GitHubManager
from managers.scheduler_manager import SchedulerManager
from agents.leetcode_agent import LeetCodeAgent
from agents.documentation_agent import DocumentationAgent
from agents.base_agent import AgentConfig
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoCommitterApp:
    def __init__(self):
        self.llm_manager = None
        self.github_manager = GitHubManager()
        self.scheduler = SchedulerManager()
        self.agents = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the app asynchronously"""
        if not self.is_initialized:
            logger.info(f"Initializing LLM Manager with provider: {settings.llm_provider}")
            self.llm_manager = LLMManager()
            await self.llm_manager._ensure_session()
            self.is_initialized = True
            logger.info(f"LLM Manager initialized with model: {settings.current_model}")
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.llm_manager:
            await self.llm_manager.close()
            logger.info("LLM Manager cleaned up")
        self.is_initialized = False
        
    def load_agents_config(self, config_path: str = "config/agents_config.yaml"):
        """Load agent configurations from YAML file"""
        try:
            with open(config_path, 'r') as f:
                configs = yaml.safe_load(f)
            
            for agent_config in configs.get('agents', []):
                self._create_agent(agent_config)
            
            logger.info(f"Loaded {len(configs.get('agents', []))} agent configurations")
            
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using default config")
            self._create_default_agents()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            self._create_default_agents()
    
    def _create_default_agents(self):
        """Create default agents if config file is not found"""
        default_agents = [
            {
                "name": "leetcode_agent_1",
                "repo_name": "leetcode-solutions-ai",
                "content_type": "leetcode",
                "commit_pattern": "problem_and_solution",
                "is_active": True,
                "max_files_per_commit": 4,
                "min_files_per_commit": 2
            },
            {
                "name": "docs_agent_1",
                "repo_name": "technical-docs-ai",
                "content_type": "documentation",
                "commit_pattern": "docs_only",
                "is_active": True,
                "max_files_per_commit": 2,
                "min_files_per_commit": 1
            }
        ]
        
        for agent_config in default_agents:
            self._create_agent(agent_config)
    
    def _create_agent(self, config_data: dict):
        """Create agent instance based on configuration"""
        try:
            agent_config = AgentConfig(**config_data)
            
            if not agent_config.is_active:
                logger.info(f"Skipping inactive agent: {agent_config.name}")
                return
            
            # Create repository if it doesn't exist
            repo_created = self.github_manager.create_repo(
                repo_name=agent_config.repo_name,
                description=f"Auto-generated {agent_config.content_type} repository"
            )
            
            if repo_created:
                logger.info(f"Created/verified repository: {agent_config.repo_name}")
            
            # Instantiate the appropriate agent (llm_manager will be set later)
            if agent_config.content_type == "leetcode":
                agent = LeetCodeAgent(
                    config=agent_config,
                    llm_manager=None,  # Will be set later
                    github_manager=self.github_manager
                )
            elif agent_config.content_type == "documentation":
                agent = DocumentationAgent(
                    config=agent_config,
                    llm_manager=None,  # Will be set later
                    github_manager=self.github_manager
                )
            else:
                logger.error(f"Unknown agent type: {agent_config.content_type}")
                return
            
            # Store agent without llm_manager for now
            agent_id = f"{agent_config.name}_{agent_config.repo_name}"
            self.agents[agent_id] = {
                'agent': agent,
                'config': agent_config
            }
            
            logger.info(f"Created agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Error creating agent {config_data.get('name', 'unknown')}: {e}")
    
    def _initialize_agents(self):
        """Initialize agents with LLM Manager"""
        if not self.llm_manager:
            logger.error("Cannot initialize agents: LLM Manager not initialized")
            return
            
        for agent_id, agent_data in self.agents.items():
            agent = agent_data['agent']
            config = agent_data['config']
            
            # Update agent with LLM Manager
            agent.llm = self.llm_manager
            
            # Register with scheduler
            self.scheduler.register_agent(agent_id, agent)
            
            # Schedule commits
            self.scheduler.schedule_daily_commits(agent_id)
            logger.info(f"Scheduled commits for agent: {agent_id}")
    
    async def test_llm_connection(self):
        """Test LLM connection with a simple prompt"""
        if not self.llm_manager:
            logger.error("LLM Manager not initialized for connection test")
            return False
            
        logger.info(f"Testing {settings.llm_provider} connection...")
        
        test_prompt = "Hello! Please respond with 'Connection successful' and nothing else."
        
        try:
            response = await self.llm_manager.generate_text(test_prompt)
            logger.info(f"LLM test response: {response}")
            return "Connection successful" in response or "connection successful" in response.lower()
        except Exception as e:
            logger.error(f"LLM connection test failed: {e}")
            return False
    
    def test_github_connection(self):
        """Test GitHub connection"""
        logger.info("Testing GitHub connection...")
        try:
            repos = self.github_manager.get_repo_list()
            logger.info(f"GitHub connection successful. Found {len(repos)} repositories.")
            return True
        except Exception as e:
            logger.error(f"GitHub connection test failed: {e}")
            return False
    
    async def run_single_commit_cycle(self, agent_id: str = None):
        """Run a single commit cycle (for testing)"""
        if agent_id:
            agents_to_run = [agent_id]
        else:
            agents_to_run = list(self.agents.keys())
        
        results = {}
        
        for aid in agents_to_run:
            if aid in self.agents:
                logger.info(f"Running commit cycle for {aid}...")
                try:
                    success = await self.agents[aid]['agent'].execute_commit_cycle()
                    results[aid] = "Success" if success else "Failed"
                    logger.info(f"Commit cycle for {aid}: {results[aid]}")
                except Exception as e:
                    logger.error(f"Error in commit cycle for {aid}: {e}")
                    results[aid] = f"Error: {e}"
        
        return results
    
    def run_scheduled(self):
        """Run with scheduler (main mode)"""
        logger.info("=" * 60)
        logger.info("Starting Auto-Committer Application")
        logger.info(f"LLM Provider: {settings.llm_provider}")
        logger.info(f"Model: {settings.current_model}")
        logger.info(f"Managing {len(self.agents)} agents")
        logger.info("=" * 60)
        
        # Start the scheduler
        self.scheduler.start()
        
        try:
            # Keep the application running
            while True:
                # Display status
                print("\n" + "=" * 40)
                print("Auto-Committer - Running")
                print("=" * 40)
                print(f"Active agents: {len(self.agents)}")
                print(f"Next scheduled tasks: {len(schedule.get_jobs())}")
                print("\nCommands:")
                print("  'status' - Show detailed status")
                print("  'test <agent>' - Test specific agent")
                print("  'run now' - Run all agents now")
                print("  'stop' - Stop the application")
                print("  'exit' or Ctrl+C - Exit")
                print("=" * 40)
                
                user_input = input("\nEnter command: ").strip().lower()
                
                if user_input == 'stop' or user_input == 'exit':
                    break
                elif user_input == 'status':
                    self.show_status()
                elif user_input.startswith('test '):
                    agent_name = user_input[5:].strip()
                    asyncio.run(self.run_single_commit_cycle(agent_name))
                elif user_input == 'run now':
                    asyncio.run(self.run_single_commit_cycle())
                elif user_input == '':
                    continue
                else:
                    print(f"Unknown command: {user_input}")
                    
        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
        finally:
            self.scheduler.stop()
            logger.info("Application stopped")
    
    def show_status(self):
        """Show detailed status of all agents"""
        print("\n" + "=" * 60)
        print("AGENT STATUS")
        print("=" * 60)
        
        for agent_id, agent_data in self.agents.items():
            agent = agent_data['agent']
            last_commit = agent.last_commit_time
            last_str = last_commit.strftime("%Y-%m-%d %H:%M") if last_commit else "Never"
            print(f"\n{agent_id}:")
            print(f"  Type: {agent.config.content_type}")
            print(f"  Repository: {agent.config.repo_name}")
            print(f"  Last commit: {last_str}")
            print(f"  Active: {agent.config.is_active}")
        
        print("\n" + "=" * 60)
        print(f"Total agents: {len(self.agents)}")
        print("=" * 60)
    
    async def setup_wizard(self):
        """Interactive setup wizard"""
        logger.info("Starting in interactive mode...")
        
        print("\n" + "=" * 60)
        print("AUTO-COMMITTER SETUP WIZARD")
        print("=" * 60)
        
        # Initialize LLM Manager
        await self.initialize()
        
        # Initialize agents with LLM Manager
        self._initialize_agents()
        
        # Test connections
        print("\n1. Testing connections...")
        
        # Test LLM
        print("   Testing LLM connection...")
        llm_ok = await self.test_llm_connection()
        print(f"   LLM Connection: {'✓' if llm_ok else '✗'}")
        
        # Test GitHub
        print("   Testing GitHub connection...")
        github_ok = self.test_github_connection()
        print(f"   GitHub Connection: {'✓' if github_ok else '✗'}")
        
        if not (llm_ok and github_ok):
            print("\n⚠️  Some connections failed. Check your configuration.")
            choice = input("Continue anyway? (y/n): ")
            if choice.lower() != 'y':
                await self.cleanup()
                return
        
        # Create test commit
        print("\n2. Running test commit...")
        choice = input("Run a test commit now? (y/n): ")
        if choice.lower() == 'y':
            print("   Running test commit...")
            results = await self.run_single_commit_cycle()
            for agent, result in results.items():
                print(f"   {agent}: {result}")
        
        # Choose mode
        print("\n3. Select mode:")
        print("   1) Scheduled mode (run continuously with random commits)")
        print("   2) Manual mode (run commits manually)")
        print("   3) Exit")
        
        mode = input("\nSelect (1-3): ").strip()
        
        if mode == '1':
            # Run scheduled mode
            print("\nStarting scheduled mode...")
            await self.cleanup()  # Cleanup for now, will reinitialize in run_scheduled
            self.run_scheduled()
        elif mode == '2':
            print("\nManual mode selected.")
            print("Run 'python main.py --manual' to start manual mode.")
            await self.cleanup()
        else:
            print("Exiting.")
            await self.cleanup()
    
    async def manual_mode(self):
        """Manual control mode"""
        await self.initialize()
        self._initialize_agents()
        
        print("\n" + "=" * 60)
        print("MANUAL CONTROL MODE")
        print("=" * 60)
        print(f"Active agents: {len(self.agents)}")
        
        while True:
            print("\nCommands:")
            print("  'list' - List all agents")
            print("  'run <agent>' - Run specific agent")
            print("  'run all' - Run all agents")
            print("  'status' - Show agent status")
            print("  'exit' - Exit")
            
            cmd = input("\nEnter command: ").strip().lower()
            
            if cmd == 'exit':
                break
            elif cmd == 'list':
                print("\nAvailable agents:")
                for agent_id in self.agents.keys():
                    print(f"  {agent_id}")
            elif cmd == 'status':
                self.show_status()
            elif cmd.startswith('run '):
                target = cmd[4:].strip()
                if target == 'all':
                    print("Running all agents...")
                    results = await self.run_single_commit_cycle()
                    for agent, result in results.items():
                        print(f"  {agent}: {result}")
                else:
                    print(f"Running agent: {target}")
                    if target in self.agents:
                        results = await self.run_single_commit_cycle(target)
                        for agent, result in results.items():
                            print(f"  {agent}: {result}")
                    else:
                        print(f"  Error: Agent '{target}' not found")
            else:
                print("Unknown command")
        
        await self.cleanup()

async def run_tests():
    """Run connection tests"""
    print("=" * 60)
    print("AUTO-COMMITTER CONNECTION TEST")
    print("=" * 60)
    
    app = AutoCommitterApp()
    app.load_agents_config()
    
    # Test GitHub
    print("\nTesting GitHub connection...")
    github_ok = app.test_github_connection()
    
    # Test LLM
    print("\nTesting LLM connection...")
    await app.initialize()
    llm_ok = await app.test_llm_connection()
    
    print(f"\nResults:")
    print(f"  LLM Connection: {'✓ PASS' if llm_ok else '✗ FAIL'}")
    print(f"  GitHub Connection: {'✓ PASS' if github_ok else '✗ FAIL'}")
    
    await app.cleanup()

async def run_manual_mode():
    """Run manual mode"""
    app = AutoCommitterApp()
    app.load_agents_config()
    await app.manual_mode()

async def run_setup_wizard():
    """Run setup wizard"""
    app = AutoCommitterApp()
    app.load_agents_config()
    await app.setup_wizard()

def main():
    """Main entry point"""
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # Test mode
            asyncio.run(run_tests())
            
        elif sys.argv[1] == "--manual":
            # Manual mode
            asyncio.run(run_manual_mode())
            
        elif sys.argv[1] == "--setup":
            # Interactive setup
            asyncio.run(run_setup_wizard())
            
        elif sys.argv[1] == "--run":
            # Run in scheduled mode directly
            app = AutoCommitterApp()
            app.load_agents_config()
            app.run_scheduled()
            
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("\nAvailable arguments:")
            print("  --setup   : Interactive setup wizard")
            print("  --test    : Test connections only")
            print("  --manual  : Manual control mode")
            print("  --run     : Run in scheduled mode")
    else:
        # Default: interactive setup
        asyncio.run(run_setup_wizard())

if __name__ == "__main__":
    main()