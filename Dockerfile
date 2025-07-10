# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working dir inside container
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 7500

# Run Flask app
CMD ["python", "app.py"]
