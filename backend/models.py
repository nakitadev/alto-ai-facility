"""
SQLAlchemy 2.0 Declarative Models corresponding to db/schema.sql.
Provides type-safe, compile-time verified database entities for:
- Machine registry
- Sensor readings (TimescaleDB hypertable)
- AI decision audit log
- Human-in-the-Loop pending actions
- LLM cost & token ledger
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    def to_dict(self) -> Dict[str, Any]:
        """Convenience serializer converting model instance attributes to a dict."""
        res = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, datetime):
                val = val.isoformat()
            res[col.name] = val
        return res

class Machine(Base):
    __tablename__ = "machines"

    machine_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    machine_type: Mapped[str] = mapped_column(String(32), nullable=False)
    zone: Mapped[str] = mapped_column(String(64), nullable=False)
    floor: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    rated_power_kw: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    is_critical_24_7: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    # Relationships
    readings: Mapped[List["SensorReading"]] = relationship(back_populates="machine")
    decisions: Mapped[List["AIDecision"]] = relationship(back_populates="machine")
    pending_actions: Mapped[List["PendingAction"]] = relationship(back_populates="machine")

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        CheckConstraint("status IN ('ON', 'OFF')", name="check_sensor_status"),
        CheckConstraint("power_kw >= 0", name="check_sensor_power_non_negative"),
        Index("idx_sensor_readings_machine_time", "machine_name", "time"),
    )

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    machine_name: Mapped[str] = mapped_column(
        String(32), ForeignKey("machines.machine_name"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    power_kw: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), default=None)
    setpoint: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2), default=None)
    speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), default=None)

    machine: Mapped["Machine"] = relationship(back_populates="readings")

class AIDecision(Base):
    __tablename__ = "ai_decisions"
    __table_args__ = (
        Index("idx_ai_decisions_time_machine", "timestamp", "machine_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    machine_name: Mapped[str] = mapped_column(
        String(32), ForeignKey("machines.machine_name"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    parameter_value: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    machine: Mapped["Machine"] = relationship(back_populates="decisions")

class PendingAction(Base):
    __tablename__ = "pending_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')", 
            name="check_action_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    machine_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("machines.machine_name"), nullable=False
    )
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    parameter_value: Mapped[Optional[str]] = mapped_column(Text, default=None)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    execution_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    machine: Mapped["Machine"] = relationship(back_populates="pending_actions")

class LLMCostLedger(Base):
    __tablename__ = "llm_cost_ledger"
    __table_args__ = (
        Index("idx_llm_cost_conv", "conversation_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), default=Decimal("0.0"), nullable=False
    )
    latency_ms: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    intent_detected: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    tools_called: Mapped[Optional[str]] = mapped_column(Text, default=None)
