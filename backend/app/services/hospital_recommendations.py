from sqlalchemy import and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.hospital import Hospital
from app.models.session_memory import RecommendationRecord
from app.schemas.platform import HospitalRecommendationRequest, HospitalRecommendationResponse, HospitalResult
from app.services.recommendations import DOCTOR_SPECIALTIES
from app.services.session_memory import read_memory
from app.services.vector_store import retrieve_chunks

DISCLAIMER = "Hospital listings are informational. Confirm current services, availability, and suitability directly with the hospital or your clinician. In an emergency, contact local emergency services."
CITY_ALIASES = {"bangalore": "bengaluru", "bengaluru": "bangalore", "mysore": "mysuru", "mysuru": "mysore", "mangalore": "mangaluru", "mangaluru": "mangalore", "hubli": "hubballi", "hubballi": "hubli"}


async def recommend_hospitals(session, user_id, payload: HospitalRecommendationRequest) -> HospitalRecommendationResponse:
    memory = await read_memory(session, payload.session_id, user_id)
    query = payload.condition or " ".join(memory.get("diagnoses", [])) or "diagnosis disease condition symptoms"
    documents = await retrieve_chunks(user_id, payload.session_id, query)
    medical_text = " ".join(d["text"] for d in documents)
    evidence = f"{payload.condition or ''} {' '.join(memory.get('diagnoses', []))} {medical_text}".casefold()
    specialties = [name.replace("_", " ").title() for name, terms in DOCTOR_SPECIALTIES.items() if any(term in evidence for term in terms)]
    if not specialties:
        specialties = ["General Medicine"]

    city_term = CITY_ALIASES.get(payload.city.strip().casefold(), payload.city.strip())
    region_term = payload.region.strip()
    location_term = payload.location.strip()
    city_filter = or_(Hospital.city.ilike(f"%{city_term}%"), Hospital.city.ilike(f"%{payload.city.strip()}%"))
    local_match = or_(Hospital.address.ilike(f"%{region_term}%"), Hospital.address.ilike(f"%{location_term}%"))
    specialty_filters = [Hospital.specialization.ilike("%general%"), Hospital.specialization.ilike("%multi-specialty%")]
    specialty_filters.extend(Hospital.specialization.ilike(f"%{name}%") for name in specialties)
    specialty_filters.extend(Hospital.specialization.ilike(f"%{name.replace('ologist', 'ology')}%") for name in specialties)
    records = await session.scalars(
        select(Hospital)
        .where(and_(city_filter, or_(*specialty_filters)))
        .order_by(case((local_match, 1), else_=0).desc(), Hospital.rating.desc().nullslast(), Hospital.name.asc())
        .limit(settings.hospital_max_results)
    )
    hospitals = []
    for item in records.all():
        hospitals.append(HospitalResult(
            id=item.id, name=item.name, city=item.city, specialization=item.specialization,
            address=item.address, phone=item.phone, website=item.website, rating=item.rating,
            reason=f"Listed for {item.specialization}; location matched {payload.city}, {payload.region}.",
        ))
    session.add(RecommendationRecord(
        user_id=user_id, session_id=payload.session_id, kind="hospital",
        payload={"city": payload.city, "region": payload.region, "location": payload.location,
                 "condition": payload.condition, "specialties": specialties,
                 "hospital_ids": [str(item.id) for item in hospitals]},
    ))
    await session.commit()
    return HospitalRecommendationResponse(hospitals=hospitals, specialties=specialties, disclaimer=DISCLAIMER)
