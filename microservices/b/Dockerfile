FROM python:3.9-slim

WORKDIR /app

# Copy the application code and entrypoint script
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir flask requests gunicorn

# Ensure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# Create a non-root user with explicit UID and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port
EXPOSE 5002

# Set the entrypoint to the script
ENTRYPOINT ["/app/entrypoint.sh"]
