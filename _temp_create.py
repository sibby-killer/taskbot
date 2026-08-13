import asyncio, aiohttp, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']

WELCOME_CAT = '1533810521059491840'
COMMUNITY_CAT = '1533811503596306543'
STAFF_CAT = '1533811509120204812'

EVERYONE_ID = '1533310208695079093'
ADMIN_ID = '1533788208037498942'
MOD_ID = '1533788211489407118'
TASKER_ID = '1533788214849175613'
BOT_ROLE_ID = '1533781443401093123'

VIEW = 1024
SEND = 2048

async def create_channel(session, headers, name, parent_id, topic, everyone_allow, everyone_deny=0):
    data = {'name': name, 'type': 0, 'parent_id': parent_id, 'topic': topic}
    async with session.post(f'https://discord.com/api/v10/guilds/{GUILD_ID}/channels', headers=headers, json=data) as r:
        if r.status in (200, 201):
            ch = await r.json()
            cid = ch['id']
            overwrites = [
                {'id': EVERYONE_ID, 'type': 0, 'allow': everyone_allow, 'deny': everyone_deny},
                {'id': ADMIN_ID, 'type': 0, 'allow': VIEW | SEND, 'deny': 0},
                {'id': BOT_ROLE_ID, 'type': 0, 'allow': VIEW | SEND, 'deny': 0},
            ]
            await session.patch(f'https://discord.com/api/v10/channels/{cid}', headers=headers, json={'permission_overwrites': overwrites})
            print(f'Created #{name} (id: {cid})')
            return cid
        else:
            err = await r.text()
            print(f'Error creating {name}: {r.status} {err}')
            return None

async def main():
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {TOKEN}', 'Content-Type': 'application/json'}

        # #verify - users submit verification, view+send for everyone
        await create_channel(session, headers, 'verify', WELCOME_CAT,
            'Submit your Reddit verification here. Include screenshot + profile link.',
            VIEW | SEND)

        # #tasks - users request tasks, view+send for taskers
        await create_channel(session, headers, 'tasks', COMMUNITY_CAT,
            'Request tasks here. Warning: 30min countdown to complete after assignment.',
            VIEW | SEND)

        # #account-guide - warming guide + CQS info, view only
        await create_channel(session, headers, 'account-guide', COMMUNITY_CAT,
            'Account warming guide and CQS information.',
            VIEW)

        # #purchase-accounts - request purchased accounts, view+send for taskers
        await create_channel(session, headers, 'purchase-accounts', COMMUNITY_CAT,
            'Request Reddit accounts here. Include what you need.',
            VIEW | SEND)

asyncio.run(main())
