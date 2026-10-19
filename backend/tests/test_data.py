import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.db.seed import seed, stable_id
from app.models.entities import (
    Account,
    Base,
    Customer,
    Policy,
    Tenant,
    Ticket,
    Transaction,
    User,
)
from app.services.tenants import find_account

EXPECTED = {
    "tenants": 2,
    "users": 6,
    "customers": 20,
    "accounts": 20,
    "tickets": 30,
    "transactions": 40,
    "policies": 10,
}


def snapshot(session):
    return {
        model.__tablename__: [
            tuple(str(v) for v in row)
            for row in session.execute(select(model.__table__).order_by(model.id)).all()
        ]
        for model in (Tenant, User, Customer, Account, Ticket, Transaction, Policy)
    }


def test_migration_upgrade(engine):
    assert set(EXPECTED).issubset(inspect(engine).get_table_names())
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []


def test_seed_counts(session):
    assert seed(session) == EXPECTED
    for model in (Tenant, User, Customer, Account, Ticket, Transaction, Policy):
        assert (
            session.scalar(select(func.count()).select_from(model))
            == EXPECTED[model.__tablename__]
        )


def test_seed_idempotent(session):
    seed(session)
    before = snapshot(session)
    seed(session)
    assert snapshot(session) == before


def test_seed_deterministic_after_rebuild(session):
    seed(session)
    before = snapshot(session)
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    seed(session)
    assert snapshot(session) == before


def test_seed_preserves_existing_changes(session):
    seed(session)
    account = session.get(Account, stable_id("0/account/0"))
    account.evidence_version = 2
    session.flush()
    seed(session)
    assert account.evidence_version == 2


def test_relationships(session):
    seed(session)
    account = session.get(Account, stable_id("0/account/0"))
    assert account.customer.tenant_id == account.tenant_id
    assert len(account.customer.accounts) == 1
    assert len(account.transactions) == 2
    assert len(account.tickets) == 2


@pytest.mark.parametrize(
    "model,values",
    [
        (
            Account,
            {
                "customer_id": stable_id("1/customer/0"),
                "status": "active",
                "evidence_version": 1,
            },
        ),
        (
            Ticket,
            {
                "account_id": stable_id("1/account/0"),
                "subject": "invalid",
                "body": "synthetic",
                "status": "open",
            },
        ),
        (
            Transaction,
            {
                "account_id": stable_id("1/account/0"),
                "reference": "SYNTHETIC-INVALID",
                "amount_minor": 1,
                "currency": "USD",
                "status": "paid",
            },
        ),
        (
            Ticket,
            {
                "account_id": stable_id("0/account/0"),
                "subject": "invalid duplicate",
                "body": "synthetic",
                "status": "open",
                "duplicate_of_id": stable_id("1/ticket/0"),
            },
        ),
    ],
)
def test_cross_tenant_relationship_rejected(session, model, values):
    seed(session)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(model(tenant_id=stable_id("tenant/0"), **values))
        session.flush()


def test_tenant_scoped_lookup(session):
    seed(session)
    assert find_account(
        session, tenant_id=stable_id("tenant/0"), account_id=stable_id("0/account/0")
    )
    assert (
        find_account(
            session,
            tenant_id=stable_id("tenant/1"),
            account_id=stable_id("0/account/0"),
        )
        is None
    )


@pytest.mark.parametrize("tenant", [0, 1])
def test_scenario_fixtures(session, tenant):
    seed(session)

    def account(i):
        return session.get(Account, stable_id(f"{tenant}/account/{i}"))

    assert account(0).block_reason == "unpaid_invoice"
    assert any(t.status == "unpaid" for t in account(0).transactions)
    assert account(1).block_reason == "security_review"
    duplicate = session.get(Ticket, stable_id(f"{tenant}/ticket/12"))
    assert duplicate.duplicate_of_id == stable_id(f"{tenant}/ticket/2")
    assert duplicate.account_id == stable_id(f"{tenant}/account/2")
    assert all(t.status == "paid" for t in account(3).transactions)
    assert {t.status for t in account(4).transactions} == {"paid", "unpaid"}
    attempt = session.get(Ticket, stable_id(f"{tenant}/ticket/5"))
    assert str(stable_id(f"{1 - tenant}/account/0")) in attempt.body
    assert attempt.tenant_id == stable_id(f"tenant/{tenant}")
    assert (
        session.scalar(
            select(func.count())
            .select_from(Policy)
            .where(Policy.tenant_id == attempt.tenant_id, Policy.key == "reactivation")
        )
        == 2
    )


def test_synthetic_identity_data(session):
    seed(session)
    for model in (User, Customer):
        assert all(
            row.email.endswith("@example.com") for row in session.scalars(select(model))
        )
    assert all(
        row.reference.startswith("SYNTHETIC-")
        for row in session.scalars(select(Transaction))
    )
