import argparse
import sys
from pathlib import Path

from codegen import generate_python
from ir import build_ir
from optimizer import optimize_ir
from lexer import LexerError, tokenize_file
from parser import ParserError, parse
from semantic import SemanticError, analyze_program
from ast_nodes import (
    LetStatement, ConstStatement, AssignStatement, PrintStatement,
    IfStatement, RepeatStatement, ForStatement, WhileStatement,
    FunctionDeclarationStatement, ReturnStatement, ContinueStatement, BreakStatement,
    NumberLiteral, Identifier, BinaryOp, ComparisonOp
)


def _format_token(token):
    return str(token.line) + ":" + str(token.column) + "  " + token.type.ljust(8) + "  " + token.value


def _iter_display_tokens(file_path, include_newlines):
    for token in tokenize_file(file_path):
        if not include_newlines and token.type == "NEWLINE":
            continue
        yield token


def run_token_phase(file_path, token_limit, include_newlines):
    print("--- TOKENS ---")
    printed = 0
    total = 0

    for token in _iter_display_tokens(file_path, include_newlines=include_newlines):
        total += 1
        if printed < token_limit:
            print(_format_token(token))
            printed += 1

    if total > token_limit:
        print("... output truncated: showing first " + str(token_limit) + " of " + str(total) + " tokens")
    else:
        print("Total tokens: " + str(total))

    return total


def run_parse_phase(file_path, ast_limit, show_ast):
    program = parse(tokenize_file(file_path))
    print("--- PARSER ---")
    print("Parsed successfully: " + str(len(program.statements)) + " statements")

    if show_ast:
        print("--- AST ---")
        for index, statement in enumerate(program.statements[:ast_limit], start=1):
            print(str(index).rjust(4) + ": " + str(statement))
        if len(program.statements) > ast_limit:
            print("... output truncated: showing first " + str(ast_limit) + " statements")

    return program


def run_semantic_phase(program, symbol_limit, show_symbols):
    result = analyze_program(program)
    print("--- SEMANTIC ---")
    print("Semantic analysis passed")
    print("Declared variables: " + str(len(result.symbols)))

    if result.warnings:
        print("--- WARNINGS ---")
        for warning in result.warnings:
            print(warning)

    if show_symbols:
        print("--- SYMBOL TABLE ---")
        for index, name in enumerate(sorted(result.symbols.keys()), start=1):
            if index > symbol_limit:
                print("... output truncated: showing first " + str(symbol_limit) + " symbols")
                break

            value = result.known_values.get(name)
            value_text = "unknown" if value is None else str(value)
            location = result.symbols[name]
            kind = "const" if location.is_const else "var"
            print(
                name.ljust(20) + " type=" + kind.ljust(5) + " value=" + value_text.ljust(10) + " "
                "declared_at=" + str(location.declared_line) + ":" + str(location.declared_column)
            )

    return result


def _print_error_context(file_path, line, column):
    if line <= 0 or column <= 0:
        return

    try:
        source_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    if line > len(source_lines):
        return

    source_line = source_lines[line - 1]
    pointer_index = min(max(column - 1, 0), max(len(source_line) - 1, 0))
    print(str(line).rjust(4) + " | " + source_line, file=sys.stderr)
    print("     | " + (" " * pointer_index) + "^", file=sys.stderr)


def _print_structured_tokens(file_path, token_limit):
    print("[1] Lexical Analysis")
    printed = 0
    total = 0

    for token in tokenize_file(file_path):
        if token.type == "NEWLINE":
            continue
        total += 1
        if printed < token_limit:
            print("  " + token.type.ljust(12) + " -> " + token.value.ljust(15))
            printed += 1

    if total > token_limit:
        print("  ... (" + str(total - printed) + " more tokens)")


def _format_statement(stmt):
    if isinstance(stmt, LetStatement):
        return "LET " + stmt.name + " := " + _format_expr(stmt.expr)
    elif isinstance(stmt, ConstStatement):
        return "CONST " + stmt.name + " := " + _format_expr(stmt.expr)
    elif isinstance(stmt, AssignStatement):
        return "ASSIGN " + stmt.name + " := " + _format_expr(stmt.expr)
    elif isinstance(stmt, PrintStatement):
        return "PRINT => " + _format_expr(stmt.expr)
    elif isinstance(stmt, IfStatement):
        return "IF " + _format_condition(stmt.condition) + " THEN ... ENDIF"
    elif isinstance(stmt, RepeatStatement):
        return "REPEAT " + _format_expr(stmt.count_expr) + " ... ENDREPEAT"
    elif isinstance(stmt, ForStatement):
        return "FOR " + stmt.loop_var + " := " + _format_expr(stmt.start_expr) + " TO " + _format_expr(stmt.end_expr) + " ... ENDFOR"
    elif isinstance(stmt, WhileStatement):
        return "WHILE " + _format_condition(stmt.condition) + " ... ENDWHILE"
    elif isinstance(stmt, FunctionDeclarationStatement):
        return "FUNCTION " + stmt.name + " ... ENDFUNCTION"
    elif isinstance(stmt, ReturnStatement):
        if stmt.expr:
            return "RETURN " + _format_expr(stmt.expr)
        else:
            return "RETURN"
    elif isinstance(stmt, ContinueStatement):
        return "CONTINUE"
    elif isinstance(stmt, BreakStatement):
        return "BREAK"
    else:
        return str(stmt)


def _format_expr(expr):
    if isinstance(expr, NumberLiteral):
        return str(expr.value)
    elif isinstance(expr, Identifier):
        return expr.name
    elif isinstance(expr, BinaryOp):
        left = _format_expr(expr.left)
        right = _format_expr(expr.right)
        return "(" + left + " " + expr.op + " " + right + ")"
    else:
        return str(expr)


def _format_condition(cond):
    if isinstance(cond, ComparisonOp):
        left = _format_expr(cond.left)
        right = _format_expr(cond.right)
        return "(" + left + " " + cond.op + " " + right + ")"
    else:
        return str(cond)


def _print_structured_ast(program, ast_limit):
    print("\n[2] Syntax Analysis")
    for index, statement in enumerate(program.statements[:ast_limit], start=1):
        stmt_str = _format_statement(statement)
        print("  " + stmt_str)

    if len(program.statements) > ast_limit:
        print("  ... (" + str(len(program.statements) - ast_limit) + " more statements)")


def _print_structured_symbols(result, symbol_limit):
    print("\n[3] Semantic Analysis")
    count = 0
    for name in sorted(result.symbols.keys()):
        if count >= symbol_limit:
            print("  ... (" + str(len(result.symbols) - symbol_limit) + " more symbols)")
            break
        
        location = result.symbols[name]
        kind = "const" if location.is_const else "var"
        value = result.known_values.get(name, "unknown")
        print("  " + name + " -> " + kind + " (value: " + str(value) + ")")
        count += 1


def _print_structured_ir(ir_program, title_num, title_text):
    print("\n[" + str(title_num) + "] " + title_text)
    if not ir_program.instructions:
        print("  (empty)")
        return

    for index, instruction in enumerate(ir_program.instructions, start=1):
        print("  " + str(index).rjust(3) + ". " + instruction)


def _print_structured_asm(asm_code):
    print("\n[6] Target Code")
    if not asm_code:
        print("  (empty)")
        return

    lines = asm_code.split("\n")
    for line in lines:
        if line.strip():
            print("  " + line)




def _print_ir(ir_program, title):
    if title:
        print(title)
    if not ir_program.instructions:
        print("(empty)")
        return

    for index, instruction in enumerate(ir_program.instructions, start=1):
        print(str(index).rjust(4) + ": " + instruction)


def _print_asm(asm_code, title, asm_limit=None):
    if title:
        print(title)
    if not asm_code:
        print("(empty)")
        return

    lines = asm_code.split("\n")
    for index, line in enumerate(lines, start=1):
        if asm_limit and index > asm_limit:
            print("... output truncated: showing first " + str(asm_limit) + " lines")
            break
        print(line)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="FlowScript compiler - lexer, parser, semantic analyzer, IR generator, optimizer, and code generator")
    parser.add_argument("input", type=Path, help="Path to .flow source file")
    parser.add_argument(
        "--phase",
        choices=["tokens", "parse", "semantic", "all"],
        default="all",
        help="Which phase(s) to run"
    )
    parser.add_argument("--show-ast", action="store_true", help="Print parsed AST statements")
    parser.add_argument("--show-symbols", action="store_true", help="Print semantic symbol table")
    parser.add_argument("--show-ir", action="store_true", help="Print generated three-address IR")
    parser.add_argument("--show-optimized-ir", action="store_true", help="Print optimized three-address IR")
    parser.add_argument("--show-asm", action="store_true", help="Print generated assembly code")
    parser.add_argument("--asm-file", type=Path, help="Write assembly code to this file")
    parser.add_argument("--token-limit", type=int, default=200, help="Max number of tokens to print")
    parser.add_argument("--ast-limit", type=int, default=60, help="Max number of AST statements to print")
    parser.add_argument("--symbol-limit", type=int, default=100, help="Max number of symbols to print")
    parser.add_argument("--asm-limit", type=int, default=200, help="Max number of assembly lines to print")
    parser.add_argument("--structured", action="store_true", help="Use structured output format [1] [2] [3] etc")
    return parser


def main():
    args = build_arg_parser().parse_args()
    file_path = args.input

    if not file_path.exists():
        print("Error: Input file not found: " + str(file_path), file=sys.stderr)
        return 1

    if args.token_limit <= 0 or args.ast_limit <= 0 or args.symbol_limit <= 0:
        print("Error: limit values must be positive integers", file=sys.stderr)
        return 1

    try:
        if args.structured:
            _print_structured_tokens(file_path, token_limit=args.token_limit)
            
            program = parse(tokenize_file(file_path))
            _print_structured_ast(program, ast_limit=args.ast_limit)
            
            semantic_result = analyze_program(program)
            _print_structured_symbols(semantic_result, symbol_limit=args.symbol_limit)
            
            ir_program = build_ir(program, semantic_result)
            _print_structured_ir(ir_program, 4, "Intermediate Code")
            
            optimized_ir, _ = optimize_ir(ir_program)
            _print_structured_ir(optimized_ir, 5, "Optimized Code")
            
            asm_code = generate_python(optimized_ir)
            _print_structured_asm(asm_code)
            
            if args.asm_file:
                args.asm_file.write_text(asm_code, encoding="utf-8")

        else:
            program = None
            semantic_result = None

            if args.phase == "tokens":
                run_token_phase(file_path, token_limit=args.token_limit, include_newlines=False)

            elif args.phase == "parse":
                run_token_phase(file_path, token_limit=args.token_limit, include_newlines=False)
                print("")
                program = run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=args.show_ast)

            elif args.phase == "semantic":
                run_token_phase(file_path, token_limit=args.token_limit, include_newlines=False)
                print("")
                program = run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=False)
                print("")
                semantic_result = run_semantic_phase(program, symbol_limit=args.symbol_limit, show_symbols=args.show_symbols)

            elif args.phase == "all":
                run_token_phase(file_path, token_limit=args.token_limit, include_newlines=False)
                print("")
                program = run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=args.show_ast)
                print("")
                semantic_result = run_semantic_phase(program, symbol_limit=args.symbol_limit, show_symbols=args.show_symbols)

                ir_program = build_ir(program, semantic_result)
                if args.show_ir:
                    print("\n--- INTERMEDIATE CODE (IR) ---")
                    _print_ir(ir_program, "")

                optimized_ir, _ = optimize_ir(ir_program)
                if args.show_optimized_ir:
                    print("\n--- OPTIMIZED INTERMEDIATE CODE ---")
                    _print_ir(optimized_ir, "")

                if args.show_asm or args.asm_file:
                    asm_code = generate_python(optimized_ir)
                    if args.show_asm:
                        print("\n--- ASSEMBLY CODE ---")
                        _print_asm(asm_code, "", asm_limit=args.asm_limit)
                    if args.asm_file:
                        args.asm_file.write_text(asm_code, encoding="utf-8")
                        print("\nAssembly code written to " + str(args.asm_file))

        return 0

    except (LexerError, ParserError, SemanticError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        line = getattr(exc, "line", 0)
        column = getattr(exc, "column", 0)
        _print_error_context(file_path, line, column)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())