from __future__ import annotations

from dataclasses import dataclass

from codegen import execute_ir, generate_python
from ir import IRProgram, build_ir
from optimizer import OptimizationReport, optimize_ir
from parser import Program
from semantic import SemanticResult


@dataclass(frozen=True)
class BackendResult:
    ir_program: IRProgram
    optimization_report: OptimizationReport
    generated_assembly: str
    execution_output: list[str]


def run_backend_pipeline(
    program: Program,
    semantic_result: SemanticResult,
    *,
    run_optimizer: bool = True,
    run_execution: bool = False,
) -> BackendResult:
    """Stable handoff API for Person 3 and Person 4.

    Converts AST + semantic analysis into optimized IR, then generates x86-64 assembly code.
    
    This function is intentionally isolated from main.py to avoid conflicts
    while both teammates develop their parts.
    
    Args:
        program: Parsed AST from the parser
        semantic_result: Symbol table and analysis from semantic analyzer
        run_optimizer: Whether to run IR optimization passes (default: True)
        run_execution: Whether to execute the IR directly (default: False)
    
    Returns:
        BackendResult containing:
        - ir_program: Optimized intermediate representation
        - optimization_report: Summary of optimizations applied
        - generated_assembly: x86-64 assembly code
        - execution_output: Output from direct execution (if enabled)
    """
    ir_program = build_ir(program, semantic_result)

    if run_optimizer:
        optimized_ir, optimization_report = optimize_ir(ir_program)
    else:
        optimized_ir = ir_program
        optimization_report = OptimizationReport(
            passes_run=0,
            changes_made=0,
            notes=["Optimizer skipped"],
        )

    generated_assembly = generate_python(optimized_ir)
    execution_output = execute_ir(optimized_ir) if run_execution else []

    return BackendResult(
        ir_program=optimized_ir,
        optimization_report=optimization_report,
        generated_assembly=generated_assembly,
        execution_output=execution_output,
    )
