from __future__ import annotations

from textwrap import dedent

from .models import Facet, Persona


PERSONA_GUIDANCE: dict[Persona, str] = {
    Persona.security_assessor: (
        "You are a security assessor who evaluates pipeline evidence with a focus on residual risk, control coverage, "
        "and IL4/IL5 accreditation readiness. Highlight compliance posture, deviations, and mitigation paths."
    ),
    Persona.compliance_officer: (
        "You are a compliance officer aligning software delivery artefacts with regulatory frameworks. "
        "Explain how evidence maps to controls, policies, and authorization requirements."
    ),
    Persona.devops_engineer: (
        "You are a DevOps engineer optimising the build-and-release flow. Emphasise pipeline health, automation, and "
        "actionable fixes that improve velocity without compromising security."
    ),
    Persona.software_developer: (
        "You are a software developer focused on code-level impact and remediation steps. Explain findings with clear "
        "developer guidance and references to affected components."
    ),
}


FACET_DESCRIPTIONS: dict[Facet, str] = {
    Facet.run_manifest: "Analyse the run manifest to explain pipeline execution, policy status, and promotional readiness.",
    Facet.sbom: "Interpret the Software Bill of Materials to surface component risk, licensing, and supply-chain drift.",
    Facet.trivy: "Review the Trivy scan results, prioritising vulnerability severity, fixes, and runtime exposure.",
    Facet.general: "Answer broad questions drawing from design context and the supplied manifests.",
}


def build_system_prompt(
    persona: Persona,
    facet: Facet,
    app_design: str,
    schemas: dict[str, str],
    context: dict[str, str] | None = None,
) -> str:
    """Compose the system prompt combining persona guidance, design context, and active schemas."""
    schema_sections = []
    for name, schema_text in schemas.items():
        schema_sections.append(f"### {name}\n{schema_text.strip()}")
    schema_block = "\n\n".join(schema_sections)
    persona_text = PERSONA_GUIDANCE[persona]
    facet_text = FACET_DESCRIPTIONS[facet]
    context_sections: list[str] = []
    if context:
        for label, value in context.items():
            context_sections.append(f"### {label}\n```json\n{value.strip()}\n```")
    context_block = "\n\n".join(context_sections)

    prompt = dedent(
        f"""
        You are the SWFT Assistant. {persona_text}
        Focus: {facet_text}

        Use the provided schemas and architectural guidance to ground every answer. Always cite specific fields, controls,
        or manifest sections you rely on. If information is missing, state the gap explicitly instead of inventing data.

        ## Architecture Context (from app-design.md)
        {app_design.strip()}

        ## JSON Schemas and Evidence Contracts
        {schema_block}

        ## Evidence Context
        {context_block if context_block else "No additional evidence was provided beyond the schemas."}

        Response requirements:
        - Return Markdown with clear headings, bullet points, and code blocks when relevant.
        - Highlight high-risk issues first and recommend next actions grounded in the evidence.
        - If a question falls outside the provided context, acknowledge the limitation and suggest the nearest relevant artefact.
        """
    ).strip()
    return prompt
