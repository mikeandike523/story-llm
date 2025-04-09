#!/bin/bash

get_flags() {
    local flags=()
    for arg in "$@"; do
        if [[ $arg == --* ]]; then
            # Split on '=' if present
            IFS='=' read -ra ADDR <<< "$arg"
            flags+=("${ADDR[0]}")
            # If there's a value, add it as the next element
            if [ ${#ADDR[@]} -eq 2 ]; then
                flags+=("${ADDR[1]}")
            fi
        elif [[ $arg == -* ]]; then
            # Handle short flags, split them into individual flags
            flag="${arg:1}"
            for (( i=0; i<${#flag}; i++ )); do
                flags+=("-${flag:$i:1}")
            done
        fi
    done
    echo "${flags[@]}"
}

# Parse flags
flags=($(get_flags "$@"))

# Initialize variables
FRESH=false

# Process flags
for ((i=0; i<${#flags[@]}; i++)); do
    case "${flags[i]}" in
        --fresh|-f)
            FRESH=true
            ;;
        --help|-h)
            echo "Usage: $0 [--fresh|-f] [--help|-h]"
            echo "  --fresh, -f    Create a fresh virtual environment"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: ${flags[i]}" >&2
            exit 1
            ;;
    esac
done

# If --fresh flag is provided, remove existing venv
if $FRESH; then
    echo "Creating fresh virtual environment..."
    rm -rf .venv
    python3 -m venv .venv
elif [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating new one..."
    python3 -m venv .venv
else
    echo "Using existing virtual environment..."
fi

source .venv/bin/activate

# Install or upgrade pipenv
pip install --upgrade pipenv

# Install dependencies
pipenv install

deactivate

chmod +x ./__pipenv

chmod +x ./__python

echo "Setup complete!"