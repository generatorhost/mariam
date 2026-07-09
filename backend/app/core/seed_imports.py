from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class SeedImportRequest(BaseModel):
    source_path: str = Field(default=r"C:\1\mayou-1001", min_length=3)
    actor_id: str = Field(default="seed-import-chief", min_length=2)
    reason: str = Field(default="Import living seed DNA into Mariam.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class SeedDomainEvidence(BaseModel):
    domain: str
    runtime_readiness: str
    total_matching_assets: int
    total_matching_terms: int
    top_source_projects: list[dict]
    top_source_categories: list[dict]


class SeedPluginCandidate(BaseModel):
    plugin_id: str
    name: str
    status: str = "candidate"
    source_domains: list[str]
    feature_summary: list[str]
    evidence_assets: int
    evidence_terms: int
    runtime_readiness: str
    data_boundary: str
    private_table_prefix: str
    governance_gate: str = "seed_review_before_activation"
    traceability: dict = Field(default_factory=dict)


class SeedDNAObject(BaseModel):
    object_key: str
    object_type: str
    name: str
    status: str = "extracted"
    source_domains: list[str]
    evidence_assets: int
    evidence_terms: int
    runtime_target: str
    governance_gate: str = "seed_dna_review_before_runtime_activation"
    traceability: dict = Field(default_factory=dict)


class ExternalSeedSource(BaseModel):
    source_key: str
    name: str
    source_type: str
    url: str
    status: str = "available"
    target_plugins: list[str]
    extracted_dna_domains: list[str]
    integration_notes: list[str]
    security_notes: list[str]
    traceability: dict = Field(default_factory=dict)


class SeedImportRecord(BaseModel):
    source_id: str
    source_path: str
    source_name: str
    status: str
    imported_at: datetime
    data_platform: str = "DB MARIAM"
    coverage: dict = Field(default_factory=dict)
    registry_files: list[str] = Field(default_factory=list)
    domain_evidence: list[SeedDomainEvidence] = Field(default_factory=list)
    dna_objects: list[SeedDNAObject] = Field(default_factory=list)
    dna_object_counts: dict[str, int] = Field(default_factory=dict)
    plugin_candidates: list[SeedPluginCandidate] = Field(default_factory=list)
    loaded_runtime_object_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SeedImportListResponse(BaseModel):
    imports: list[SeedImportRecord]


class ExternalSeedSourceListResponse(BaseModel):
    external_sources: list[ExternalSeedSource]


class SeedImportResponse(BaseModel):
    seed_import: SeedImportRecord


class SeedPluginCandidateListResponse(BaseModel):
    source_id: str
    plugin_candidates: list[SeedPluginCandidate]


class SeedPluginPromotionRequest(BaseModel):
    actor_id: str = Field(default="seed-import-chief", min_length=2)
    reason: str = Field(default="Promote seed plugin candidate into disabled Mariam plugin.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class SeedPluginPromotionResponse(BaseModel):
    source_id: str
    plugin_id: str
    status: str
    data_platform: str = "DB MARIAM"
    promotion_notes: list[str]


class SeedRuntimeLoadRequest(BaseModel):
    actor_id: str = Field(default="seed-runtime-chief", min_length=2)
    reason: str = Field(default="Load extracted seed DNA into DB MARIAM runtime store.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class SeedRuntimeLoadResponse(BaseModel):
    source_id: str
    status: str
    data_platform: str = "DB MARIAM"
    loaded_runtime_object_ids: list[str]
    loaded_counts: dict[str, int]
    runtime_store: str = "runtime_objects"
    notes: list[str]


def create_seed_import_record(
    source_path: str,
    source_name: str,
    coverage: dict,
    registry_files: list[str],
    domain_evidence: list[SeedDomainEvidence],
    dna_objects: list[SeedDNAObject],
    plugin_candidates: list[SeedPluginCandidate],
    warnings: list[str],
) -> SeedImportRecord:
    counts: dict[str, int] = {}
    for dna_object in dna_objects:
        counts[dna_object.object_type] = counts.get(dna_object.object_type, 0) + 1
    return SeedImportRecord(
        source_id=f"seed-{uuid4()}",
        source_path=source_path,
        source_name=source_name,
        status="inspected",
        imported_at=datetime.now(UTC),
        coverage=coverage,
        registry_files=registry_files,
        domain_evidence=domain_evidence,
        dna_objects=dna_objects,
        dna_object_counts=counts,
        plugin_candidates=plugin_candidates,
        warnings=warnings,
    )
