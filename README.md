# AI Auto-Committer Hub

An intelligent, modular system that automatically generates and commits code, documentation, and other content to GitHub repositories using LLM APIs. Designed to create realistic, varied commit patterns while avoiding detection.

## Key Features

- **Multi-Agent Architecture**: Multiple agents working on different repos simultaneously
- **Intelligent Scheduling**: Realistic commit patterns that mimic human behavior
- **State Management**: Tracks generated content to avoid duplicates
- **Async-First Design**: Efficient concurrent operations
- **Multiple LLM Providers**: OpenRouter, NVIDIA NIM, Google Gemini
- **Robust Error Handling**: Automatic retries and graceful degradation
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Major Improvements in This Version

### 1. **Async Scheduler** (`AsyncSchedulerManager`)
- Replaced sync `schedule` library with native async implementation
- Realistic commit timing patterns (morning bursts, lunch lulls, evening slowdowns)
- Proper async/await integration throughout

### 2. **State Manager** (`StateManager`)
- Tracks generated titles to avoid duplicates
- Maintains commit history and statistics
- Records daily stats per agent
- Automatic cleanup of old data

### 3. **Enhanced Base Agent**
- Retry logic with exponential backoff
- Content validation before committing
- State integration for deduplication
- Better error handling and cleanup

### 4. **Improved Main Application**
- Proper async initialization and cleanup
- Signal handlers for graceful shutdown
- Better status reporting
- Fixed LLM manager lifecycle issues

## Project Structure

```
ai-commit-hub/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── agents_config.yaml
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Enhanced with state management
│   ├── leetcode_agent.py
│   └── documentation_agent.py
├── managers/
│   ├── __init__.py
│   ├── github_manager.py
│   ├── llm_manager.py
│   ├── scheduler_manager.py   # NEW: Async scheduler
│   ├── state_manager.py       # NEW: State tracking
│   └── file_manager.py
├── utils/
│   ├── __init__.py
│   ├── randomizer.py
│   ├── logger.py
│   └── security.py
├── data/
│   ├── templates/
│   ├── cache/
│   └── state.json             # NEW: Persistent state
├── repos/                      # Local repository storage
├── requirements.txt
├── .env.example
├── .env
├── main.py                     # Enhanced main application
├── auto_committer.log          # NEW: Log file
└── README.md
```

## 🛠️ Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-commit-hub

# Run setup script
bash setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username

# LLM Configuration
OPENROUTER_API_KEY=your_openrouter_key
GOOGLE_API_KEY=your_google_api_key
LLM_PROVIDER=openrouter  # or: nim, google

# App Configuration
MAX_COMMITS_PER_DAY=30
MIN_COMMITS_PER_DAY=20
LOG_LEVEL=INFO

# Rate Limiting
REQUESTS_PER_MINUTE=10
MAX_RETRIES=3
```

**Getting API Keys:**
- **GitHub Token**: Settings → Developer settings → Personal access tokens → Generate new token (needs `repo` scope)
- **OpenRouter**: Sign up at [openrouter.ai](https://openrouter.ai) and get API key
- **Google AI**: Get key from [makersuite.google.com](https://makersuite.google.com)

### 3. Configure Agents

Edit `config/agents_config.yaml` to define your agents:

```yaml
agents:
  - name: "leetcode_solver_1"
    repo_name: "leetcode-solutions-ai"
    content_type: "leetcode"
    commit_pattern: "problem_and_solution"
    is_active: true
    max_files_per_commit: 4
    min_files_per_commit: 2
  
  - name: "docs_writer_1"
    repo_name: "technical-docs-ai"
    content_type: "documentation"
    commit_pattern: "docs_only"
    is_active: true
    max_files_per_commit: 2
    min_files_per_commit: 1
```

## 🎮 Usage

### Interactive Setup Wizard (Recommended for first time)

```bash
python main.py --setup
```

This will:
1. Test your LLM and GitHub connections
2. Optionally run a test commit
3. Let you choose between scheduled or manual mode

### Run Modes

#### 1. Scheduled Mode (Production)

Runs continuously with realistic commit patterns:

```bash
python main.py --run
```

The scheduler will:
- Generate a daily schedule with 20-30 commits
- Distribute commits realistically throughout the day
- Create morning bursts, lunch lulls, and evening slowdowns
- Automatically regenerate schedule each day

#### 2. Manual Mode (Testing/Development)

Interactive control:

```bash
python main.py --manual
```

Commands:
- `list` - Show all agents
- `run all` - Execute all agents once
- `run <agent_name>` - Execute specific agent
- `status` - Show detailed status
- `stats` - Show statistics
- `exit` - Exit program

#### 3. Test Mode

Test connections without committing:

```bash
python main.py --test
```

### Running as a Service (Linux)

Create `/etc/systemd/system/auto-committer.service`:

```ini
[Unit]
Description=AI Auto-Committer Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/ai-commit-hub
Environment="PATH=/path/to/ai-commit-hub/venv/bin"
ExecStart=/path/to/ai-commit-hub/venv/bin/python main.py --run
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable auto-committer
sudo systemctl start auto-committer
sudo systemctl status auto-committer
```

## Monitoring

### View Logs

```bash
# Real-time logs
tail -f auto_committer.log

# Last 100 lines
tail -n 100 auto_committer.log

# Search for errors
grep ERROR auto_committer.log
```

### Check Status

While running in scheduled mode, you can check status by sending SIGUSR1:

```bash
# In a separate terminal
pkill -USR1 -f "python main.py --run"
```

### State File

The `data/state.json` file contains:
- Generated titles history
- Used combinations
- Commit history
- Daily statistics

## Advanced Configuration

### Adding New Agent Types

1. Create a new agent class in `agents/`:

```python
from agents.base_agent import BaseAgent, AgentConfig
from typing import Dict

class MyCustomAgent(BaseAgent):
    async def generate_content(self) -> Dict[str, str]:
        # Your content generation logic
        pass
    
    def get_commit_message(self, content: Dict[str, str]) -> str:
        # Your commit message logic
        pass
```

2. Register in `main.py`:

```python
elif agent_config.content_type == "my_custom_type":
    agent = MyCustomAgent(
        config=agent_config,
        llm_manager=None,
        github_manager=self.github_manager
    )
```

3. Add to `agents_config.yaml`:

```yaml
- name: "my_custom_agent"
  repo_name: "my-custom-repo"
  content_type: "my_custom_type"
  commit_pattern: "custom_pattern"
  is_active: true
```

### Customizing Commit Patterns

Edit `AsyncSchedulerManager.generate_daily_schedule()` to adjust timing patterns:

```python
if 8 <= hour < 10:
    gap_minutes = random.randint(15, 45)  # Your custom timing
```

### Changing LLM Providers

In `.env`:

```bash
LLM_PROVIDER=google  # Options: openrouter, nim, google
GOOGLE_MODEL=gemini-2.0-flash-exp
```

## Troubleshooting

### Common Issues

**1. "LLM Manager not initialized"**
- Ensure your API key is correct in `.env`
- Check that the provider is supported
- Try running `--test` mode to diagnose

**2. "GitHub authentication failed"**
- Verify your token has `repo` scope
- Check token hasn't expired
- Ensure username is correct

**3. "No changes to commit"**
- Check that repos exist and are initialized
- Verify file paths are correct
- Look for errors in content generation

**4. Commits seem unnatural**
- Adjust timing in `AsyncSchedulerManager`
- Increase randomization in commit messages
- Vary content generation prompts

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG python main.py --run
```

## Important Notes

### Rate Limiting

- Default: 10 requests/minute
- Adjust in `.env`: `REQUESTS_PER_MINUTE=10`
- Too many requests may get your API key throttled

### Content Quality

The quality of generated content depends on:
- Your LLM provider and model
- Prompt engineering in agents
- Temperature and other LLM settings

### GitHub Usage

- Creates public repos by default
- Each agent needs its own repo
- Repos are created automatically if they don't exist

### Avoiding Detection

This system uses:
- Randomized commit timing
- Realistic daily patterns
- Varied commit messages
- Multiple agents/repos

However, be aware that:
- GitHub may still detect automated patterns
- Use responsibly and within GitHub's TOS
- Consider making repos private

## Best Practices

1. **Start Small**: Test with 1-2 agents first
2. **Monitor Logs**: Check for errors regularly
3. **Adjust Timing**: Fine-tune patterns based on your needs
4. **Backup State**: Keep `data/state.json` backed up
5. **API Keys**: Never commit `.env` file
6. **Resource Usage**: Monitor your API quotas

## Future Enhancements

- [ ] Web dashboard for monitoring
- [ ] More agent types (blog posts, code reviews, etc.)
- [ ] Machine learning for more natural patterns
- [ ] Multi-language support for code generation
- [ ] Integration with more LLM providers
- [ ] Webhook notifications for failures
- [ ] Analytics and insights dashboard

## Disclaimer

This tool is for educational and personal use. Ensure you comply with:
- GitHub's Terms of Service
- API provider terms
- Applicable laws and regulations

Use responsibly and ethically.

**Happy Auto-Committing! 🎉**