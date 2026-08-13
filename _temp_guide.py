import asyncio, aiohttp, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']
CHANNEL_ID = '1537510584046846004'

WARMING_GUIDE = """# 📖 Account Warming Guide

## ⚠️ Why Warming Matters
Reddit detects sudden activity from new/inactive accounts. Warming builds trust and avoids flags.

---

## 📅 Day 0-1: Just Browse
- Create/claim account
- Browse Reddit normally (10-15 min)
- Join 3-5 subreddits in your niche
- Upvote 5-10 posts you like
- **DO NOT post or comment yet**

---

## 📅 Day 2-3: Light Engagement
- Browse daily (15-20 min)
- Upvote 10-15 posts
- Save a few posts
- Leave 1-2 simple comments ("Great post!", "Thanks for sharing!")
- **Keep it natural**

---

## 📅 Day 4-5: First Comments
- Comment on 2-3 posts daily
- Write 1-2 sentences each
- Stay in subreddits you joined
- Upvote regularly
- **Still NO posts**

---

## 📅 Day 6-7: More Comments
- Comment on 3-5 posts daily
- Write 2-3 sentences
- Start participating in discussions
- Upvote and save posts

---

## 📅 Day 8-10: First Posts
- Make your first post (simple, helpful)
- Continue commenting (3-5/day)
- Engage with replies on your post
- Keep upvoting

---

## 📅 Day 11+: Normal Use
- Post 1-2 times daily
- Comment 5-10 times daily
- Engage naturally
- Build karma steadily

---

## ❌ Things to AVOID
- Posting links immediately
- Spamming comments
- Using multiple accounts
- VPN/proxy usage
- Copy-pasting comments
- Posting in banned subreddits

---

## ✅ Best Practices
- Use consistent IP/device
- Write unique comments
- Be helpful and genuine
- Follow subreddit rules
- Wait for CQS to improve"""

CQS_GUIDE = """# 🔍 Reddit CQS (Contributor Quality Score)

## What is CQS?
CQS is Reddit's internal quality score for accounts. It determines:
- Whether your posts need approval
- Your visibility in feeds
- Your trust level

---

## 📊 CQS Tiers

### 🔴 Lowest
- New accounts
- Low karma
- Suspicious activity
- **Impact:** Posts may be filtered, limited visibility

### 🟠 Low
- Some karma, but low engagement
- Inconsistent activity
- **Impact:** Posts may need approval, reduced reach

### 🟡 Moderate
- Decent karma and activity
- Some account age
- **Impact:** Normal posting, good visibility

### 🟢 High
- High karma, active account
- Good standing
- **Impact:** Full access, best visibility, trusted

---

## 🔎 How to Check Your CQS

### Method 1: Reddit Request
1. Go to r/WhatIsMyCQS
2. Comment "!cqs" on any post
3. Bot will reply with your tier

### Method 2: Manual Check
1. Try posting in a subreddit
2. If filtered/removed immediately = Low CQS
3. If approved quickly = High CQS

---

## 📈 How to Improve CQS

### Quick Wins (1-2 weeks)
- Comment regularly (5-10/day)
- Upvote quality content
- Avoid controversial topics
- Follow all subreddit rules

### Medium Term (1-2 months)
- Build karma consistently
- Get upvotes on your comments
- Avoid reports/removals
- Maintain daily activity

### Long Term (3+ months)
- Established post history
- High karma score
- Positive community standing
- No violations

---

## ⚠️ What LOWERS CQS
- Getting reported
- Having posts removed
- Spamming
- Using bots/automation
- Multiple account violations
- Posting controversial content

---

## 🎯 Target: Get to HIGH CQS
- Takes 1-3 months of consistent activity
- Enables full posting ability
- Maximizes your earnings potential"""

async def main():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}

        warming_msg = {'content': WARMING_GUIDE}
        r = await session.post(f'https://discord.com/api/v10/channels/{CHANNEL_ID}/messages', headers=headers, json=warming_msg)
        if r.status in (200, 201):
            print('Warming guide sent')
        else:
            print(f'Error: {await r.text()}')

        await asyncio.sleep(1)

        cqs_msg = {'content': CQS_GUIDE}
        r = await session.post(f'https://discord.com/api/v10/channels/{CHANNEL_ID}/messages', headers=headers, json=cqs_msg)
        if r.status in (200, 201):
            print('CQS guide sent')
        else:
            print(f'Error: {await r.text()}')

asyncio.run(main())
