# Glossary

The project's controlled vocabulary. Agents MUST use these terms in code, documents and
conversation, and flag any term they invent. Changes to this file are reviewed changes,
made in a pull request like code.

**Rule:** prefer current industry terms. If a term is invented or ambiguous, say so and
give the industry equivalent.

## Project terms

<!-- TEMPLATE PLACEHOLDER — add the product's domain terms during the planning session. -->

| Term | Meaning | Industry equivalent(s) | Notes |
|---|---|---|---|
| **Slice** | A thin, end-to-end, independently testable increment of a feature (elephant carpaccio). | User story / vertical slice | Status in `documents/feature-list.json`. |

## Acronyms

Every acronym the documents use is spelled out here; `tests/harness/test_documents.py`
fails on one that is not. Codes and keywords that are not acronyms go in that test's
`NOT_ACRONYMS` instead.

| Acronym | Meaning | Notes |
|---|---|---|
| **ADR** | Architecture decision record | `documents/adr/`, process in ADR 000 |
| **AI** | Artificial intelligence | |
| **API** | Application programming interface | |
| **CC0** | Creative Commons Zero public-domain dedication | A licence |
| **MADR** | Markdown Architectural Decision Records | The ADR template (ADR 000) |
| **MIT** | MIT License (Massachusetts Institute of Technology) | A permissive licence |
| **PR** | Pull request | |
| **YAML** | YAML Ain't Markup Language | Used for ADR front matter |
