from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.domain import Incident, SourceType
import uuid


class IncidentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Incident:
        inc = Incident(
            title=data["title"],
            description=data.get("description", ""),
            severity=data.get("severity", "P3"),
            affected_service=data.get("affected_service"),
            root_cause=data.get("root_cause"),
            resolution=data.get("resolution"),
            source_type=SourceType(data.get("source_type", "incident")),
            metadata_=data.get("metadata"),
        )
        self.db.add(inc)
        await self.db.commit()
        await self.db.refresh(inc)
        return inc

    async def list_by_service(self, service: str, limit: int = 20) -> list[Incident]:
        result = await self.db.execute(
            select(Incident).where(Incident.affected_service == service)
            .order_by(Incident.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_cluster(self, cluster_id: str) -> list[Incident]:
        result = await self.db.execute(
            select(Incident).where(Incident.cluster_id == cluster_id)
        )
        return list(result.scalars().all())
