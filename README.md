# FlowScript Compiler

A simple compiler for the FlowScript language.

## How It Works

The compiler has 6 phases:

### 1. Lexical Analysis (lexer.py)
Reads source code and breaks it into tokens.

**Example:**
```
Input:  let a := 5
Output: LET -> let, IDENT -> a, ASSIGN := , NUMBER -> 5
```

### 2. Syntax Analysis (parser.py)
Reads tokens and builds an Abstract Syntax Tree (AST).

**Example:**
```
Input:  Tokens from Phase 1
Output: LET a := 5 (AST node)
```

### 3. Semantic Analysis (semantic.py)
Checks if the program makes sense: variable types, declarations, etc.

**Example:**
```
Input:  AST from Phase 2
Output: Symbol table: { a -> var (value: 5.0) }
```

### 4. Intermediate Code (ir.py)
Converts AST to simple Three-Address Code.

**Example:**
```
Input:  AST from Phase 3
Output: 1. a = 5
        2. print a
```

### 5. Code Optimization (optimizer.py)
Simplifies the code by computing constants.

**Example:**
```
Input:  Three-Address Code from Phase 4
Output: Optimized code with constants computed
```

### 6. Code Generation (codegen.py)
Converts to assembly code.

**Example:**
```
Input:  Optimized Code from Phase 5
Output: MOV a, 5
        MOV R1, a
        PRINT R1
```

## Files

```
lexer.py          - Phase 1
parser.py         - Phase 2
ast_nodes.py      - AST definitions
semantic.py       - Phase 3
ir.py             - Phase 4
optimizer.py      - Phase 5
codegen.py        - Phase 6
main.py           - Runs all phases
sample.flow       - Example program
README.md         - This file
```

## Usage

Run the full compiler:
```bash
python main.py sample.flow --phase all --structured
```

Run a single phase:
```bash
python main.py sample.flow --phase tokens
python main.py sample.flow --phase parse
python main.py sample.flow --phase semantic
```

Show intermediate code:
```bash
python main.py sample.flow --phase semantic --show-ir --show-optimized-ir --show-asm
```

Save assembly to file:
```bash
python main.py sample.flow --asm-file output.asm
```

## FlowScript Language

Simple language with:
- Variables: `let x := 5`
- Constants: `const MAX := 100`
- Assignment: `x := a + b`
- Operators: `+`, `-`, `*`, `/`
- If statement: `if x > 5 ... endif`
- Repeat: `repeat 10 ... endrepeat`
- For loop: `for i := 1 to 10 ... endfor`
- While loop: `while x > 0 ... endwhile`
- Functions: `function add ... endfunction`
- Print: `print => x`

## Example

```flowscript
@start
let a := 12
let b := 4
let c := (a + b) * 2
print => c
@end
```

This program:
1. Creates variable `a` with value 12
2. Creates variable `b` with value 4
3. Creates variable `c` with value (12 + 4) * 2 = 32
4. Prints the value of `c`
