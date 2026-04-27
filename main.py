from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexer import LexerError, Token, tokenize_file
from parser import ParserError, Program, parse
from semantic import SemanticError, SemanticResult, analyze_program


@dataclass(frozen=True)
class PhaseMetrics:
    duration_ms: float
    token_count: int | None = None
    statement_count: int | None = None
    symbol_count: int | None = None
    warning_count: int | None = None


def _format_token(token: Token) -> str:
    return f"{token.line}:{token.column}  {token.type:<8}  {token.value}"


def _iter_display_tokens(file_path: Path, include_newlines: bool):
    for token in tokenize_file(file_path):
        if not include_newlines and token.type == "NEWLINE":
            continue
        yield token


def run_token_phase(file_path: Path, token_limit: int, include_newlines: bool) -> int:
    print("--- TOKENS ---")
    printed = 0
    total = 0

    for token in _iter_display_tokens(file_path, include_newlines=include_newlines):
        total += 1
        if printed < token_limit:
            print(_format_token(token))
            printed += 1

    if total > token_limit:
        print(f"... output truncated: showing first {token_limit} of {total} tokens")
    else:
        print(f"Total tokens: {total}")

    return total


def run_parse_phase(file_path: Path, ast_limit: int, show_ast: bool) -> Program:
    program = parse(tokenize_file(file_path))
    print("--- PARSER ---")
    print(f"Parsed successfully: {len(program.statements)} statements")

    if show_ast:
        print("--- AST ---")
        for index, statement in enumerate(program.statements[:ast_limit], start=1):
            print(f"{index:>4}: {statement}")
        if len(program.statements) > ast_limit:
            print(f"... output truncated: showing first {ast_limit} statements")

    return program


def run_semantic_phase(program: Program, symbol_limit: int, show_symbols: bool) -> SemanticResult:
    result = analyze_program(program)
    print("--- SEMANTIC ---")
    print("Semantic analysis passed")
    print(f"Declared variables: {len(result.symbols)}")

    if result.warnings:
        print("--- WARNINGS ---")
        for warning in result.warnings:
            print(warning)

    if show_symbols:
        print("--- SYMBOL TABLE ---")
        for index, name in enumerate(sorted(result.symbols.keys()), start=1):
            if index > symbol_limit:
                print(f"... output truncated: showing first {symbol_limit} symbols")
                break

            value = result.known_values.get(name)
            value_text = "unknown" if value is None else str(value)
            location = result.symbols[name]
            kind = "const" if location.is_const else "var"
            print(
                f"{name:<20} type={kind:<5} value={value_text:<10} "
                f"declared_at={location.declared_line}:{location.declared_column}"
            )

    return result


def _print_error_context(file_path: Path, line: int, column: int) -> None:
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
    print(f"{line:>4} | {source_line}", file=sys.stderr)
    print(f"     | {' ' * pointer_index}^", file=sys.stderr)


def _print_profile(metrics: dict[str, PhaseMetrics]) -> None:
    print("--- PROFILE ---")
    total_ms = 0.0
    for phase_name in ("tokens", "parse", "semantic"):
        metric = metrics.get(phase_name)
        if metric is None:
            continue

        total_ms += metric.duration_ms
        extras: list[str] = []
        if metric.token_count is not None:
            extras.append(f"tokens={metric.token_count}")
        if metric.statement_count is not None:
            extras.append(f"statements={metric.statement_count}")
        if metric.symbol_count is not None:
            extras.append(f"symbols={metric.symbol_count}")
        if metric.warning_count is not None:
            extras.append(f"warnings={metric.warning_count}")

        extra_text = " " if not extras else " " + " ".join(extras)
        print(f"{phase_name:<8} {metric.duration_ms:>9.3f} ms{extra_text}")
    print(f"total    {total_ms:>9.3f} ms")


def _write_report_file(
    report_file: Path,
    input_file: Path,
    metrics: dict[str, PhaseMetrics],
    semantic_result: SemanticResult | None,
) -> None:
    report: dict[str, Any] = {
        "input_file": str(input_file),
        "phases": {},
    }

    for phase_name, metric in metrics.items():
        report["phases"][phase_name] = {
            "duration_ms": round(metric.duration_ms, 3),
            "token_count": metric.token_count,
            "statement_count": metric.statement_count,
            "symbol_count": metric.symbol_count,
            "warning_count": metric.warning_count,
        }

    if semantic_result is not None:
        report["semantic"] = {
            "declared_symbols": sorted(semantic_result.symbols.keys()),
            "warnings": semantic_result.warnings,
        }

    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FlowScript front-end compiler (lexer + parser + semantic analyzer)")
    parser.add_argument("input", type=Path, help="Path to .flow source file")
    parser.add_argument(
        "--phase",
        choices=["tokens", "parse", "semantic", "all"],
        default="all",
        help="Which phase(s) to run",
    )
    parser.add_argument("--token-limit", type=int, default=200, help="Max number of tokens to print")
    parser.add_argument("--ast-limit", type=int, default=60, help="Max number of AST statements to print")
    parser.add_argument("--symbol-limit", type=int, default=100, help="Max number of symbols to print")
    parser.add_argument("--show-ast", action="store_true", help="Print parsed AST statements")
    parser.add_argument("--show-symbols", action="store_true", help="Print semantic symbol table")
    parser.add_argument("--include-newlines", action="store_true", help="Include NEWLINE tokens in token output")
    parser.add_argument("--profile", action="store_true", help="Show phase timing and counts")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat semantic warnings as errors")
    parser.add_argument("--report-file", type=Path, help="Write compile report JSON to this path")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    file_path: Path = args.input

    if not file_path.exists():
        print(f"Error: Input file not found: {file_path}", file=sys.stderr)
        return 1

    if args.token_limit <= 0 or args.ast_limit <= 0 or args.symbol_limit <= 0:
        print("Error: limit values must be positive integers", file=sys.stderr)
        return 1

    metrics: dict[str, PhaseMetrics] = {}
    semantic_result: SemanticResult | None = None

    try:
        if args.phase == "tokens":
            start = time.perf_counter()
            token_count = run_token_phase(file_path, token_limit=args.token_limit, include_newlines=args.include_newlines)
            duration_ms = (time.perf_counter() - start) * 1000
            metrics["tokens"] = PhaseMetrics(duration_ms=duration_ms, token_count=token_count)
            if args.profile:
                _print_profile(metrics)
            if args.report_file is not None:
                _write_report_file(args.report_file, file_path, metrics, semantic_result)
            return 0

        if args.phase == "parse":
            start = time.perf_counter()
            run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=args.show_ast)
            duration_ms = (time.perf_counter() - start) * 1000
            program = parse(tokenize_file(file_path))
            metrics["parse"] = PhaseMetrics(duration_ms=duration_ms, statement_count=len(program.statements))
            if args.profile:
                _print_profile(metrics)
            if args.report_file is not None:
                _write_report_file(args.report_file, file_path, metrics, semantic_result)
            return 0

        if args.phase == "semantic":
            parse_start = time.perf_counter()
            program = run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=args.show_ast)
            parse_ms = (time.perf_counter() - parse_start) * 1000
            metrics["parse"] = PhaseMetrics(duration_ms=parse_ms, statement_count=len(program.statements))

            sem_start = time.perf_counter()
            semantic_result = run_semantic_phase(program, symbol_limit=args.symbol_limit, show_symbols=args.show_symbols)
            sem_ms = (time.perf_counter() - sem_start) * 1000
            metrics["semantic"] = PhaseMetrics(
                duration_ms=sem_ms,
                symbol_count=len(semantic_result.symbols),
                warning_count=len(semantic_result.warnings),
            )

            if args.profile:
                _print_profile(metrics)
            if args.report_file is not None:
                _write_report_file(args.report_file, file_path, metrics, semantic_result)
            if args.strict_warnings and semantic_result.warnings:
                print("Error: strict-warnings is enabled and semantic warnings were found", file=sys.stderr)
                return 1
            return 0

        token_start = time.perf_counter()
        token_count = run_token_phase(file_path, token_limit=args.token_limit, include_newlines=args.include_newlines)
        token_ms = (time.perf_counter() - token_start) * 1000
        metrics["tokens"] = PhaseMetrics(duration_ms=token_ms, token_count=token_count)

        parse_start = time.perf_counter()
        program = run_parse_phase(file_path, ast_limit=args.ast_limit, show_ast=args.show_ast)
        parse_ms = (time.perf_counter() - parse_start) * 1000
        metrics["parse"] = PhaseMetrics(duration_ms=parse_ms, statement_count=len(program.statements))

        sem_start = time.perf_counter()
        semantic_result = run_semantic_phase(program, symbol_limit=args.symbol_limit, show_symbols=args.show_symbols)
        sem_ms = (time.perf_counter() - sem_start) * 1000
        metrics["semantic"] = PhaseMetrics(
            duration_ms=sem_ms,
            symbol_count=len(semantic_result.symbols),
            warning_count=len(semantic_result.warnings),
        )

        if args.profile:
            _print_profile(metrics)
        if args.report_file is not None:
            _write_report_file(args.report_file, file_path, metrics, semantic_result)
        if args.strict_warnings and semantic_result.warnings:
            print("Error: strict-warnings is enabled and semantic warnings were found", file=sys.stderr)
            return 1
        return 0
    except (LexerError, ParserError, SemanticError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        line = getattr(exc, "line", 0)
        column = getattr(exc, "column", 0)
        _print_error_context(file_path, line, column)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())