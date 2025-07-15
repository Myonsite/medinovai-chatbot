# Development Environment Setup - MedinovAI Chatbot

This guide will help you set up a complete development environment for contributing to the MedinovAI Chatbot project.

## Prerequisites

### System Requirements

#### Minimum Requirements
- **Operating System**: macOS 12+, Ubuntu 20.04+, or Windows 11 with WSL2
- **RAM**: 16 GB (32 GB recommended)
- **Storage**: 100 GB free space (SSD recommended)
- **Network**: Stable internet connection for API access

#### Recommended Development Setup
- **macOS**: Latest macOS with Homebrew
- **Ubuntu**: Ubuntu 22.04 LTS
- **Windows**: Windows 11 with WSL2 (Ubuntu 22.04)

### Required Software

#### 1. **Git**
```bash
# macOS
brew install git

# Ubuntu
sudo apt update && sudo apt install git

# Windows (WSL2)
sudo apt update && sudo apt install git
```

#### 2. **Python 3.11+**
```bash
# macOS
brew install python@3.11

# Ubuntu
sudo apt install python3.11 python3.11-pip python3.11-venv

# Windows (WSL2)
sudo apt install python3.11 python3.11-pip python3.11-venv
```

#### 3. **Node.js 18+**
```bash
# Using Node Version Manager (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Verify installation
node --version
npm --version
```

#### 4. **Docker & Docker Compose**
```bash
# macOS
brew install docker docker-compose

# Ubuntu
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER

# Windows (WSL2)
# Install Docker Desktop for Windows with WSL2 backend
```

#### 5. **PostgreSQL Client**
```bash
# macOS
brew install postgresql

# Ubuntu/WSL2
sudo apt install postgresql-client
```

#### 6. **Redis CLI**
```bash
# macOS
brew install redis

# Ubuntu/WSL2
sudo apt install redis-tools
```

### Optional but Recommended Tools

#### Development IDEs
- **VS Code**: With Python, TypeScript, and Docker extensions
- **PyCharm Professional**: For advanced Python development
- **WebStorm**: For frontend development

#### Database Tools
- **DBeaver**: Universal database tool
- **Redis Insight**: Redis management tool
- **pgAdmin**: PostgreSQL administration

#### API Testing
- **Postman**: API testing and documentation
- **Insomnia**: Alternative API client
- **curl**: Command-line HTTP client

## Project Setup

### 1. **Clone Repository**

```bash
# Clone the main repository
git clone https://github.com/myonsite-healthcare/MedinovAI-Chatbot.git
cd MedinovAI-Chatbot

# Verify you're on the main branch
git branch
git status
```

### 2. **Environment Configuration**

#### Create Environment File
```bash
# Copy the example environment file
cp .env.example .env

# Open in your preferred editor
code .env  # VS Code
nano .env  # Terminal editor
```

#### Configure Environment Variables
```bash
# =============================================================================
# MedinovAI Chatbot - Development Environment Configuration
# =============================================================================

# Application Settings
APP_NAME="MedinovAI Chatbot"
APP_VERSION="1.0.0"
ENVIRONMENT="development"
DEBUG=true
LOG_LEVEL="debug"

# Server Configuration
HOST="localhost"
PORT=8000
CORS_ORIGINS="http://localhost:3000,http://localhost:8000"

# Database Configuration
DATABASE_URL="postgresql://medinovai:dev_password@localhost:5432/medinovai_dev"
REDIS_URL="redis://localhost:6379"

# AI/ML Configuration
OPENAI_API_KEY="your-openai-api-key-here"
OPENAI_MODEL="gpt-4-turbo"
ANTHROPIC_API_KEY="your-anthropic-api-key-here"
CHROMA_PERSIST_DIRECTORY="./data/chroma"

# Twilio Configuration (Development)
TWILIO_ACCOUNT_SID="your-test-account-sid"
TWILIO_AUTH_TOKEN="your-test-auth-token"
TWILIO_PHONE_NUMBER="+15551234567"

# OAuth2 Configuration (Development)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Security Configuration
JWT_SECRET_KEY="your-jwt-secret-for-development"
JWT_ALGORITHM="RS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Configuration (Development)
SMTP_HOST="localhost"
SMTP_PORT=1025
SMTP_USERNAME=""
SMTP_PASSWORD=""
SMTP_USE_TLS=false

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
JAEGER_ENABLED=true

# Feature Flags
ENABLE_VOICE_CHAT=true
ENABLE_MATTERMOST=true
ENABLE_EHR_INTEGRATION=false
```

### 3. **Backend Setup (Python/FastAPI)**

#### Create Virtual Environment
```bash
cd src

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux
source venv/bin/activate

# Windows (if not using WSL2)
venv\Scripts\activate

# Verify activation
which python
python --version
```

#### Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
pip list
```

#### Database Setup
```bash
# Start PostgreSQL and Redis with Docker
docker-compose up -d postgres redis

# Wait for services to start (30 seconds)
sleep 30

# Create database
createdb -h localhost -U medinovai medinovai_dev

# Run database migrations
alembic upgrade head

# Load initial data (optional)
python scripts/load_initial_data.py
```

#### Start Backend Development Server
```bash
# Start the FastAPI development server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or use the development script
python dev.py

# Verify server is running
curl http://localhost:8000/health
```

### 4. **Frontend Setup (Next.js)**

#### Open New Terminal and Navigate to Frontend
```bash
cd admin-ui

# Install dependencies
npm install

# Or using yarn
yarn install
```

#### Configure Frontend Environment
```bash
# Create frontend environment file
cp .env.local.example .env.local

# Edit environment variables
code .env.local
```

```bash
# Frontend Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME="MedinovAI Admin"
NEXT_PUBLIC_ENVIRONMENT=development

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret-for-development

# Analytics (optional for development)
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=""
```

#### Start Frontend Development Server
```bash
# Start Next.js development server
npm run dev

# Or using yarn
yarn dev

# Verify frontend is running
open http://localhost:3000
```

### 5. **Docker Development Environment**

#### Start All Services with Docker Compose
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

#### Individual Service Management
```bash
# Start only database services
docker-compose up -d postgres redis chroma

# Start monitoring stack
docker-compose up -d prometheus grafana jaeger

# Restart specific service
docker-compose restart api
```

## Development Workflow

### 1. **Code Standards and Linting**

#### Python Code Standards
```bash
cd src

# Run black formatter
black .

# Run isort for import sorting
isort .

# Run flake8 linter
flake8 .

# Run mypy type checker
mypy .

# Run all checks with pre-commit
pre-commit run --all-files
```

#### Frontend Code Standards
```bash
cd admin-ui

# Run ESLint
npm run lint

# Fix ESLint issues
npm run lint:fix

# Run Prettier
npm run format

# Type checking
npm run type-check
```

### 2. **Testing**

#### Backend Testing
```bash
cd src

# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_auth.py

# Run tests with verbose output
pytest -v

# Run integration tests
pytest tests/integration/
```

#### Frontend Testing
```bash
cd admin-ui

# Run unit tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run end-to-end tests
npm run test:e2e

# Generate test coverage
npm run test:coverage
```

### 3. **Database Management**

#### Create New Migration
```bash
cd src

# Generate migration for model changes
alembic revision --autogenerate -m "Add new table"

# Review generated migration
cat alembic/versions/[revision_id]_add_new_table.py

# Apply migration
alembic upgrade head
```

#### Database Operations
```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Downgrade to previous migration
alembic downgrade -1

# Reset database (development only)
alembic downgrade base
alembic upgrade head
```

### 4. **API Development**

#### Test API Endpoints
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/auth/sms/request \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+15551234567"}'

# Test with authentication token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/auth/user/me
```

#### API Documentation
```bash
# View interactive API docs
open http://localhost:8000/docs

# View ReDoc documentation
open http://localhost:8000/redoc

# Generate OpenAPI spec
curl http://localhost:8000/openapi.json > openapi.json
```

## Development Tools and Extensions

### VS Code Extensions

#### Essential Extensions
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode-remote.remote-containers",
    "ms-azuretools.vscode-docker"
  ]
}
```

#### VS Code Settings
```json
{
  "python.defaultInterpreterPath": "./src/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.path": "isort",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "eslint.workingDirectories": ["admin-ui"],
  "tailwindCSS.includeLanguages": {
    "typescript": "javascript",
    "typescriptreact": "javascript"
  }
}
```

### Git Configuration

#### Git Hooks Setup
```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Update pre-commit hooks
pre-commit autoupdate
```

#### Git Configuration
```bash
# Configure Git (if not already done)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Set up useful aliases
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
```

## Debugging and Troubleshooting

### Common Issues and Solutions

#### Python Environment Issues
```bash
# Virtual environment not found
which python
source src/venv/bin/activate

# Package installation issues
pip install --upgrade pip
pip install -r src/requirements.txt --force-reinstall

# Permission issues (macOS/Linux)
sudo chown -R $USER:$USER src/venv
```

#### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check database connection
psql -h localhost -U medinovai -d medinovai_dev

# Reset database
docker-compose down postgres
docker volume rm medinovai-chatbot_postgres_data
docker-compose up -d postgres
```

#### API Server Issues
```bash
# Port already in use
lsof -ti:8000 | xargs kill -9

# Module import errors
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Environment variable issues
source .env
set | grep -E "(DATABASE_URL|OPENAI_API_KEY)"
```

#### Frontend Build Issues
```bash
# Clear Next.js cache
cd admin-ui
rm -rf .next
npm run build

# Node modules issues
rm -rf node_modules package-lock.json
npm install

# TypeScript compilation errors
npm run type-check
```

### Debugging Tools

#### Python Debugging
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
import debugpy; debugpy.breakpoint()

# Environment-specific debugging
if os.getenv("DEBUG"):
    import pdb; pdb.set_trace()
```

#### Frontend Debugging
```javascript
// Browser developer tools
console.log('Debug info:', debugInfo);
debugger; // Browser will pause here

// React Developer Tools
// Install browser extension for component debugging
```

#### Database Debugging
```bash
# Check slow queries
docker-compose exec postgres psql -U medinovai -d medinovai_dev -c "
  SELECT query, mean_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC 
  LIMIT 10;"

# Monitor database activity
docker-compose logs -f postgres
```

## Performance Optimization

### Development Performance Tips

#### Python Performance
```bash
# Use uvloop for better async performance
pip install uvloop

# Profile code with cProfile
python -m cProfile -o profile.prof main.py
python -c "import pstats; pstats.Stats('profile.prof').sort_stats('tottime').print_stats(10)"

# Memory profiling
pip install memory-profiler
python -m memory_profiler your_script.py
```

#### Frontend Performance
```bash
# Analyze bundle size
cd admin-ui
npm run analyze

# Check for unused dependencies
npx depcheck

# Optimize images
npm install next-optimized-images
```

#### Database Performance
```sql
-- Explain query performance
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename = 'users';
```

## Security Considerations

### Development Security

#### Environment Security
```bash
# Never commit .env files
echo ".env" >> .gitignore

# Use different secrets for development
openssl rand -hex 32  # Generate random secret

# Secure API keys
export OPENAI_API_KEY=$(cat ~/secrets/openai_key)
```

#### HTTPS in Development
```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout localhost.key -out localhost.crt

# Start server with HTTPS
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile localhost.key --ssl-certfile localhost.crt
```

#### Database Security
```sql
-- Create limited development user
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT CONNECT ON DATABASE medinovai_dev TO dev_user;
GRANT USAGE ON SCHEMA public TO dev_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dev_user;
```

## CI/CD Integration

### GitHub Actions Local Testing
```bash
# Install act for local testing
brew install act

# Run tests locally
act -j test

# Run specific workflow
act -j lint-and-format
```

### Docker Development
```bash
# Build development image
docker build -f Dockerfile.dev -t medinovai:dev .

# Run with docker-compose override
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

## Additional Resources

### Documentation
- [API Documentation](../api/) - Complete API reference
- [Architecture Overview](../architecture/overview.md) - System architecture
- [Contributing Guidelines](contributing.md) - How to contribute
- [Code Review Guidelines](code-review.md) - Code review process

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

### Support
- **Internal Wiki**: [wiki.myonsitehealthcare.com](https://wiki.myonsitehealthcare.com)
- **Slack Channel**: #medinovai-dev
- **Email Support**: dev-support@myonsitehealthcare.com
- **Office Hours**: Tuesdays 2-3 PM PST

## Next Steps

Once your development environment is set up:

1. **Review the codebase**: Start with [Architecture Overview](../architecture/overview.md)
2. **Check open issues**: Look at GitHub issues labeled "good first issue"
3. **Read contributing guidelines**: Review [Contributing Guide](contributing.md)
4. **Join team communication**: Get access to Slack and team channels
5. **Schedule onboarding**: Book time with team lead for project overview

## Troubleshooting Checklist

Before asking for help, please check:

- [ ] All required software is installed and updated
- [ ] Virtual environment is activated
- [ ] Environment variables are correctly set
- [ ] Database is running and accessible
- [ ] No port conflicts (8000, 3000, 5432, 6379)
- [ ] Git repository is up to date
- [ ] Pre-commit hooks are installed
- [ ] Tests pass locally

---

**Welcome to the MedinovAI development team!** If you encounter any issues with this setup guide, please update the documentation and submit a pull request to help future developers. 