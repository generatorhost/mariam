from pydantic import BaseModel


class Term(BaseModel):
    name: str
    definition: str
    forbidden_aliases: list[str] = []


OFFICIAL_TERMS = [
    Term(
        name="Mariam Living Enterprise OS Core",
        definition="The official name for the core runtime that coordinates learning, expansion, DNA import/export, runtime objects, governance, and evolution.",
        forbidden_aliases=["AI Kernel", "Kernel only"],
    ),
    Term(
        name="Mariam Data Platform",
        definition="The official data layer covering runtime, knowledge, audit, governance, mission, CRM, scraping, opportunity, communication, document, DNA, capability, workflow, vector, object, cache, logs, metrics, and artifacts stores.",
        forbidden_aliases=["Business DB", "Business Database"],
    ),
    Term(
        name="Runtime Object",
        definition="An object that can be added, edited, deleted, disabled, enabled, upgraded, replaced, forked, rolled back, imported from DNA, and exported as DNA.",
    ),
    Term(
        name="DNA Managed Runtime Object",
        definition="A runtime object governed by DNA identity, versioning, compatibility, audit, tests, import, export, and rollback.",
    ),
    Term(
        name="Plugin Business Unit",
        definition="A plugin or app managed as an independent business unit with dashboard, settings, Chief Agent, swarm, data boundary, workflows, tests, and delivery gates.",
        forbidden_aliases=["simple plugin", "small add-on"],
    ),
    Term(
        name="Provider",
        definition="A registered model, service, platform, tool, or runtime provider governed through provider lifecycle rules.",
        forbidden_aliases=["hardcoded provider"],
    ),
    Term(
        name="Connector",
        definition="A governed bridge to an external system, platform, API, account, webhook, or data source.",
    ),
    Term(
        name="MCP Server",
        definition="A managed integration runtime exposed through the Model Context Protocol boundary.",
    ),
    Term(
        name="Chief Agent",
        definition="The accountable lead agent for a plugin, department, mission, platform, or capability.",
    ),
    Term(
        name="Swarm",
        definition="A coordinated group of agents with declared roles, permissions, events, tests, and acceptance criteria.",
    ),
    Term(
        name="Mission",
        definition="A governed unit of work with traceability, runtime state, events, artifacts, approvals, and rollback.",
    ),
    Term(
        name="Artifact",
        definition="A generated or imported file, report, document, model, export, dataset, or evidence package managed by Mariam.",
    ),
    Term(
        name="Governance Gate",
        definition="A permission, audit, approval, quality, compatibility, or security checkpoint before side effects or delivery.",
    ),
]


def list_official_terms() -> list[Term]:
    return OFFICIAL_TERMS


def forbidden_aliases() -> set[str]:
    aliases: set[str] = set()
    for term in OFFICIAL_TERMS:
        aliases.update(term.forbidden_aliases)
    return aliases

