from django.db import transaction
from .models import ClientDocItem, DocCategory

@transaction.atomic
def carry_forward_annual_docs(from_fy: str, to_fy: str):
    """
    Copy ANNUAL checklist items from from_fy to to_fy for categories that are continuing.
    """
    items = ClientDocItem.objects.select_related("category").filter(doc_kind="ANNUAL", financial_year=from_fy)

    created = 0
    for it in items:
        # only if category continues (repeat till stopped/closed)
        if not it.category.continue_till_closed and it.category.name.lower() != "others":
            continue

        exists = ClientDocItem.objects.filter(
            client=it.client, category=it.category, subtype=it.subtype,
            doc_kind="ANNUAL", financial_year=to_fy
        ).exists()

        if not exists:
            ClientDocItem.objects.create(
                client=it.client,
                category=it.category,
                subtype=it.subtype,
                doc_kind="ANNUAL",
                financial_year=to_fy,
                status="PENDING",
                remarks="(Auto carried forward)"
            )
            created += 1

    return created
