import asyncio, aiohttp, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']

STAFF_CAT = '1533811509120204812'
EVERYONE_ID = '1533310208695079093'
ADMIN_ID = '1533788208037498942'
MOD_ID = '1533788211489407118'
BOT_ROLE_ID = '1533781443401093123'  # TaskBridge Bot

VIEW = 1024
SEND = 2048

async def main():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}

        # Create #referral-logs under STAFF ONLY
        data = {
            'name': 'referral-logs',
            'type': 0,
            'parent_id': STAFF_CAT,
            'topic': 'Automated referral completion notifications.'
        }
        async with session.post(f'https://discord.com/api/v10/guilds/{GUILD_ID}/channels', headers=headers, json=data) as r:
            if r.status in (200, 201):
                ch = await r.json()
                cid = ch['id']
                print(f'Created #referral-logs (id: {cid})')

                overwrites = [
                    {'id': EVERYONE_ID, 'type': 0, 'allow': 0, 'deny': VIEW},
                    {'id': ADMIN_ID, 'type': 0, 'allow': VIEW | SEND, 'deny': 0},
                    {'id': MOD_ID, 'type': 0, 'allow': VIEW | SEND, 'deny': 0},
                    {'id': BOT_ROLE_ID, 'type': 0, 'allow': VIEW | SEND, 'deny': 0},
                ]
                r2 = await session.patch(f'https://discord.com/api/v10/channels/{cid}', headers=headers, json={'permission_overwrites': overwrites})
                print(f'Permissions: {r2.status}')

asyncio.run(main())
