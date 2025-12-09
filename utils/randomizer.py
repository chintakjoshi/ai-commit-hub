import random
import time
from datetime import datetime, timedelta
from typing import List, Tuple
from config.settings import settings

class Randomizer:
    @staticmethod
    def get_daily_commit_count() -> int:
        """Get random number of commits for today"""
        return random.randint(
            settings.min_commits_per_day,
            settings.max_commits_per_day
        )
    
    @staticmethod
    def generate_commit_times(num_commits: int) -> List[datetime]:
        """Generate random commit times throughout the day"""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        times = []
        for _ in range(num_commits):
            # Generate random time within the day
            random_seconds = random.randint(0, 86400)
            commit_time = start_of_day + timedelta(seconds=random_seconds)
            
            # Ensure minimum gap between commits
            if times:
                while abs((commit_time - times[-1]).total_seconds()) < settings.min_time_between_commits:
                    random_seconds = random.randint(0, 86400)
                    commit_time = start_of_day + timedelta(seconds=random_seconds)
            
            times.append(commit_time)
        
        return sorted(times)
    
    @staticmethod
    def get_random_delay() -> float:
        """Get random delay between operations"""
        return random.uniform(
            settings.min_time_between_commits,
            settings.max_time_between_commits
        )