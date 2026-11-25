from sqlalchemy import and_, case, or_, select

from app.core.config import settings
from app.models.hospital import Hospital
from app.models.message import Message, MessageRole
from app.models.session_memory import RecommendationRecord
from app.schemas.platform import (
    HospitalRecommendationRequest,
    HospitalRecommendationResponse,
    HospitalResult,
)
from app.services.recommendations import (
    derive_specialties,
    recommendation_documents,
)
from app.services.session_memory import read_memory
from app.services.vector_store import make_citations

DISCLAIMER = "Hospital listings are informational. Confirm current services, availability, and suitability directly with the hospital or your clinician. In an emergency, contact local emergency services."
CITY_ALIASES = {"bangalore": "bengaluru", "bengaluru": "bangalore", "mysore": "mysuru", "mysuru": "mysore", "mangalore": "mangaluru", "mangaluru": "mangalore", "hubli": "hubballi", "hubballi": "hubli"}


async def recommend_hospitals(session, user_id, payload: HospitalRecommendationRequest) -> HospitalRecommendationResponse:
    search_city = payload.city.strip().casefold() != "not-provided"
    memory = await read_memory(session, payload.session_id, user_id)
    recent_turns = await session.scalars(
        select(Message.content)
        .where(Message.session_id == payload.session_id, Message.role == MessageRole.USER)
        .order_by(Message.created_at.desc())
        .limit(8)
    )
    recent_patient_context = " ".join(reversed(recent_turns.all()))[-3_000:]
    query = f"{payload.condition or ''} {recent_patient_context}\ndiagnosis impression assessment laboratory findings symptoms"
    documents = await recommendation_documents(session, user_id, payload.session_id, query)
    medical_text = " ".join(d["text"] for d in documents)
    patient_context = " ".join(filter(None, [payload.condition, recent_patient_context, memory.get("reported_symptoms")]))
    specialties, _reasons = derive_specialties(patient_context, medical_text)
    if not specialties:
        if search_city:
            session.add(RecommendationRecord(
                user_id=user_id,
                session_id=payload.session_id,
                kind="hospital",
                payload={"city": payload.city, "region": payload.region, "location": payload.location, "postal_code": payload.postal_code,
                         "condition": payload.condition, "specialties": [], "hospital_ids": []},
            ))
            await session.commit()
        return HospitalRecommendationResponse(hospitals=[], specialties=[], sources=make_citations(documents), disclaimer=DISCLAIMER)

    city_term = CITY_ALIASES.get(payload.city.strip().casefold(), payload.city.strip())
    region_term = (payload.region or "").strip()
    location_term = (payload.location or "").strip()
    city_filter = or_(Hospital.city.ilike(f"%{city_term}%"), Hospital.city.ilike(f"%{payload.city.strip()}%"))
    postal_code = (payload.postal_code or "").strip()
    local_terms = [term for term in (region_term, location_term, postal_code) if term]
    local_match = or_(*(Hospital.address.ilike(f"%{term}%") for term in local_terms)) if local_terms else Hospital.id.is_not(None)
    specialty_filters = [Hospital.specialization.ilike("%general%"), Hospital.specialization.ilike("%multi-specialty%")]
    for name in specialties:
        normalized = name.casefold()
        aliases = {name, name.replace("ologist", "ology")}
        if normalized == "urologist":
            aliases.update({"urology", "urologic", "urinary"})
        elif normalized == "nephrologist":
            aliases.update({"nephrology", "renal"})
        specialty_filters.extend(Hospital.specialization.ilike(f"%{alias}%") for alias in aliases if alias)
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
            reason=f"Directory listing for {item.specialization} in {item.city}.",
        ))
    if search_city:
        session.add(RecommendationRecord(
            user_id=user_id, session_id=payload.session_id, kind="hospital",
            payload={"city": payload.city, "region": payload.region, "location": payload.location, "postal_code": payload.postal_code,
                     "condition": payload.condition, "specialties": specialties,
                     "hospital_ids": [str(item.id) for item in hospitals]},
        ))
        await session.commit()
    return HospitalRecommendationResponse(hospitals=hospitals, specialties=specialties, sources=make_citations(documents), disclaimer=DISCLAIMER)
