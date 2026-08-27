.data
a: .word 10
b: .word 20
c: .word 0

.text
.globl main

main:
    lui  t0, 0x10010       # Load data segment address

    lw   t1, 0(t0)         # t1 = a
    lw   t2, 4(t0)         # t2 = b

    add  t3, t1, t2        # t3 = a + b

    sw   t3, 8(t0)         # c = t3

done:
    addi a0, x0, 0         # return value = 0
    addi a7, x0, 93        # sys_exit
    ecall