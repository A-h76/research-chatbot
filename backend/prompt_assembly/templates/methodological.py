METHODOLOGICAL_SYSTEM = (
    "You are a research methodology reviewer. "
    "Evaluate design and validity using only the provided document context."
)

METHODOLOGICAL_TEMPLATE = """## Document Context
{document_context}

## Method / Approach
{method}

## Task
{task_description}

## Evidence / Findings
{evidence}
{statistics}

## Instructions
{instructions}

## Output Format
{output_format}
"""
