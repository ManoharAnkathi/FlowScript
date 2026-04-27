from __future__ import annotations

from dataclasses import dataclass

from ir import IRProgram


@dataclass(frozen=True)
class OptimizationReport:
    passes_run: int
    changes_made: int
    notes: list[str]


def optimize_ir(ir_program: IRProgram) -> tuple[IRProgram, OptimizationReport]:
    """Person 3 ownership.

    Recommended first passes:
    1. Constant folding
    2. Dead temporary elimination
    3. Algebraic simplification (x + 0, x * 1)
    """
    report = OptimizationReport(
        passes_run=0,
        changes_made=0,
        notes=["TODO_PERSON_3: add optimization passes"],
    )
    return ir_program, report
