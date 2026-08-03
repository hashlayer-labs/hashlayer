# HashLayer Validator Docker Image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*


# Copy project files
COPY pyproject.toml ./
COPY hashlayer ./hashlayer

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Force install bittensor compatible with finney/test runtime spec 432+
# (bittensor>=10.5.0 + ASI 2.x / cyscale). See MIGRATION-GUIDE.md
RUN pip install --no-cache-dir --force-reinstall \
    bittensor==10.5.0 \
    bittensor-wallet==4.1.0 \
    bt_decode \
    tabulate \
    python-dotenv

# Create necessary directories
RUN mkdir -p /app/config \
    && mkdir -p /root/.bittensor/wallets \
    && mkdir -p /root/.bittensor/chains \
    && mkdir -p /root/.bittensor/neurons

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import hashlayer.validator.validator; print('Validator import successful')" || exit 1

# Startup command - supports command line arguments
ENTRYPOINT ["python", "-m", "hashlayer.validator.validator"]
CMD ["run"]
