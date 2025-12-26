module.exports = {
  apps: [{
    name: 'sentinel-bot',
    script: 'main.py',
    interpreter: 'venv/bin/python',
    cwd: '/var/www/Sentinel',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      PYTHONUNBUFFERED: '1',
      NODE_ENV: 'production'
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true,
    merge_logs: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};


