.data
a:      .word 10, 9, 9, 4, 0
        .word 0, 6, 6, 2, 2
        .word 5, 9, 8, 4, 3
        .word 7, 5, 5, 4, 3
        .word 8, 10, 8, 5, 0
gx:     .word -1, 0, 1
        .word -2, 0, 2
        .word -1, 0, 1
gy:     .word 1, 2, 1
        .word 0, 0, 0
        .word -1, -2, -1
c:      .word 0, 0, 0
        .word 0, 0, 0
        .word 0, 0, 0

.text
.globl main

main:
    lui  s0, 0x10010          # data base
    addi s7, s0, 0            # window row ptr = &a[0][0]
    addi s8, s0, 172          # output ptr = &c[0][0]
    addi s1, x0, 0            # i = 0

row_loop:
    addi t0, x0, 3            # loop max
    beq  s1, t0, done         # while i < 3
    addi s9, s7, 0            # window ptr = window row ptr
    addi s2, x0, 0            # j = 0

col_loop:
    addi t0, x0, 3            # loop max
    beq  s2, t0, col_done     # while j < 3
    addi s5, x0, 0            # sx = 0
    addi s6, x0, 0            # sy = 0
    addi s10, s9, 0           # a ptr = window ptr
    addi s11, s0, 100         # kernel ptr = &gx[0][0]
    addi s3, x0, 0            # ki = 0

krow_loop:
    addi t0, x0, 3            # loop max
    beq  s3, t0, krow_done    # while ki < 3
    addi s4, x0, 0            # kj = 0

kcol_loop:
    addi t0, x0, 3            # loop max
    beq  s4, t0, kcol_done    # while kj < 3
    lw   a0, 0(s10)           # a0 = a[i+ki][j+kj]
    lw   a1, 0(s11)           # a1 = gx[ki][kj]
    jal  ra, mul              # a2 = a0 * a1
    add  s5, s5, a2           # sx = sx + a2
    lw   a0, 0(s10)           # a0 = a[i+ki][j+kj]
    lw   a1, 36(s11)          # a1 = gy[ki][kj], 36 bytes past gx
    jal  ra, mul              # a2 = a0 * a1
    add  s6, s6, a2           # sy = sy + a2
    addi s10, s10, 4          # next a element
    addi s11, s11, 4          # next kernel element
    addi s4, s4, 1            # kj = kj + 1
    jal  x0, kcol_loop        # go back to kcol_loop

kcol_done:
    addi s10, s10, 8          # a ptr to start of next window row
    addi s3, s3, 1            # ki = ki + 1
    jal  x0, krow_loop        # go back to krow_loop

krow_done:
    addi a0, s5, 0            # a0 = sx
    addi a1, s5, 0            # a1 = sx
    jal  ra, mul              # a2 = sx * sx
    addi s5, a2, 0            # sx = sx * sx
    addi a0, s6, 0            # a0 = sy
    addi a1, s6, 0            # a1 = sy
    jal  ra, mul              # a2 = sy * sy
    add  a2, a2, s5           # a2 = sx*sx + sy*sy
    sw   a2, 0(s8)            # c[i][j] = a2
    addi s8, s8, 4            # next output element
    addi s9, s9, 4            # slide window right by 1
    addi s2, s2, 1            # j = j + 1
    jal  x0, col_loop         # go back to col_loop

col_done:
    addi s7, s7, 20           # slide window down by 1 row
    addi s1, s1, 1            # i = i + 1
    jal  x0, row_loop         # go back to row_loop

done:
    addi a0, x0, 0            # return value = 0
    addi a7, x0, 93           # sys_exit
    ecall

mul:
    addi a2, x0, 0            # product = 0
    addi t0, x0, 0            # i = 0
    addi t1, x0, 32           # loop max
    addi t2, a0, 0            # t2 = a0
    addi t3, a1, 0            # t3 = a1

mul_loop:
    beq  t0, t1, mul_done     # while i < 32
    beq  t3, x0, mul_done     # stop once no bits are left in t3
    andi t4, t3, 1            # t4 = t3 & 1
    beq  t4, x0, mul_skip     # if t4 == 0, jump to mul_skip
    add  a2, a2, t2           # product = product + t2

mul_skip:
    slli t2, t2, 1            # t2 = t2 << 1
    srli t3, t3, 1            # t3 = t3 >> 1
    addi t0, t0, 1            # i = i + 1
    jal  x0, mul_loop         # go back to mul_loop

mul_done:
    jalr x0, 0(ra)            # return to caller
