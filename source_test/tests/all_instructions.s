.data
v_head:
    .word 7, 0x2A, -32768, 1000000
v_mid:
    .word 65535, -3
v_tail:
    .word 0x7FFFFFFF, -1

.text
.globl main

main:
    # ---- set up a sane data base pointer (0x10010000) ----
    lui   gp, 0x10010
    addi  tp, gp, 0

    # ================= U-type: lui =================
    lui   x0, 2
    lui   s2, 0x10010
    lui   x31, 1048574
    lui   a7, 4095

    # ================= U-type: auipc =================
    auipc x0, 1
    auipc s3, 0x7FFFF
    auipc x31, 1048575
    auipc a6, 16

loop_start:
    # ================= I-type ALU: addi =================
    addi  x0, x31, 0
    addi  a3, a4, 1024
    addi  s4, x0, -2047
    addi  t5, t5, -1
    addi  x1, gp, 0x7FF

    # ================= I-type ALU: andi =================
    andi  a5, s5, 1023
    andi  x31, x1, -2048
    andi  t4, x0, 0
    andi  s6, a6, -9

    # ================= I-type ALU: ori =================
    ori   a2, s7, 0x2A
    ori   x0, x31, 2047
    ori   t3, t4, -1
    ori   s8, x1, 16

    # ================= I-type ALU: xori =================
    xori  a1, s9, 512
    xori  x31, x0, -2048
    xori  t2, t1, 0x100
    xori  s10, a0, -1

    # ================= I-type ALU: slti =================
    slti  a0, s11, 1
    slti  x0, x1, -2048
    slti  t1, t0, 2047
    slti  ra, x31, -100

    # ================= I-type ALU: sltiu =================
    sltiu s1, s0, 3
    sltiu x1, x0, 2047
    sltiu t0, t6, -2048
    sltiu a4, a5, 0

    # ================= I-type shifts: slli =================
    slli  s0, s1, 2
    slli  x0, x31, 31
    slli  t6, t0, 0
    slli  a4, a3, 24

    # ================= I-type shifts: srli =================
    srli  s1, s2, 3
    srli  x31, x1, 31
    srli  t0, t2, 0
    srli  a3, a2, 12

    # ================= I-type shifts: srai =================
    srai  s2, s3, 4
    srai  x1, x0, 31
    srai  t2, t4, 0
    srai  a2, a1, 8

    # ================= R-type: or =================
    or    s3, s4, s5
    or    x0, x31, x1
    or    t4, t3, t6

    # ================= R-type: and =================
    and   s5, s6, s7
    and   x31, x0, x0
    and   a1, a0, ra

    # ================= R-type: xor =================
    xor   s7, s8, s9
    xor   x1, x31, x0
    xor   a0, ra, sp

    # ================= R-type: add =================
    add   s9, s10, s11
    add   x0, x1, x0
    add   ra, sp, gp
    add   t3, t3, t3

    # ================= R-type: sub =================
    sub   sp, gp, tp
    sub   x31, x0, x31
    sub   t6, t5, t4

    # ================= R-type: sll =================
    sll   t5, t4, t3
    sll   x0, x31, x1
    sll   a7, a6, a5

    # ================= R-type: srl =================
    srl   a6, a5, a4
    srl   x1, x1, x1
    srl   s11, s10, s9

    # ================= R-type: sra =================
    sra   a5, a4, a3
    sra   x31, x31, x0
    sra   s10, s9, s8

    # ================= R-type: slt =================
    slt   a4, a3, a2
    slt   x0, x0, x31
    slt   s8, s7, s6

    # ================= R-type: sltu =================
    sltu  a3, a2, a1
    sltu  x31, x1, x1
    sltu  s6, s5, s4

    # ================= Loads: lb =================
    lb    s0, 0(tp)
    lb    x31, 7(tp)
    lb    a0, -7(tp)
    lb    x0, -2048(x1)
    lb    t0, 2047(x31)

    # ================= Loads: lbu =================
    lbu   s1, 0(tp)
    lbu   x1, 9(tp)
    lbu   a1, -9(tp)
    lbu   x0, 2047(x0)
    lbu   t1, -2048(gp)

    # ================= Loads: lh =================
    lh    s2, 0(tp)
    lh    x31, 12(tp)
    lh    a2, -12(tp)
    lh    x0, -2048(x31)
    lh    t2, 2046(x1)

    # ================= Loads: lhu =================
    lhu   s3, 0(tp)
    lhu   x1, 14(tp)
    lhu   a3, -14(tp)
    lhu   x0, 2046(gp)
    lhu   t3, -2048(x0)

    # ================= Loads: lw =================
    lw    s4, 0(tp)
    lw    x31, 16(tp)
    lw    a4, -16(tp)
    lw    x0, 2044(x1)
    lw    t4, -2048(tp)

    # ================= Stores: sb =================
    sb    s5, 0(tp)
    sb    x0, 11(tp)
    sb    x31, -11(tp)
    sb    a5, 2047(x1)
    sb    t5, -2048(gp)

    # ================= Stores: sh =================
    sh    s6, 0(tp)
    sh    x1, 18(tp)
    sh    a6, -18(tp)
    sh    x0, -2048(x31)
    sh    t6, 2046(x0)

    # ================= Stores: sw =================
    sw    s7, 0(tp)
    sw    x31, 20(tp)
    sw    a7, -20(tp)
    sw    x0, -2048(x1)
    sw    ra, 2044(gp)

    # ================= Branches (forward) =================
    bne   s8, s9, skip_ahead
    beq   x31, x0, skip_ahead
    bge   a0, a1, skip_ahead
    blt   x1, x31, skip_ahead
    bgeu  t0, t1, skip_ahead
    bltu  x0, x1, skip_ahead

    # ================= Branches (backward) =================
    bne   x0, x31, loop_start
    beq   t2, t3, loop_start
    bge   x31, x1, loop_start
    blt   a2, a3, loop_start
    bgeu  x1, x0, loop_start
    bltu  s10, s11, loop_start

    # ================= J-type: jal (forward) =================
    jal   x31, skip_ahead
    jal   x0, skip_ahead
    jal   ra, skip_ahead

skip_ahead:
    # ================= I-type: jalr (3-operand register form) =================
    jalr  x31, t0, 0
    jalr  x0, ra, -1
    jalr  ra, gp, 2047
    jalr  s0, x31, -2048
    jalr  a1, x1, 8

    # ================= J-type: jal (backward) =================
    jal   ra, loop_start
    jal   x31, main

    # ================= end of program =================
    addi  a7, x0, 10
    ecall
