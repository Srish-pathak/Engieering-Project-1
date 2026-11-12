FROM node:22-bookworm

WORKDIR /app

# Install Python + pip + venv support required by the app's backend engine
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create venv and use it for Python packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Node dependencies first
COPY package.json package-lock.json* ./
RUN npm install --include=dev

# Install Python dependencies used by code analysis
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Build frontend assets for Vite app
RUN npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npx", "tsx", "server.ts"]
