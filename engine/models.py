from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DriftType(str, Enum):
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_RENAMED = "column_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABILITY_CHANGED = "nullability_changed"


class ColumnSchema(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    sample_values: list[str] = Field(default_factory=list)


class TableSchema(BaseModel):
    database: str
    schema_name: str
    table: str
    columns: list[ColumnSchema]
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def fqn(self) -> str:
        return f"{self.database}.{self.schema_name}.{self.table}"


class DriftEvent(BaseModel):
    table_fqn: str
    drift_type: DriftType
    old_column: Optional[str] = None
    new_column: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    confidence: float = 1.0
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class DownstreamAsset(BaseModel):
    asset_id: str
    asset_type: str
    name: str
    revenue_per_hour: float
    column_criticality: dict[str, float] = Field(default_factory=dict)


class RevenueImpact(BaseModel):
    drift_event: DriftEvent
    affected_assets: list[str]
    estimated_dollars_per_hour: float
    confidence_low: float
    confidence_high: float
    minutes_since_detected: float
    estimated_dollars_exposed_so_far: float


class AdapterSuggestion(BaseModel):
    drift_event: DriftEvent
    suggested_sql: str
    mapping_confidence: float
    rationale: str
    requires_human_approval: bool = True
    approved: bool = False
