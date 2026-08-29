.data
a: .word 22
b: .word 59
c: .word 0

.text
.globl main

main:
    lui  t0, 0x10010    # data base
    lw   t1, 0(t0)      # a
    lw   t2, 4(t0)      # b
    addi t3, x0, 0      # c = 0
    addi t4, x0, 0      # i = 0
    addi t6, x0, 32     # loop max

loop:
    beq  t4, t6, done   # while i < 32
    andi t5, t2, 1      # t5 = b & 1
    beq  t5, x0, skip   # if t5 == 0, jump to skip
    add  t3, t3, t1     # c = c + a

skip:
    slli t1, t1, 1      # a = a << 1
    srli t2, t2, 1      # b = b >> 1
    addi  t4, t4, 1     # i = i + 1
    jal  x0, loop       # go back to loop

done:
    sw   t3, 8(t0)      # store result
    addi a0, x0, 0      # return value = 0
    addi a7, x0, 93     # sys_exit
    ecall