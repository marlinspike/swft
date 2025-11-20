from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class AzurePolicySet:
    id: str
    label: str
    filename: str
    default_scope: str
    description: str


BUILTIN_POLICY_SETS: tuple[AzurePolicySet, ...] = (
    AzurePolicySet(
        id="nist-sp-800-53-r5",
        label="NIST SP 800-53 Rev 5",
        filename="NIST_SP_800-53_R5.json",
        default_scope="gov",
        description="Microsoft-authored mapping for NIST 800-53 Rev 5 controls.",
    ),
    AzurePolicySet(
        id="fedramp-high",
        label="FedRAMP High",
        filename="FedRAMP_High.json",
        default_scope="gov",
        description="Baseline initiative aligning Azure resources with FedRAMP High requirements.",
    ),
    AzurePolicySet(
        id="fedramp-moderate",
        label="FedRAMP Moderate",
        filename="FedRAMP_Moderate.json",
        default_scope="gov",
        description="Policy set for FedRAMP Moderate controls.",
    ),
    AzurePolicySet(
        id="iso-27001",
        label="ISO/IEC 27001:2013",
        filename="ISO_27001_2013.json",
        default_scope="commercial",
        description="Policies that cover the ISO/IEC 27001:2013 standard.",
    ),
    AzurePolicySet(
        id="cmmc-l3",
        label="CMMC Level 3",
        filename="CMMC_L3.json",
        default_scope="gov",
        description="Cybersecurity Maturity Model Certification Level 3 initiative.",
    ),
    AzurePolicySet(
        id="soc-2",
        label="SOC 2 Type 2",
        filename="SOC_2_Type2.json",
        default_scope="commercial",
        description="Controls aligned with SOC 2 Type 2 reporting objectives.",
    ),
)


def list_policy_sets() -> Sequence[AzurePolicySet]:
    return BUILTIN_POLICY_SETS


def get_policy_set(policy_id: str) -> AzurePolicySet | None:
    for policy in BUILTIN_POLICY_SETS:
        if policy.id == policy_id:
            return policy
    return None
