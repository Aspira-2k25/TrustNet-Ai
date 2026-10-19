"""Explicit live inspection of a saved, owner-scoped message link."""
from datetime import datetime, timezone
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from services.scan_management.app.config.settings import settings
from services.scan_management.app.database.session import get_db
from services.scan_management.app.db_models.scan import LinkInspection
from services.scan_management.app.routers.scan_router import get_current_user_id
from services.scan_management.app.services.scan_service import ScanService
from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.schemas.detection_result import DetectionResult
from shared.schemas.url_inspection import inspection_summary
from shared.utils.ids import generate_request_id

router = APIRouter(prefix='/scans', tags=['Link inspections'])


class InspectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


@router.post('/{scan_id}/links/{link_index}/inspection')
async def inspect_link(scan_id: str, request: InspectionRequest, link_index: int = Path(ge=0, le=7),
                       user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    service = ScanService(db)
    scan = await service.get_scan(scan_id, user_id)
    links = (scan.result or {}).get('metadata', {}).get('links', [])
    if scan.content_type != 'text' or (scan.result or {}).get('module') != 'scam_message' or link_index >= len(links):
        raise HTTPException(404, 'No supported saved message link at this position')
    url = links[link_index]['url']
    if not isinstance(url, str) or not 1 <= len(url) <= 2048:
        raise HTTPException(422, 'This saved link cannot be inspected')
    if not url.lower().startswith(('http://', 'https://', 'www.')):
        raise HTTPException(422, 'Only web URLs can be inspected. Email addresses and non-web links cannot be inspected as websites.')
    now = datetime.now(timezone.utc)
    key = (scan_id, link_index)
    row = await db.get(LinkInspection, key)
    if row and row.status == 'COMPLETED':
        return APIResponse(data=scan, meta=ResponseMeta(request_id=generate_request_id()))
    if row:
        age = (now - row.updated_at.replace(tzinfo=timezone.utc)).total_seconds()
        if row.status == 'PROCESSING' and age < 90:
            raise HTTPException(409, 'Inspection is already running. Refresh this saved scan shortly.')
        claim = await db.execute(update(LinkInspection).where(LinkInspection.scan_id == scan_id,
            LinkInspection.link_index == link_index, LinkInspection.updated_at == row.updated_at,
            LinkInspection.status == row.status).values(status='PROCESSING', updated_at=now))
        if claim.rowcount != 1:
            raise HTTPException(409, 'Inspection is already running')
    else:
        db.add(LinkInspection(scan_id=scan_id, link_index=link_index, status='PROCESSING', updated_at=now, assessment={}))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, 'Inspection is already running')
    inspection_id = str(uuid.uuid4())
    data = {'url': url, 'requested_at': now.isoformat()}
    state = 'UNAVAILABLE'
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(35, connect=3), trust_env=False) as client:
            response = await client.post(settings.PHISHING_SERVICE_URL.rstrip('/') + '/inspect',
                                         json={'scan_id': inspection_id, 'url': url})
            response.raise_for_status()
            result = DetectionResult.model_validate(response.json()['data'])
        if result.scan_id != inspection_id or result.module.value != 'phishing':
            raise ValueError('Mismatched inspection response')
        data['summary'] = inspection_summary(result)
        data['result'] = result.model_dump(mode='json')
        state = 'COMPLETED' if result.status.value in ('SUCCESS', 'PARTIAL_SUCCESS') and data['summary']['live_checks_observed'] > 0 else 'UNAVAILABLE'
        if state == 'UNAVAILABLE':
            data['reason'] = 'Live website checks were unavailable. The saved quick assessment remains available.'
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        data['reason'] = 'The inspection service is unavailable, busy, timed out or returned an invalid response. Retry later.'
    await db.execute(update(LinkInspection).where(LinkInspection.scan_id == scan_id,
        LinkInspection.link_index == link_index, LinkInspection.updated_at == now,
        LinkInspection.status == 'PROCESSING').values(status=state, assessment=data, updated_at=datetime.now(timezone.utc)))
    await db.commit()
    # Reload the original record with its separate inspection snapshot attached.
    db.expire_all()
    return APIResponse(data=await service.get_scan(scan_id, user_id), meta=ResponseMeta(request_id=generate_request_id()))
