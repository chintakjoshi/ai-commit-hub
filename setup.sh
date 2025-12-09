#!/bin/bash

echo "Setting up Auto-Committer AI..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
if [ "$OSTYPE" = "msys" ] || [ "$OSTYPE" = "cygwin" ]; then
    # Windows
    source venv/Scripts/activate
else
    # Unix/Linux/Mac
    source venv/bin/activate
fi

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p config agents managers utils data/templates data/cache
mkdir -p repos  # For local repository storage

# Create agent directories in the repo structure
mkdir -p repos/leetcode-solutions-ai/{problems,solutions,tests,explanations}
mkdir -p repos/technical-docs-ai/docs
mkdir -p repos/coding-challenges-ai/{problems,solutions}
mkdir -p repos/api-documentation-ai/docs
mkdir -p repos/algorithm-practice-ai/{solutions,tests}
mkdir -p repos/tutorials-ai/docs

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your API keys."
fi

# Create default config if it doesn't exist
if [ ! -f config/agents_config.yaml ]; then
    echo "Creating default agents configuration..."
    cat > config/agents_config.yaml << 'EOF'
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
  
  - name: "leetcode_solver_2"
    repo_name: "coding-challenges-ai"
    content_type: "leetcode"
    commit_pattern: "problem_only"
    is_active: true
    max_files_per_commit: 3
    min_files_per_commit: 1
  
  - name: "docs_writer_2"
    repo_name: "api-documentation-ai"
    content_type: "documentation"
    commit_pattern: "api_docs"
    is_active: true
    max_files_per_commit: 2
    min_files_per_commit: 1
EOF
    echo "Created default config/agents_config.yaml"
fi

# Make setup script executable
chmod +x setup.sh

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your API keys:"
echo "   - GITHUB_TOKEN (from GitHub Settings > Developer settings > Personal access tokens)"
echo "   - OPENROUTER_API_KEY (from https://openrouter.ai)"
echo "   - GOOGLE_API_KEY (from https://makersuite.google.com)"
echo ""
echo "2. Run the setup wizard:"
echo "   python main.py --setup"
echo ""
echo "3. Or run in different modes:"
echo "   python main.py           # Interactive mode"
echo "   python main.py --manual  # Manual control mode"
echo "   python main.py --test    # Test connections"