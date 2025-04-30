#!/bin/bash

# Define the commands
COMMAND_1="cd flatland_librarian_server && python server.py"
COMMAND_2="cd flatland-librarian-web && pnpm preview"

# Name of the tmux session
SESSION_NAME="flatland-prod"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create a new tmux session
tmux new-session -d -s $SESSION_NAME

# Split the window vertically
tmux split-window -h

# Select the left pane and run COMMAND_1
tmux select-pane -t 0
tmux send-keys "conda activate story-llm-env && $COMMAND_1" C-m

# Select the right pane and run COMMAND_2
tmux select-pane -t 1
tmux send-keys "conda activate story-llm-env && $COMMAND_2" C-m

# Set up a hook to kill the session on detach
tmux set-hook -t $SESSION_NAME client-detached[0] "kill-session -t $SESSION_NAME"

# Attach to the tmux session
tmux attach-session -t $SESSION_NAME