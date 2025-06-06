#!/bin/bash

# Time Tracker Bot Setup Script
# This script sets up and runs the Time Tracker Bot in Docker

set -e  # Exit on any error

echo "🤖 Time Tracker Bot Setup Script"
echo "================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_warning "Please create .env file based on .env.example"
    echo ""
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your actual values"
    exit 1
fi

# Validate required environment variables
print_status "Validating environment variables..."

# Source .env file to check variables
source .env

required_vars=("TELEGRAM_BOT_TOKEN" "GOOGLE_SERVICE_ACCOUNT_FILE" "ALLOWED_USERS")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    printf '%s\n' "${missing_vars[@]}"
    exit 1
fi

# Check if Google service account file exists
if [ ! -f "$GOOGLE_SERVICE_ACCOUNT_FILE" ]; then
    print_error "Google service account file not found: $GOOGLE_SERVICE_ACCOUNT_FILE"
    exit 1
fi

print_status "Environment validation passed ✅"

# Function to stop existing containers
stop_containers() {
    print_status "Stopping existing containers..."
    docker compose down 2>/dev/null || true
}

# Function to build and start containers
start_containers() {
    print_status "Building and starting containers..."
    docker compose up --build -d
    
    if [ $? -eq 0 ]; then
        print_status "Bot started successfully! 🚀"
        echo ""
        echo "Container status:"
        docker compose ps
        echo ""
        echo "To view logs: docker compose logs -f"
        echo "To stop: docker compose down"
    else
        print_error "Failed to start containers"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    print_status "Showing bot logs..."
    docker compose logs -f
}

# Function to show status
show_status() {
    print_status "Container status:"
    docker compose ps
}

# Main script logic
case "${1:-start}" in
    "start")
        stop_containers
        start_containers
        ;;
    "stop")
        stop_containers
        print_status "Bot stopped 🛑"
        ;;
    "restart")
        stop_containers
        start_containers
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "build")
        stop_containers
        print_status "Building containers..."
        docker compose build
        start_containers
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|build}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the bot (default)"
        echo "  stop    - Stop the bot"
        echo "  restart - Restart the bot"
        echo "  logs    - Show bot logs"
        echo "  status  - Show container status"
        echo "  build   - Rebuild and start containers"
        exit 1
        ;;
esac