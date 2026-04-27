Team Handoff Contract (Person 3 + Person 4)

Goal
- Work in parallel after semantic analysis with zero ownership overlap.

Ownership
- Person 3 owns:
  - ir.py
  - optimizer.py
- Person 4 owns:
  - codegen.py
  - backend_pipeline.py (only integration logic related to backend output)

Do Not Touch Rules
- Person 3 should not edit codegen.py.
- Person 4 should not edit ir.py or optimizer.py internals.
- Both should avoid edits to lexer.py, parser.py, semantic.py, and main.py unless team agrees.

Interface Contracts
- build_ir(program, semantic_result) -> IRProgram
- optimize_ir(ir_program) -> (IRProgram, OptimizationReport)
- generate_python(ir_program) -> str
- execute_ir(ir_program) -> list[str]
- run_backend_pipeline(program, semantic_result, ...) -> BackendResult

Recommended Git Workflow
- Person 3 branch: feature/person3-ir-opt
- Person 4 branch: feature/person4-codegen
- Merge order:
  1) Person 3 merges ir.py + optimizer.py
  2) Person 4 rebases and merges codegen/backend changes

Initial Milestones
- Milestone 1 (Person 3): Create working IR for let/const/assign/print and + - * /
- Milestone 2 (Person 3): Add constant folding pass
- Milestone 3 (Person 4): Generate valid Python code from IR
- Milestone 4 (Person 4): Optional direct IR executor for terminal output
