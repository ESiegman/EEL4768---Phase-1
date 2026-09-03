import os
import re
import sys


TEXT_BASE = 0x00400000
DATA_BASE = 0x10010000


# Numeric + ABI register names required by the assignment/reference card.
REGISTERS = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13,
    "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21,
    "s6": 22, "s7": 23, "s8": 24, "s9": 25,
    "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}
REGISTERS.update({f"x{i}": i for i in range(32)})

INSTRUCTIONS = {
    
    # R type instructions
    "add":  ("R", 0x33, 0b000, 0b0000000),
    "sub":  ("R", 0x33, 0b000, 0b0100000),
    "sll":  ("R", 0x33, 0b001, 0b0000000),
    "slt":  ("R", 0x33, 0b010, 0b0000000),
    "sltu": ("R", 0x33, 0b011, 0b0000000),
    "xor":  ("R", 0x33, 0b100, 0b0000000),
    "srl":  ("R", 0x33, 0b101, 0b0000000),
    "sra":  ("R", 0x33, 0b101, 0b0100000),
    "or":   ("R", 0x33, 0b110, 0b0000000),
    "and":  ("R", 0x33, 0b111, 0b0000000),

    # I type instructions
    "addi":  ("I", 0x13, 0b000, None),
    "slti":  ("I", 0x13, 0b010, None),
    "sltiu": ("I", 0x13, 0b011, None),
    "xori":  ("I", 0x13, 0b100, None),
    "ori":   ("I", 0x13, 0b110, None),
    "andi":  ("I", 0x13, 0b111, None),

    # I type shifts
    "slli": ("SHIFT", 0x13, 0b001, 0b0000000),
    "srli": ("SHIFT", 0x13, 0b101, 0b0000000),
    "srai": ("SHIFT", 0x13, 0b101, 0b0100000),

    # loads
    "lb":  ("LOAD", 0x03, 0b000, None),
    "lh":  ("LOAD", 0x03, 0b001, None),
    "lw":  ("LOAD", 0x03, 0b010, None),
    "lbu": ("LOAD", 0x03, 0b100, None),
    "lhu": ("LOAD", 0x03, 0b101, None),

    # stores
    "sb": ("S", 0x23, 0b000, None),
    "sh": ("S", 0x23, 0b001, None),
    "sw": ("S", 0x23, 0b010, None),

    # conditionals
    "beq":  ("B", 0x63, 0b000, None),
    "bne":  ("B", 0x63, 0b001, None),
    "blt":  ("B", 0x63, 0b100, None),
    "bge":  ("B", 0x63, 0b101, None),
    "bltu": ("B", 0x63, 0b110, None),
    "bgeu": ("B", 0x63, 0b111, None),

    # upper immediates
    "lui":   ("U", 0x37, None, None),
    "auipc": ("U", 0x17, None, None),

    # jumps
    "jal":  ("J", 0x6F, None, None),
    "jalr": ("JALR", 0x67, 0b000, None),
}


def reg(name):
    name = name.strip().lower()
    if name not in REGISTERS:
        raise ValueError(f"Unknown register: {name}")
    return REGISTERS[name]


def number(token, labels=None, pc=None, relative=False):
    token = token.strip()
    if labels is not None and token in labels:
        value = labels[token]
        return value - pc if relative else value
    return int(token, 0)


def memory_operand(text):
    match = re.fullmatch(r"\s*(.*?)\s*\(\s*([^()]+)\s*\)\s*", text)
    if not match:
        raise ValueError(f"Expected offset(register), got: {text}")
    offset_text, rs1_text = match.groups()
    offset = number(offset_text) if offset_text.strip() else 0
    return offset, reg(rs1_text)


def encode_r(rd, rs1, rs2, opcode, funct3, funct7):
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | \
           (funct3 << 12) | (rd << 7) | opcode


def encode_i(rd, rs1, imm, opcode, funct3):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | \
           (funct3 << 12) | (rd << 7) | opcode


def encode_shift(rd, rs1, shamt, opcode, funct3, funct7):
    return (funct7 << 25) | ((shamt & 0x1F) << 20) | (rs1 << 15) | \
           (funct3 << 12) | (rd << 7) | opcode


def encode_s(rs1, rs2, imm, opcode, funct3):
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | \
           (funct3 << 12) | ((imm & 0x1F) << 7) | opcode


def encode_b(rs1, rs2, imm, opcode, funct3):
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | \
           (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | \
           (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | opcode


def encode_u(rd, imm, opcode):
    return ((imm & 0xFFFFF) << 12) | (rd << 7) | opcode


def encode_j(rd, imm, opcode):
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | \
           (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | \
           (rd << 7) | opcode


def encode_instruction(mnemonic, operands, pc, labels):
    op = mnemonic.lower()

    if op == "ecall":
        if operands:
            raise ValueError("ecall takes no operands")
        return 0x00000073

    if op not in INSTRUCTIONS:
        raise ValueError(f"Unsupported instruction: {mnemonic}")

    fmt, opcode, funct3, funct7 = INSTRUCTIONS[op]

    if fmt == "R":
        rd, rs1, rs2 = map(reg, operands)
        return encode_r(rd, rs1, rs2, opcode, funct3, funct7)

    if fmt == "I":
        rd, rs1 = reg(operands[0]), reg(operands[1])
        imm = number(operands[2], labels)
        return encode_i(rd, rs1, imm, opcode, funct3)

    if fmt == "SHIFT":
        rd, rs1 = reg(operands[0]), reg(operands[1])
        shamt = number(operands[2])
        return encode_shift(rd, rs1, shamt, opcode, funct3, funct7)

    if fmt == "LOAD":
        rd = reg(operands[0])
        imm, rs1 = memory_operand(operands[1])
        return encode_i(rd, rs1, imm, opcode, funct3)

    if fmt == "S":
        rs2 = reg(operands[0])
        imm, rs1 = memory_operand(operands[1])
        return encode_s(rs1, rs2, imm, opcode, funct3)

    if fmt == "B":
        rs1, rs2 = reg(operands[0]), reg(operands[1])
        imm = number(operands[2], labels, pc, relative=True)
        return encode_b(rs1, rs2, imm, opcode, funct3)

    if fmt == "U":
        rd = reg(operands[0])
        imm = number(operands[1], labels)
        return encode_u(rd, imm, opcode)

    if fmt == "J":
        rd = reg(operands[0])
        imm = number(operands[1], labels, pc, relative=True)
        return encode_j(rd, imm, opcode)

    if fmt == "JALR":
        rd = reg(operands[0])
        if len(operands) == 2:
            imm, rs1 = memory_operand(operands[1])
        elif len(operands) == 3:
            rs1 = reg(operands[1])
            imm = number(operands[2], labels)
        else:
            raise ValueError("jalr expects rd, offset(rs1) or rd, rs1, imm")
        return encode_i(rd, rs1, imm, opcode, funct3)

    raise ValueError(f"Unhandled instruction format: {fmt}")


def clean_line(raw_line):
    return raw_line.split("#", 1)[0].strip()


def take_labels(line):
    labels = []
    while True:
        match = re.match(r"^([A-Za-z_.$][\w.$]*)\s*:\s*(.*)$", line)
        if not match:
            return labels, line
        labels.append(match.group(1))
        line = match.group(2).strip()


def split_statement(statement):
    parts = statement.split(None, 1)
    head = parts[0]
    operands = []
    if len(parts) == 2:
        operands = [item.strip() for item in parts[1].split(",") if item.strip()]
    return head, operands


def assemble(source):
    section = "text"
    text_addr = TEXT_BASE
    data_addr = DATA_BASE

    labels = {}
    instructions = []      
    data_words = []       

    for raw_line in source.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue

        line_labels, statement = take_labels(line)
        for label in line_labels:
            labels[label] = data_addr if section == "data" else text_addr

        if not statement:
            continue

        head, operands = split_statement(statement)
        directive = head.lower()

        if directive == ".data":
            section = "data"
            continue
        if directive == ".text":
            section = "text"
            continue
        if directive in (".globl", ".global"):
            continue
        if directive == ".word":
            if section != "data":
                raise ValueError(".word is only supported in the .data section")
            data_words.extend(operands)
            data_addr += 4 * len(operands)
            continue
        if directive.startswith("."):
            raise ValueError(f"Unsupported directive: {head}")

        if section != "text":
            raise ValueError(f"Instruction found outside .text: {statement}")

        instructions.append((text_addr, head, operands))
        text_addr += 4

    data_bytes = bytearray()
    for token in data_words:
        value = number(token, labels) & 0xFFFFFFFF
        data_bytes.extend(value.to_bytes(4, "little"))

    instruction_bytes = bytearray()
    for pc, mnemonic, operands in instructions:
        word = encode_instruction(mnemonic, operands, pc, labels)
        instruction_bytes.extend((word & 0xFFFFFFFF).to_bytes(4, "little"))

    return instruction_bytes, data_bytes


def write_lines(path, values, binary=False):
    with open(path, "w") as out:
        if binary:
            out.writelines(f"{byte:08b}\n" for byte in values)
        else:
            out.writelines(f"0x{byte:02x}\n" for byte in values)


def write_outputs(assembly_file, instruction_bytes, data_bytes):
    directory = os.path.dirname(assembly_file) or "."
    name = os.path.splitext(os.path.basename(assembly_file))[0]

    write_lines(os.path.join(directory, f"{name}.hex.txt"), instruction_bytes)
    write_lines(os.path.join(directory, f"{name}.bin.txt"), instruction_bytes, binary=True)
    write_lines(os.path.join(directory, f"{name}_instr.hex.txt"), instruction_bytes)
    write_lines(os.path.join(directory, f"{name}_instr.bin.txt"), instruction_bytes, binary=True)
    write_lines(os.path.join(directory, f"{name}_data.hex.txt"), data_bytes)
    write_lines(os.path.join(directory, f"{name}_data.bin.txt"), data_bytes, binary=True)


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <assembly_file>")
        sys.exit(1)

    assembly_file = sys.argv[1]
    with open(assembly_file, "r", errors="replace") as source_file:
        source = source_file.read()

    instruction_bytes, data_bytes = assemble(source)
    write_outputs(assembly_file, instruction_bytes, data_bytes)


if __name__ == "__main__":
    main()
