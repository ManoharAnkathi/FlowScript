import re

from ir import IRProgram


def generate_python(ir_program):
    lines = []
    
    # Process each IR instruction
    for instr in ir_program.instructions:
        instr = instr.strip()
        if not instr:
            continue
            
        # Label
        if instr.endswith(":"):
            lines.append(instr)
            continue
        
        # Assignment: x = value or x = y + z
        match = re.match(r"(\w+)\s*=\s*(.+)", instr)
        if match:
            var = match.group(1)
            expr = match.group(2).strip()
            
            # Simple value (number or variable)
            if not any(op in expr for op in ["+", "-", "*", "/"]):
                lines.append("MOV " + var + ", " + expr)
            else:
                # Binary operation: a + b, a - b, etc
                match_op = re.match(r"(\S+)\s*([\+\-\*/])\s*(\S+)", expr)
                if match_op:
                    left, op, right = match_op.groups()
                    
                    # Load operands into registers
                    lines.append("MOV R1, " + left)
                    lines.append("MOV R2, " + right)
                    
                    # Perform operation
                    op_map = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
                    lines.append(op_map[op] + " R1, R2")
                    
                    # Store result
                    lines.append("MOV " + var + ", R1")
            continue
        
        # Print statement
        if instr.startswith("print"):
            match = re.match(r"print\s+(\S+)", instr)
            if match:
                value = match.group(1)
                lines.append("MOV R1, " + value)
                lines.append("PRINT R1")
            continue
        
        # If condition: if x > 5 goto L1
        if instr.startswith("if"):
            match = re.match(r"if\s+(\S+)\s+([<>!=]=?|==|!=)\s+(\S+)\s+goto\s+(\S+)", instr)
            if match:
                left, op, right, label = match.groups()
                lines.append("MOV R1, " + left)
                lines.append("MOV R2, " + right)
                
                jump_ops = {"<": "JL", "<=": "JLE", ">": "JG", ">=": "JGE", "==": "JE", "!=": "JNE"}
                lines.append("CMP R1, R2")
                lines.append(jump_ops[op] + " " + label)
            continue
        
        # Unconditional jump
        if instr.startswith("goto"):
            match = re.match(r"goto\s+(\S+)", instr)
            if match:
                lines.append("JMP " + match.group(1))
            continue
        
        # Function start
        if instr.startswith("func"):
            match = re.match(r"func\s+(\w+):", instr)
            if match:
                lines.append(match.group(1) + ":")
            continue
        
        # Return
        if instr.startswith("return"):
            match = re.match(r"return\s*(\S+)?", instr)
            if match and match.group(1):
                val = match.group(1)
                lines.append("MOV R1, " + val)
            lines.append("RET")
            continue
    
    return "\n".join(lines)


def execute_ir(ir_program):
    _ = ir_program
    return ["TODO: Assembly execution"]