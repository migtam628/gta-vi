FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 bot \
    && useradd --uid 10001 --gid bot --no-create-home bot \
    && mkdir /data \
    && chown bot:bot /data
COPY bot.py seed_channels.py channel_seed_posts.json auto_post.py auto_post_schedule.json ./
USER bot
CMD ["python", "bot.py"]
