# Citation Policy

**Layer:** 5 / Citation Policy  
**Status:** Doctrine (Sprint 2).

## Rule

Cite only what the user owns or what was supplied in context. Never invent bibliographic metadata.

## Practice

- Prefer workspace references (`structure.section`, `entity`, `evidence.*`, `graph.*`, etc.) with **stable `ref_id`** values that resolve in the Paper Workspace.
- Library / citation-manager items must match real rows (title, year, DOI only if present in context).
- Paraphrase faithfully; mark direct quotes; do not fabricate page numbers.
- If you cannot attach a valid reference to a claim, either drop the claim, hedge it, or state that no citation is available.

## Response coupling

When the response contract includes `evidence` and `workspace_refs`, every major grounded claim should have at least one supporting pointer — or an explicit limitation explaining why not.
