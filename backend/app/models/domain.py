import uuid
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Float, Integer, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, UUIDMixin, TimestampMixin


class SourceType(str, enum.Enum):
    GIT = "git"
    PDF = "pdf"
    MARKDOWN = "markdown"
    CONFLUENCE = "confluence"
    JIRA = "jira"
    LOG = "log"
    API_SPEC = "api_spec"
    COMMIT = "commit"
    PR = "pr"
    INCIDENT = "incident"


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType))
    source_path: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|processing|done|failed

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    qdrant_id: Mapped[str | None] = mapped_column(String(100), index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Incident(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # P0-P4
    affected_service: Mapped[str | None] = mapped_column(String(200))
    root_cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType), default=SourceType.INCIDENT)
    cluster_id: Mapped[str | None] = mapped_column(String(100), index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)


class ArchitecturalDecision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "architectural_decisions"

    title: Mapped[str] = mapped_column(String(500))
    context: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    alternatives_considered: Mapped[dict | None] = mapped_column(JSON)
    consequences: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="accepted")
    tags: Mapped[list | None] = mapped_column(JSON)


class KGEntity(Base, UUIDMixin, TimestampMixin):
    """Mirrors Neo4j nodes in PostgreSQL for fast lookup."""
    __tablename__ = "kg_entities"

    neo4j_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    properties: Mapped[dict | None] = mapped_column(JSON)
