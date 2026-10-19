import re

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import aliased

from app.models.entities import Account, Customer, Policy, Ticket, Transaction
from app.tools.context import ReadScope
from app.tools.contracts import (
    AccountInput,
    AccountOutput,
    CustomerInput,
    CustomerOutput,
    CustomerTicketsInput,
    PoliciesOutput,
    PolicyInput,
    PolicyMatch,
    TicketInput,
    TicketOutput,
    TicketsOutput,
    TransactionsInput,
    TransactionsOutput,
    TransactionSummary,
)
from app.tools.errors import ToolError
from app.tools.registry import ToolDefinition, ToolRegistry


def required(scope: ReadScope, model, resource_id):
    scope.check_cancelled()
    row = scope.repository.get(model, resource_id)
    if row is None:
        raise ToolError("not_found")
    return row


def get_customer(args: CustomerInput, scope: ReadScope) -> CustomerOutput:
    row = required(scope, Customer, args.customer_id)
    return CustomerOutput(customer_id=row.id, name=row.name, updated_at=row.updated_at)


def get_account_status(args: AccountInput, scope: ReadScope) -> AccountOutput:
    row = required(scope, Account, args.account_id)
    return AccountOutput(
        account_id=row.id,
        customer_id=row.customer_id,
        status=row.status,
        block_reason=row.block_reason,
        evidence_version=row.evidence_version,
        updated_at=row.updated_at,
    )


def ticket_summary(row: Ticket, scope: ReadScope) -> TicketOutput:
    account = required(scope, Account, row.account_id)
    categories = {
        "unpaid_invoice": "billing",
        "security_review": "security",
        "resolved_billing": "reactivation",
        "conflicting_evidence": "evidence_conflict",
    }
    category = (
        "duplicate"
        if row.duplicate_of_id or "Duplicate" in row.subject
        else categories.get(account.block_reason, "service")
    )
    return TicketOutput(
        ticket_id=row.id,
        account_id=row.account_id,
        status=row.status,
        category=category,
        summary=(row.subject + " — " + row.body)[:400],
        duplicate_of_id=row.duplicate_of_id,
        updated_at=row.updated_at,
    )


def get_ticket(args: TicketInput, scope: ReadScope) -> TicketOutput:
    return ticket_summary(required(scope, Ticket, args.ticket_id), scope)


def list_customer_tickets(
    args: CustomerTicketsInput, scope: ReadScope
) -> TicketsOutput:
    required(scope, Customer, args.customer_id)
    tenant = scope.context.tenant_id
    rows = scope.repository.session.scalars(
        select(Ticket)
        .join(
            Account,
            (Account.id == Ticket.account_id) & (Account.tenant_id == Ticket.tenant_id),
        )
        .where(
            Ticket.tenant_id == tenant,
            Account.tenant_id == tenant,
            Account.customer_id == args.customer_id,
        )
        .order_by(Ticket.created_at.desc(), Ticket.id.asc())
        .limit(args.limit)
    ).all()
    return TicketsOutput(
        customer_id=args.customer_id,
        items=[ticket_summary(row, scope) for row in rows],
        limit=args.limit,
    )


def list_recent_transactions(
    args: TransactionsInput, scope: ReadScope
) -> TransactionsOutput:
    required(scope, Account, args.account_id)
    rows = scope.repository.session.scalars(
        select(Transaction)
        .where(
            Transaction.tenant_id == scope.context.tenant_id,
            Transaction.account_id == args.account_id,
        )
        .order_by(Transaction.created_at.desc(), Transaction.id.asc())
        .limit(args.limit)
    ).all()
    return TransactionsOutput(
        account_id=args.account_id,
        items=[
            TransactionSummary(
                transaction_id=row.id,
                updated_at=row.updated_at,
                amount_minor=row.amount_minor,
                currency=row.currency,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ],
        limit=args.limit,
    )


def search_policy(args: PolicyInput, scope: ReadScope) -> PoliciesOutput:
    scope.check_cancelled()
    terms = sorted(set(re.findall(r"[a-z0-9]{2,32}", args.query.lower())))[:8]
    conditions = [
        or_(Policy.key.ilike(f"%{term}%"), Policy.description.ilike(f"%{term}%"))
        for term in terms
    ]
    if not conditions:
        return PoliciesOutput(items=[], limit=args.limit)
    score = sum(case((condition, 1), else_=0) for condition in conditions).label(
        "relevance"
    )
    key_score = sum(case((Policy.key.ilike(f"%{term}%"), 1), else_=0) for term in terms)
    newer = aliased(Policy)
    now = func.current_timestamp()
    effective = (Policy.effective_at <= now) & or_(
        Policy.expires_at.is_(None), Policy.expires_at > now
    )
    superseded = exists(
        select(newer.id).where(
            newer.tenant_id == Policy.tenant_id,
            newer.key == Policy.key,
            newer.version > Policy.version,
            newer.effective_at <= now,
            or_(newer.expires_at.is_(None), newer.expires_at > now),
        )
    )
    rows = scope.repository.session.execute(
        select(Policy, score)
        .where(
            Policy.tenant_id == scope.context.tenant_id,
            effective,
            ~superseded,
            or_(*conditions),
        )
        .order_by(
            key_score.desc(), score.desc(), Policy.version.desc(), Policy.id.asc()
        )
        .limit(args.limit)
    ).all()
    return PoliciesOutput(
        items=[
            PolicyMatch(
                policy_id=row.Policy.id,
                version=row.Policy.version,
                title=row.Policy.key.replace("_", " ").title(),
                summary=row.Policy.description[:400],
                relevance=row.relevance,
                key=row.Policy.key,
                category=row.Policy.category,
                resource_type=row.Policy.resource_type,
                effective_at=row.Policy.effective_at,
                expires_at=row.Policy.expires_at,
                updated_at=row.Policy.updated_at,
                account_states=row.Policy.account_states,
                scenarios=row.Policy.scenarios,
                policy_status="current",
            )
            for row in rows
        ],
        limit=args.limit,
    )


def build_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                "get_customer",
                "1.0",
                "Read minimal synthetic customer identity",
                CustomerInput,
                CustomerOutput,
                "customer:read",
                "read",
                2.0,
                16384,
                get_customer,
            ),
            ToolDefinition(
                "get_account_status",
                "1.0",
                "Read account status and evidence version",
                AccountInput,
                AccountOutput,
                "account:read",
                "read",
                2.0,
                16384,
                get_account_status,
            ),
            ToolDefinition(
                "get_ticket",
                "1.0",
                "Read a bounded untrusted ticket summary",
                TicketInput,
                TicketOutput,
                "ticket:read",
                "read",
                2.0,
                16384,
                get_ticket,
            ),
            ToolDefinition(
                "list_customer_tickets",
                "1.0",
                "List a customer's tickets in stable order",
                CustomerTicketsInput,
                TicketsOutput,
                "ticket:read",
                "read",
                2.0,
                32768,
                list_customer_tickets,
            ),
            ToolDefinition(
                "list_recent_transactions",
                "1.0",
                "List synthetic summaries without financial references",
                TransactionsInput,
                TransactionsOutput,
                "account:read",
                "read",
                2.0,
                16384,
                list_recent_transactions,
            ),
            ToolDefinition(
                "search_policy",
                "1.0",
                "Deterministic tenant policy keyword evidence search",
                PolicyInput,
                PoliciesOutput,
                "account:read",
                "read",
                2.0,
                32768,
                search_policy,
            ),
        ]
    )
