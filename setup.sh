#!/bin/bash
# Setup script for Daily Email Brief

echo "Setting up Daily Email Brief..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file with your OPENAI_API_KEY"
echo "2. Download Gmail OAuth credentials.json from Google Cloud Console"
echo "3. Run: source venv/bin/activate"
echo "4. Run: python main.py fetch"
