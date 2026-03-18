"""
Onboarding ConversationHandler.
Flow: /start → name → city → fitness level → goals →
      exercise walkthrough (squats → pushups → situps) →
      confirm → group creation → persona intros
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from config import Config
from logger import log
from db.connection import async_session
from db.queries.users import get_user_by_telegram_id, create_user, mark_onboarding_complete
from db.queries.personas import get_all_personas, set_calibration
from db.models import TeamGroup
from personas.calibration import calculate_adjusted_baseline
from personas.definitions import PERSONAS

# Conversation states
(NAME, CITY, FITNESS_LEVEL, GOALS,
 EXERCISE_SQUATS, EXERCISE_SQUATS_HELP,
 EXERCISE_PUSHUPS, EXERCISE_PUSHUPS_HELP,
 EXERCISE_SITUPS, EXERCISE_SITUPS_HELP,
 CONFIRM) = range(11)

# Common Australian cities
CITIES = [
    "Gold Coast", "Brisbane", "Sydney", "Melbourne",
    "Perth", "Adelaide", "Hobart", "Canberra",
]

# ──────────────────────────────────────────────
# Exercise descriptions
# ──────────────────────────────────────────────

SQUATS_INTRO = (
    "Now let's walk through the 3 exercises your squad does every day.\n\n"
    "1️⃣  SQUATS\n\n"
    "Stand with feet shoulder-width apart. Bend your knees and lower your hips "
    "like you're sitting into a chair. Go as low as comfortable, then push back "
    "up through your heels. Keep your chest up and your weight on your heels.\n\n"
    "That's it — simple and effective."
)

PUSHUPS_INTRO = (
    "2️⃣  PUSH-UPS\n\n"
    "There are two options — pick whichever suits you right now. "
    "You can always level up later.\n\n"
    "FROM KNEES (easier):\n"
    "Hands shoulder-width on the floor, knees on the ground, ankles crossed. "
    "Lower your chest to the floor, then push back up. Keep your back straight "
    "— no sagging hips.\n\n"
    "FROM TOES (standard):\n"
    "Same as above but on your toes instead of knees. Body forms a straight "
    "line from head to heels. Lower until your chest nearly touches the floor.\n\n"
    "Which will you start with?"
)

SITUPS_INTRO = (
    "3️⃣  SIT-UPS / CRUNCHES\n\n"
    "Again, two options — pick what works for you.\n\n"
    "CRUNCHES (easier):\n"
    "Lie on your back, knees bent, feet flat on the floor. Hands across your "
    "chest or behind your head. Lift just your shoulders off the ground, squeeze "
    "your abs, then lower back down. Small controlled movement.\n\n"
    "FULL SIT-UPS:\n"
    "Same starting position but come all the way up until your chest meets your "
    "knees. Slower is harder — don't use momentum.\n\n"
    "Which will you start with?"
)


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command — begin onboarding."""
    async with async_session() as session:
        existing = await get_user_by_telegram_id(session, update.effective_user.id)
        if existing and existing.onboarding_complete:
            await update.message.reply_text(
                f"Welcome back, {existing.first_name}! You're already set up. "
                "Use /workout to log your exercises or /stats to see your progress."
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "Hey! Welcome to Start Squad 💪\n\n"
        "I'm about to set you up with a fitness team that will train "
        "alongside you every single day.\n\n"
        "Let's get to know you first. What's your name?"
    )
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name, ask for city."""
    context.user_data["name"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton(city, callback_data=f"city_{city}")]
        for city in CITIES
    ]
    keyboard.append([InlineKeyboardButton("Other", callback_data="city_other")])

    await update.message.reply_text(
        f"Nice to meet you, {context.user_data['name']}! Where are you based?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CITY


async def receive_city_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    city = query.data.replace("city_", "")
    if city == "other":
        await query.edit_message_text("No worries! Just type your city:")
        return CITY
    context.user_data["city"] = city
    return await _ask_fitness_level(query.message, context)


async def receive_city_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["city"] = update.message.text.strip()
    return await _ask_fitness_level(update.message, context)


async def _ask_fitness_level(message, context) -> int:
    keyboard = [
        [InlineKeyboardButton("Beginner (just starting)", callback_data="level_beginner")],
        [InlineKeyboardButton("Intermediate (somewhat active)", callback_data="level_intermediate")],
        [InlineKeyboardButton("Advanced (regular training)", callback_data="level_advanced")],
    ]
    await message.reply_text(
        "How would you describe your current fitness level?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return FITNESS_LEVEL


async def receive_fitness_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    level = query.data.replace("level_", "")
    context.user_data["fitness_level"] = level
    await query.edit_message_text(
        "What's your main fitness goal?\n"
        "(e.g., get stronger, lose weight, build a habit, feel better)"
    )
    return GOALS


async def receive_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store goals, begin exercise walkthrough."""
    context.user_data["goals"] = update.message.text.strip()

    await update.message.reply_text(SQUATS_INTRO)
    await update.message.reply_text(
        "Ready to move on, or need more detail on squats?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Got it, next!", callback_data="squats_ok")],
            [InlineKeyboardButton("Tell me more", callback_data="squats_help")],
        ]),
    )
    return EXERCISE_SQUATS


# ──── SQUATS ────

async def squats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "squats_help":
        await query.edit_message_text("Getting more detail on squats...")
        return await _squats_help(query.message, context)

    # squats_ok — move to pushups
    context.user_data["squat_variant"] = "standard"
    await query.edit_message_text("Squats ✅")
    await query.message.reply_text(
        PUSHUPS_INTRO,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("From knees", callback_data="pushups_knees")],
            [InlineKeyboardButton("From toes", callback_data="pushups_toes")],
            [InlineKeyboardButton("Tell me more", callback_data="pushups_help")],
        ]),
    )
    return EXERCISE_PUSHUPS


async def _squats_help(message, context) -> int:
    """Provide LLM-powered extra detail on squats."""
    from llm.client import generate_message

    help_text = await generate_message(
        system_prompt=(
            "You are a friendly fitness coach helping a beginner learn squats. "
            "Keep it short (under 400 chars), practical, encouraging. "
            "No hashtags, no emojis overload. Talk like a real person."
        ),
        user_prompt=(
            "The user wants more detail on how to do bodyweight squats properly. "
            "Cover: foot placement, depth, common mistakes (knees caving in, "
            "leaning too far forward, heels lifting). Keep it simple and encouraging."
        ),
        max_tokens=200,
        temperature=0.7,
    )

    if not help_text:
        help_text = (
            "A few extra tips:\n\n"
            "• Point your toes slightly outward (about 30 degrees)\n"
            "• Push your knees out over your toes — don't let them cave inward\n"
            "• Only go as low as you can while keeping your heels on the ground\n"
            "• If you're wobbly, try squatting to a chair first\n"
            "• Speed: 2 seconds down, 1 second up"
        )

    await message.reply_text(help_text)
    await message.reply_text(
        "Ready to move on to push-ups?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yep, let's go!", callback_data="squats_done")],
        ]),
    )
    return EXERCISE_SQUATS_HELP


async def squats_help_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["squat_variant"] = "standard"
    await query.edit_message_text("Squats ✅")
    await query.message.reply_text(
        PUSHUPS_INTRO,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("From knees", callback_data="pushups_knees")],
            [InlineKeyboardButton("From toes", callback_data="pushups_toes")],
            [InlineKeyboardButton("Tell me more", callback_data="pushups_help")],
        ]),
    )
    return EXERCISE_PUSHUPS


# ──── PUSHUPS ────

async def pushups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "pushups_help":
        await query.edit_message_text("Getting more detail on push-ups...")
        return await _pushups_help(query.message, context)

    # Store choice
    variant = "knees" if query.data == "pushups_knees" else "toes"
    context.user_data["pushup_variant"] = variant
    label = "from knees" if variant == "knees" else "from toes"
    await query.edit_message_text(f"Push-ups ({label}) ✅")

    # Move to situps
    await query.message.reply_text(
        SITUPS_INTRO,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Crunches", callback_data="situps_crunches")],
            [InlineKeyboardButton("Full sit-ups", callback_data="situps_full")],
            [InlineKeyboardButton("Tell me more", callback_data="situps_help")],
        ]),
    )
    return EXERCISE_SITUPS


async def _pushups_help(message, context) -> int:
    from llm.client import generate_message

    help_text = await generate_message(
        system_prompt=(
            "You are a friendly fitness coach helping someone learn push-ups. "
            "Keep it short (under 400 chars), practical, encouraging. "
            "Talk like a real person, not a textbook."
        ),
        user_prompt=(
            "The user wants more detail on push-ups. Cover both from-knees and "
            "from-toes variations. Common mistakes: hips sagging, elbows flaring "
            "out too wide, not going low enough. Explain when to graduate from "
            "knees to toes. Keep it simple."
        ),
        max_tokens=200,
        temperature=0.7,
    )

    if not help_text:
        help_text = (
            "A few extra tips:\n\n"
            "• Keep your elbows at about 45 degrees from your body (not flared out)\n"
            "• Lower until your chest is a fist-width from the floor\n"
            "• Keep your core tight — imagine a straight line from head to knees/heels\n"
            "• From knees is not 'easier' — it's a progression. No shame.\n"
            "• When you can do 15+ from knees comfortably, try toes"
        )

    await message.reply_text(help_text)
    await message.reply_text(
        "Which will you start with?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("From knees", callback_data="pushups_knees_after_help")],
            [InlineKeyboardButton("From toes", callback_data="pushups_toes_after_help")],
        ]),
    )
    return EXERCISE_PUSHUPS_HELP


async def pushups_help_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    variant = "knees" if "knees" in query.data else "toes"
    context.user_data["pushup_variant"] = variant
    label = "from knees" if variant == "knees" else "from toes"
    await query.edit_message_text(f"Push-ups ({label}) ✅")

    await query.message.reply_text(
        SITUPS_INTRO,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Crunches", callback_data="situps_crunches")],
            [InlineKeyboardButton("Full sit-ups", callback_data="situps_full")],
            [InlineKeyboardButton("Tell me more", callback_data="situps_help")],
        ]),
    )
    return EXERCISE_SITUPS


# ──── SITUPS ────

async def situps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "situps_help":
        await query.edit_message_text("Getting more detail on sit-ups/crunches...")
        return await _situps_help(query.message, context)

    variant = "crunches" if query.data == "situps_crunches" else "full_situps"
    context.user_data["situp_variant"] = variant
    label = "Crunches" if variant == "crunches" else "Full sit-ups"
    await query.edit_message_text(f"{label} ✅")

    # Show summary and confirm
    return await _show_confirmation(query.message, context)


async def _situps_help(message, context) -> int:
    from llm.client import generate_message

    help_text = await generate_message(
        system_prompt=(
            "You are a friendly fitness coach helping someone learn sit-ups and crunches. "
            "Keep it short (under 400 chars), practical, encouraging. "
            "Talk like a real person."
        ),
        user_prompt=(
            "The user wants more detail on crunches vs full sit-ups. Cover: "
            "hand placement (behind head vs across chest), breathing (exhale on the "
            "way up), not pulling on your neck, engaging your core not your hip flexors. "
            "When to move from crunches to full sit-ups."
        ),
        max_tokens=200,
        temperature=0.7,
    )

    if not help_text:
        help_text = (
            "A few extra tips:\n\n"
            "• Breathe out as you come up, in as you lower\n"
            "• If hands behind head — don't pull on your neck. Elbows wide.\n"
            "• Crunches: just lift your shoulder blades off the ground. Small movement.\n"
            "• Full sit-ups: come all the way up. Go slow — momentum is cheating.\n"
            "• When 20 crunches feel easy, try full sit-ups"
        )

    await message.reply_text(help_text)
    await message.reply_text(
        "Which will you start with?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Crunches", callback_data="situps_crunches_after_help")],
            [InlineKeyboardButton("Full sit-ups", callback_data="situps_full_after_help")],
        ]),
    )
    return EXERCISE_SITUPS_HELP


async def situps_help_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    variant = "crunches" if "crunches" in query.data else "full_situps"
    context.user_data["situp_variant"] = variant
    label = "Crunches" if variant == "crunches" else "Full sit-ups"
    await query.edit_message_text(f"{label} ✅")

    return await _show_confirmation(query.message, context)


# ──── CONFIRM ────

async def _show_confirmation(message, context) -> int:
    data = context.user_data
    pushup_label = "from knees" if data.get("pushup_variant") == "knees" else "from toes"
    situp_label = "Crunches" if data.get("situp_variant") == "crunches" else "Full sit-ups"

    await message.reply_text(
        f"Here's your setup, {data['name']}:\n\n"
        f"📍 {data['city']}\n"
        f"💪 {data['fitness_level'].title()}\n"
        f"🎯 {data['goals']}\n\n"
        f"Your daily exercises:\n"
        f"  🦵 Squats\n"
        f"  💪 Push-ups ({pushup_label})\n"
        f"  🫡 {situp_label}\n\n"
        "Your squad is ready to meet you!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Let's go!", callback_data="confirm_yes")],
            [InlineKeyboardButton("Start over", callback_data="confirm_no")],
        ]),
    )
    return CONFIRM


async def confirm_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create user, group, and trigger persona introductions."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("No worries! Let's start over. What's your name?")
        return NAME

    data = context.user_data
    city = data["city"]

    # Step 1: "Assigning you to a team..."
    await query.edit_message_text(f"Finding you a {city} team... 🔍")
    await asyncio.sleep(2)

    await query.message.reply_text(
        f"Great news — we've found a {city} squad with a spot for you! 🎉\n\n"
        "Setting up your team now..."
    )
    await asyncio.sleep(1.5)

    tg_user = update.effective_user

    async with async_session() as session:
        # Create user
        user = await create_user(
            session,
            telegram_id=tg_user.id,
            first_name=data["name"],
            city=city,
            fitness_level=data["fitness_level"],
            goals=data["goals"],
            telegram_username=tg_user.username,
            pushup_variant=data.get("pushup_variant", "toes"),
            situp_variant=data.get("situp_variant", "full_situps"),
        )

        # Calibrate personas to user's fitness level
        personas = await get_all_personas(session)
        if not personas:
            await _seed_personas(session)
            personas = await get_all_personas(session)

        for persona in personas:
            adjusted = calculate_adjusted_baseline(
                persona.slug, persona.fitness_baseline, data["fitness_level"]
            )
            await set_calibration(session, user.id, persona.id, adjusted)

        await mark_onboarding_complete(session, user.id)

    # Step 2: Introduce the team roster
    # TODO: Send profile photos once we have them (bot.send_photo)
    roster = (
        f"Meet your {city} squad:\n\n"
        "👩 Tash Murray — Graphic designer, Burleigh Heads\n"
        "     Your biggest cheerleader. Morning workout warrior.\n\n"
        "👷 Damo Reilly — Electrician, Nerang\n"
        "     Competitive but fair. Up before the sparrows.\n\n"
        "🧑‍⚕️ Sam Taufa — Physio student, Southport\n"
        "     Your squad coach. Form tips and recovery advice.\n\n"
        "🏄 Jake Henderson — Barista, Palm Beach\n"
        "     The funny one. New to fitness like you.\n\n"
        "👩‍👧 Mel Kovac — Accountant & mum, Robina\n"
        "     Tells it like it is. Squeezes workouts into nap time."
    )
    await query.message.reply_text(roster)
    await asyncio.sleep(1)

    # Step 3: How it works
    pushup_label = "from knees" if data.get("pushup_variant") == "knees" else "from toes"
    situp_label = "crunches" if data.get("situp_variant") == "crunches" else "sit-ups"

    await query.message.reply_text(
        f"Here's how it works, {data['name']}:\n\n"
        f"• Every day, do squats, push-ups ({pushup_label}), and {situp_label}\n"
        "• Your team posts their workouts too — you're not alone\n"
        "• Log yours with /workout (e.g. /workout squats 30)\n"
        "• Check your day with /today\n"
        "• Chat with your coach with /coach\n\n"
        "Your team members will start saying hi shortly.\n"
        "Welcome to Start Squad! 💪"
    )

    # Step 4: Schedule natural persona introductions
    asyncio.create_task(_send_persona_intros(
        update.effective_chat.id, data["name"], city
    ))

    return ConversationHandler.END


async def _send_persona_intros(chat_id: int, human_name: str, city: str):
    """
    Send staggered introduction messages from each persona.
    First one within 5 min, second ~15 min, rest spread naturally.
    Randomised order each time so it feels different per user.
    """
    import random
    from bot.app import get_persona_bot

    intros = {
        "tash": f"YESSS new squad member!! Welcome {human_name}! I'm Tash, I do my squats on the balcony watching the sunrise at Burleigh. Literally so pumped to have you here! 🔥✨",
        "damo": f"Welcome aboard mate. I'm Damo. Sparky from Nerang. Fair warning — I like a bit of friendly competition 💪",
        "sam": f"Hey {human_name}! I'm Sam. Physio student at Griffith. If you ever need form tips or have any aches, I'm your guy uso 💚",
        "jake": f"yooo {human_name}! jake here. barista at burleigh. don't worry i'm also terrible at this. we suffer together 😂💀",
        "mel": f"Welcome {human_name}. I'm Mel. Robina mum life — I squeeze workouts in during nap time so if I go quiet, the toddler won. Glad you're here ☕💪",
    }

    # Randomise the order each time
    slugs = list(intros.keys())
    random.shuffle(slugs)

    # First person: 2-5 minutes
    # Second person: 10-20 minutes
    # Third person: 30-60 minutes
    # Fourth person: 1-3 hours
    # Fifth person: 2-6 hours
    delay_ranges = [
        (120, 300),       # 2-5 min
        (600, 1200),      # 10-20 min
        (1800, 3600),     # 30-60 min
        (3600, 10800),    # 1-3 hours
        (7200, 21600),    # 2-6 hours
    ]

    for i, slug in enumerate(slugs):
        min_delay, max_delay = delay_ranges[i]
        delay = random.randint(min_delay, max_delay)
        log.info(f"[{slug}] Will introduce in {delay}s ({delay // 60} min)")
        await asyncio.sleep(delay)
        bot = get_persona_bot(slug)
        if bot:
            try:
                await bot.send_message(chat_id=chat_id, text=intros[slug])
                log.info(f"[{slug}] Sent intro to chat {chat_id}")
            except Exception as e:
                log.error(f"[{slug}] Failed to send intro: {e}")


async def _seed_personas(session):
    """Seed persona records into database."""
    from db.models import Persona
    for p_data in PERSONAS:
        persona = Persona(
            slug=p_data["slug"],
            display_name=p_data["display_name"],
            bot_token=Config.PERSONA_TOKENS.get(p_data["slug"], ""),
            bio=p_data["bio"],
            personality=p_data["personality"],
            fitness_baseline=p_data["fitness_baseline"],
            posting_window=p_data["posting_window"],
            emoji_style=p_data["emoji_style"],
            slang_notes=p_data["slang_notes"],
            motivation_style=p_data["motivation_style"],
            profile_photo_path=p_data["profile_photo_path"],
        )
        session.add(persona)
    await session.commit()
    log.info("Seeded 5 personas into database")


def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the onboarding conversation."""
    return ConversationHandler.END


def get_onboarding_handler() -> ConversationHandler:
    """Build and return the onboarding ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            CITY: [
                CallbackQueryHandler(receive_city_button, pattern="^city_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_city_text),
            ],
            FITNESS_LEVEL: [
                CallbackQueryHandler(receive_fitness_level, pattern="^level_"),
            ],
            GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_goals)],
            EXERCISE_SQUATS: [
                CallbackQueryHandler(squats_callback, pattern="^squats_"),
            ],
            EXERCISE_SQUATS_HELP: [
                CallbackQueryHandler(squats_help_done, pattern="^squats_done"),
            ],
            EXERCISE_PUSHUPS: [
                CallbackQueryHandler(pushups_callback, pattern="^pushups_"),
            ],
            EXERCISE_PUSHUPS_HELP: [
                CallbackQueryHandler(pushups_help_done, pattern="^pushups_"),
            ],
            EXERCISE_SITUPS: [
                CallbackQueryHandler(situps_callback, pattern="^situps_"),
            ],
            EXERCISE_SITUPS_HELP: [
                CallbackQueryHandler(situps_help_done, pattern="^situps_"),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_and_create, pattern="^confirm_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
