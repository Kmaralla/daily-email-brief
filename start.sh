#!/bin/bash
# Easy startup script for Daily Email Brief

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created!"
    echo ""
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Dependencies installed!"
    echo ""
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating .env file template..."
    echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
    echo "✅ .env file created! Please add your OPENAI_API_KEY"
    echo ""
fi

# Run the launcher
echo "🚀 Starting Daily Email Brief..."
echo ""
python main.py
