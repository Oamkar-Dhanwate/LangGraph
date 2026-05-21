import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database.connection import get_db_session
from backend.database.models import Company
from backend.services.graph_service import graph_service
from decimal import Decimal

async def main():
    async with get_db_session() as db:
        print("Testing DB session creation...")
        # Create a new Company model
        company = Company(
            name="Direct Test Co " + str(Decimal("70.00")),
            industry="Testing",
            size_category="smb",
            annual_revenue=Decimal("1234567.89"),
            country="United States",
            website="https://directtest.co",
            account_tier="silver",
            health_score=Decimal("70.00"),
            churn_risk=Decimal("0.10")
        )
        db.add(company)
        await db.flush()
        print("Company flushed, id:", company.id)
        
        # Test upsert_company
        print("Testing upsert_company in graph_service...")
        entity = await graph_service.upsert_company(db, company)
        print("Graph Entity upserted, id:", entity.id)
        
        print("Everything works!")

if __name__ == "__main__":
    asyncio.run(main())
