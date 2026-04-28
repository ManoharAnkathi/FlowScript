class NumberLiteral:
    def __init__(self, value, line, column):
        self.value = value
        self.line = line
        self.column = column

class Identifier:
    def __init__(self, name, line, column):
        self.name = name
        self.line = line
        self.column = column

class BinaryOp:
    def __init__(self, op, left, right, line, column):
        self.op = op
        self.left = left
        self.right = right
        self.line = line
        self.column = column

class ComparisonOp:
    def __init__(self, op, left, right, line, column):
        self.op = op
        self.left = left
        self.right = right
        self.line = line
        self.column = column

class LetStatement:
    def __init__(self, name, expr, line, column):
        self.name = name
        self.expr = expr
        self.line = line
        self.column = column

class ConstStatement:
    def __init__(self, name, expr, line, column):
        self.name = name
        self.expr = expr
        self.line = line
        self.column = column

class AssignStatement:
    def __init__(self, name, expr, line, column):
        self.name = name
        self.expr = expr
        self.line = line
        self.column = column

class PrintStatement:
    def __init__(self, expr, line, column):
        self.expr = expr
        self.line = line
        self.column = column

class IfStatement:
    def __init__(self, condition, body, line, column):
        self.condition = condition
        self.body = body
        self.line = line
        self.column = column

class RepeatStatement:
    def __init__(self, count_expr, body, line, column):
        self.count_expr = count_expr
        self.body = body
        self.line = line
        self.column = column

class ForStatement:
    def __init__(self, loop_var, start_expr, end_expr, body, line, column):
        self.loop_var = loop_var
        self.start_expr = start_expr
        self.end_expr = end_expr
        self.body = body
        self.line = line
        self.column = column

class WhileStatement:
    def __init__(self, condition, body, line, column):
        self.condition = condition
        self.body = body
        self.line = line
        self.column = column

class FunctionDeclarationStatement:
    def __init__(self, name, body, line, column):
        self.name = name
        self.body = body
        self.line = line
        self.column = column

class ReturnStatement:
    def __init__(self, expr, line, column):
        self.expr = expr
        self.line = line
        self.column = column

class ContinueStatement:
    def __init__(self, line, column):
        self.line = line
        self.column = column

class BreakStatement:
    def __init__(self, line, column):
        self.line = line
        self.column = column

class Program:
    def __init__(self, statements):
        self.statements = statements

# Type aliases for compatibility with other modules
Statement = None  # Placeholder for type compatibility