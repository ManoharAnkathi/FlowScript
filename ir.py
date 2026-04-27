from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from parser import Program
from semantic import SemanticResult

IROp = Literal[
    "LOAD_CONST",
    "LOAD_NAME",
    "STORE_NAME",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "PRINT",
]


@dataclass(frozen=True)
class IRInstruction:
    op: IROp
    arg1: str | float | None = None
    arg2: str | float | None = None
    result: str | None = None
    source_line: int = 0
    source_column: int = 0


@dataclass(frozen=True)
class IRProgram:
    instructions: list[IRInstruction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def build_ir(program: Program, semantic_result: SemanticResult) -> IRProgram:
    """Person 3 ownership.

    Input contract:
    - program: parsed AST from parser.parse(...)
    - semantic_result: validated symbol data from semantic.analyze_program(...)

    Output contract:
    - IRProgram with three-address style instructions.
    """
    _ = (program, semantic_result)
    return IRProgram(
        instructions=[],
        metadata={
            "status": "TODO_PERSON_3",
            "notes": "Implement AST -> IR lowering here.",
        },
    )
