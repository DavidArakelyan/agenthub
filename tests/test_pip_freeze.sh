#!/bin/bash

# Simple test script for pip freeze requirements-lock generation
echo "Testing pip freeze for requirements-lock generation:"

# Create a temporary directory
temp_dir=$(mktemp -d)
echo "Created temporary directory: $temp_dir"

# Create a test requirements.txt file
echo "Creating test requirements.txt file..."
cat > "$temp_dir/requirements.txt" << EOF
requests==2.31.0
python-dotenv>=0.21.0
EOF

# Set up a virtual environment
echo "Setting up a virtual environment..."
python3 -m venv "$temp_dir/venv"
source "$temp_dir/venv/bin/activate"

# Install the requirements
echo "Installing requirements..."
pip install -r "$temp_dir/requirements.txt"

# Generate requirements-lock.txt using pip freeze
echo "Generating requirements-lock.txt using pip freeze..."
pip freeze > "$temp_dir/requirements-lock.txt"

# Show the generated file
echo "Generated requirements-lock.txt:"
cat "$temp_dir/requirements-lock.txt"

# Clean up
deactivate
rm -rf "$temp_dir"
echo "Cleaned up temporary directory."

echo "Test completed successfully!"
