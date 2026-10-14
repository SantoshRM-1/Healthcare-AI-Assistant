"""Import or update directory records from a CSV file."""
import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionFactory, engine
from app.models.hospital import Hospital
from app.schemas.platform import HospitalImportRow


async def import_file(path: Path) -> int:
    rows = 0
    async with SessionFactory() as session:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            required = {"name", "city", "specialization", "address", "phone", "website", "rating"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(f"CSV must include columns: {', '.join(sorted(required))}")
            for raw in reader:
                if not any((value or "").strip() for value in raw.values()):
                    continue
                item = HospitalImportRow.model_validate({key: (value or "").strip() or None for key, value in raw.items()})
                existing = await session.scalar(select(Hospital).where(Hospital.name == item.name, Hospital.city == item.city, Hospital.specialization == item.specialization))
                hospital = existing or Hospital(name=item.name, city=item.city, specialization=item.specialization, address=item.address)
                hospital.address = item.address
                hospital.phone = item.phone
                hospital.website = item.website
                hospital.rating = item.rating
                session.add(hospital)
                rows += 1
        await session.commit()
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    try:
        count = await import_file(args.csv_file)
        print(f"Imported or updated {count} hospital rows")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
