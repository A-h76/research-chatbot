CLINICAL_SYSTEM = (
    "You are a clinical trial specialist with expertise in RCT analysis. "
    "Use only the provided study context. Do not invent trial identifiers, outcomes, or bias ratings."
)

CLINICAL_TRIAL_TEMPLATE = """## Study Identification
{document_context}
NCT Number: {nct_number}
Design: {study_design}

## Population
{population}

## Intervention
{intervention}

## Comparator
{comparator}

## Outcomes
{outcomes}

## Results / Statistics
{statistics}

## Risk of Bias / Grading
{risk_of_bias}
{grading}

## Task
{task_description}

## Instructions
{instructions}

## Format
{output_format}
"""
