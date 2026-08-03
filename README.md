# TaskBridge Bot (Python) — Complete Production Setup

This is a full rebuild in Python, backed by Turso, deployed on Render, kept
alive with UptimeRobot — replacing the earlier Node.js version entirely.
Follow every phase in order; this assumes zero prior setup.

## What this bot does (and what it doesn't)

**Built and working:**
- Onboarding: Reddit verification (karma + account age → tier), full name +
  WhatsApp + country collected, referral capture — all via one `/verify` form
- Tiers (1/2/3) calculated exactly per the rate card, including the
  "karma qualifies but account too young → stays Tier 1" rule
- Referrals: $1 per referral, but only pays out once the referred person
  completes 1 post **and** 1 comment (shown live in `/profile`)
- A full worst-case task request/submit flow (`/request-post`,
  `/request-comment`, `/submit`) with the exact timers, cooldowns, and daily
  limits from the plan
- Payments: Binance UID / USDT / USDC only, $12 minimum withdrawal, admin
  payout queue with proof-of-payment upload
- Tickets, a basic ad/spam filter, and an approval queue for anything
  Redwire's bot posts
- Admin lookups by location (`/taskers-by-country`)

**Deliberately NOT built yet — depends on confirming with Redwire:**
- Whether Redwire's bot handles task distribution itself (in which case
  `/request-post`, `/request-comment`, `/submit` here may end up unused —
  no harm, they just sit ready as a fallback)
- How your bot would learn a submission was accepted/rejected by Redwire's
  verification system
- The exact 1%–21% verification fee formula
- `REDWIRE_BOT_ID` — once you have it, one line in `.env`, everything else
  (announcement approval queue) is already built and waiting

---

## PHASE 0 — Get these two things onto your computer first

1. **Python** — [python.org/downloads](https://python.org/downloads) → download → install (click through with defaults, and on Windows, tick **"Add Python to PATH"** during install — this matters).
2. **VS Code** — [code.visualstudio.com](https://code.visualstudio.com) → install like any normal program.

Open the unzipped project folder in VS Code: **File → Open Folder** → select `taskbridge-py`.

Open a terminal inside VS Code: **Terminal → New Terminal**. Every command below goes there.

Test Python installed correctly:
```
python3 --version
```
(Windows: try `python --version` if `python3` doesn't work.)

---

## PHASE 1 — Install the bot's building blocks

```
pip install -r requirements.txt
```
(Windows: `pip3 install -r requirements.txt` if that fails.)

---

## PHASE 2 — Create the Discord bot application

1. [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application** → name it.
2. **Bot** tab → **Reset Token** → copy it → this is `DISCORD_BOT_TOKEN` (shown once).
3. On that same **Bot** page, scroll to **Privileged Gateway Intents** → turn ON **Server Members Intent** and **Message Content Intent**. The bot won't work without these — it needs them for role assignment and the moderation filter.
4. **OAuth2 → URL Generator** → Scopes: check `bot` and `applications.commands` → Bot Permissions: check `Administrator` → copy the generated URL.
5. Paste that URL in your browser → pick your server → **Authorize**.

## PHASE 3 — Get your Discord Server ID

1. Discord app → User Settings (gear icon) → Advanced → **Developer Mode** → On.
2. Right-click your server icon → **Copy Server ID** → this is `DISCORD_GUILD_ID`.

## PHASE 4 — Create your Turso database

1. Install the Turso CLI — follow [docs.turso.tech/cli/installation](https://docs.turso.tech/cli/installation) for your OS (it's a couple of copy-paste terminal commands, no coding).
2. In your terminal:
   ```
   turso auth login
   turso db create taskbridge
   turso db show taskbridge --url
   turso db tokens create taskbridge
   ```
3. The first command's output is your `TURSO_DATABASE_URL`. The second is your `TURSO_AUTH_TOKEN`.

## PHASE 5 — Fill in your `.env` file

1. In VS Code, copy `.env.example`, rename the copy to `.env`.
2. Fill in the values from Phases 2-4:
   ```
   DISCORD_BOT_TOKEN=<from Phase 2>
   DISCORD_GUILD_ID=<from Phase 3>
   TURSO_DATABASE_URL=<from Phase 4>
   TURSO_AUTH_TOKEN=<from Phase 4>
   REDWIRE_BOT_ID=
   PORT=8080
   ```

**What to leave blank:** `REDWIRE_BOT_ID` — leave it empty until Redwire confirms their bot's Discord user ID with you. Nothing breaks by leaving it blank; that one feature (auto-queueing their announcements) just stays inactive until you add it. **Don't touch `PORT`** — Render sets that automatically once deployed; the `8080` here is only for testing on your own computer.

## PHASE 6 — Build the server structure (run once, locally)

```
python3 setup.py
```
Wait for `✅ Server setup complete.` — check Discord, you'll see the new roles and channels.

## PHASE 7 — Test it locally before deploying

```
python3 bot.py
```
You should see `Logged in as ...` and `Synced 16 slash commands`. In Discord, try `/verify` on yourself to confirm the whole flow works. Press `Ctrl+C` in the terminal to stop it once you've tested — you're about to move it to Render for real 24/7 hosting.

---

## PHASE 8 — Put the project on GitHub (Render deploys from a Git repo, not a zip)

1. Go to [github.com](https://github.com) → sign up if you don't have an account (free).
2. Click the **+** icon (top right) → **New repository** → name it `taskbridge-bot` → keep it **Private** → **Create repository**.
3. On the next page, click **uploading an existing file**.
4. Drag your entire `taskbridge-py` folder's contents into the browser window (all the `.py` files, `requirements.txt`, `runtime.txt`, `.gitignore` — **do NOT upload your `.env` file**, it has your secrets in it).
5. Scroll down, click **Commit changes**.

## PHASE 9 — Deploy to Render

1. [render.com](https://render.com) → sign up (free) → **New +** → **Web Service**.
2. Connect your GitHub account when prompted → select the `taskbridge-bot` repo.
3. Fill in:
   - **Name**: anything, e.g. `taskbridge-bot`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free
4. Scroll to **Environment Variables** → click **Add Environment Variable** for each of these (copy the exact values from your local `.env` — never upload the `.env` file itself, just re-type the values here):
   ```
   DISCORD_BOT_TOKEN
   DISCORD_GUILD_ID
   TURSO_DATABASE_URL
   TURSO_AUTH_TOKEN
   REDWIRE_BOT_ID   (leave the value blank if you don't have it yet)
   ```
   Do **not** add `PORT` — Render sets it automatically.
5. Click **Create Web Service**. Wait a few minutes for the first deploy — watch the **Logs** tab, you're looking for `Logged in as ...` and `Synced 16 slash commands`.
6. Once it's live, copy the URL Render gives you at the top of the page (something like `https://taskbridge-bot.onrender.com`).

**Known tradeoff with the free tier:** Render's free Web Services sleep after 15 minutes with no incoming traffic. That's exactly what Phase 10 (UptimeRobot) works around — as long as something pings it more often than every 15 minutes, it never sleeps. This is a widely-used approach for small bots, but it's worth knowing it's a workaround, not a guarantee — an occasional restart (e.g. during Render's own maintenance) will briefly disconnect the bot until it reconnects.

## PHASE 10 — Set up UptimeRobot to keep it awake

1. [uptimerobot.com](https://uptimerobot.com) → sign up (free).
2. **+ Add New Monitor**.
3. **Monitor Type**: HTTP(s)
4. **Friendly Name**: anything, e.g. "TaskBridge Bot"
5. **URL**: paste your Render URL from Phase 9, step 6
6. **Monitoring Interval**: 5 minutes (well under Render's 15-minute sleep threshold)
7. **Create Monitor**.

That's it — UptimeRobot will now ping your bot every 5 minutes, keeping it awake continuously.

---

## PHASE 11 — Add a Moderator

This is just Discord's built-in role system, no bot command needed:
1. Server Settings → click the person you want → **Roles** → check **Moderator**.

The Moderator role (created by `setup.py`) already has Kick, Timeout, and Manage Messages permissions built in — real Discord moderation powers, separate from this bot's own Admin-only commands (which stay locked to the **Admin** role specifically).

## PHASE 12 — Add MEE6 (optional, for extra moderation/leveling features)

1. [mee6.xyz](https://mee6.xyz) → **Add to Discord** → pick your server → Authorize.
2. Configure whatever MEE6 features you want from its dashboard (leveling, extra auto-mod, etc.).

No conflict with this bot — separate bot account, separate role, Discord keeps slash commands namespaced per-bot automatically.

---

## Command reference

**Everyone (after `/verify`):**
- `/verify` — onboarding form (Reddit username, country, full name, WhatsApp, optional referrer)
- `/refresh-tier` — re-check your Reddit stats
- `/profile` — tier, balance, cooldowns, referral stats
- `/set-payment-method` — Binance UID / USDT / USDC
- `/withdraw` — request payout (min $12)
- `/request-post`, `/request-comment` — claim a task (fallback system — see note above)
- `/submit` — submit a completed task
- `/ticket` — open a private support ticket

**Admin only:**
- `/withdrawals` — list pending payout requests
- `/mark-paid` — pay a withdrawal, attach proof screenshot
- `/taskers-by-country` — look up taskers by location
- `/set-verification-status` — manually verify/unverify/flag an account
- `/stats` — platform overview
- `/add-task` — add a task to the fallback pool
- `/close-ticket` — close a ticket (run inside it)

## Production readiness checklist

- [ ] `.env` filled in locally, and the **same values** (not the file) added to Render's Environment Variables
- [ ] Server Members Intent + Message Content Intent turned ON in the Discord Developer Portal (Phase 2, step 3) — bot silently breaks without these
- [ ] `setup.py` run once, roles/channels visible in Discord
- [ ] Render deploy logs show "Synced 16 slash commands" with no errors
- [ ] UptimeRobot monitor active and green
- [ ] Tested `/verify` end-to-end yourself before opening it to real taskers
- [ ] Moderator assigned (Phase 11)
- [ ] `REDWIRE_BOT_ID` added once Redwire confirms it (safe to add later — nothing else waits on this)

## Project files

```
bot.py          Entry point — loads cogs, syncs commands, runs the health server
setup.py        One-time server builder (run locally, not on Render)
config.py       Server blueprint — roles & static channels
db.py           All database logic (Turso/libSQL)
tiers.py        Tier calculation (pure, tested)
rates.py        Payout rates, limits, payment methods — single source of truth
limits.py       Cooldown/daily-limit logic (pure, tested)
reddit.py       Reddit verification via public JSON endpoint (pure parsing, tested)
cogs/onboarding.py   /verify, /refresh-tier, referral capture
cogs/tasks.py        /request-post, /request-comment, /submit, /add-task
cogs/payments.py     /profile, /set-payment-method, /withdraw
cogs/tickets.py      /ticket, /close-ticket
cogs/moderation.py   Ad/spam filter, Redwire announcement approval queue
cogs/admin.py        /withdrawals, /mark-paid, /taskers-by-country, /stats
```

## If something doesn't work

- **Slash commands don't appear in Discord** → check Render logs for "Synced 16 slash commands" — if that line's missing, the bot didn't start correctly; check the log above it for the actual error.
- **Role assignment fails** → the bot's own role (created by `setup.py`) needs to sit above Tasker/Tier roles in Server Settings → Roles → drag order.
- **"Privileged intent" error on startup** → go back to Phase 2, step 3, make sure both intent toggles are ON.
- **Bot goes offline randomly** → check your UptimeRobot monitor is actually green/active; if Render's free tier put it to sleep, the next ping wakes it within a minute.
- **Reddit verification always fails** → Reddit occasionally rate-limits the public endpoint this uses; wait a minute and retry. If it's persistent, it's a sign to consider registering a proper Reddit API app instead (see the comment at the top of `reddit.py`).
