import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """Manages state to avoid duplicate content and track history"""
    
    def __init__(self, state_file: str = "data/state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.state = {
            'generated_titles': {},  # {agent_id: [titles]}
            'used_combinations': {},  # {agent_id: [category+difficulty combos]}
            'commit_history': [],  # Recent commits
            'daily_stats': {},  # {date: {agent: count}}
            'last_updated': None
        }
        
        self.load_state()
    
    def load_state(self):
        """Load state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    loaded_state = json.load(f)
                    self.state.update(loaded_state)
                logger.info(f"Loaded state from {self.state_file}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
        else:
            logger.info("No existing state file, starting fresh")
    
    def save_state(self):
        """Save state to file"""
        try:
            self.state['last_updated'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def content_hash(self, content: str) -> str:
        """Generate hash of content"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_title_used(self, agent_id: str, title: str, days_threshold: int = 30) -> bool:
        """Check if a title was recently used"""
        if agent_id not in self.state['generated_titles']:
            return False
        
        # Clean old entries
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        recent_titles = [
            entry for entry in self.state['generated_titles'][agent_id]
            if entry['date'] > cutoff_date
        ]
        
        self.state['generated_titles'][agent_id] = recent_titles
        
        # Check if title exists
        title_lower = title.lower().strip()
        for entry in recent_titles:
            if entry['title'].lower().strip() == title_lower:
                return True
        
        return False
    
    def record_generated_title(self, agent_id: str, title: str, metadata: Dict = None):
        """Record a generated title"""
        if agent_id not in self.state['generated_titles']:
            self.state['generated_titles'][agent_id] = []
        
        self.state['generated_titles'][agent_id].append({
            'title': title,
            'date': datetime.now().isoformat(),
            'metadata': metadata or {}
        })
        
        # Keep only last 100 entries per agent
        self.state['generated_titles'][agent_id] = \
            self.state['generated_titles'][agent_id][-100:]
        
        self.save_state()
    
    def is_combination_used(self, agent_id: str, combination: str, days_threshold: int = 7) -> bool:
        """Check if a combination (e.g., category+difficulty) was recently used"""
        if agent_id not in self.state['used_combinations']:
            return False
        
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        recent_combos = [
            entry for entry in self.state['used_combinations'][agent_id]
            if entry['date'] > cutoff_date
        ]
        
        self.state['used_combinations'][agent_id] = recent_combos
        
        combo_lower = combination.lower().strip()
        for entry in recent_combos:
            if entry['combination'].lower().strip() == combo_lower:
                return True
        
        return False
    
    def record_combination(self, agent_id: str, combination: str):
        """Record a used combination"""
        if agent_id not in self.state['used_combinations']:
            self.state['used_combinations'][agent_id] = []
        
        self.state['used_combinations'][agent_id].append({
            'combination': combination,
            'date': datetime.now().isoformat()
        })
        
        # Keep only last 50 per agent
        self.state['used_combinations'][agent_id] = \
            self.state['used_combinations'][agent_id][-50:]
        
        self.save_state()
    
    def record_commit(self, agent_id: str, repo_name: str, commit_message: str, 
                     success: bool, files_count: int = 0):
        """Record a commit"""
        commit_record = {
            'agent_id': agent_id,
            'repo_name': repo_name,
            'message': commit_message,
            'success': success,
            'files_count': files_count,
            'timestamp': datetime.now().isoformat()
        }
        
        self.state['commit_history'].append(commit_record)
        
        # Keep only last 200 commits
        self.state['commit_history'] = self.state['commit_history'][-200:]
        
        # Update daily stats
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.state['daily_stats']:
            self.state['daily_stats'][today] = {}
        
        if agent_id not in self.state['daily_stats'][today]:
            self.state['daily_stats'][today][agent_id] = 0
        
        if success:
            self.state['daily_stats'][today][agent_id] += 1
        
        # Clean old daily stats (keep last 7 days)
        cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        self.state['daily_stats'] = {
            date: stats for date, stats in self.state['daily_stats'].items()
            if date >= cutoff
        }
        
        self.save_state()
    
    def get_agent_commit_count_today(self, agent_id: str) -> int:
        """Get commit count for agent today"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.state['daily_stats'].get(today, {}).get(agent_id, 0)
    
    def get_total_commits_today(self) -> int:
        """Get total commits today"""
        today = datetime.now().strftime('%Y-%m-%d')
        return sum(self.state['daily_stats'].get(today, {}).values())
    
    def get_recent_commits(self, limit: int = 10) -> List[Dict]:
        """Get recent commits"""
        return self.state['commit_history'][-limit:]
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total_commits = len(self.state['commit_history'])
        successful = sum(1 for c in self.state['commit_history'] if c['success'])
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_commits = self.get_total_commits_today()
        
        return {
            'total_commits_all_time': total_commits,
            'successful_commits': successful,
            'success_rate': f"{(successful/total_commits*100):.1f}%" if total_commits > 0 else "0%",
            'commits_today': today_commits,
            'agents_tracked': len(self.state['generated_titles']),
            'last_updated': self.state.get('last_updated', 'Never')
        }
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up data older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Clean titles
        for agent_id in self.state['generated_titles']:
            self.state['generated_titles'][agent_id] = [
                entry for entry in self.state['generated_titles'][agent_id]
                if entry['date'] > cutoff_date
            ]
        
        # Clean combinations
        for agent_id in self.state['used_combinations']:
            self.state['used_combinations'][agent_id] = [
                entry for entry in self.state['used_combinations'][agent_id]
                if entry['date'] > cutoff_date
            ]
        
        # Clean commit history
        self.state['commit_history'] = [
            commit for commit in self.state['commit_history']
            if commit['timestamp'] > cutoff_date
        ]
        
        self.save_state()
        logger.info(f"Cleaned up data older than {days} days")