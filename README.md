# TaskBridge

**Get paid for posting and commenting on Reddit.**

TaskBridge is a Discord bot platform that connects taskers with Reddit tasks. Complete posts and comments, earn money based on your tier, and get paid through crypto.

## How It Works

1. **Verify** — Link your Reddit account to check karma and account age
2. **Get Your Tier** — Your stats determine your pay rate
3. **Complete Tasks** — Post or comment on Reddit, submit proof, get paid
4. **Get Paid** — Withdraw via Binance UID, USDT, or USDC

## Pay Rates

| Tier | Requirements | Post | Comment |
|------|-------------|------|---------|
| Tier 1 | 100 karma | $1.50 | $0.50 |
| Tier 2 | 1,500 karma + 2 months | $3.50 | $1.50 |
| Tier 3 | 5,000 karma + 5 months | $7.00 | $3.00 |

## Earn Through Referrals

Don't qualify for tasks yet? You can still earn **$1 per qualified referral**. Just invite friends to the server — when they complete 1 post + 1 comment, you get paid. No limit on referrals.

## Features

- Reddit account verification with automatic tier assignment
- Task distribution and submission tracking
- Crypto payments (Binance UID, USDT, USDC)
- Referral system with automatic tracking
- Auto-moderation and spam filtering
- Support tickets
- Admin dashboard with location-based tasker lookup

## Tech Stack

- Python 3.14
- Discord.py
- Turso (libSQL)
- Render (hosting)
- UptimeRobot (keep-alive)

## Self-Host

```bash
git clone https://github.com/sibby-killer/taskbot.git
cd taskbot
pip install -r requirements.txt
cp .env.example .env  # Fill in your values
python3 bot.py
```

## Environment Variables

```
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
TURSO_DATABASE_URL=your_turso_url
TURSO_AUTH_TOKEN=your_turso_token
PORT=8080
```

## License

MIT
