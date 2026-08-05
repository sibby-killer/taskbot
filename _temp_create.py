import asyncio, aiohttp, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']

WELCOME_CAT = '1533810521059491840'
EVERYONE_ID = '1533310208695079093'
ADMIN_ID = '1533788208037498942'
MOD_ID = '1533788211489407118'

VIEW = 1024
SEND = 2048
ATTACH = 8192  # attach_files permission

async def main():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}

        # Create #payment-proof channel
        data = {
            'name': 'payment-proof',
            'type': 0,
            'parent_id': WELCOME_CAT,
            'topic': 'Post payment proof here — images with description.'
        }
        async with session.post(f'https://discord.com/api/v10/guilds/{GUILD_ID}/channels', headers=headers, json=data) as r:
            if r.status in (200, 201):
                ch = await r.json()
                cid = ch['id']
                print(f'Created #payment-proof (id: {cid})')

                # Everyone can view, admin can send text+images, members can only send images
                overwrites = [
                    {'id': EVERYONE_ID, 'type': 0, 'allow': VIEW, 'deny': SEND},  # view only, no text
                    {'id': ADMIN_ID, 'type': 0, 'allow': VIEW | SEND | ATTACH, 'deny': 0},  # full access
                    {'id': MOD_ID, 'type': 0, 'allow': VIEW | SEND | ATTACH, 'deny': 0},
                ]
                r2 = await session.patch(f'https://discord.com/api/v10/channels/{cid}', headers=headers, json={'permission_overwrites': overwrites})
                print(f'Permissions: {r2.status}')
            else:
                err = await r.text()
                print(f'Error: {r.status} {err}')

asyncio.run(main())
