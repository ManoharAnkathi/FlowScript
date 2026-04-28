import re
from ir import IRProgram


class OptimizationReport:
    def __init__(self, passes_run, changes_made, notes):
        self.passes_run = passes_run
        self.changes_made = changes_made
        self.notes = notes


class Optimizer:
    def __init__(self):
        self.constants = {}

    def optimize(self, ir_code):
        constants = self._collect_constants(ir_code)
        propagated = self._propagate_constants(ir_code, constants)
        folded = self._fold_constants(propagated)
        cleaned = self._eliminate_dead_temps(folded)
        return cleaned

    def _collect_constants(self, ir_code):
        constants = {}
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

    def _propagate_constants(self, ir_code, constants):
        return [self._propagate_line(line, constants) for line in ir_code]

    def _propagate_line(self, line, constants):
        target, expr = _parse_assignment(line)
        if target is not None and expr is not None:
            return target + " = " + _replace_in_expr(expr, constants)

        match = _IF_GOTO_RE.match(line)
        if match:
            left, op, right, label = match.groups()
            left = _replace_token(left, constants)
            right = _replace_token(right, constants)
            return "if " + left + " " + op + " " + right + " goto " + label

        match = _PRINT_RE.match(line)
        if match:
            expr = match.group(1)
            return "print " + _replace_in_expr(expr, constants)

        match = _RETURN_RE.match(line)
        if match:
            expr = match.group(1)
            if expr is None:
                return line
            return "return " + _replace_in_expr(expr, constants)

        return line

    def _fold_constants(self, ir_code):
        folded = []
        for line in ir_code:
            target, expr = _parse_assignment(line)
            if target is None or expr is None:
                folded.append(line)
                continue

            folded_expr = _try_fold_expr(expr)
            folded.append(target + " = " + folded_expr)
        return folded

    def _eliminate_dead_temps(self, ir_code):
        used = _collect_used_names(ir_code)
        cleaned = []
        for line in ir_code:
            target, expr = _parse_assignment(line)
            if target is not None and expr is not None and _TEMP_RE.fullmatch(target) and target not in used:
                continue
            cleaned.append(line)
        return cleaned


def optimize_ir(ir_program):
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


def _parse_assignment(line):
    match = _ASSIGN_RE.match(line)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _parse_number_literal(text):
    stripped = text.strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", stripped) is None:
        return None
    return stripped


def _replace_in_expr(expr, constants):
    tokens = expr.split()
    replaced = [_replace_token(token, constants) for token in tokens]
    return " ".join(replaced)


def _replace_token(token, constants):
    return constants.get(token, token)


def _try_fold_expr(expr):
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


def _apply_numeric_op(left, right, op):
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    raise ValueError("Unsupported operator")


def _format_number(value):
    if value.is_integer():
        return str(int(value))
    return str(value)


def _collect_used_names(ir_code):
    used = set()
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


def _extract_names(expr):
    names = set()
    for token in expr.split():
        if _parse_number_literal(token) is not None:
            continue
        if token in {"+", "-", "*", "/"}:
            continue
        names.add(token)
    return names
