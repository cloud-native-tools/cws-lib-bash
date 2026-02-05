> Note: `$ARGUMENTS` 为**可选补充输入**。`$ARGUMENTS` 是用户的输入，根据用户输入的不同整体的执行流程也会不同：如果 `$ARGUMENTS` 为空，则代表进行整体性的创建或更新；如果 `$ARGUMENTS` 有内容，则需要针对具体的部分内容进行更新或修改。

## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the content of `$ARGUMENTS` to determine the execution flow:
- If `$ARGUMENTS` is empty: Perform a comprehensive creation or update of the instructions.
- If `$ARGUMENTS` has content: Update or modify specific parts based on the provided input.

## Outline

1. **Setup**: Run `.specify/scripts/bash/generate-instructions.sh` to ensure the basic directory structure, `.copilotignore`, and template `.ai/instructions.md` exist.
   - This script handles the "heavy lifting" of creating directories, ignoring files, and establishing symlinks for various AI tools (`.clinerules`, `.github`, `.lingma`, etc.).
   - It will only create a template `.ai/instructions.md` if one does not exist.

2. **Analyze Project Context**:
   - Read `README.md` to understand the project's purpose and existing features.
   - Inspect configuration files (`pyproject.toml`, `package.json`, `pom.xml`, `Makefile`, etc.) to determine the tech stack.
   - Check `.specify/memory/constitution.md` (if exists) to identify any mandated project rules.
   - Check `.specify/memory/features.md` (if exists) for feature status reference.
   - **Check `.specify/` Directory**: When referencing the `.specify/` directory (if exists), **ONLY** consider the one in the **project root**. Ignore any `.specify/` directories found inside subdirectories or submodules (as they belong to other projects).

3. **Update Instructions Content**:
   - Read the content of `.ai/instructions.md` (whether newly created or existing).
   - **Fill Placeholders**: Replace any bracketed placeholders (e.g., `[Brief summary...]`, `[Detected tech stack...]`) with concrete details derived from your analysis.
   - **Update Documentation Map**: Ensure the table correctly points to existing documentation files in the repository.
   - **Preserve Sections**: Do NOT remove or overwrite the `## Tools` and `## Skills` sections or their placeholder comments (`<!-- TOOLS_PLACEHOLDER -->`, `<!-- SKILLS_PLACEHOLDER -->`). These are reserved for the `skills` command.
   - **Incorporate User Input**: If `$ARGUMENTS` provided specific instructions or context, integrate them into the file.

4. **Validation**:
   - Ensure the file is well-formatted Markdown.
   - Verify that the resulting instructions clearly describe the project to a fresh AI instance.

5. **Report**:
   - Report the full path of the instructions file (`.ai/instructions.md`).
   - Confirm that symlinks for Copilot, Cline, Lingma, Trae, and Qoder have been established.

## Handoffs

**Before running this command**:

- Run when you need to (re)generate project-wide AI instructions or compatibility symlinks.

**After running this command**:

- Run `/speckit.skills` to populate the Tools and Skills sections based on the project scan.