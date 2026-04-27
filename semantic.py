from __future__ import annotations

from dataclasses import dataclass

from parser import (
    AssignStatement,
    BinaryOp,
    BreakStatement,
    ComparisonOp,
    ConstStatement,
    ContinueStatement,
    Expr,
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
        self._loop_depth = 0
        self._function_depth = 0

    def analyze(self, program: Program) -> SemanticResult:
        for statement in program.statements:
            self._analyze_statement(statement)

        warnings = self._collect_warnings()
        return SemanticResult(
            symbols=dict(self._symbols),
            known_values=dict(self._known_values),
            warnings=warnings,
        )

    def _analyze_statement(self, statement: Statement) -> None:
        if isinstance(statement, LetStatement):
            self._analyze_let(statement)
            return

        if isinstance(statement, ConstStatement):
            self._analyze_const(statement)
            return

        if isinstance(statement, AssignStatement):
            self._analyze_assign(statement)
            return

        if isinstance(statement, PrintStatement):
            self._analyze_expr(statement.expr)
            return

        if isinstance(statement, IfStatement):
            self._analyze_condition(statement.condition)
            for child in statement.body:
                self._analyze_statement(child)
            return

        if isinstance(statement, RepeatStatement):
            self._analyze_expr(statement.count_expr)
            self._loop_depth += 1
            try:
                for child in statement.body:
                    self._analyze_statement(child)
            finally:
                self._loop_depth -= 1
            return

        if isinstance(statement, ForStatement):
            self._analyze_expr(statement.start_expr)
            self._analyze_expr(statement.end_expr)

            if statement.loop_var not in self._symbols:
                self._symbols[statement.loop_var] = SymbolInfo(statement.line, statement.column, is_const=False)
                self._known_values.setdefault(statement.loop_var, None)
                self._read_counts.setdefault(statement.loop_var, 0)
            elif self._symbols[statement.loop_var].is_const:
                raise SemanticError(
                    f"Loop variable '{statement.loop_var}' cannot be const",
                    statement.line,
                    statement.column,
                )

            self._loop_depth += 1
            try:
                for child in statement.body:
                    self._analyze_statement(child)
            finally:
                self._loop_depth -= 1
            return

        if isinstance(statement, WhileStatement):
            self._analyze_condition(statement.condition)
            self._loop_depth += 1
            try:
                for child in statement.body:
                    self._analyze_statement(child)
            finally:
                self._loop_depth -= 1
            return

        if isinstance(statement, FunctionDeclarationStatement):
            self._function_depth += 1
            try:
                for child in statement.body:
                    self._analyze_statement(child)
            finally:
                self._function_depth -= 1
            return

        if isinstance(statement, ReturnStatement):
            if self._function_depth <= 0:
                raise SemanticError("'return' is only allowed inside a function", statement.line, statement.column)
            if statement.expr is not None:
                self._analyze_expr(statement.expr)
            return

        if isinstance(statement, ContinueStatement):
            if self._loop_depth <= 0:
                raise SemanticError("'continue' is only allowed inside a loop", statement.line, statement.column)
            return

        if isinstance(statement, BreakStatement):
            if self._loop_depth <= 0:
                raise SemanticError("'break' is only allowed inside a loop", statement.line, statement.column)
            return

        raise SemanticError("Unsupported statement", 1, 1)

    def _analyze_let(self, statement: LetStatement) -> None:
        if statement.name in self._symbols:
            previous = self._symbols[statement.name]
            raise SemanticError(
                f"Variable '{statement.name}' already declared at line {previous.declared_line}",
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)
        self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=False)
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
        self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=True)
        self._known_values[statement.name] = constant_value
        self._read_counts.setdefault(statement.name, 0)

    def _analyze_assign(self, statement: AssignStatement) -> None:
        if statement.name not in self._symbols:
            # FlowScript allows variable introduction via assignment.
            self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=False)
            self._read_counts.setdefault(statement.name, 0)

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

            if expr.op == "/" and right_value == 0:
                raise SemanticError(
                    "Division by zero detected",
                    expr.line,
                    expr.column,
                )

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

    def _analyze_condition(self, condition: ComparisonOp) -> None:
        left_type, _ = self._analyze_expr(condition.left)
        right_type, _ = self._analyze_expr(condition.right)

        if left_type != "number" or right_type != "number":
            raise SemanticError("Condition operands must be numeric", condition.line, condition.column)

        if condition.op != ">":
            raise SemanticError(f"Unsupported condition operator '{condition.op}'", condition.line, condition.column)

    def _collect_warnings(self) -> list[str]:
        warnings: list[str] = []

        for name, symbol in sorted(self._symbols.items(), key=lambda item: item[1].declared_line):
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
