import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    agent_id: str
    scheduled_time: datetime
    task: Optional[asyncio.Task] = None
    completed: bool = False
    success: Optional[bool] = None

class AsyncSchedulerManager:
    """Async-first scheduler that properly handles async agents"""
    
    def __init__(self, min_commits_per_day: int = 20, max_commits_per_day: int = 30):
        self.agents = {}
        self.scheduled_tasks: List[ScheduledTask] = []
        self.running = False
        self.scheduler_task = None
        self.min_commits = min_commits_per_day
        self.max_commits = max_commits_per_day
        self.min_gap_minutes = 15  # Minimum 15 minutes between commits
        self.max_gap_minutes = 120  # Maximum 2 hours between commits
        
    def register_agent(self, agent_id: str, agent_instance):
        """Register an agent with the scheduler"""
        self.agents[agent_id] = agent_instance
        logger.info(f"Registered agent: {agent_id}")
    
    def generate_daily_schedule(self) -> List[ScheduledTask]:
        """Generate a realistic daily commit schedule"""
        now = datetime.now()
        start_of_day = now.replace(hour=8, minute=0, second=0, microsecond=0)  # Start at 8 AM
        end_of_day = now.replace(hour=22, minute=0, second=0, microsecond=0)  # End at 10 PM
        
        # If we're past 8 AM, start from current time
        if now > start_of_day:
            start_of_day = now + timedelta(minutes=random.randint(5, 15))
        
        # Determine number of commits
        num_commits = random.randint(self.min_commits, self.max_commits)
        
        # Distribute agents across commits
        agent_ids = list(self.agents.keys())
        if not agent_ids:
            logger.warning("No agents registered")
            return []
        
        scheduled_tasks = []
        current_time = start_of_day
        
        # Create commit schedule with realistic patterns
        for i in range(num_commits):
            # Pick random agent
            agent_id = random.choice(agent_ids)
            
            # Add some randomization patterns:
            # - Morning burst (8-10 AM): shorter gaps
            # - Midday lull (12-2 PM): longer gaps
            # - Afternoon activity (3-6 PM): medium gaps
            # - Evening wind-down (7-10 PM): longer gaps
            
            hour = current_time.hour
            
            if 8 <= hour < 10:
                # Morning burst
                gap_minutes = random.randint(15, 45)
            elif 12 <= hour < 14:
                # Lunch break - fewer commits
                gap_minutes = random.randint(60, 120)
            elif 15 <= hour < 18:
                # Afternoon activity
                gap_minutes = random.randint(20, 60)
            else:
                # Evening
                gap_minutes = random.randint(30, 90)
            
            # Add some randomness to make it more human
            gap_minutes += random.randint(-5, 10)
            gap_minutes = max(self.min_gap_minutes, min(self.max_gap_minutes, gap_minutes))
            
            current_time = current_time + timedelta(minutes=gap_minutes)
            
            # Don't schedule past end of day
            if current_time > end_of_day:
                break
            
            scheduled_tasks.append(ScheduledTask(
                agent_id=agent_id,
                scheduled_time=current_time
            ))
        
        # Sort by time
        scheduled_tasks.sort(key=lambda x: x.scheduled_time)
        
        logger.info(f"Generated schedule with {len(scheduled_tasks)} commits")
        for task in scheduled_tasks[:5]:  # Log first 5
            logger.info(f"  {task.scheduled_time.strftime('%H:%M')} - {task.agent_id}")
        
        return scheduled_tasks
    
    async def run_scheduled_commit(self, task: ScheduledTask):
        """Execute a scheduled commit"""
        try:
            agent = self.agents.get(task.agent_id)
            if not agent:
                logger.error(f"Agent {task.agent_id} not found")
                task.success = False
                return
            
            logger.info(f"Executing scheduled commit for {task.agent_id}")
            success = await agent.execute_commit_cycle()
            
            task.success = success
            task.completed = True
            
            if success:
                logger.info(f"✓ Commit successful for {task.agent_id}")
            else:
                logger.warning(f"✗ Commit failed for {task.agent_id}")
                
        except Exception as e:
            logger.error(f"Error in scheduled commit for {task.agent_id}: {e}")
            task.success = False
            task.completed = True
    
    async def scheduler_loop(self):
        """Main scheduler loop - async version"""
        logger.info("Scheduler loop started")
        
        # Generate initial schedule
        self.scheduled_tasks = self.generate_daily_schedule()
        last_schedule_date = datetime.now().date()
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check if we need a new schedule (new day)
                if now.date() > last_schedule_date:
                    logger.info("New day detected, generating new schedule")
                    self.scheduled_tasks = self.generate_daily_schedule()
                    last_schedule_date = now.date()
                
                # Check for tasks that need to run
                for task in self.scheduled_tasks:
                    if not task.completed and task.scheduled_time <= now:
                        # Run the task
                        task.task = asyncio.create_task(self.run_scheduled_commit(task))
                
                # Clean up completed tasks older than 1 hour
                self.scheduled_tasks = [
                    t for t in self.scheduled_tasks 
                    if not t.completed or (now - t.scheduled_time).total_seconds() < 3600
                ]
                
                # Sleep for a bit before checking again
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self.scheduler_loop())
        logger.info("Async scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Wait for any running tasks to complete
        running_tasks = [t.task for t in self.scheduled_tasks if t.task and not t.task.done()]
        if running_tasks:
            logger.info(f"Waiting for {len(running_tasks)} tasks to complete...")
            await asyncio.gather(*running_tasks, return_exceptions=True)
        
        logger.info("Scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get current status of the scheduler"""
        now = datetime.now()
        
        upcoming = [t for t in self.scheduled_tasks if not t.completed and t.scheduled_time > now]
        completed = [t for t in self.scheduled_tasks if t.completed]
        successful = [t for t in completed if t.success]
        
        return {
            'running': self.running,
            'agents_registered': len(self.agents),
            'upcoming_commits': len(upcoming),
            'completed_today': len(completed),
            'successful_today': len(successful),
            'next_commit': upcoming[0].scheduled_time if upcoming else None
        }