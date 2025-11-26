#!/bin/bash

# UV Environment Setup and Jupyter Kernel Registration Script (pyproject.toml based)
# Usage: ./setup_uv_jupyter.sh <environment_name> [python_version]

set -e  # Stop script on error

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions: Output messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print usage
usage() {
    echo "Usage: $0 <environment_name> [python_version]"
    echo ""
    echo "Examples:"
    echo "  $0 myproject"
    echo "  $0 myproject 3.11"
    echo "  $0 myproject 3.11.5"
    echo ""
    echo "Options:"
    echo "  environment_name : Name of the environment to create (required)"
    echo "  python_version   : Python version to use (optional, default: 3.11)"
    exit 1
}

# Validate arguments
if [ $# -lt 1 ]; then
    print_error "Environment name is required."
    usage
fi

ENV_NAME=$1
PYTHON_VERSION=${2:-3.11}
VENV_PATH=".venv"  # Explicitly set virtual environment path

print_info "Starting environment setup..."
print_info "Environment name: $ENV_NAME"
print_info "Python version: $PYTHON_VERSION"
print_info "Virtual environment path: $VENV_PATH"

# Clean up existing virtual environment
if [ -d "$VENV_PATH" ]; then
    print_warning "Removing existing virtual environment: $VENV_PATH"
    rm -rf .venv
    print_success "Existing virtual environment has been removed."
fi

# Check and auto-install UV
install_uv() {
    print_info "Installing UV..."

    # Use official installation script (recommended)
    print_info "Using official installation script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Update PATH (add possible installation paths)
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    # Source environment file if it exists
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    fi

    # Verify installation
    if command -v uv &> /dev/null; then
        print_success "UV has been successfully installed!"
        uv --version
    else
        print_error "UV installation failed."
        print_info "Manual installation methods:"
        echo "  1. Official script: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  2. pip: pip install uv"
        echo "  3. pipx: pipx install uv"
        exit 1
    fi
}

if ! command -v uv &> /dev/null; then
    print_warning "UV is not installed."
    read -p "Would you like to install UV automatically? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_uv
    else
        print_error "UV is required. Please install it manually."
        print_info "Installation methods:"
        echo "  1. Official script (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  2. pip: pip install uv"
        echo "  3. pipx: pipx install uv"
        exit 1
    fi
fi

# 1. Set Python version (before creating virtual environment)
print_info "Setting Python $PYTHON_VERSION..."
uv python pin $PYTHON_VERSION
print_success "Python $PYTHON_VERSION has been set."

# 2. Initialize project
print_info "Initializing project..."
if [ ! -f "pyproject.toml" ]; then
    uv init --name "$ENV_NAME"
    print_success "Project has been initialized as '$ENV_NAME'."
else
    print_warning "pyproject.toml already exists. Using existing project."
fi

# 3. Add essential packages
print_info "Adding Jupyter-related essential packages..."
uv add ipykernel jupyter

# 4. Check pyproject.toml and install dependencies
if [ -f "pyproject.toml" ]; then
    print_info "Found pyproject.toml. Synchronizing dependencies..."

    # Sync environment based on pyproject.toml dependencies
    uv sync

    print_success "Dependencies have been installed based on pyproject.toml."
    print_info "Lock file has been automatically created/updated: uv.lock"
else
    print_error "pyproject.toml not found. Project initialization may have failed."
    exit 1
fi

sudo apt-get update
sudo apt-get install pandoc -y
sudo apt-get install texlive -y
sudo apt-get install texlive-xetex -y
sudo apt-get install poppler-utils -y

# 5. Register Jupyter kernel
print_info "Registering Jupyter kernel..."
DISPLAY_NAME="$ENV_NAME (UV)"

# Remove existing kernel if it exists
if jupyter kernelspec list 2>/dev/null | grep -q "$ENV_NAME"; then
    print_warning "Removing existing '$ENV_NAME' kernel..."
    jupyter kernelspec remove -f "$ENV_NAME" || {
        print_warning "Failed to remove kernel, continuing..."
    }
fi

# Register new kernel (with error handling)
uv run python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME" || {
    print_error "Failed to register Jupyter kernel."
    print_info "To register manually: uv run python -m ipykernel install --user --name \"$ENV_NAME\" --display-name \"$DISPLAY_NAME\""
    exit 1
}
print_success "Jupyter kernel has been registered as '$DISPLAY_NAME'."

# 6. Verify installation
print_info "Verifying installation..."
echo ""
echo "=== Installed Python Version ==="
uv run python --version

echo ""
echo "=== Installed Packages ==="
uv pip list

echo ""
echo "=== pyproject.toml Dependencies ==="
if command -v grep &> /dev/null && [ -f "pyproject.toml" ]; then
    grep -A 20 "dependencies = \[" pyproject.toml || echo "Unable to read dependency information."
fi

echo ""
echo "=== Registered Jupyter Kernels ==="
jupyter kernelspec list 2>/dev/null | grep -E "(Available|$ENV_NAME)" || echo "Unable to retrieve kernel list."

# 7. Link environment files to root directory (create symlinks)
print_info "Linking UV environment files to root directory..."
cd ..

# Backup and remove existing files if they exist
for file in pyproject.toml .venv uv.lock; do
    if [ -e "$file" ] && [ ! -L "$file" ]; then
        print_warning "Backing up existing $file to ${file}.backup"
        mv "$file" "${file}.backup"
    elif [ -L "$file" ]; then
        print_info "Removing existing symlink $file"
        rm "$file"
    fi
done

# Create symlinks
ln -s setup/pyproject.toml . || {
    print_error "Failed to create pyproject.toml symlink"
    exit 1
}

ln -s setup/.venv . || {
    print_error "Failed to create .venv symlink"
    exit 1
}

if [ -f "setup/uv.lock" ]; then
    ln -s setup/uv.lock . || {
        print_warning "Failed to create uv.lock symlink"
    }
fi

print_success "UV environment files have been linked to root directory!"

echo ""
print_success "Environment setup completed successfully!"
echo ""
echo "=== Usage ==="
echo "1. Add package: uv add <package_name>"
echo "2. Remove package: uv remove <package_name>"
echo "3. Sync dependencies: uv sync"
echo "4. Run script: uv run python main.py (can run from root!)"
echo "5. Run Jupyter Lab: uv run jupyter lab"
echo "6. Select '$DISPLAY_NAME' kernel when creating new notebooks"
echo ""
echo "=== File Information ==="
echo "- pyproject.toml: Project configuration and dependencies (managed in setup/, symlinked to root)"
echo "- uv.lock: Exact version lock file (recommended to include in version control)"
echo "- .venv/: Virtual environment directory (exclude from version control)"
echo ""
print_info "You can now run 'uv run python main.py' from the root directory!"
print_info "Traditional activation: source .venv/bin/activate"
print_info "UV recommended method: uv run <command>"