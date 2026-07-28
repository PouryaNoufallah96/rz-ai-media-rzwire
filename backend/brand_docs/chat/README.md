# Chat knowledge drop-in folder

Drop business / company knowledge files here — they are auto-loaded by the
in-app chat assistant at backend startup. No code changes needed.

## Supported formats
- `*.md`   — plain Markdown (recommended). Formatting is preserved as text.
- `*.docx` — paragraphs are concatenated (same loader as the brand bibles).

## What to put here
Anything the chatbot should know beyond the brand bibles and the built-in
RZWire workspace overview. Good candidates:

- **`faq.md`** — workspace access, brand guidance, safety controls, and common workflows,
  supported regions, etc.
- **`sales.md`** — value props, comparison points, common objections.
- **`onboarding.md`** — step-by-step "how do I…" answers for new users.

## Rules
- One topic per file is fine; large files are auto-chunked (~900 chars).
- Filenames are used only as labels in logs and (optionally) retrieval metadata.
- Removing a file removes it from the assistant's knowledge on next server restart.

This folder is optional — if empty, the assistant still answers from the brand
bibles + platform overview loaded in `backend/chat_knowledge.py`.
