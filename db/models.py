from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, Float,
    DateTime, Date, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    telegram_username = Column(String(64))
    first_name = Column(String(128), nullable=False)
    city = Column(String(128), nullable=False)
    fitness_level = Column(String(20), nullable=False)  # beginner, intermediate, advanced
    goals = Column(Text)
    timezone = Column(String(64), default="Australia/Brisbane")
    onboarding_complete = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team_group = relationship("TeamGroup", back_populates="user", uselist=False)
    calibrations = relationship("UserPersonaCalibration", back_populates="user")
    daily_stats = relationship("DailyStat", back_populates="user")


class TeamGroup(Base):
    __tablename__ = "team_groups"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=False)
    group_title = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="team_group")
    workout_posts = relationship("WorkoutPost", back_populates="team_group")
    reaction_messages = relationship("ReactionMessage", back_populates="team_group")
    scheduled_jobs = relationship("ScheduledJob", back_populates="team_group")


class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True)
    slug = Column(String(32), unique=True, nullable=False)
    display_name = Column(String(64), nullable=False)
    bot_token = Column(String(128), nullable=False)
    bio = Column(Text, nullable=False)
    personality = Column(Text, nullable=False)
    fitness_baseline = Column(JSON, nullable=False)  # {"squats": 35, "pushups": 20, "situps": 30}
    posting_window = Column(JSON, nullable=False)  # {"primary": {"start": 6.5, "end": 8}, ...}
    emoji_style = Column(Text)
    slang_notes = Column(Text)
    motivation_style = Column(String(32))  # cheerleader, competitive, coach, joker, realist
    profile_photo_path = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    calibrations = relationship("UserPersonaCalibration", back_populates="persona")


class UserPersonaCalibration(Base):
    __tablename__ = "user_persona_calibration"
    __table_args__ = (UniqueConstraint("user_id", "persona_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    adjusted_baseline = Column(JSON, nullable=False)  # calibrated to user's level
    variance_factor = Column(Float, default=0.15)

    user = relationship("User", back_populates="calibrations")
    persona = relationship("Persona", back_populates="calibrations")


class WorkoutPost(Base):
    __tablename__ = "workout_posts"

    id = Column(Integer, primary_key=True)
    team_group_id = Column(Integer, ForeignKey("team_groups.id", ondelete="CASCADE"), nullable=False)
    author_type = Column(String(10), nullable=False)  # human, persona
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)
    exercise_type = Column(String(32))  # squats, pushups, situps, mixed, rest_day
    reps = Column(Integer)
    sets = Column(Integer)
    message_text = Column(Text, nullable=False)
    telegram_message_id = Column(BigInteger)
    mood = Column(String(20))  # great, good, ok, tired, struggling
    posted_at = Column(DateTime, default=datetime.utcnow)

    team_group = relationship("TeamGroup", back_populates="workout_posts")


class ReactionMessage(Base):
    __tablename__ = "reaction_messages"

    id = Column(Integer, primary_key=True)
    team_group_id = Column(Integer, ForeignKey("team_groups.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)
    in_reply_to_post_id = Column(Integer, ForeignKey("workout_posts.id"), nullable=True)
    message_text = Column(Text, nullable=False)
    telegram_message_id = Column(BigInteger)
    posted_at = Column(DateTime, default=datetime.utcnow)

    team_group = relationship("TeamGroup", back_populates="reaction_messages")


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True)
    team_group_id = Column(Integer, ForeignKey("team_groups.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)
    job_type = Column(String(32), nullable=False)  # workout_post, morning_reminder, evening_nudge, reaction
    scheduled_for = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="pending")  # pending, executed, failed, skipped
    created_at = Column(DateTime, default=datetime.utcnow)

    team_group = relationship("TeamGroup", back_populates="scheduled_jobs")


class DailyStat(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint("user_id", "stat_date"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stat_date = Column(Date, nullable=False)
    total_squats = Column(Integer, default=0)
    total_pushups = Column(Integer, default=0)
    total_situps = Column(Integer, default=0)
    workout_count = Column(Integer, default=0)
    completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="daily_stats")
