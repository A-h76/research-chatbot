SYSTEMATIC_SYSTEM = (
    "You are a systematic review methodology expert. "
    "Ground synthesis comments in the provided review context and grades. Do not invent included studies."
)

SYSTEMATIC_REVIEW_TEMPLATE = """## Review Meta-data
{document_context}

## Review Question / PICO
{pico}

## Evidence Synthesis Inputs
{evidence}
{statistics}

## Risk of Bias Summary
{risk_of_bias}

## GRADE Assessment
{grade_assessment}
{grading}

## Task
{task_description}

## Instructions
{instructions}

## Output
{output_format}
"""
