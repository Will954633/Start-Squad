# Creating Persona Bots via BotFather

You need to create 5 additional Telegram bots (one per persona) via @BotFather.
Each bot gets its own name, username, and profile photo.

## Steps for each persona:

1. Open Telegram and message @BotFather
2. Send `/newbot`
3. Follow the prompts:

### Bot 1: Mia Chen
- **Name:** Mia Chen
- **Username:** StartSquad_Mia_bot (or similar available name)
- **Profile Photo:** Upload `assets/profile_photos/mia.jpg`
- **Store token as:** `PERSONA_MIA_TOKEN` in `.env`

### Bot 2: Damo Torres
- **Name:** Damo Torres
- **Username:** StartSquad_Damo_bot
- **Profile Photo:** Upload `assets/profile_photos/damo.jpg`
- **Store token as:** `PERSONA_DAMO_TOKEN` in `.env`

### Bot 3: Priya Sharma
- **Name:** Priya Sharma
- **Username:** StartSquad_Priya_bot
- **Profile Photo:** Upload `assets/profile_photos/priya.jpg`
- **Store token as:** `PERSONA_PRIYA_TOKEN` in `.env`

### Bot 4: Jake Nguyen
- **Name:** Jake Nguyen
- **Username:** StartSquad_Jake_bot
- **Profile Photo:** Upload `assets/profile_photos/jake.jpg`
- **Store token as:** `PERSONA_JAKE_TOKEN` in `.env`

### Bot 5: Lena Volkova
- **Name:** Lena Volkova
- **Username:** StartSquad_Lena_bot
- **Profile Photo:** Upload `assets/profile_photos/lena.jpg`
- **Store token as:** `PERSONA_LENA_TOKEN` in `.env`

## Setting Profile Photos

After creating each bot:
1. Message @BotFather
2. Send `/setuserpic`
3. Select the bot
4. Upload the profile photo

## Disabling Bot "Join Groups" Permission

For the persona bots, you'll want to enable group mode:
1. Message @BotFather
2. Send `/setjoingroups`
3. Select each persona bot
4. Choose "Enable"

## Setting Bot Descriptions

For each persona bot:
1. `/setdescription` → Select bot → "I'm part of the Start Squad fitness team!"
2. `/setabouttext` → Select bot → Use the persona's one-liner

## After Creating All Bots

Update your `.env` file with all 6 tokens:
```
TELEGRAM_BOT_TOKEN=<main StartSquad_bot token>
PERSONA_MIA_TOKEN=<Mia's token>
PERSONA_DAMO_TOKEN=<Damo's token>
PERSONA_PRIYA_TOKEN=<Priya's token>
PERSONA_JAKE_TOKEN=<Jake's token>
PERSONA_LENA_TOKEN=<Lena's token>
```

Then update Railway environment variables with the same values.
