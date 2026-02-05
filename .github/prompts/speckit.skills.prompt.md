> Note: 
> - Argument format: `<name> - <description>` (e.g., `testing - Unit testing utils`) 
> - Or flags: `--name <name> --description <desc>`

## User Input

```text
$ARGUMENTS
```

## Outline

Goal: Interactively guide the user to create a high-quality SpecKit Skill, ensuring all necessary components are properly structured and documented according to best practices.

Execution Steps:

1.  **Initialize or Refresh**:
    - Execute `.specify/scripts/bash/create-new-skill.sh --json $ARGUMENTS`.
    - Parse JSON output.
    - **Case 1: Refresh Only** (Input was empty or invalid format):
        - Output includes `"status": "refreshed"`.
        - Action: Display the message from `.specify/scripts/bash/create-new-skill.sh --json $ARGUMENTS` output.
        - **STOP**. (Do not proceed to step 2).
    - **Case 2: Created Skill**:
        - Output includes `"SKILL_DIR"`.
        - Parse `SKILL_DIR`, `SKILL_NAME`, `SKILL_DESCRIPTION`.
        - Confirm success: "Created skill backbone at `SKILL_DIR`."

2.  **Sequential Configuration Loop (Interactive)**:
    - **Constraint**: Ask **EXACTLY ONE** question at a time. Wait for user response before proceeding.
    - **Style**: Use "recommended" defaults to minimize typing (answer "yes" to accept).

    **Q1: Clarify Triggers** (Skip if description provided is already specific, >10 words)
    - Context: Skills need clear triggers to be selected by the agent.
    - Question: "What specific user intent or query should trigger this skill?"
    - **Suggested Answer**: Generate a specific trigger sentence based on `SKILL_NAME`.
    - Format: `**Suggested:** <Sentence> - (Reply "yes" to accept or type your own)`

    **Q2: Resource Strategy**
    - Context: Decide which resource folder to prioritize.
    - Question: "What creates the most value in this skill?"
    - **Analysis**: Suggest an option based on Q1.
    - Options Table:
      | Opt | Resource Type | Best Usage |
      |-----|---------------|------------|
      | A | **Scripts** (`/scripts`) | Deterministic logic, API calls, data transformation |
      | B | **References** (`/references`) | Schemas, API docs, large text context |
      | C | **Assets** (`/assets`) | Templates, boilerplates, files to copy to user |
      | D | **Instructions** (Pure) | Logic complex enough to handle with just prompt engineering |
    - Format: Present options, highlight recommendation (`**Recommended:** Option A...`), ask for selection.

    **Q3: Content Source** (If Q2 is A, B, or C)
    - Question: "Do you have existing files to import for this?"
    - Options:
      - **Yes**: "I'll guide you to copy them."
      - **No**: "We will create a placeholder/template."

3.  **Tailored Implementation**:
    - Provide specific actions based on Q2 & Q3.
    - **If Scripts**: "Create your script in `{SKILL_DIR}/.specify/scripts/`. Remember to make it executable."
    - **If References**: "Add your markdown/text files to `{SKILL_DIR}/references/`."
    - **If Assets**: "Place template files in `{SKILL_DIR}/assets/`."
    - **Action**: Instruct user to open `{SKILL_DIR}/SKILL.md` and update the `description` field with the accepted answer from Q1.

4.  **Completion**:
    - Summarize what was created.
    - Verify `SKILL.md` exists.

## Handoffs

**Before running this command**:

- Use when you need to add a new reusable agent skill or refresh existing ones.

**After running this command**:

- Run `/speckit.instructions` so the project-level instructions reflect available skills.