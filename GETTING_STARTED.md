# Getting Started with Tech Recon Web Application

> **🏠 Local Machine Setup Guide**
>
> This guide will walk you through setting up and running the Tech Recon web application **on your local machine** (Windows, macOS, or Linux) from scratch, assuming no existing virtual environment.

## Prerequisites

Before you begin, ensure you have the following installed on your local system:

- **Python 3.12 or higher** - [Download Python](https://www.python.org/downloads/)
- **pip** (comes with Python) or **UV package manager** (recommended for faster installation)
- **Git** (optional, for cloning the repository) - [Download Git](https://git-scm.com/downloads)
- **AWS Account** with access to Amazon Bedrock
- **AWS CLI** configured with credentials - [Install AWS CLI](https://aws.amazon.com/cli/)
- **Tavily API Key** (for search functionality) - [Get API Key](https://tavily.com)

## Installation Steps

### Step 1: Get the Project Files

#### Option A: Clone from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/aws-samples/aws-ai-ml-workshop-kr.git

# Navigate to the Tech Recon directory
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/01_tech_recon
```

#### Option B: Use Existing Project Directory

If you already have the project files:

```bash
# Navigate to your project directory
cd /path/to/your/01_tech_recon
```

### Step 2: Create Virtual Environment


#### Using UV (Faster, Recommended for Local Development)

UV is a fast Python package installer and resolver. Install it first:

```bash
# Install UV (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or install via pip
pip install uv

# Or install via Homebrew (macOS)
brew install uv

# After installation, add UV to PATH
export PATH="$HOME/.local/bin:$PATH"
```

Then create the environment:

```bash
# Navigate to setup directory
cd setup
chmod +x ./create-uv-env.sh
./create-uv-env.sh tech-recon 3.12
cd ..
```

The script will automatically:
- Check and install UV if needed
- Create a virtual environment in `.venv/`
- Install all required dependencies from `pyproject.toml`
- Create symlinks (`pyproject.toml` and `uv.lock`) in the root directory
- Return to the project root directory


### Step 3: Configure Environment Variables

Copy the example environment file and configure it with your credentials:

```bash
# Copy example file
cp .env.example .env

# Edit the .env file with your favorite editor
nano .env  # or vim, code, etc.
```

Required environment variables in `.env`:

```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_DEFAULT_REGION=us-west-2
AWS_ACCOUNT_ID=857988933565

# Bedrock Model Configuration
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# Tavily Search Configuration
TAVILY_API_KEY=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
TAVILY_MAX_RESULTS=5

# AWS OpenTelemetry Configuration (Optional)
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
AGENT_OBSERVABILITY_ENABLED=true
```

**Important**: Replace the following placeholders:
- `your-account-id-here` - Your AWS account ID
- `your-tavily-api-key-here` - Your Tavily API key (get it from [tavily.com](https://tavily.com))

### Step 4: Configure AWS Credentials (Local Machine)

For local development, you need to configure AWS credentials. Choose one of the following methods:

#### Method 1: Using AWS CLI (Recommended)

```bash
# Configure AWS CLI with your credentials
aws configure

# You will be prompted to enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region name (e.g., us-west-2)
# - Default output format (e.g., json)

# Verify configuration
aws configure list
aws sts get-caller-identity
```

#### Method 2: Environment Variables

```bash
# Set AWS credentials as environment variables
# On macOS/Linux:
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-west-2

# On Windows (PowerShell):
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
$env:AWS_DEFAULT_REGION="us-west-2"

# For temporary credentials (if using AWS SSO or assumed role):
export AWS_SESSION_TOKEN=your-session-token
```

#### Method 3: AWS Credentials File

Create or edit `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your-access-key
aws_secret_access_key = your-secret-key

# Optional: For specific profile
[tech-recon]
aws_access_key_id = your-access-key
aws_secret_access_key = your-secret-key
region = us-west-2
```

Create or edit `~/.aws/config`:

```ini
[default]
region = us-west-2
output = json

[profile tech-recon]
region = us-west-2
output = json
```

### Step 5: Test Installation (Optional)

Verify that all dependencies are installed correctly:

```bash
# Activate virtual environment first (if using venv)
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Test Python packages
python -c "import flask, flask_socketio, socketio; print('✓ Web packages installed successfully!')"
python -c "import boto3; print('✓ AWS SDK installed successfully!')"
python -c "from strands_agents import Agent; print('✓ Strands Agents installed successfully!')"

# Test AWS credentials
aws sts get-caller-identity

# If using UV
uv run python -c "import flask, flask_socketio, socketio; print('✓ All packages installed successfully!')"
```

Expected output:
```
✓ Web packages installed successfully!
✓ AWS SDK installed successfully!
✓ Strands Agents installed successfully!
{
    "UserId": "AIDACKCEVSQ6C2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

## Running the Application on Your Local Machine

Now you're ready to run the Tech Recon web application locally!

### Method 1: Using the Start Script (Recommended)

The easiest way to start the application:

```bash
# Make sure you're in the project root directory
cd ..

# Make the script executable (first time only)
chmod +x start_web.sh

# Run the start script
./start_web.sh
```

The script will:
1. Display startup information
2. Sync dependencies (if using UV)
3. Install web-specific packages (Flask, SocketIO)
4. Start the web server on port 5000

### Method 2: Manual Start

If you prefer to start manually or the script doesn't work:

```bash
# Navigate to project root
cd /path/to/01_tech_recon

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
.venv\Scripts\activate.bat

# Run the web application
python web_app.py
```

### Method 3: Using UV (If you set up with UV)

```bash
# From the project root directory
uv run python web_app.py
```

### Expected Output

When the server starts successfully, you should see:

```
==========================================
Tech Recon Web Application Starter
==========================================
Working directory: /path/to/01_tech_recon
Syncing dependencies...
Installing web packages...

==========================================
Starting Web Server...
==========================================

============================================================
Tech Recon Web Application
============================================================
Server starting at: http://localhost:5000
Press Ctrl+C to stop the server
============================================================
```

## Accessing the Application on Your Local Machine

1. **Open your web browser** (Chrome, Firefox, Safari, or Edge)
2. **Navigate to**: `http://localhost:5000`
3. You should see the **Tech Recon web interface**

**Note for local access:**
- The application runs on your local machine at `localhost:5000`
- If you want to access from other devices on your local network:
  - Find your local IP address:
    ```bash
    # macOS/Linux
    ifconfig | grep "inet " | grep -v 127.0.0.1

    # Windows
    ipconfig | findstr IPv4
    ```
  - Access via `http://YOUR-LOCAL-IP:5000` from other devices on the same network

## Using the Application

### Running Analysis Tasks

The application provides two main tasks:

1. **Part 1: Technical Research**
   - Click the "Run Part 1" button
   - Monitors technical research and reconnaissance
   - Generates research artifacts

2. **Part 2: Advanced Analysis**
   - Click the "Run Part 2" button
   - Performs deeper analysis
   - Creates comprehensive reports

### Monitoring Execution

- **Real-time Logs**: View execution progress in the left panel
- **Color-coded Output**:
  - Blue: Reasoning processes
  - Yellow: Tool usage
  - Green: Tool results
  - Red: Errors
  - White: General information

### Downloading Results

#### Individual Files
- Browse generated files in the right panel
- Click "Download" next to any file

#### Bulk Downloads
- **Download Part 1 (ZIP)**: All Part 1 artifacts
- **Download Part 2 (ZIP)**: All Part 2 artifacts
- **Download All (ZIP)**: Complete archive of all files

## Troubleshooting (Local Environment)

### Port 5000 Already in Use

```bash
# On macOS/Linux - Find process using port 5000
lsof -i :5000

# Kill the process (replace <PID> with actual process ID)
kill -9 <PID>

# On Windows - Find and kill process
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Python Version Issues

```bash
# Check Python version (must be 3.12 or higher)
python3 --version

# If version is too old, install Python 3.12+
# macOS: brew install python@3.12
# Windows: Download from python.org
# Linux: sudo apt install python3.12
```

### Package Installation Errors

```bash
# Upgrade pip and retry
pip install --upgrade pip
pip install -r requirements_web.txt --force-reinstall

# Or with UV
uv sync --reinstall

# If specific package fails, try installing individually
pip install flask flask-socketio python-socketio boto3 strands-agents
```

### AWS Credentials Not Found

```bash
# Check if AWS CLI is configured
aws configure list

# Verify credentials file exists
# macOS/Linux:
cat ~/.aws/credentials

# Windows:
type %USERPROFILE%\.aws\credentials

# Test AWS connection
aws sts get-caller-identity

# If not working, reconfigure:
aws configure
```

### Bedrock Access Denied Error

If you get permission errors when running:

1. **Enable Bedrock Model Access** in AWS Console:
   - Go to AWS Console → Bedrock → Model Access
   - Enable Claude models (Haiku, Sonnet, etc.)
   - Wait for approval (usually instant)

2. **Check IAM Permissions**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### Module Import Errors

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate  # Windows

# Verify which Python is being used
which python  # macOS/Linux
where python  # Windows

# Should point to .venv/bin/python

# Reinstall dependencies
pip install -r requirements_web.txt
```

### WebSocket Connection Issues

1. Check browser console (F12) for errors
2. Verify the server is running on port 5000:
   ```bash
   # macOS/Linux
   lsof -i :5000

   # Windows
   netstat -ano | findstr :5000
   ```
3. Try a different browser (Chrome, Firefox recommended)
4. Check firewall settings - allow port 5000
5. Try accessing via `127.0.0.1:5000` instead of `localhost:5000`

### Environment Variable Errors

```bash
# Verify .env file exists and has correct values
cat .env  # macOS/Linux
type .env  # Windows

# Check if environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('AWS_REGION:', os.getenv('AWS_REGION'))"

# Common issues:
# 1. .env file not in project root
# 2. Missing quotes around values with spaces
# 3. Windows line endings (use dos2unix or save with LF)
```

### UV Installation Issues

```bash
# If UV install script fails, try pip method
pip install uv

# Or use Homebrew (macOS)
brew install uv

# Verify installation
uv --version

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

### Virtual Environment Activation Issues (Windows)

If you get execution policy error on Windows:

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.venv\Scripts\Activate.ps1
```

## System Requirements for Local Machine

### Minimum Requirements
- **OS**: macOS 10.15+, Windows 10+, or Linux (Ubuntu 20.04+)
- **CPU**: 2 cores (Intel/AMD/Apple Silicon)
- **RAM**: 4GB
- **Disk**: 2GB free space
- **Python**: 3.12 or higher
- **Network**: Stable internet connection for AWS Bedrock and Tavily API

### Recommended Requirements
- **OS**: macOS 12+, Windows 11, or Ubuntu 22.04+
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 5GB+ free space
- **Python**: 3.12+
- **Network**: Broadband connection (10+ Mbps)

### Supported Platforms
- ✅ macOS (Intel and Apple Silicon)
- ✅ Windows 10/11
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)
- ✅ WSL2 (Windows Subsystem for Linux)

## Network Configuration (Local Machine)

### Default Configuration

The application runs on `0.0.0.0:5000` by default, making it accessible from:
- **Your local machine**: `http://localhost:5000` or `http://127.0.0.1:5000`
- **Other devices on your local network**: `http://<your-local-ip>:5000`

### Finding Your Local IP Address

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1

# Windows (PowerShell)
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*"}

# Windows (Command Prompt)
ipconfig | findstr IPv4
```

### Changing the Port

If port 5000 is already in use or you want to use a different port, edit `web_app.py`:

```python
# Find this line near the end of web_app.py (around line 200+)
socketio.run(app, host='0.0.0.0', port=5000, debug=False)

# Change port to your desired value (e.g., 8080)
socketio.run(app, host='0.0.0.0', port=8080, debug=False)
```

### Firewall Configuration

If accessing from other devices on your network:

**macOS:**
```bash
# System Preferences → Security & Privacy → Firewall
# Add Python to allowed apps
```

**Windows:**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Tech Recon Web App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

**Linux (Ubuntu/Debian):**
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

## Security Considerations (Local Development)

### Important Security Practices

1. **Never commit `.env` file** to version control
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

2. **Protect AWS Credentials**
   - Never share your AWS Access Keys
   - Use temporary credentials when possible
   - Consider using AWS SSO for better security
   - Rotate credentials regularly

3. **Rotate API keys** regularly
   - Tavily API keys should be rotated
   - Monitor API usage for unusual activity

4. **Local Network Security**
   - The app binds to `0.0.0.0` (all interfaces) by default
   - For localhost-only access, change to `127.0.0.1`:
     ```python
     # In web_app.py
     socketio.run(app, host='127.0.0.1', port=5000, debug=False)
     ```

5. **Keep dependencies updated**
   ```bash
   # Check for updates
   pip list --outdated

   # Update packages
   pip install --upgrade flask boto3 strands-agents

   # Or with UV
   uv pip install --upgrade flask boto3 strands-agents
   ```

6. **Use IAM Best Practices**
   - Don't use root AWS credentials
   - Create IAM user with minimum required permissions
   - Use AWS temporary credentials when possible

7. **Environment File Permissions**
   ```bash
   # Restrict .env file access (Unix-like systems)
   chmod 600 .env
   ```

## Next Steps

After successful setup:

1. Review the [WEB_README.md](WEB_README.md) for detailed feature documentation
2. Check [README.md](README.md) for project overview
3. Explore the `tutorials/` directory for examples
4. Review `CLAUDE.md` for AI agent configuration details

## Quick Start Summary (TL;DR)

For experienced users who want to get started quickly:

```bash
# 1. Clone and navigate
git clone https://github.com/aws-samples/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/01_tech_recon

# 2. Setup with UV (recommended)
cd setup/ && ./create-uv-env.sh tech-recon 3.12

# Or setup with pip
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements_web.txt

# 3. Configure
cp .env.example .env
# Edit .env with your AWS and Tavily credentials
aws configure  # Setup AWS credentials

# 4. Run
./start_web.sh
# Or: python web_app.py

# 5. Access
# Open browser: http://localhost:5000
```

## FAQ (Frequently Asked Questions)

### Q: Can I run this on Windows?
**A:** Yes! The application works on Windows 10/11. Use PowerShell or Command Prompt for setup commands, and activate the virtual environment with `.venv\Scripts\activate`.

### Q: Do I need SageMaker to run this?
**A:** No! This guide is specifically for running on your local machine. You only need Python, AWS credentials, and internet access.

### Q: What AWS services do I need?
**A:** You need access to Amazon Bedrock (specifically Claude models). Make sure to enable model access in the AWS Bedrock console.

### Q: How much does it cost to run?
**A:** Costs depend on your usage:
- **AWS Bedrock**: Pay per token (varies by model)
- **Tavily API**: Free tier available, then pay-as-you-go
- **Local compute**: Free (runs on your machine)

### Q: Can I use a different AI model?
**A:** Yes! Edit the `.env` file and change `BEDROCK_MODEL_ID` to any supported Bedrock model (e.g., Claude Sonnet, Haiku, Nova, etc.).

### Q: The application is slow. How can I speed it up?
**A:** Try these:
- Use a faster model (e.g., Claude Haiku)
- Ensure good internet connection
- Check your local machine resources
- Consider running on a more powerful machine

### Q: Can I run this without Tavily API?
**A:** The application requires Tavily for search functionality. You'll need at least a free tier API key from [tavily.com](https://tavily.com).

### Q: How do I stop the server?
**A:** Press `Ctrl+C` in the terminal where the server is running.

### Q: Can I access this from my phone/tablet?
**A:** Yes! If both devices are on the same local network:
1. Find your computer's local IP address
2. Access `http://YOUR-LOCAL-IP:5000` from your mobile browser

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the Troubleshooting section** above for common issues
2. **Review existing GitHub issues**: [AWS AI/ML Workshop Issues](https://github.com/aws-samples/aws-ai-ml-workshop-kr/issues)
3. **AWS Bedrock documentation**: [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/)
4. **Create a new issue** with detailed error messages and your environment details

## Additional Resources

- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **Tavily API**: https://tavily.com
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Socket.IO**: https://socket.io/docs/

## License

This project is licensed under the MIT License. See [LICENSE](../../LICENSE) for details.

## Acknowledgments

This project is part of the AWS AI/ML Workshop Korea repository and leverages:
- Amazon Bedrock for AI capabilities
- Tavily for search functionality
- Flask and Socket.IO for web interface
