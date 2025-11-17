
# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/001-build-a-slack/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Slack bot that autonomously monitors designated channels for OOM incident alerts, extracts pod/namespace details using regex patterns, and responds with structured diagnostic reports containing data from OpenShift, Prometheus, and AWS CloudWatch. Implemented as a lightweight Python service using Slack Bolt SDK with in-memory processing and direct API integrations.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: slack-bolt-python, aiohttp, boto3, pydantic, structlog
**Storage**: N/A (in-memory processing only)
**Testing**: pytest with asyncio support
**Target Platform**: Linux server/container
**Project Type**: single (standalone service)
**Performance Goals**: <30 second response time for diagnostic reports, handle 10+ concurrent alerts
**Constraints**: <100MB memory footprint, minimal dependencies, stateless operation
**Scale/Scope**: Monitor 10+ Slack channels, integrate with 3 data sources, process 100+ alerts/day

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Excellence (Principle I)
- [x] Static analysis tools configured (linting, type checking, security)
- [x] Code review process defined
- [x] Documentation standards established
- [x] Formatting and naming conventions specified

### Test-Driven Development (Principle II - NON-NEGOTIABLE)
- [x] TDD approach confirmed: Tests → User approval → Tests fail → Implementation
- [x] Unit, integration, and contract test plans defined
- [x] Performance benchmarks identified for diagnostic operations
- [x] Test coverage targets established (95%+ required)

### User Experience Consistency (Principle III)
- [x] CLI command conventions follow UNIX standards
- [x] Output formats support both JSON and human-readable modes
- [x] Error message patterns defined with actionable guidance
- [x] Progress indicators planned for long operations

### Performance Standards (Principle IV)
- [x] Performance requirements specified (<30s response time, 500ms startup)
- [x] Memory footprint limits defined (<100MB during analysis)
- [x] CPU usage optimization strategy outlined
- [x] Performance regression testing approach planned

### Observability and Transparency (Principle V)
- [x] Structured logging framework selected
- [x] Metrics collection strategy defined
- [x] Debug modes and tracing capabilities planned
- [x] Algorithm documentation requirements established

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: [DEFAULT to Option 1 unless Technical Context indicates web/mobile app]

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Slack API contract tests → Slack event handling tests [P]
- External API contracts → OpenShift/Prometheus/CloudWatch integration tests [P]
- Data model entities → Model classes and validation [P]
- User scenarios → End-to-end integration tests
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation
- Dependency order: Models → Services → Event Handlers → Bot Integration
- Mark [P] for parallel execution (independent modules)
- Slack integration before external API integrations

**Estimated Output**: 28-32 numbered, ordered tasks in tasks.md

**Key Task Categories**:
1. Setup: Project structure, dependencies, configuration
2. Contract Tests: Slack API, OpenShift API, Prometheus API, CloudWatch API [P]
3. Model Implementation: OOMAlert, DiagnosticReport, PodInformation classes [P]
4. Service Layer: AlertDetector, DataCollector, ReportGenerator [P]
5. Integration: Slack event handling, external API clients
6. End-to-End: Full workflow testing with quickstart scenarios
7. Polish: Error handling, logging, metrics, documentation

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (30s response time target set)
- [x] Complexity deviations documented

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
