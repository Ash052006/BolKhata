#!/usr/bin/env bash
# ==============================================================================
# BolKhata Deterministic Demo Seed & Reset Script
#
# Wipes local development database and seeds deterministic kirana records
# for the 90-second hackathon live demo flow.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Resetting BolKhata local database..."

cd "${PROJECT_ROOT}/backend"

uv run python - << 'EOF'
import asyncio
import uuid
from datetime import datetime, UTC
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bolkhata.common.base import Base
from bolkhata.config.settings import settings
from bolkhata.domains.ledger.db_models import Customer, LedgerEvent

async def reset_and_seed():
    engine = create_async_engine(settings.database_url, echo=False)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # 1. Truncate existing data
        await session.execute(delete(LedgerEvent))
        await session.execute(delete(Customer))
        await session.commit()

        # 2. Seed realistic Kirana customers
        sharma = Customer(
            id="cust-sharma-001",
            name="Ramesh Sharma",
            normalized_name="ramesh sharma",
            phone="+919876543210",
        )
        verma = Customer(
            id="cust-verma-002",
            name="Suresh Verma",
            normalized_name="suresh verma",
            phone="+919876543211",
        )
        gupta = Customer(
            id="cust-gupta-003",
            name="Sunita Gupta",
            normalized_name="sunita gupta",
            phone="+919876543212",
        )
        session.add_all([sharma, verma, gupta])
        await session.commit()

        # 3. Seed baseline transactions
        # Gupta ji starts with ₹500 previous credit
        e1 = LedgerEvent(
            id=str(uuid.uuid4()),
            customer_id=gupta.id,
            event_type="add_credit_sale",
            amount=500.0,
            currency="INR",
            items=["atta", "tel"],
            quantity=5.0,
            unit="kg",
            date_str="kal",
            notes="Previous day groceries",
            idempotency_key="demo-seed-001",
            is_compensated=False,
            created_at=datetime.now(UTC),
        )
        session.add(e1)
        await session.commit()

    await engine.dispose()
    print("==> Database successfully seeded with 3 customers and 1 baseline event.")

asyncio.run(reset_and_seed())
EOF

echo "==> BolKhata is ready for the 90-second live demonstration!"
