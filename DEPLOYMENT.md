# Deployment Guide

This guide covers different ways to deploy the Telegram Admin Bot.

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot))

## Local Development

### 1. Setup

```bash
# Clone the repository
git clone https://github.com/shahrukh275/Telegram-Bot-.git
cd Telegram-Bot-

# Install dependencies
pip install -r requirements.txt

# Run setup script
python setup.py
```

### 2. Configuration

Edit the `.env` file with your bot credentials:

```env
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username_here
SUPER_ADMIN_ID=your_telegram_user_id_here
DATABASE_URL=sqlite:///bot.db
LOG_LEVEL=INFO
```

### 3. Run the Bot

```bash
# Test the bot
python test_bot.py

# Run the bot
python bot.py
```

## Production Deployment

### Option 1: VPS/Server Deployment

#### Using systemd (Linux)

1. **Create a service file**:
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

2. **Add the following content**:
```ini
[Unit]
Description=Telegram Admin Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Telegram-Bot-
Environment=PATH=/path/to/your/python/env/bin
ExecStart=/path/to/your/python/env/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. **Enable and start the service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

#### Using Docker

1. **Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

2. **Create docker-compose.yml**:
```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - BOT_USERNAME=${BOT_USERNAME}
      - SUPER_ADMIN_ID=${SUPER_ADMIN_ID}
      - DATABASE_URL=sqlite:///data/bot.db
    volumes:
      - ./data:/app/data
    env_file:
      - .env
```

3. **Deploy**:
```bash
docker-compose up -d
```

### Option 2: Cloud Platforms

#### Heroku

1. **Create Procfile**:
```
worker: python bot.py
```

2. **Deploy**:
```bash
heroku create your-bot-name
heroku config:set BOT_TOKEN=your_token
heroku config:set BOT_USERNAME=your_username
heroku config:set SUPER_ADMIN_ID=your_id
git push heroku main
heroku ps:scale worker=1
```

#### Railway

1. **Connect your GitHub repository**
2. **Set environment variables** in Railway dashboard
3. **Deploy automatically** on push

#### DigitalOcean App Platform

1. **Create app from GitHub repository**
2. **Set environment variables**
3. **Choose worker service type**

## Database Options

### SQLite (Default)
- Good for small to medium deployments
- No additional setup required
- File-based storage

### PostgreSQL (Recommended for Production)
```env
DATABASE_URL=postgresql://user:password@localhost/botdb
```

### MySQL
```env
DATABASE_URL=mysql://user:password@localhost/botdb
```

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use secure methods to store sensitive data
- Rotate tokens regularly

### Database Security
- Use strong passwords
- Enable SSL connections for remote databases
- Regular backups

### Bot Permissions
- Give the bot only necessary permissions
- Regularly audit admin lists
- Monitor bot activity logs

## Monitoring and Logging

### Log Configuration
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Log Files
```bash
# Redirect logs to file
python bot.py > bot.log 2>&1 &

# Or use systemd journal
journalctl -u telegram-bot -f
```

### Health Checks
Create a simple health check endpoint or monitor the bot's last activity.

## Backup and Recovery

### Database Backup
```bash
# SQLite
cp bot.db bot_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump botdb > backup_$(date +%Y%m%d).sql
```

### Configuration Backup
- Backup `.env` file securely
- Document any custom configurations
- Keep deployment scripts versioned

## Scaling

### Horizontal Scaling
- Use database clustering
- Load balance across multiple bot instances
- Implement proper session management

### Vertical Scaling
- Monitor memory and CPU usage
- Optimize database queries
- Use connection pooling

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check token validity
   - Verify network connectivity
   - Check logs for errors

2. **Database errors**
   - Verify database URL
   - Check permissions
   - Ensure database exists

3. **Permission errors**
   - Verify bot admin status
   - Check required permissions
   - Update admin cache

### Debug Mode
```env
LOG_LEVEL=DEBUG
```

### Testing Commands
```bash
# Test configuration
python -c "from config import Config; Config.validate(); print('Config OK')"

# Test database
python -c "from database import db; print('Database OK')"

# Run full tests
python test_bot.py
```

## Performance Optimization

### Database Optimization
- Add indexes for frequently queried fields
- Use connection pooling
- Regular maintenance and cleanup

### Memory Management
- Monitor memory usage
- Implement cleanup routines
- Use appropriate data structures

### Network Optimization
- Use webhooks instead of polling (advanced)
- Implement rate limiting
- Cache frequently accessed data

## Updates and Maintenance

### Updating the Bot
```bash
# Backup current version
cp -r Telegram-Bot- Telegram-Bot-backup

# Pull updates
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Test before deploying
python test_bot.py

# Restart service
sudo systemctl restart telegram-bot
```

### Regular Maintenance
- Monitor logs regularly
- Clean up old database entries
- Update dependencies
- Review and update configurations

## Support

For deployment issues:
1. Check the logs first
2. Verify configuration
3. Test with minimal setup
4. Create an issue on GitHub with details