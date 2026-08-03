import asyncio, os, aiohttp
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['DISCORD_GUILD_ID']
BASE = 'https://discord.com/api/v10'
HEADERS = {'Authorization': f'Bot {TOKEN}'}

async def main():
    async with aiohttp.ClientSession() as s:
        async with s.get(f'{BASE}/guilds/{GUILD_ID}', headers=HEADERS) as r:
            guild = await r.json()
        print(f"Guild: {guild.get('name')}", flush=True)

        # Use search to find bots
        async with s.get(f'{BASE}/guilds/{GUILD_ID}/members/search?query=&limit=1000', headers=HEADERS) as r:
            if r.status == 200:
                members = await r.json()
            else:
                print(f"Members search failed: {r.status}", flush=True)
                members = []
        
        print(f"\nBots in server:", flush=True)
        for m in members:
            user = m.get('user', {})
            if user.get('bot'):
                print(f"  {user.get('username')} (ID: {user.get('id')})", flush=True)

asyncio.run(main())
