# Creating Persona Bots via BotFather

You need to create 5 additional Telegram bots (one per persona) via @BotFather.
Each bot gets its own name, username, and profile photo.

## Steps for each persona:

1. Open Telegram and message @BotFather
2. Send `/newbot`
3. Follow the prompts:

### Bot 1: Tash Murray
- **Name:** Tash Murray
- **Username:** StartSquad_Tash_bot (or similar available name)
- **Profile Photo:** Upload `assets/profile_photos/tash.jpg`
- **Store token as:** `PERSONA_TASH_TOKEN` in `.env`

### Bot 2: Damo Reilly
- **Name:** Damo Reilly
- **Username:** StartSquad_Damo_bot
- **Profile Photo:** Upload `assets/profile_photos/damo.jpg`
- **Store token as:** `PERSONA_DAMO_TOKEN` in `.env`

### Bot 3: Sam Taufa
- **Name:** Sam Taufa
- **Username:** StartSquad_Sam_bot
- **Profile Photo:** Upload `assets/profile_photos/sam.jpg`
- **Store token as:** `PERSONA_SAM_TOKEN` in `.env`

### Bot 4: Jake Henderson
- **Name:** Jake Henderson
- **Username:** StartSquad_Jake_bot
- **Profile Photo:** Upload `assets/profile_photos/jake.jpg`
- **Store token as:** `PERSONA_JAKE_TOKEN` in `.env`

### Bot 5: Mel Kovac
- **Name:** Mel Kovac
- **Username:** StartSquad_Mel_bot
- **Profile Photo:** Upload `assets/profile_photos/mel.jpg`
- **Store token as:** `PERSONA_MEL_TOKEN` in `.env`

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
PERSONA_TASH_TOKEN=<Tash's token>
PERSONA_DAMO_TOKEN=<Damo's token>
PERSONA_SAM_TOKEN=<Sam's token>
PERSONA_JAKE_TOKEN=<Jake's token>
PERSONA_MEL_TOKEN=<Mel's token>
```

Then update Railway environment variables with the same values.
