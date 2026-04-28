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


class IRProgram:
    def __init__(self, instructions=None, metadata=None):
        self.instructions = instructions if instructions is not None else []
        self.metadata = metadata if metadata is not None else {}


class IRGenerator:
    def __init__(self):
        self.code = []
        self._temp_counter = 0
        self._label_counter = 0
        self._loop_stack = []

    def new_temp(self):
        self._temp_counter += 1
        return "t" + str(self._temp_counter)

    def new_label(self):
        self._label_counter += 1
        return "L" + str(self._label_counter)

    def generate(self, node):
        if isinstance(node, Program):
            for statement in node.statements:
                self.generate(statement)
            return

        if isinstance(node, (LetStatement, ConstStatement, AssignStatement)):
            target = node.name
            value = self.generate_expr(node.expr)
            self.code.append(target + " = " + value)
            return

        if isinstance(node, PrintStatement):
            value = self.generate_expr(node.expr)
            self.code.append("print " + value)
            return

        if isinstance(node, IfStatement):
            true_label = self.new_label()
            end_label = self.new_label()
            left, op, right = self._generate_condition(node.condition)
            self.code.append("if " + left + " " + op + " " + right + " goto " + true_label)
            self.code.append("goto " + end_label)
            self.code.append(true_label + ":")
            for child in node.body:
                self.generate(child)
            self.code.append(end_label + ":")
            return

        if isinstance(node, RepeatStatement):
            count = self.generate_expr(node.count_expr)
            counter = self.new_temp()
            check_label = self.new_label()
            inc_label = self.new_label()
            end_label = self.new_label()

            self.code.append(counter + " = 0")
            self.code.append(check_label + ":")
            self.code.append("if " + counter + " >= " + count + " goto " + end_label)

            self._loop_stack.append((inc_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append(inc_label + ":")
            self.code.append(counter + " = " + counter + " + 1")
            self.code.append("goto " + check_label)
            self.code.append(end_label + ":")
            return

        if isinstance(node, ForStatement):
            start_value = self.generate_expr(node.start_expr)
            end_value = self.generate_expr(node.end_expr)
            check_label = self.new_label()
            inc_label = self.new_label()
            end_label = self.new_label()

            self.code.append(node.loop_var + " = " + start_value)
            self.code.append(check_label + ":")
            self.code.append("if " + node.loop_var + " > " + end_value + " goto " + end_label)

            self._loop_stack.append((inc_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append(inc_label + ":")
            self.code.append(node.loop_var + " = " + node.loop_var + " + 1")
            self.code.append("goto " + check_label)
            self.code.append(end_label + ":")
            return

        if isinstance(node, WhileStatement):
            check_label = self.new_label()
            body_label = self.new_label()
            end_label = self.new_label()
            left, op, right = self._generate_condition(node.condition)

            self.code.append(check_label + ":")
            self.code.append("if " + left + " " + op + " " + right + " goto " + body_label)
            self.code.append("goto " + end_label)
            self.code.append(body_label + ":")

            self._loop_stack.append((check_label, end_label))
            try:
                for child in node.body:
                    self.generate(child)
            finally:
                self._loop_stack.pop()

            self.code.append("goto " + check_label)
            self.code.append(end_label + ":")
            return

        if isinstance(node, FunctionDeclarationStatement):
            self.code.append("func " + node.name + ":")
            for child in node.body:
                self.generate(child)
            self.code.append("endfunc " + node.name)
            return

        if isinstance(node, ReturnStatement):
            if node.expr is None:
                self.code.append("return")
            else:
                value = self.generate_expr(node.expr)
                self.code.append("return " + value)
            return

        if isinstance(node, ContinueStatement):
            if not self._loop_stack:
                raise ValueError("continue used outside loop")
            continue_label, _ = self._loop_stack[-1]
            self.code.append("goto " + continue_label)
            return

        if isinstance(node, BreakStatement):
            if not self._loop_stack:
                raise ValueError("break used outside loop")
            _, break_label = self._loop_stack[-1]
            self.code.append("goto " + break_label)
            return

        raise ValueError("Unsupported statement")

    def generate_expr(self, node):
        if isinstance(node, NumberLiteral):
            return str(node.value)

        if isinstance(node, Identifier):
            return node.name

        if isinstance(node, BinaryOp):
            left = self.generate_expr(node.left)
            right = self.generate_expr(node.right)
            temp = self.new_temp()
            self.code.append(temp + " = " + left + " " + node.op + " " + right)
            return temp

        raise ValueError("Unsupported expression")

    def _generate_condition(self, node):
        left = self.generate_expr(node.left)
        right = self.generate_expr(node.right)
        return left, node.op, right


def build_ir(program, semantic_result):
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
