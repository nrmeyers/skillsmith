"""Compose endpoint router — real handler wired to ComposeOrchestrator."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from skillsmith.api.compose_models import (
    ComposedResult,
    ComposeRequest,
    EmptyResult,
    ErrorResponse,
)
from skillsmith.orchestration.compose import ComposeOrchestrator

router = APIRouter()


# Dependency provider — overridden in tests via app.dependency_overrides[].
def get_orchestrator() -> ComposeOrchestrator:
    raise RuntimeError("get_orchestrator must be bound during app lifespan; no default available")


@router.post(
    "/compose",
    response_model=ComposedResult | EmptyResult,
    responses={
        503: {"model": ErrorResponse, "description": "Retrieval or assembly stage failure"},
    },
    summary="Compose task-specific guidance",
    description=(
        "Returns assembled guidance from active domain fragments plus applicable "
        "system-skill fragments. System-skill inclusion is stubbed in M1 and lands "
        "with NXS-771/NXS-772 in M2."
    ),
)
async def compose(
    req: ComposeRequest,
    orchestrator: ComposeOrchestrator = Depends(get_orchestrator),
) -> ComposedResult | EmptyResult:
    return await orchestrator.compose(req)


@router.post(
    "/compose/text",
    response_class=PlainTextResponse,
    summary="Compose task-specific guidance as plain text",
    description="Returns only the assembled skill text — no JSON wrapper. Intended for agent curl calls.",
)
async def compose_text(
    req: ComposeRequest,
    orchestrator: ComposeOrchestrator = Depends(get_orchestrator),
) -> PlainTextResponse:
    result = await orchestrator.compose(req)
    return PlainTextResponse(content=result.output)


class FromContractRequest(BaseModel):
    contract_path: str


@router.post(
    "/compose/from-contract",
    response_model=ComposedResult | EmptyResult,
    responses={
        400: {"model": ErrorResponse, "description": "Contract malformed or invalid"},
        503: {"model": ErrorResponse, "description": "Retrieval or assembly stage failure"},
    },
    summary="Compose using a contract file",
    description=(
        "Reads phase and domain_tags from a contract file, uses the contract body "
        "as the task description, and runs the standard compose pipeline."
    ),
)
async def compose_from_contract(
    req: FromContractRequest,
    orchestrator: ComposeOrchestrator = Depends(get_orchestrator),
) -> ComposedResult | EmptyResult:
    from skillsmith.contracts import ContractMalformed, parse_contract, validate_contract

    path = Path(req.contract_path)
    try:
        contract = parse_contract(path)
    except ContractMalformed as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "contract_malformed", "issues": [str(exc)]},
        ) from exc

    issues = validate_contract(contract, path.parent.parent.parent)
    if issues:
        raise HTTPException(
            status_code=400,
            detail={"error": "contract_invalid", "issues": issues},
        )

    compose_req = ComposeRequest(
        task=contract.body or contract.task_slug,
        phase=contract.phase,  # type: ignore[arg-type]
        contract_tags=contract.domain_tags,
        contract_path=req.contract_path,
    )
    return await orchestrator.compose(compose_req)
