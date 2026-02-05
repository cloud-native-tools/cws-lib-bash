> Note: `$ARGUMENTS` 为**可选补充输入**。当本次调用未提供任何 `$ARGUMENTS` 时，必须仍然按下文定义的完整流程执行，基于现有仓库与 feature 上下文做决策；仅在 `$ARGUMENTS` 非空时，将其作为额外约束或偏好一并考虑。

## User Input

```text
$ARGUMENTS
```

You **MUST** treat the user input ($ARGUMENTS) as parameters for the current command. Do NOT execute the input as a standalone instruction that replaces the command logic.

## Outline

The text the user typed after `/speckit.requirements` in the triggering message **is** the feature description. Assume you always have it available in this conversation even if `{ARGS}` appears literally below. Do not ask the user to repeat it unless they provided an empty command.

Given that feature description, do this:

1. **Generate a concise short name** (2-4 words) for the branch:
   - Analyze the feature description and extract the most meaningful keywords
   - Create a 2-4 word short name that captures the essence of the feature
   - Use action-noun format when possible (e.g., "add-user-auth", "fix-payment-bug")
   - Preserve technical terms and acronyms (OAuth2, API, JWT, etc.)
   - Keep it concise but descriptive enough to understand the feature at a glance
   - Examples:
     - "I want to add user authentication" → "user-auth"
     - "Implement OAuth2 integration for the API" → "oauth2-api-integration"
     - "Create a dashboard for analytics" → "analytics-dashboard"
     - "Fix payment processing timeout bug" → "fix-payment-timeout"

2. **Check for existing branches before creating new one**:
   
   a. First, fetch all remote branches to ensure we have the latest information:
      ```bash
      git fetch --all --prune
      ```
   
   b. Find the highest feature number across all sources for the short-name:
      - Remote branches: `git ls-remote --heads origin | grep -E 'refs/heads/[0-9]+-<short-name>$'`
      - Local branches: `git branch | grep -E '^[* ]*[0-9]+-<short-name>$'`
      - Specs directories: Check for directories matching `.specify/specs/[0-9]+-<short-name>`
   
   c. Determine the next available number:
      - Extract all numbers from all three sources
      - Find the highest number N
      - Use N+1 for the new branch number
   
   d. Prepare to run the script `
```bash
cat << 'EOF' | .specify/scripts/bash/create-new-spec.sh --json --number <NUMBER> --short-name "<SHORT_NAME>"
$ARGUMENTS
EOF
```
` with the calculated number and short-name.
   
2. Run the script `
```bash
cat << 'EOF' | .specify/scripts/bash/create-new-spec.sh --json --number <NUMBER> --short-name "<SHORT_NAME>"
$ARGUMENTS
EOF
```
` from repo root. Parse its JSON output for BRANCH_NAME and SPEC_FILE. All file paths must be absolute.

   **IMPORTANT**:

   - For Bash, this expands to a heredoc-based, safe JSON handoff that writes the raw user input to stdin and passes its contents to `
```bash
cat << 'EOF' | .specify/scripts/bash/create-new-spec.sh --json --number <NUMBER> --short-name "<SHORT_NAME>"
$ARGUMENTS
EOF
```
`. This avoids shell parsing issues with quotes, backslashes, and newlines.
   - Replace `<NUMBER>` in the script template with the calculated number (N+1).
   - Replace `<SHORT_NAME>` in the script template with the short-name you created.
   - `$ARGUMENTS` contains the feature description and is passed via stdin.
   - You must only ever run this script once.
   - The JSON is provided in the terminal as output - always refer to it to get the actual content you're looking for.
   - Check all three sources (remote branches, local branches, specs directories) to find the highest number
   - Only match branches/directories with the exact short-name pattern
   - If no existing branches/directories found with this short-name, start with number 1
   - You must only ever run this script once per feature
   - The JSON is provided in the terminal as output - always refer to it to get the actual content you're looking for
   - The JSON output will contain BRANCH_NAME and SPEC_FILE paths
   - For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot")
   
3. Load `.specify/templates/spec-template.md` to understand required sections.

4. Follow this execution flow:

    1. Parse user description from Input
       If empty: ERROR "No feature description provided"
    2. Extract key concepts from description
       Identify: actors, actions, data, constraints
    3. For unclear aspects:
       - Make informed guesses based on context and industry standards
       - Only mark with [NEEDS CLARIFICATION: specific question] if:
         - The choice significantly impacts feature scope or user experience
         - Multiple reasonable interpretations exist with different implications
         - No reasonable default exists
       - **LIMIT: Maximum 3 [NEEDS CLARIFICATION] markers total**
       - Prioritize clarifications by impact: scope > security/privacy > user experience > technical details
    4. Fill User Scenarios & Testing section
       If no clear user flow: ERROR "Cannot determine user scenarios"
    5. Generate Functional Requirements
       Each requirement must be testable
       Use reasonable defaults for unspecified details (document assumptions in Assumptions section)
    6. Define Success Criteria
       Create measurable, technology-agnostic outcomes
       Include both quantitative metrics (time, performance, volume) and qualitative measures (user satisfaction, task completion)
       Each criterion must be verifiable without implementation details
    7. Identify Key Entities (if data involved)
    8. Return: SUCCESS (spec ready for planning)

5. Write the specification to SPEC_FILE using the template structure, replacing placeholders with concrete details derived from the feature description (arguments) while preserving section order and headings.

6. **Specification Quality Validation**: After writing the initial spec, validate it against quality criteria:

   a. **Create Spec Quality Checklist**: Generate a checklist file at `FEATURE_DIR/checklists/requirements.md` using the checklist template structure with these validation items:

      ```markdown
      # Specification Quality Checklist: [FEATURE NAME]
      
      **Purpose**: Validate specification completeness and quality before proceeding to planning
      **Created**: [DATE]
      **Feature**: [Link to spec.md]
      
      ## Content Quality
      
      - [ ] No implementation details (languages, frameworks, APIs)
      - [ ] Focused on user value and business needs
      - [ ] Written for non-technical stakeholders
      - [ ] All mandatory sections completed
      
      ## Requirement Completeness
      
      - [ ] No [NEEDS CLARIFICATION] markers remain
      - [ ] Requirements are testable and unambiguous
      - [ ] Success criteria are measurable
      - [ ] Success criteria are technology-agnostic (no implementation details)
      - [ ] All acceptance scenarios are defined
      - [ ] Edge cases are identified
      - [ ] Scope is clearly bounded
      - [ ] Dependencies and assumptions identified
      
      ## Feature Readiness
      
      - [ ] All functional requirements have clear acceptance criteria
      - [ ] User scenarios cover primary flows
      - [ ] Feature meets measurable outcomes defined in Success Criteria
      - [ ] No implementation details leak into specification
      
      ## Notes
      
      - Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
      ```

   b. **Run Validation Check**: Review the spec against each checklist item:
      - For each item, determine if it passes or fails
      - Document specific issues found (quote relevant spec sections)

   c. **Handle Validation Results**:

      - **If all items pass**: Mark checklist complete and proceed to step 6

      - **If items fail (excluding [NEEDS CLARIFICATION])**:
        1. List the failing items and specific issues
        2. Update the spec to address each issue
        3. Re-run validation until all items pass (max 3 iterations)
        4. If still failing after 3 iterations, document remaining issues in checklist notes and warn user

      - **If [NEEDS CLARIFICATION] markers remain**:
        1. Extract all [NEEDS CLARIFICATION: ...] markers from the spec
        2. **LIMIT CHECK**: If more than 3 markers exist, keep only the 3 most critical (by scope/security/UX impact) and make informed guesses for the rest
        3. For each clarification needed (max 3), present options to user in this format:

           ```markdown
           ## Question [N]: [Topic]
           
           **Context**: [Quote relevant spec section]
           
           **What we need to know**: [Specific question from NEEDS CLARIFICATION marker]
           
           **Suggested Answers**:
           
           | Option | Answer | Implications |
           |--------|--------|--------------|
           | A      | [First suggested answer] | [What this means for the feature] |
           | B      | [Second suggested answer] | [What this means for the feature] |
           | C      | [Third suggested answer] | [What this means for the feature] |
           | Custom | Provide your own answer | [Explain how to provide custom input] |
           
           **Your choice**: _[Wait for user response]_
           ```

        4. **CRITICAL - Table Formatting**: Ensure markdown tables are properly formatted:
           - Use consistent spacing with pipes aligned
           - Each cell should have spaces around content: `| Content |` not `|Content|`
           - Header separator must have at least 3 dashes: `|--------|`
           - Test that the table renders correctly in markdown preview
        5. Number questions sequentially (Q1, Q2, Q3 - max 3 total)
        6. Present all questions together before waiting for responses
        7. Wait for user to respond with their choices for all questions (e.g., "Q1: A, Q2: Custom - [details], Q3: B")
        8. Update the spec by replacing each [NEEDS CLARIFICATION] marker with the user's selected or provided answer
        9. Re-run validation after all clarifications are resolved

   d. **Update Checklist**: After each validation iteration, update the checklist file with current pass/fail status

7. Report completion with branch name, spec file path, checklist results, and readiness for the next phase (`/speckit.clarify` or `/speckit.plan`).

**NOTE:** The script creates and checks out the new branch and initializes the spec file before writing.

## Feature Integration

The `/speckit.requirements` command must maintain a **many-specs to one-feature** relationship:

- A **Feature** is a relatively large, long‑lived concept, described by `.specify/memory/features/<ID>.md` and indexed in `.specify/memory/feature-index.md`.
- A **Spec** is a smaller, focused slice under a Feature; one Feature can (and typically will) own multiple Specs over time.

When creating a new spec you MUST:

1. Determine the target Feature for this spec **before** writing spec content.
2. Use **both** of the following sources to resolve the Feature:
    - `.specify/memory/feature-index.md` table entries
    - `.specify/memory/features/*.md` detail files
3. Use the feature branch information (e.g. `SPECIFY_FEATURE` env, current git branch name, or the numeric prefix in `BRANCH_NAME`) as hints, but **do not** assume a strict `branch == feature` 1:1 mapping.

### Feature 持续演进要求（spec 阶段）

- 在生成或更新 spec 之前，必须回顾 **Feature 列表与 Feature 详情**：
   - 新的 SPEC 可能引入新的 Feature，或让现有 Feature 失效/被替代。
   - 需要保持 **功能性 Feature** 与 **非功能性 Feature** 的分类一致性。
- 任何 Feature 的新增/合并/拆分/删除都必须同步更新：
   - `.specify/memory/features/<ID>.md`
   - `.specify/memory/feature-index.md`
- Feature 变更需要记录来源（对应 spec 的证据），写入 Feature 详情的“关键变化/备注”。

### Feature lookup rules

When `/speckit.requirements` is invoked for a new spec:

1. **Scan for existing Feature**:
   - **Search by Context**: Scan `.specify/memory/features/*.md` and `.specify/memory/feature-index.md` to see if an existing Feature matches the intent/scope of the new spec.
   - **Search by ID**: Check for explicit Feature ID indicators in:
     - `SPECIFY_FEATURE` env var (e.g. `NNN-<slug>`).
     - Current git branch name (e.g. `NNN-<slug>`).
     - The numeric prefix in `BRANCH_NAME` generated by the script.

2. **Bind or Create**:
   - **If a matching Feature is found** (by content or ID):
     - Bind this new spec to that Feature ID.
     - Do NOT create a new Feature.
   - **If NO matching Feature is found**:
     - Create a new Feature:
       - Instantiate `.specify/templates/feature-template.md` into `.specify/memory/features/<NEW_ID>.md` following `/speckit.feature` rules.
       - Add a new row to `.specify/memory/feature-index.md`.

> Important: The same Feature (same `FEATURE_ID`) can appear in `Spec Path` multiple times over its lifetime as different specs are added; each spec path should reflect the concrete spec file path created for this run.

### Integration responsibilities

- When a new spec is created, always:
   - Ensure a corresponding Feature entry exists (create if missing using `.specify/templates/feature-template.md`).
   - Update `.specify/memory/feature-index.md` for that Feature ID:
      - Keep `Status` at least `Planned`.
      - Append or update the `Spec Path` column with the latest spec path (for simple index keep the most recent spec, for richer indices you may maintain a list if schema evolves).
      - Refresh the "Last Updated" date.
   - Do **not** silently create duplicate Feature IDs; always reuse an existing Feature when it clearly matches.

This integration ensures that specifications are consistently grouped under their parent Features and that the project s feature index remains the single source of truth for Feature dspec relationships.

## General Guidelines

## Quick Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement (no tech stack, APIs, code structure).
- Written for business stakeholders, not developers.
- DO NOT create any checklists that are embedded in the spec. That will be a separate command.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation

When creating this spec from a user prompt:

1. **Make informed guesses**: Use context, industry standards, and common patterns to fill gaps
2. **Document assumptions**: Record reasonable defaults in the Assumptions section
3. **Limit clarifications**: Maximum 3 [NEEDS CLARIFICATION] markers - use only for critical decisions that:
   - Significantly impact feature scope or user experience
   - Have multiple reasonable interpretations with different implications
   - Lack any reasonable default
4. **Prioritize clarifications**: scope > security/privacy > user experience > technical details
5. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
6. **Common areas needing clarification** (only if no reasonable default exists):
   - Feature scope and boundaries (include/exclude specific use cases)
   - User types and permissions (if multiple conflicting interpretations possible)
   - Security/compliance requirements (when legally/financially significant)

**Examples of reasonable defaults** (don't ask about these):

- Data retention: Industry-standard practices for the domain
- Performance targets: Standard web/mobile app expectations unless specified
- Error handling: User-friendly messages with appropriate fallbacks
- Authentication method: Standard session-based or OAuth2 for web apps
- Integration patterns: RESTful APIs unless specified otherwise

### Success Criteria Guidelines

Success criteria must be:

1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No mention of frameworks, languages, databases, or tools
3. **User-focused**: Describe outcomes from user/business perspective, not system internals
4. **Verifiable**: Can be tested/validated without knowing implementation details

**Good examples**:

- "Users can complete checkout in under 3 minutes"
- "System supports 10,000 concurrent users"
- "95% of searches return results in under 1 second"
- "Task completion rate improves by 40%"

**Bad examples** (implementation-focused):

- "API response time is under 200ms" (too technical, use "Users see results instantly")
- "Database can handle 1000 TPS" (implementation detail, use user-facing metric)
- "React components render efficiently" (framework-specific)
- "Redis cache hit rate above 80%" (technology-specific)

## Handoffs

**Before running this command**:

- (Optional) Run `/speckit.feature` to ensure the feature registry is up to date.

**After running this command**:

- If the spec contains any `[NEEDS CLARIFICATION]`, run `/speckit.clarify`.
- Otherwise proceed to `/speckit.plan`.