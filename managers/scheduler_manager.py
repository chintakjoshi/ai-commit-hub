import asyncio
import schedule
import time
from datetime import datetime
from typing import Dict, List
from utils.randomizer import Randomizer
import threading

class SchedulerManager:
    def __init__(self):
        self.agents = {}
        self.scheduled_tasks = {}
        self.running = False
    
    def register_agent(self, agent_id: str, agent_instance):
        """Register an agent with the scheduler"""
        self.agents[agent_id] = agent_instance
    
    def schedule_daily_commits(self, agent_id: str):
        """Schedule daily commits for an agent"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not registered")
        
        # Clear existing schedule for this agent
        if agent_id in self.scheduled_tasks:
            for task in self.scheduled_tasks[agent_id]:
                schedule.cancel_job(task)
        
        # Generate random commit times for today
        num_commits = Randomizer.get_daily_commit_count()
        commit_times = Randomizer.generate_commit_times(num_commits)
        
        now = datetime.now()
        scheduled_jobs = []
        
        for commit_time in commit_times:
            if commit_time > now:  # Only schedule future commits
                time_str = commit_time.strftime("%H:%M")
                
                job = schedule.every().day.at(time_str).do(
                    self._run_agent_commit, agent_id
                ).tag(agent_id)
                
                scheduled_jobs.append(job)
                print(f"Scheduled commit for {agent_id} at {time_str}")
        
        self.scheduled_tasks[agent_id] = scheduled_jobs
    
    def _run_agent_commit(self, agent_id: str):
        """Run agent commit cycle (to be called by scheduler)"""
        agent = self.agents[agent_id]
        asyncio.run(agent.execute_commit_cycle())
    
    def start(self):
        """Start the scheduler in a separate thread"""
        self.running = True
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        print("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()