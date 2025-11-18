#!/bin/bash
# Setup Script for Testing Claude's Code Changes
# Run this on the server: ssh username@10.242.128.44 && bash setup_testing_branch.sh
# Or: curl -s https://raw.githubusercontent.com/cybersecurity-minh/KubeLLM-Minh/main/setup_testing_branch.sh | bash

set -e

echo "======================================================"
echo "  KubeLLM Testing Branch Setup"
echo "======================================================"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    echo "Please run this from your KubeLLM directory"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo ""

# Step 1: Check current remotes
echo "[1/5] Checking current Git remotes..."
echo "Current remotes:"
git remote -v
echo ""

# Step 2: Add fork as remote if not exists
echo "[2/5] Adding your fork as remote..."
if git remote | grep -q "myfork"; then
    echo "✅ Remote 'myfork' already exists, skipping..."
else
    git remote add myfork https://github.com/cybersecurity-minh/KubeLLM-Minh.git
    echo "✅ Added 'myfork' remote"
fi
echo ""

# Step 3: Fetch from fork
echo "[3/5] Fetching branches from your fork..."
git fetch myfork
echo "✅ Fetched successfully"
echo ""

# Step 4: Create/checkout testing branch
echo "[4/5] Setting up testing branch..."
BRANCH_NAME="dev/claude-testing"
REMOTE_BRANCH="myfork/claude/kubellm-qa-feature-01ARfPjWkVo3dBb12nxyJv89"

# Check if local branch exists
if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "✅ Branch '$BRANCH_NAME' already exists, checking out..."
    git checkout "$BRANCH_NAME"
    git pull myfork claude/kubellm-qa-feature-01ARfPjWkVo3dBb12nxyJv89
else
    echo "Creating new branch '$BRANCH_NAME' tracking remote..."
    git checkout -b "$BRANCH_NAME" "$REMOTE_BRANCH"
fi
echo "✅ Testing branch ready: $(git branch --show-current)"
echo ""

# Step 5: Verify setup
echo "[5/5] Verifying setup..."
echo ""
echo "======================================================"
echo "  Setup Complete! ✅"
echo "======================================================"
echo ""
echo "📊 Current Status:"
echo "  Current branch: $(git branch --show-current)"
echo "  Latest commit: $(git log -1 --pretty=format:'%h - %s')"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. To pull my latest changes:"
echo "   git pull myfork claude/kubellm-qa-feature-01ARfPjWkVo3dBb12nxyJv89"
echo ""
echo "2. To start Minikube and test:"
echo "   minikube start --profile xyz"
echo "   eval \$(minikube -p xyz docker-env)"
echo "   python3 main.py debug_assistant_latest/troubleshooting/port_mismatch/config_step.json"
echo ""
echo "3. To clean up after testing:"
echo "   python3 teardownenv.py port_mismatch"
echo ""
echo "4. To revert all changes (if something breaks):"
echo "   git reset --hard HEAD"
echo ""
echo "📚 Useful Commands:"
echo "   git status                    # Check current status"
echo "   git log --oneline -5          # See recent commits"
echo "   git diff origin/main          # Compare with original repo"
echo ""
echo "💡 To see all available Claude branches:"
echo "   git branch -r | grep claude"
echo ""
