"""Fail-closed gates shared by indexing/retrieval and exercised without infrastructure."""


def source_is_approved(status: str) -> bool:
    return status == "approved"


def document_is_indexable(source_status: str, approval_status: str) -> bool:
    return source_is_approved(source_status) and approval_status == "approved"


def document_is_retrievable(
    source_status: str,
    approval_status: str,
    is_active: bool,
    processing_status: str,
) -> bool:
    return (
        source_is_approved(source_status)
        and approval_status == "approved"
        and is_active
        and processing_status == "indexed"
    )
