FROM python:3.10-slim

# सभी जरूरी पैकेज एक साथ इंस्टॉल
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# YouTube PO token provider (script mode - no background server/port needed)
# Fixes "Requested format is not available" / bot-detection errors from
# cookies-based downloads. Runs as a one-off subprocess per request via
# yt-dlp's plugin, so it doesn't cost any extra Render instance-hours.
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /root/bgutil-ytdlp-pot-provider \
    && cd /root/bgutil-ytdlp-pot-provider/server \
    && npm ci \
    && npx tsc

# ऐप कॉपी करें
COPY . /app/
WORKDIR /app/

# पायथन पैकेज इंस्टॉल करें
RUN pip install -r requirements.txt

# स्टार्ट कमांड
CMD bash start
