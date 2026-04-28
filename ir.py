from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from parser import (
    AssignStatement,
    BinaryOp,
    BreakStatement,
    ComparisonOp,
    ConstStatement,
    ContinueStatement,
    ForStatement,
    FunctionDeclarationStatement,
    Identifier,
    IfStatement,
    LetStatement,
    NumberLiteral,
    PrintStatement,
    Program,
    RepeatStatement,
    ReturnStatement,
    Statement,
    WhileStatement,
)
from semantic import SemanticResult


@dataclass(frozen=True)
class IRProgram:
    instructions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class IRGenerator:
    def __init__(self) -> None:
        self.code: list[str] = []
        self._temp_counter = 0
        self._label_counter = 0
        self._loop_stack: list[tuple[str, str]] = []

    def new_temp(self) -> str:
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def new_label(self) -> str:
        self._label_counter += 1
        return f"L{self._label_counter}"

    def generate(self, node: Program | Statement) -> None:
        if isinstance(node, Program):
            for statement in node.statements:
                self.generate(statement)
            return

        if isinstance(node, (LetStatement, ConstStatement, AssignStatement)):
            target = node.name
            value = self.generate_expr(node.expr)
            self.code.append(f"{target} = {value}")
            return

        if isinstance(node, PrintStatement):
            value = self.generate_expr(node.expr)
            self.code.append(f"print {value}")
            return

        if isinstance(node, IfStatement):
            true_label = self.new_label()
            end_label = self.new_label()
            left, op, right = self._generate_condition(node.condition)
            self.code.append(f"if {left} {op} {right} goto {true_label}")
            self.code.append(f"goto {end_label}")
            self.code.append(f"{true_label}:")
            for child in node.body:
                self.generate(child)
            self.code.append(f"{end_label}:")
            return

        if isinstance(node, RepeatStatement):
            count = self.generate_expr(node.count_expr)
            counter = self.new_temp()
            check_label = self.new_label()
            inc_label = self.new_label()
            end_label = self.new_label()

            self.code.append(f"{counter} = 0")
            self.code.append(f"{check_label}:")
            self.code.append(f"if {counter} >= {count} goto {end_label}")

            self._loop_stack.append((inc_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append(f"{inc_label}:")
            self.code.append(f"{counter} = {counter} + 1")
            self.code.append(f"goto {check_label}")
            self.code.append(f"{end_label}:")
            return

        if isinstance(node, ForStatement):
            start_value = self.generate_expr(node.start_expr)
            end_value = self.generate_expr(node.end_expr)
            check_label = self.new_label()
            inc_label = self.new_label()
            end_label = self.new_label()

            self.code.append(f"{node.loop_var} = {start_value}")
            self.code.append(f"{check_label}:")
            self.code.append(f"if {node.loop_var} > {end_value} goto {end_label}")

            self._loop_stack.append((inc_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append(f"{inc_label}:")
            self.code.append(f"{node.loop_var} = {node.loop_var} + 1")
            self.code.append(f"goto {check_label}")
            self.code.append(f"{end_label}:")
            return

        if isinstance(node, WhileStatement):
            check_label = self.new_label()
            body_label = self.new_label()
            end_label = self.new_label()
            left, op, right = self._generate_condition(node.condition)

            self.code.append(f"{check_label}:")
            self.code.append(f"if {left} {op} {right} goto {body_label}")
            self.code.append(f"goto {end_label}")
            self.code.append(f"{body_label}:")

            self._loop_stack.append((check_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append(f"goto {check_label}")
            self.code.append(f"{end_label}:")
            return

        if isinstance(node, FunctionDeclarationStatement):
            self.code.append(f"func {node.name}:")
            for child in node.body:
                self.generate(child)
            self.code.append(f"endfunc {node.name}")
            return

        if isinstance(node, ReturnStatement):
            if node.expr is None:
                self.code.append("return")
            else:
                value = self.generate_expr(node.expr)
                self.code.append(f"return {value}")
            return

        if isinstance(node, ContinueStatement):
            if not self._loop_stack:
                raise ValueError("continue used outside loop")
            continue_label, _ = self._loop_stack[-1]
            self.code.append(f"goto {continue_label}")
            return

        if isinstance(node, BreakStatement):
            if not self._loop_stack:
                raise ValueError("break used outside loop")
            _, break_label = self._loop_stack[-1]
            self.code.append(f"goto {break_label}")
            return

        raise ValueError("Unsupported statement")

    def generate_expr(self, node: NumberLiteral | Identifier | BinaryOp) -> str:
        if isinstance(node, NumberLiteral):
            return str(node.value)

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, BinaryOp):
            left = self.generate_expr(node.left)
            right = self.generate_expr(node.right)
            temp = self.new_temp()
            self.code.append(f"{temp} = {left} {node.op} {right}")
            return temp

        raise ValueError("Unsupported expression")

    def _generate_condition(self, node: ComparisonOp) -> tuple[str, str, str]:
        left = self.generate_expr(node.left)
        right = self.generate_expr(node.right)
        return left, node.op, right


def build_ir(program: Program, semantic_result: SemanticResult) -> IRProgram:
    """Person 3 ownership.

    Input contract:
    - program: parsed AST from parser.parse(...)
    - semantic_result: validated symbol data from semantic.analyze_program(...)

    Output contract:
    - IRProgram with three-address style instructions.
    """
    _ = semantic_result
    generator = IRGenerator()
    generator.generate(program)
    return IRProgram(
        instructions=generator.code,
        metadata={
            "status": "ok",
            "notes": "Generated three-address code",
        },
    )
