from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from services.scan_management.app.db_models.scan import Scan, ScanAssessment

class ScanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, scan_id: str) -> Optional[Scan]:
        stmt = select(Scan).where(Scan.id == scan_id)
        result = await self.session.execute(stmt)
        scan = result.scalar_one_or_none()
        if scan:
            saved = await self.session.get(ScanAssessment, scan.id)
            scan.saved_assessment = saved.assessment if saved else {}
        return scan

    async def list_by_user(self, user_id: Optional[str] = None, offset: int = 0, limit: int = 20) -> Tuple[List[Scan], int]:
        # Count total
        count_stmt = select(func.count(Scan.id))
        if user_id:
            count_stmt = count_stmt.where(Scan.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one()

        # Query items
        stmt = select(Scan)
        if user_id:
            stmt = stmt.where(Scan.user_id == user_id)
        stmt = stmt.order_by(Scan.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        scans = list(result.scalars().all())
        if scans:
            saved = await self.session.execute(select(ScanAssessment).where(ScanAssessment.scan_id.in_([s.id for s in scans])))
            by_id = {s.scan_id: s.assessment for s in saved.scalars()}
            for scan in scans:
                scan.saved_assessment = by_id.get(scan.id, {})
        return scans, total

    async def create(self, scan: Scan) -> Scan:
        self.session.add(scan)
        await self.session.flush()
        await self.session.refresh(scan)
        return scan

    async def update_status(self, scan_id: str, status: str) -> Optional[Scan]:
        scan = await self.get_by_id(scan_id)
        if scan:
            scan.status = status
            await self.session.flush()
            await self.session.refresh(scan)
        return scan
