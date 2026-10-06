# Superpowers Workflow

When developing software in this workspace, follow the Superpowers skills methodology:

## Skill Invocation
- **Brainstorming (`brainstorming`)**: Use before any creative work, creating features, building components, or modifying behavior. Explore requirements and present design options before writing plans or implementation.
- **Writing Plans (`writing-plans`)**: Create structured, bite-sized implementation plans emphasizing TDD, YAGNI, and DRY.
- **Executing Plans (`executing-plans` / `subagent-driven-development`)**: Execute implementation plans task-by-task with verification.
- **Test-Driven Development (`test-driven-development`)**: Write failing tests first, verify the failure, implement minimal code to pass, and refactor.
- **Systematic Debugging (`systematic-debugging`)**: For bugs, conduct root-cause analysis and trace defects before applying fixes.
- **Verification (`verification-before-completion`)**: Always verify changes against evidence before marking tasks complete.

## Tooling Conventions for Antigravity
- Subagent dispatch: Use `invoke_subagent` (`TypeName: "self"` for full execution or `"research"` for read-only).
- Task tracking: Use task artifacts created with `write_to_file`.
