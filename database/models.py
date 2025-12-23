"""
Database models for AI Yoga Bot
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model - stores user information and preferences"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Onboarding data
    goals = Column(JSON)  # User's yoga goals
    experience_level = Column(String(50))  # beginner, intermediate, advanced
    health_conditions = Column(JSON)  # Any health limitations
    preferred_time = Column(String(10))  # Preferred practice time
    available_duration = Column(Integer)  # Available time in minutes
    
    # User state
    current_state = Column(String(100), default='start')
    current_module_id = Column(Integer, ForeignKey('modules.id'))
    
    # Settings
    language = Column(String(5), default='uk')
    notifications_enabled = Column(Boolean, default=True)
    reminder_time = Column(String(10))
    reminder_frequency = Column(String(50), default='daily')
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    practices = relationship("Practice", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    current_module = relationship("Module", foreign_keys=[current_module_id])
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name={self.first_name})>"


class Module(Base):
    """Module model - represents learning modules"""
    __tablename__ = 'modules'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    level = Column(String(50))  # beginner, intermediate, advanced
    order = Column(Integer)  # Module sequence
    
    # Module content metadata
    topics = Column(JSON)  # List of topics covered
    duration_weeks = Column(Integer)  # Estimated duration
    
    # Requirements
    prerequisites = Column(JSON)  # Required previous modules
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Module(name={self.name}, level={self.level})>"


class Practice(Base):
    """Practice model - stores user practice sessions"""
    __tablename__ = 'practices'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module_id = Column(Integer, ForeignKey('modules.id'))
    
    # Practice details
    practice_type = Column(String(100))  # asana, pranayama, meditation, etc.
    duration = Column(Integer)  # Duration in minutes
    difficulty = Column(String(50))
    
    # AI-generated content
    practice_content = Column(JSON)  # AI-generated practice instructions
    personalization_notes = Column(Text)  # AI personalization reasoning
    
    # User feedback
    completed = Column(Boolean, default=False)
    rating = Column(Integer)  # 1-5 stars
    feedback = Column(Text)
    challenges = Column(JSON)  # What was difficult
    
    # Metadata
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="practices")
    module = relationship("Module")
    
    def __repr__(self):
        return f"<Practice(user_id={self.user_id}, type={self.practice_type}, completed={self.completed})>"


class UserProgress(Base):
    """UserProgress model - tracks user progress through modules"""
    __tablename__ = 'user_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module_id = Column(Integer, ForeignKey('modules.id'), nullable=False)
    
    # Progress tracking
    status = Column(String(50), default='not_started')  # not_started, in_progress, completed
    progress_percentage = Column(Float, default=0.0)
    
    # Statistics
    practices_completed = Column(Integer, default=0)
    total_practice_time = Column(Integer, default=0)  # Total minutes
    average_rating = Column(Float)
    
    # Adaptation data
    adaptation_level = Column(String(50))  # How practices are adapted
    strengths = Column(JSON)  # User's strengths
    areas_to_improve = Column(JSON)  # Areas needing focus
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_practice_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="progress")
    module = relationship("Module")
    
    def __repr__(self):
        return f"<UserProgress(user_id={self.user_id}, module_id={self.module_id}, status={self.status})>"
