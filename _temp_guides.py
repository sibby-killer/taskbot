import asyncio, aiohttp, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']

VERIFY_CHANNEL = '1537510572491415592'
TASKS_CHANNEL = '1537510579575459840'
ACCOUNTS_CHANNEL = '1537510587964071967'

async def send_guide(session, headers, channel_id, content):
    msg = {'content': content}
    r = await session.post(f'https://discord.com/api/v10/channels/{channel_id}/messages', headers=headers, json=msg)
    if r.status in (200, 201):
        print(f'Guide sent to {channel_id}')
    else:
        print(f'Error: {await r.text()}')

async def main():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}

        verify_guide = """# 📋 How to Verify

## Commands
**`/verify`** — Submit your Reddit account for verification

## How to Use
1. Take a **screenshot** of your Reddit profile
2. Copy your **Reddit profile link** (e.g., reddit.com/user/yourname)
3. Use `/verify` with:
   - `reddit_username` — Your Reddit username
   - `screenshot` — Upload the screenshot
   - `profile_link` — Paste your profile link

## What Happens Next
- Your request goes to **pending**
- Admin reviews and approves/rejects
- If approved, you get the **Tasker** role and access to tasks
- You'll receive a DM with next steps

## Tips
- Make sure your username matches exactly
- Screenshot should show your karma and account age
- Profile link must be public"""

        tasks_guide = """# 📝 How to Request Tasks

## Commands
**`/request-post`** — Request a Reddit post task ($1.00)
**`/request-comment`** — Request a Reddit comment task ($0.50)
**`/my-tasks`** — View your tasks and earnings
**`/submit-task`** — Submit your completed task

## How to Request
1. Use `/request-post` or `/request-comment`
2. Fill in `title` and `description`
3. Wait for admin to assign

## Timeline
- **30 min** to complete after assignment
- **5 min** warning when admin sends the link
- **2 min** final warning before expiry
- If you fail, task goes to someone else

## Cooldowns
- Posts: **2 hours** between requests
- Comments: **30 minutes** between requests

## Submitting
1. Complete the task on Reddit
2. Use `/submit-task` with the task ID and link
3. Wait for admin approval
4. Get paid!

## Tips
- Only request if you can complete in time
- Check your tasks with `/my-tasks`
- You can only have **1 pending task** at a time"""

        accounts_guide = """# 🔑 How to Request Accounts

## Commands
**`/request-account`** — Request a Reddit account
**`/submit-review`** — Submit a review for a purchased account

## How to Request
1. Use `/request-account`
2. Fill in `account_type` (e.g., aged, high-karma)
3. Fill in `details` (age, karma, niche needed)
4. Wait for admin to fulfill

## What You Get
- Reddit username and password
- Instructions for first login
- Link to warming guide

## Account Warming
After receiving your account:
1. **Day 0-1:** Just browse, join subreddits
2. **Day 2-3:** Light upvoting
3. **Day 4-5:** First comments
4. **Day 6-7:** More comments
5. **Day 8-10:** First posts
6. **Day 11+:** Normal use

Full guide in <#1537510584046846004>

## Tips
- Change password immediately
- Don't use VPN/proxy
- Follow warming schedule strictly
- Check CQS at r/WhatIsMyCQS"""

        await send_guide(session, headers, VERIFY_CHANNEL, verify_guide)
        await asyncio.sleep(1)
        await send_guide(session, headers, TASKS_CHANNEL, tasks_guide)
        await asyncio.sleep(1)
        await send_guide(session, headers, ACCOUNTS_CHANNEL, accounts_guide)

asyncio.run(main())
