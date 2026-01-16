# Deploy feed.theones.io

## Quick Deploy to borg.tools

```bash
# 1. SSH to server
ssh vizi@borg.tools

# 2. Create directory structure
mkdir -p /home/vizi/feed.theones.io/{api,logs,collector}

# 3. Copy files (from local machine)
# Run this locally:
scp -r feed.theones.io/* vizi@borg.tools:/home/vizi/feed.theones.io/

# 4. Setup Python venv on server
ssh vizi@borg.tools
cd /home/vizi/feed.theones.io
python3 -m venv venv
source venv/bin/activate
pip install feedparser

# 5. Make cron script executable
chmod +x /home/vizi/feed.theones.io/cron.sh

# 6. Setup cron (4x daily)
crontab -e
# Add these lines:
0 0 * * * /home/vizi/feed.theones.io/cron.sh
0 6 * * * /home/vizi/feed.theones.io/cron.sh
0 12 * * * /home/vizi/feed.theones.io/cron.sh
0 18 * * * /home/vizi/feed.theones.io/cron.sh

# 7. Run initial collection
/home/vizi/feed.theones.io/cron.sh

# 8. Setup Nginx
sudo cp /home/vizi/feed.theones.io/nginx.conf /etc/nginx/sites-available/feed.theones.io
sudo ln -sf /etc/nginx/sites-available/feed.theones.io /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 9. Setup SSL with Certbot
sudo certbot --nginx -d feed.theones.io

# 10. Add DNS record
# A record: feed.theones.io -> 194.181.240.37
```

## Verify

```bash
# Check API
curl https://feed.theones.io/api/news.json

# Check logs
tail -f /home/vizi/feed.theones.io/logs/collect.log

# Check cron
crontab -l
```

## Structure on Server

```
/home/vizi/feed.theones.io/
├── index.html          # Frontend
├── api/
│   └── news.json       # JSON API (auto-generated)
├── collector/
│   ├── collect.py      # Collection script
│   └── requirements.txt
├── logs/
│   └── collect.log     # Logs
├── venv/               # Python venv
├── cron.sh             # Cron runner
└── nginx.conf          # Nginx config (reference)
```

## Troubleshooting

**Agent Zero timeout:**
- Check if Agent Zero is running: `curl http://194.181.240.37:50001/`
- Increase timeout in collect.py if needed

**RSS feed errors:**
- Some feeds may be blocked or changed URL
- Check logs for specific errors
- Remove problematic feeds from RSS_FEEDS list

**Cron not running:**
- Check cron logs: `grep CRON /var/log/syslog`
- Verify script permissions: `ls -la /home/vizi/feed.theones.io/cron.sh`
