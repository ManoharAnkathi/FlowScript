from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from lexer import Token


class ParserError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, start=1):
        curr = [i]
        for j, ch_b in enumerate(b, start=1):
            cost = 0 if ch_a == ch_b else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


@dataclass(frozen=True)
class NumberLiteral:
    value: int
    line: int
    column: int


@dataclass(frozen=True)
class Identifier:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class BinaryOp:
    op: str
    left: "Expr"
    right: "Expr"
    line: int
    column: int


Expr = NumberLiteral | Identifier | BinaryOp


@dataclass(frozen=True)
class LetStatement:
    name: str
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True)
class ConstStatement:
    name: str
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True)
class AssignStatement:
    name: str
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True)
class PrintStatement:
    expr: Expr
    line: int
    column: int


Statement = LetStatement | ConstStatement | AssignStatement | PrintStatement


@dataclass(frozen=True)
class Program:
    statements: list[Statement]


class TokenStream:
    def __init__(self, tokens: Iterable[Token]) -> None:
        self._tokens: Iterator[Token] = iter(tokens)
        self._buffer: list[Token] = []

    def _fill(self, count: int) -> None:
        while len(self._buffer) < count:
            self._buffer.append(next(self._tokens))

    def peek(self, offset: int = 0) -> Token:
        self._fill(offset + 1)
        return self._buffer[offset]

    def advance(self) -> Token:
        token = self.peek(0)
        self._buffer.pop(0)
        return token

    def match(self, *types: str) -> Token | None:
        token = self.peek(0)
        if token.type in types:
            self._buffer.pop(0)
            return token
        return None

    def expect(self, token_type: str, message: str) -> Token:
        token = self.peek(0)
        if token.type != token_type:
            raise ParserError(message, token.line, token.column)
        self._buffer.pop(0)
        return token


class Parser:
    def __init__(self, tokens: Iterable[Token]) -> None:
        self.stream = TokenStream(tokens)

    def parse_program(self) -> Program:
        self._consume_newlines()
        first_token = self.stream.peek()
        if first_token.type != "START":
            if first_token.type == "ATWORD":
                hint = ""
                if _edit_distance(first_token.value, "@start") <= 2:
                    hint = " Did you mean '@start'?"
                raise ParserError(f"Unknown directive '{first_token.value}'.{hint}".rstrip(), first_token.line, first_token.column)
            raise ParserError("Program must start with @start", first_token.line, first_token.column)
        self.stream.advance()
        self._consume_newlines()

        statements: list[Statement] = []
        while self.stream.peek().type not in {"END", "EOF"}:
            statements.append(self.parse_statement())
            self._require_statement_separator()

        end_token = self.stream.peek()
        if end_token.type != "END":
            if end_token.type == "ATWORD":
                hint = ""
                if _edit_distance(end_token.value, "@end") <= 2:
                    hint = " Did you mean '@end'?"
                raise ParserError(f"Unknown directive '{end_token.value}'.{hint}".rstrip(), end_token.line, end_token.column)
            raise ParserError("Program must end with @end", end_token.line, end_token.column)
        self.stream.advance()
        self._consume_newlines()
        self.stream.expect("EOF", "Unexpected tokens after @end")

        return Program(statements=statements)

    def parse_statement(self) -> Statement:
        token = self.stream.peek()

        if token.type == "LET":
            return self._parse_let_statement()

        if token.type == "CONST":
            return self._parse_const_statement()

        if token.type == "PRINT":
            return self._parse_print_statement()

        if token.type == "IDENT" and self.stream.peek(1).type == "ASSIGN":
            return self._parse_assign_statement()

        if token.type == "IDENT":
            lowered = token.value.lower()
            hints = ["let", "const", "print"]
            best_hint = min(hints, key=lambda item: _edit_distance(lowered, item))
            if _edit_distance(lowered, best_hint) <= 2:
                raise ParserError(f"Invalid statement '{token.value}'. Did you mean '{best_hint}'?", token.line, token.column)

        raise ParserError("Invalid statement", token.line, token.column)

    def _parse_let_statement(self) -> LetStatement:
        let_token = self.stream.expect("LET", "Expected 'let'")
        ident = self.stream.expect("IDENT", "Expected identifier after 'let'")
        self.stream.expect("ASSIGN", "Expected ':=' in declaration")
        expr = self.parse_expression()
        return LetStatement(ident.value, expr, let_token.line, let_token.column)

    def _parse_const_statement(self) -> ConstStatement:
        const_token = self.stream.expect("CONST", "Expected 'const'")
        ident = self.stream.expect("IDENT", "Expected identifier after 'const'")
        self.stream.expect("ASSIGN", "Expected ':=' in constant declaration")
        expr = self.parse_expression()
        return ConstStatement(ident.value, expr, const_token.line, const_token.column)

    def _parse_assign_statement(self) -> AssignStatement:
        ident = self.stream.expect("IDENT", "Expected identifier")
        self.stream.expect("ASSIGN", "Expected ':=' in assignment")
        expr = self.parse_expression()
        return AssignStatement(ident.value, expr, ident.line, ident.column)

    def _parse_print_statement(self) -> PrintStatement:
        print_token = self.stream.expect("PRINT", "Expected 'print'")
        self.stream.expect("ARROW", "Expected '=>' after 'print'")
        expr = self.parse_expression()
        return PrintStatement(expr, print_token.line, print_token.column)

    def parse_expression(self) -> Expr:
        node = self.parse_term()
        while True:
            op_token = self.stream.match("PLUS", "MINUS")
            if op_token is None:
                return node
            right = self.parse_term()
            node = BinaryOp(op=op_token.value, left=node, right=right, line=op_token.line, column=op_token.column)

    def parse_term(self) -> Expr:
        node = self.parse_factor()
        while True:
            op_token = self.stream.match("STAR", "SLASH")
            if op_token is None:
                return node
            right = self.parse_factor()
            node = BinaryOp(op=op_token.value, left=node, right=right, line=op_token.line, column=op_token.column)

    def parse_factor(self) -> Expr:
        token = self.stream.peek()

        if token.type == "NUMBER":
            number = self.stream.advance()
            return NumberLiteral(value=int(number.value), line=number.line, column=number.column)

        if token.type == "IDENT":
            ident = self.stream.advance()
            return Identifier(name=ident.value, line=ident.line, column=ident.column)

        if token.type == "LPAREN":
            self.stream.advance()
            expr = self.parse_expression()
            self.stream.expect("RPAREN", "Expected ')' to close expression")
            return expr

        raise ParserError("Expected number, identifier, or '('", token.line, token.column)

    def _consume_newlines(self) -> int:
        count = 0
        while self.stream.match("NEWLINE") is not None:
            count += 1
        return count

    def _require_statement_separator(self) -> None:
        count = self._consume_newlines()
        if count > 0:
            return

        next_token = self.stream.peek()
        if next_token.type in {"END", "EOF"}:
            return

        raise ParserError("Expected end of line after statement", next_token.line, next_token.column)


def parse(tokens: Iterable[Token]) -> Program:
    return Parser(tokens).parse_program()