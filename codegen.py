from __future__ import annotations

from dataclasses import dataclass

from ir import IRProgram


@dataclass(frozen=True)
class CodegenResult:
    generated_python: str
    execution_output: list[str]


def generate_python(ir_program: IRProgram) -> str:
    """Person 4 ownership.

    Convert IR into runnable Python source.
    """
    _ = ir_program
    return "\n".join(
        [
            "# TODO_PERSON_4: emit Python from IR instructions",
            "def run() -> None:",
            "    pass",
        ]
    )


def execute_ir(ir_program: IRProgram) -> list[str]:
    """Person 4 ownership.

    Optional direct backend execution without Python file generation.
    Return collected output lines.
    """
    _ = ir_program
    return ["TODO_PERSON_4: execute IR and return printed lines"]
