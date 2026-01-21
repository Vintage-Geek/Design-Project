import asyncio
from app.database import engine, async_session
from app.models import Customer, Policy
from sqlmodel import SQLModel

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async with async_session() as session:
        c1 = Customer(full_name="John Doe", phone_number="+917373077820")
        session.add(c1)
        await session.commit()
        
        p1 = Policy(policy_number="POL-999", amount_due=250.00, customer_id=c1.id)
        session.add(p1)
        await session.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())