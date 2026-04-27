from __future__ import annotations

from dataclasses import dataclass

from parser import (
    AssignStatement,
    BinaryOp,
    ConstStatement,
    Expr,
    Identifier,
    LetStatement,
    NumberLiteral,
    PrintStatement,
    Program,
)


class SemanticError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


@dataclass(frozen=True)
class SymbolInfo:
    declared_line: int
    declared_column: int
    is_const: bool


@dataclass(frozen=True)
class SemanticResult:
    symbols: dict[str, SymbolInfo]
    known_values: dict[str, float | None]
    warnings: list[str]


class SemanticAnalyzer:
    def __init__(self) -> None:
        self._symbols: dict[str, SymbolInfo] = {}
        self._known_values: dict[str, float | None] = {}
        self._read_counts: dict[str, int] = {}

    def analyze(self, program: Program) -> SemanticResult:
        for statement in program.statements:
            if isinstance(statement, LetStatement):
                self._analyze_let(statement)

            elif isinstance(statement, ConstStatement):
                self._analyze_const(statement)

            elif isinstance(statement, AssignStatement):
                self._analyze_assign(statement)

            elif isinstance(statement, PrintStatement):
                _, value = self._analyze_expr(statement.expr)

                # ✅ FIX: actually print output
                if value is not None:
                    print(value)
                else:
                    print("Unknown value")

            else:
                raise SemanticError("Unsupported statement", 1, 1)

        warnings = self._collect_warnings()

        return SemanticResult(
            symbols=dict(self._symbols),
            known_values=dict(self._known_values),
            warnings=warnings,
        )

    def _analyze_let(self, statement: LetStatement) -> None:
        if statement.name in self._symbols:
            previous = self._symbols[statement.name]
            raise SemanticError(
                f"Variable '{statement.name}' already declared at line {previous.declared_line}",
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)

        self._symbols[statement.name] = SymbolInfo(
            statement.line,
            statement.column,
            is_const=False,
        )

        self._known_values[statement.name] = constant_value
        self._read_counts.setdefault(statement.name, 0)

    def _analyze_const(self, statement: ConstStatement) -> None:
        if statement.name in self._symbols:
            previous = self._symbols[statement.name]
            raise SemanticError(
                f"Variable '{statement.name}' already declared at line {previous.declared_line}",
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)

        self._symbols[statement.name] = SymbolInfo(
            statement.line,
            statement.column,
            is_const=True,
        )

        self._known_values[statement.name] = constant_value
        self._read_counts.setdefault(statement.name, 0)

    def _analyze_assign(self, statement: AssignStatement) -> None:
        if statement.name not in self._symbols:
            raise SemanticError(
                f"Variable '{statement.name}' used before declaration",
                statement.line,
                statement.column,
            )

        if self._symbols[statement.name].is_const:
            raise SemanticError(
                f"Cannot reassign constant '{statement.name}'",
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)
        self._known_values[statement.name] = constant_value

    def _analyze_expr(self, expr: Expr) -> tuple[str, float | None]:
        if isinstance(expr, NumberLiteral):
            return "number", float(expr.value)

        if isinstance(expr, Identifier):
            if expr.name not in self._symbols:
                raise SemanticError(
                    f"Variable '{expr.name}' used before declaration",
                    expr.line,
                    expr.column,
                )

            self._read_counts[expr.name] = self._read_counts.get(expr.name, 0) + 1
            return "number", self._known_values.get(expr.name)

        if isinstance(expr, BinaryOp):
            left_type, left_value = self._analyze_expr(expr.left)
            right_type, right_value = self._analyze_expr(expr.right)

            if left_type != "number" or right_type != "number":
                raise SemanticError(
                    "Only numeric expressions are supported",
                    expr.line,
                    expr.column,
                )

            # ✅ Division by zero check
            if expr.op == "/" and right_value == 0:
                raise SemanticError(
                    "Division by zero detected",
                    expr.line,
                    expr.column,
                )

            # If unknown values → propagate None
            if left_value is None or right_value is None:
                return "number", None

            if expr.op == "+":
                return "number", left_value + right_value

            if expr.op == "-":
                return "number", left_value - right_value

            if expr.op == "*":
                return "number", left_value * right_value

            if expr.op == "/":
                return "number", left_value / right_value

            raise SemanticError(
                f"Unsupported operator '{expr.op}'",
                expr.line,
                expr.column,
            )

        raise SemanticError("Invalid expression", 1, 1)

    def _collect_warnings(self) -> list[str]:
        warnings: list[str] = []

        for name, symbol in sorted(
            self._symbols.items(), key=lambda item: item[1].declared_line
        ):
            reads = self._read_counts.get(name, 0)

            if reads == 0:
                kind = "Constant" if symbol.is_const else "Variable"
                warnings.append(
                    f"Warning: {kind} '{name}' declared at line {symbol.declared_line} is never used"
                )

        return warnings


def analyze_program(program: Program) -> SemanticResult:
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(program)
