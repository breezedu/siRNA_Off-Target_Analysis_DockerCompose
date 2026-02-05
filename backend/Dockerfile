FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install ViennaRNA (for RNA structure prediction)
RUN apt-get update && apt-get install -y \
    wget \
    && wget https://www.tbi.univie.ac.at/RNA/download/sourcecode/2_6_x/ViennaRNA-2.6.4.tar.gz \
    && tar -xzf ViennaRNA-2.6.4.tar.gz \
    && cd ViennaRNA-2.6.4 \
    && ./configure --without-perl --without-python3 \
    && make \
    && make install \
    && ldconfig \
    && cd .. \
    && rm -rf ViennaRNA-2.6.4* \
    && apt-get remove -y wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data/transcriptome

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
