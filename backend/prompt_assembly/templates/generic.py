GENERIC_SYSTEM = (
    "You are a careful research assistant. "
    "Use only the provided document context. Do not invent facts or citations."
)

GENERIC_TEMPLATE = """## Document Context
{document_context}

## Abstract
{abstract}

## Task
{task_description}

## Available Extracted Content
{evidence}
{pico}
{clinical_entities}
{statistics}
{grading}

## Instructions
{instructions}

## Output Format
{output_format}
"""
