from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from ir import IRProgram


@dataclass(frozen=True)
class OptimizationReport:
    passes_run: int
    changes_made: int
    notes: list[str]


class Optimizer:
    def __init__(self) -> None:
        self.constants: dict[str, str] = {}

    def optimize(self, ir_code: list[str]) -> list[str]:
        constants = self._collect_constants(ir_code)
        propagated = self._propagate_constants(ir_code, constants)
        folded = self._fold_constants(propagated)
        cleaned = self._eliminate_dead_temps(folded)
        return cleaned

    def _collect_constants(self, ir_code: Iterable[str]) -> dict[str, str]:
        constants: dict[str, str] = {}
        for line in ir_code:
            target, expr = _parse_assignment(line)
            if target is None or expr is None:
                continue
            value = _parse_number_literal(expr)
            if value is None:
                constants.pop(target, None)
                continue
            constants[target] = value
        return constants

    def _propagate_constants(self, ir_code: list[str], constants: dict[str, str]) -> list[str]:
        return [self._propagate_line(line, constants) for line in ir_code]

    def _propagate_line(self, line: str, constants: dict[str, str]) -> str:
        target, expr = _parse_assignment(line)
        if target is not None and expr is not None:
            return f"{target} = {_replace_in_expr(expr, constants)}"

        match = _IF_GOTO_RE.match(line)
        if match:
            left, op, right, label = match.groups()
            left = _replace_token(left, constants)
            right = _replace_token(right, constants)
            return f"if {left} {op} {right} goto {label}"

        match = _PRINT_RE.match(line)
        if match:
            expr = match.group(1)
            return f"print {_replace_in_expr(expr, constants)}"

        match = _RETURN_RE.match(line)
        if match:
            expr = match.group(1)
            if expr is None:
                return line
            return f"return {_replace_in_expr(expr, constants)}"

        return line

    def _fold_constants(self, ir_code: list[str]) -> list[str]:
        folded: list[str] = []
        for line in ir_code:
            target, expr = _parse_assignment(line)
            if target is None or expr is None:
                folded.append(line)
                continue

            folded_expr = _try_fold_expr(expr)
            folded.append(f"{target} = {folded_expr}")
        return folded

    def _eliminate_dead_temps(self, ir_code: list[str]) -> list[str]:
        used = _collect_used_names(ir_code)
        cleaned: list[str] = []
        for line in ir_code:
            target, expr = _parse_assignment(line)
            if target is not None and expr is not None and _TEMP_RE.fullmatch(target) and target not in used:
                continue
            cleaned.append(line)
        return cleaned


def optimize_ir(ir_program: IRProgram) -> tuple[IRProgram, OptimizationReport]:
    optimizer = Optimizer()
    optimized_instructions = optimizer.optimize(ir_program.instructions)
    changes_made = sum(
        1 for original, optimized in zip(ir_program.instructions, optimized_instructions) if original != optimized
    )
    if len(ir_program.instructions) != len(optimized_instructions):
        changes_made += abs(len(ir_program.instructions) - len(optimized_instructions))

    report = OptimizationReport(
        passes_run=3,
        changes_made=changes_made,
        notes=[
            "Constant propagation",
            "Constant folding",
            "Dead temporary elimination",
        ],
    )
    return IRProgram(instructions=optimized_instructions, metadata=ir_program.metadata), report


_ASSIGN_RE = re.compile(r"^\s*(\w+)\s*=\s*(.+?)\s*$")
_BINOP_RE = re.compile(r"^\s*(\S+)\s*([+\-*/])\s*(\S+)\s*$")
_IF_GOTO_RE = re.compile(r"^\s*if\s+(\S+)\s+([<>]=?|==|!=)\s+(\S+)\s+goto\s+(\S+)\s*$")
_PRINT_RE = re.compile(r"^\s*print\s+(.+?)\s*$")
_RETURN_RE = re.compile(r"^\s*return(?:\s+(.+?))?\s*$")
_TEMP_RE = re.compile(r"t\d+")


def _parse_assignment(line: str) -> tuple[str | None, str | None]:
    match = _ASSIGN_RE.match(line)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _parse_number_literal(text: str) -> str | None:
    stripped = text.strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", stripped) is None:
        return None
    return stripped


def _replace_in_expr(expr: str, constants: dict[str, str]) -> str:
    tokens = expr.split()
    replaced = [_replace_token(token, constants) for token in tokens]
    return " ".join(replaced)


def _replace_token(token: str, constants: dict[str, str]) -> str:
    return constants.get(token, token)


def _try_fold_expr(expr: str) -> str:
    match = _BINOP_RE.match(expr)
    if not match:
        return expr

    left, op, right = match.groups()
    left_num = _parse_number_literal(left)
    right_num = _parse_number_literal(right)
    if left_num is None or right_num is None:
        return expr

    result = _apply_numeric_op(float(left_num), float(right_num), op)
    return _format_number(result)


def _apply_numeric_op(left: float, right: float, op: str) -> float:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    raise ValueError("Unsupported operator")


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _collect_used_names(ir_code: list[str]) -> set[str]:
    used: set[str] = set()
    for line in ir_code:
        target, expr = _parse_assignment(line)
        if target is not None and expr is not None:
            used.update(_extract_names(expr))
            continue
        match = _IF_GOTO_RE.match(line)
        if match:
            used.update({match.group(1), match.group(3)})
            continue
        match = _PRINT_RE.match(line)
        if match:
            used.update(_extract_names(match.group(1)))
            continue
        match = _RETURN_RE.match(line)
        if match and match.group(1):
            used.update(_extract_names(match.group(1)))
    return used


def _extract_names(expr: str) -> set[str]:
    names: set[str] = set()
    for token in expr.split():
        if _parse_number_literal(token) is not None:
            continue
        if token in {"+", "-", "*", "/"}:
            continue
        names.add(token)
    return names
