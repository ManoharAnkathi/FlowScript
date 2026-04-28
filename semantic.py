from ast_nodes import (
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
    WhileStatement,
)


class SemanticError(Exception):
    def __init__(self, message, line, column):
        super(SemanticError, self).__init__(message + " at line " + str(line) + ", column " + str(column))
        self.line = line
        self.column = column


class SymbolInfo:
    def __init__(self, declared_line, declared_column, is_const):
        self.declared_line = declared_line
        self.declared_column = declared_column
        self.is_const = is_const


class SemanticResult:
    def __init__(self, symbols, known_values, warnings):
        self.symbols = symbols
        self.known_values = known_values
        self.warnings = warnings


class SemanticAnalyzer:
    def __init__(self):
        self._symbols = {}
        self._known_values = {}
        self._read_counts = {}
        self._loop_depth = 0
        self._function_depth = 0
        
        self._handlers = {
            "LetStatement": self._analyze_let,
            "ConstStatement": self._analyze_const,
            "AssignStatement": self._analyze_assign,
            "PrintStatement": self._analyze_print,
            "IfStatement": self._analyze_if,
            "RepeatStatement": self._analyze_repeat,
            "ForStatement": self._analyze_for,
            "WhileStatement": self._analyze_while,
            "FunctionDeclarationStatement": self._analyze_function,
            "ReturnStatement": self._analyze_return,
            "ContinueStatement": self._analyze_continue,
            "BreakStatement": self._analyze_break,
        }

    def analyze(self, program):
        for statement in program.statements:
            self._analyze_statement(statement)

        warnings = self._collect_warnings()
        return SemanticResult(
            symbols=dict(self._symbols),
            known_values=dict(self._known_values),
            warnings=warnings,
        )

    def _analyze_statement(self, statement):
        stmt_type = statement.__class__.__name__
        handler = self._handlers.get(stmt_type)
        if handler:
            handler(statement)
        else:
            raise SemanticError("Unsupported statement", 1, 1)
    
    def _analyze_print(self, statement):
        self._analyze_expr(statement.expr)
    
    def _analyze_if(self, statement):
        self._analyze_condition(statement.condition)
        for child in statement.body:
            self._analyze_statement(child)
    
    def _analyze_repeat(self, statement):
        self._analyze_expr(statement.count_expr)
        self._loop_depth += 1
        try:
            for child in statement.body:
                self._analyze_statement(child)
        finally:
            self._loop_depth -= 1
    
    def _analyze_while(self, statement):
        self._analyze_condition(statement.condition)
        self._loop_depth += 1
        try:
            for child in statement.body:
                self._analyze_statement(child)
        finally:
            self._loop_depth -= 1
    
    def _analyze_function(self, statement):
        self._function_depth += 1
        try:
            for child in statement.body:
                self._analyze_statement(child)
        finally:
            self._function_depth -= 1
    
    def _analyze_return(self, statement):
        if self._function_depth <= 0:
            raise SemanticError("'return' is only allowed inside a function", statement.line, statement.column)
        if statement.expr is not None:
            self._analyze_expr(statement.expr)
    
    def _analyze_continue(self, statement):
        if self._loop_depth <= 0:
            raise SemanticError("'continue' is only allowed inside a loop", statement.line, statement.column)
    
    def _analyze_break(self, statement):
        if self._loop_depth <= 0:
            raise SemanticError("'break' is only allowed inside a loop", statement.line, statement.column)
    
    def _analyze_for(self, statement):
        self._analyze_expr(statement.start_expr)
        self._analyze_expr(statement.end_expr)

        if statement.loop_var not in self._symbols:
            self._symbols[statement.loop_var] = SymbolInfo(statement.line, statement.column, is_const=False)
            self._known_values.setdefault(statement.loop_var, None)
            self._read_counts.setdefault(statement.loop_var, 0)
        elif self._symbols[statement.loop_var].is_const:
            raise SemanticError(
                "Loop variable '" + statement.loop_var + "' cannot be const",
                statement.line,
                statement.column,
            )

        self._loop_depth += 1
        try:
            for child in statement.body:
                self._analyze_statement(child)
        finally:
            self._loop_depth -= 1

    def _analyze_let(self, statement):
        if statement.name in self._symbols:
            previous = self._symbols[statement.name]
            raise SemanticError(
                "Variable '" + statement.name + "' already declared at line " + str(previous.declared_line),
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)
        self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=False)
        self._known_values[statement.name] = constant_value
        self._read_counts.setdefault(statement.name, 0)

    def _analyze_const(self, statement):
        if statement.name in self._symbols:
            previous = self._symbols[statement.name]
            raise SemanticError(
                "Variable '" + statement.name + "' already declared at line " + str(previous.declared_line),
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)
        self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=True)
        self._known_values[statement.name] = constant_value
        self._read_counts.setdefault(statement.name, 0)

    def _analyze_assign(self, statement):
        if statement.name not in self._symbols:
            # FlowScript allows variable introduction via assignment.
            self._symbols[statement.name] = SymbolInfo(statement.line, statement.column, is_const=False)
            self._read_counts.setdefault(statement.name, 0)

        if self._symbols[statement.name].is_const:
            raise SemanticError(
                "Cannot reassign constant '" + statement.name + "'",
                statement.line,
                statement.column,
            )

        _, constant_value = self._analyze_expr(statement.expr)
        self._known_values[statement.name] = constant_value

    def _analyze_expr(self, expr):
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
                "Unsupported operator '" + expr.op + "'",
                expr.line,
                expr.column,
            )

        raise SemanticError("Invalid expression", 1, 1)

    def _analyze_condition(self, condition):
        left_type, _ = self._analyze_expr(condition.left)
        right_type, _ = self._analyze_expr(condition.right)

        if left_type != "number" or right_type != "number":
            raise SemanticError("Condition operands must be numeric", condition.line, condition.column)

        if condition.op != ">":
            raise SemanticError("Unsupported condition operator '" + condition.op + "'", condition.line, condition.column)

    def _collect_warnings(self):
        warnings = []

        for name, symbol in sorted(self._symbols.items(), key=lambda item: item[1].declared_line):
            reads = self._read_counts.get(name, 0)
            if reads == 0:
                kind = "Constant" if symbol.is_const else "Variable"
                warnings.append(
                    "Warning: " + kind + " '" + name + "' declared at line " + str(symbol.declared_line) + " is never used"
                )

        return warnings


def analyze_program(program):
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(program)
