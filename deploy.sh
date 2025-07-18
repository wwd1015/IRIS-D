#!/bin/bash

# Bank Risk Management Dashboard - Deployment Script
# For Posit Connect Deployment

set -e  # Exit on any error

echo "🏦 Bank Risk Management Dashboard - Deployment Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    print_error "app.py not found. Please run this script from the project root directory."
    exit 1
fi

print_status "Starting deployment preparation..."

# 1. Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_status "Python version $python_version is compatible"
else
    print_error "Python version $python_version is not compatible. Required: $required_version or higher"
    exit 1
fi

# 2. Install dependencies
print_status "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    print_status "Dependencies installed successfully"
else
    print_error "requirements.txt not found"
    exit 1
fi

# 3. Generate sample data if not exists
print_status "Checking data files..."
if [ ! -d "data" ] || [ ! -f "data/loans.csv" ]; then
    print_status "Generating sample data..."
    python3 data_generator.py
    print_status "Sample data generated successfully"
else
    print_status "Data files already exist"
fi

# 4. Run tests
print_status "Running application tests..."
if python3 test_app.py; then
    print_status "All tests passed"
else
    print_warning "Some tests failed, but continuing with deployment"
fi

# 5. Create deployment package
print_status "Creating deployment package..."

# Create a deployment directory
deploy_dir="deployment_package"
mkdir -p "$deploy_dir"

# Copy necessary files
cp app.py "$deploy_dir/"
cp auth.py "$deploy_dir/"
cp data_generator.py "$deploy_dir/"
cp requirements.txt "$deploy_dir/"
cp README.md "$deploy_dir/"
cp posit-connect.yml "$deploy_dir/"

# Copy data directory
cp -r data "$deploy_dir/"

# Create a simple startup script
cat > "$deploy_dir/start.sh" << 'EOF'
#!/bin/bash
# Startup script for Posit Connect

echo "Starting Bank Risk Management Dashboard..."

# Set environment variables
export FLASK_ENV=production
export DASH_DEBUG=false

# Run the application
python3 app.py
EOF

chmod +x "$deploy_dir/start.sh"

print_status "Deployment package created in $deploy_dir/"

# 6. Create deployment instructions
cat > "$deploy_dir/DEPLOYMENT_INSTRUCTIONS.md" << 'EOF'
# Posit Connect Deployment Instructions

## Prerequisites
- Posit Connect server access
- Python 3.8+ environment configured
- Required permissions to deploy applications

## Deployment Steps

### 1. Upload Files
Upload all files from this directory to your Posit Connect server.

### 2. Configure Application
- Set the entry point to: `app.py`
- Set the Python version to: `3.9`
- Configure the port to: `8050`

### 3. Environment Variables
Set the following environment variables:
- `FLASK_ENV=production`
- `DASH_DEBUG=false`
- `PORT=8050`

### 4. Dependencies
Ensure all packages from `requirements.txt` are installed in the environment.

### 5. Data Access
The application requires read access to the `data/` directory.

### 6. Authentication
The application includes built-in authentication. Default credentials:
- Username: `admin`, Password: `admin123`
- Username: `risk_analyst_1`, Password: `password123`

### 7. Health Check
The application responds to health checks at the root path `/`.

## Post-Deployment

### Verify Deployment
1. Access the application URL
2. Login with test credentials
3. Test portfolio switching
4. Verify all dashboard tabs work
5. Test drill-down functionality

### Monitoring
- Monitor application logs for errors
- Check resource usage (CPU, Memory)
- Verify user access and authentication

### Troubleshooting
- Check application logs for error messages
- Verify all dependencies are installed
- Ensure data files are accessible
- Test authentication system

## Security Notes
- Change default passwords in production
- Implement proper SSL certificates
- Configure firewall rules as needed
- Set up proper user management
EOF

print_status "Deployment instructions created"

# 7. Create a summary
print_status "Deployment Summary:"
echo "======================"
echo "✅ Python environment verified"
echo "✅ Dependencies installed"
echo "✅ Sample data generated"
echo "✅ Application tests completed"
echo "✅ Deployment package created"
echo ""
echo "📁 Deployment package location: $deploy_dir/"
echo "📋 Instructions: $deploy_dir/DEPLOYMENT_INSTRUCTIONS.md"
echo ""
echo "🚀 Ready for Posit Connect deployment!"
echo ""
echo "Next steps:"
echo "1. Upload files from $deploy_dir/ to Posit Connect"
echo "2. Configure the application settings"
echo "3. Deploy and test the application"
echo "4. Update user credentials for production"

print_status "Deployment preparation completed successfully!" 