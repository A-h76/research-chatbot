MEDICAL_SYSTEM = (
    "You are a medical research analyst with expertise in evidence-based medicine. "
    "Base every claim on the provided context. Do not invent citations, statistics, or grades."
)

MEDICAL_TEMPLATE = """## Document Context
{document_context}

## Abstract
{abstract}

## Task
{task_description}

## Clinical Entities
{clinical_entities}

## PICO Elements
{pico}

## Statistical Findings
{statistics}

## Evidence Quality
{grading}

## Supporting Evidence
{evidence}

## Instructions
{instructions}

## Output Format
{output_format}
"""
