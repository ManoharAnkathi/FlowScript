from __future__ import annotations

import re
from dataclasses import dataclass

from ir import IRProgram


@dataclass(frozen=True)
class CodegenResult:
    generated_python: str
    execution_output: list[str]


def generate_python(ir_program: IRProgram) -> str:
    lines = []
    
    # Process each IR instruction
    for instr in ir_program.instructions:
        instr = instr.strip()
        if not instr:
            continue
            
        # Label
        if instr.endswith(":"):
            lines.append(f"{instr}")
            continue
        
        # Assignment: x = value or x = y + z
        match = re.match(r"(\w+)\s*=\s*(.+)", instr)
        if match:
            var = match.group(1)
            expr = match.group(2).strip()
            
            # Simple value (number or variable)
            if not any(op in expr for op in ["+", "-", "*", "/"]):
                lines.append(f"MOV {var}, {expr}")
            else:
                # Binary operation: a + b, a - b, etc
                match_op = re.match(r"(\S+)\s*([\+\-\*/])\s*(\S+)", expr)
                if match_op:
                    left, op, right = match_op.groups()
                    
                    # Load operands into registers
                    lines.append(f"MOV R1, {left}")
                    lines.append(f"MOV R2, {right}")
                    
                    # Perform operation
                    op_map = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
                    lines.append(f"{op_map[op]} R1, R2")
                    
                    # Store result
                    lines.append(f"MOV {var}, R1")
            continue
        
        # Print statement
        if instr.startswith("print"):
            match = re.match(r"print\s+(\S+)", instr)
            if match:
                value = match.group(1)
                lines.append(f"MOV R1, {value}")
                lines.append(f"PRINT R1")
            continue
        
        # If condition: if x > 5 goto L1
        if instr.startswith("if"):
            match = re.match(r"if\s+(\S+)\s+([<>!=]=?|==|!=)\s+(\S+)\s+goto\s+(\S+)", instr)
            if match:
                left, op, right, label = match.groups()
                lines.append(f"MOV R1, {left}")
                lines.append(f"MOV R2, {right}")
                
                jump_ops = {"<": "JL", "<=": "JLE", ">": "JG", ">=": "JGE", "==": "JE", "!=": "JNE"}
                lines.append(f"CMP R1, R2")
                lines.append(f"{jump_ops[op]} {label}")
            continue
        
        # Unconditional jump
        if instr.startswith("goto"):
            match = re.match(r"goto\s+(\S+)", instr)
            if match:
                lines.append(f"JMP {match.group(1)}")
            continue
        
        # Function start
        if instr.startswith("func"):
            match = re.match(r"func\s+(\w+):", instr)
            if match:
                lines.append(f"{match.group(1)}:")
            continue
        
        # Return
        if instr.startswith("return"):
            match = re.match(r"return\s*(\S+)?", instr)
            if match and match.group(1):
                val = match.group(1)
                lines.append(f"MOV R1, {val}")
            lines.append(f"RET")
            continue
    
    return "\n".join(lines)


def execute_ir(ir_program: IRProgram) -> list[str]:
    _ = ir_program
    return ["TODO: Assembly execution"]