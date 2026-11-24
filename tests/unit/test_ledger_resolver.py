"""
Unit tests for customer name resolution, honorific stripping, and gray-zone handling.
"""

import pytest

from bolkhata.domains.ledger.resolver import CustomerRecord, CustomerResolver


@pytest.fixture
def sample_customers() -> list[CustomerRecord]:
    return [
        CustomerRecord(id="cust_01", name="Ramesh Sharma", phone="9876543210"),
        CustomerRecord(id="cust_02", name="Suresh Verma", phone="9876543211"),
        CustomerRecord(id="cust_03", name="Mahesh Gupta", phone="9876543212"),
    ]


@pytest.mark.asyncio
async def test_resolve_exact_and_honorifics(sample_customers: list[CustomerRecord]) -> None:
    resolver = CustomerResolver(sample_customers)

    # Honorific "ji"
    res1 = await resolver.resolve("Ramesh Sharma ji")
    assert res1.is_resolved is True
    assert res1.resolved_id == "cust_01"

    # Suffix "bhaiya"
    res2 = await resolver.resolve("Suresh Verma bhaiya")
    assert res2.is_resolved is True
    assert res2.resolved_id == "cust_02"

    # Suffix "uncle"
    res3 = await resolver.resolve("Mahesh Gupta uncle")
    assert res3.is_resolved is True
    assert res3.resolved_id == "cust_03"


@pytest.mark.asyncio
async def test_resolve_cross_script_devanagari(sample_customers: list[CustomerRecord]) -> None:
    resolver = CustomerResolver(sample_customers)
    # Stored as "Ramesh Sharma", queried as "रमेश शर्मा जी"
    res = await resolver.resolve("रमेश शर्मा जी")
    assert res.is_resolved is True
    assert res.resolved_id == "cust_01"


@pytest.mark.asyncio
async def test_resolve_gray_zone_ambiguity(sample_customers: list[CustomerRecord]) -> None:
    # Adding two similar customers
    customers = [
        CustomerRecord(id="cust_10", name="Ram Sharma"),
        CustomerRecord(id="cust_11", name="Ramesh Sharma"),
    ]
    resolver = CustomerResolver(customers)

    # Query "Rame Sharma" is equidistant / close between both
    res = await resolver.resolve("Rame Sharma")
    # Must flag ambiguity rather than silently merging
    assert res.is_ambiguous is True
    assert res.is_resolved is False
    assert len(res.candidates) >= 2


@pytest.mark.asyncio
async def test_resolve_unrecognized_new_customer(sample_customers: list[CustomerRecord]) -> None:
    resolver = CustomerResolver(sample_customers)

    # Completely new name
    res = await resolver.resolve("Anjali Devi")
    assert res.is_resolved is False
    assert res.is_ambiguous is False
    assert res.is_new is True
    assert res.resolved_name == "Anjali Devi"


@pytest.mark.asyncio
async def test_never_silently_merge_distinct_customers(
    sample_customers: list[CustomerRecord],
) -> None:
    resolver = CustomerResolver(sample_customers)

    # Query "Suresh" must never resolve to "Ramesh"
    res = await resolver.resolve("Suresh ji")
    assert res.resolved_id != "cust_01"
    assert res.resolved_id == "cust_02"
