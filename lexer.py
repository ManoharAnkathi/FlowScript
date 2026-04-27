from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


KEYWORDS = {
    "let": "LET",
    "const": "CONST",
    "print": "PRINT",
    "to": "TO",
    "return": "RETURN",
    "continue": "CONTINUE",
    "break": "BREAK",
    "giveback": "RETURN",
    "skip": "CONTINUE",
    "stop": "BREAK",
}

SINGLE_CHAR_TOKENS = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
    ">": "GREATER",
    "(": "LPAREN",
    ")": "RPAREN",
}


def _is_identifier_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_identifier_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _is_token_boundary(text: str, end_index: int) -> bool:
    if end_index >= len(text):
        return True
    return not _is_identifier_part(text[end_index])


def _scan_line(line: str, line_no: int) -> Iterator[Token]:
    i = 0
    length = len(line)

    while i < length:
        ch = line[i]
        col = i + 1

        if ch in " \t\r":
            i += 1
            continue

        if ch == "\n":
            break

        if ch == "#":
            break

        if line.startswith("@start", i) and _is_token_boundary(line, i + 6):
            yield Token("START", "@start", line_no, col)
            i += 6
            continue

        if line.startswith("@end", i) and _is_token_boundary(line, i + 4):
            yield Token("END", "@end", line_no, col)
            i += 4
            continue

        if line.startswith("@if", i) and _is_token_boundary(line, i + 3):
            yield Token("IF", "@if", line_no, col)
            i += 3
            continue

        if line.startswith("@endif", i) and _is_token_boundary(line, i + 6):
            yield Token("ENDIF", "@endif", line_no, col)
            i += 6
            continue

        if line.startswith("@repeat", i) and _is_token_boundary(line, i + 7):
            yield Token("REPEAT", "@repeat", line_no, col)
            i += 7
            continue

        if line.startswith("@endrepeat", i) and _is_token_boundary(line, i + 10):
            yield Token("ENDREPEAT", "@endrepeat", line_no, col)
            i += 10
            continue

        if line.startswith("@for", i) and _is_token_boundary(line, i + 4):
            yield Token("FOR", "@for", line_no, col)
            i += 4
            continue

        if line.startswith("@endfor", i) and _is_token_boundary(line, i + 7):
            yield Token("ENDFOR", "@endfor", line_no, col)
            i += 7
            continue

        if line.startswith("@while", i) and _is_token_boundary(line, i + 6):
            yield Token("WHILE", "@while", line_no, col)
            i += 6
            continue

        if line.startswith("@endwhile", i) and _is_token_boundary(line, i + 9):
            yield Token("ENDWHILE", "@endwhile", line_no, col)
            i += 9
            continue

        if line.startswith("@function", i) and _is_token_boundary(line, i + 9):
            yield Token("FUNCTION", "@function", line_no, col)
            i += 9
            continue

        if line.startswith("@endfunction", i) and _is_token_boundary(line, i + 12):
            yield Token("ENDFUNCTION", "@endfunction", line_no, col)
            i += 12
            continue

        if ch == "@":
            start = i
            i += 1
            while i < length and _is_identifier_part(line[i]):
                i += 1
            text = line[start:i]
            yield Token("ATWORD", text, line_no, start + 1)
            continue

        if line.startswith(":=", i):
            yield Token("ASSIGN", ":=", line_no, col)
            i += 2
            continue

        if line.startswith("=>", i):
            yield Token("ARROW", "=>", line_no, col)
            i += 2
            continue

        token_type = SINGLE_CHAR_TOKENS.get(ch)
        if token_type is not None:
            yield Token(token_type, ch, line_no, col)
            i += 1
            continue

        if ch.isdigit():
            start = i
            while i < length and line[i].isdigit():
                i += 1
            yield Token("NUMBER", line[start:i], line_no, start + 1)
            continue

        if _is_identifier_start(ch):
            start = i
            i += 1
            while i < length and _is_identifier_part(line[i]):
                i += 1
            text = line[start:i]
            yield Token(KEYWORDS.get(text, "IDENT"), text, line_no, start + 1)
            continue

        raise LexerError(f"Unexpected character '{ch}'", line_no, col)

    yield Token("NEWLINE", "\\n", line_no, length + 1)


def tokenize_file(file_path: str | Path) -> Iterator[Token]:
    path = Path(file_path)
    last_line = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            last_line = line_no
            yield from _scan_line(line, line_no)

    eof_line = 1 if last_line == 0 else last_line + 1
    yield Token("EOF", "", eof_line, 1)


def tokenize_text(source: str) -> Iterator[Token]:
    last_line = 0
    for line_no, line in enumerate(source.splitlines(keepends=True), start=1):
        last_line = line_no
        yield from _scan_line(line, line_no)
    eof_line = 1 if last_line == 0 else last_line + 1
    yield Token("EOF", "", eof_line, 1)


def collect_tokens(tokens: Iterable[Token]) -> list[Token]:
    return list(tokens)