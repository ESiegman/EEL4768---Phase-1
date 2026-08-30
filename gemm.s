.data
a:  .word 1, 2, 5, 7
    .word 3, 9, 2, 5
    .word 1, 9, 8, 2
    .word 4, 1, 6, 6
b:  .word 3, 4, 9, 2
    .word 1, 8, 7, 3
    .word 8, 9, 1, 2
    .word 6, 3, 7, 5
c:  .word 0, 0, 0, 0
    .word 0, 0, 0, 0
    .word 0, 0, 0, 0
    .word 0, 0, 0, 0

.text
.globl main

# REGISTERS USED
#s3: k counter
#s4 
#s5
#t3
#t0:
#a7:

# LABELS
# k_loop:
# k_done:
# mult:
# mult_loop: 
# mult_skip:
# mult_done:


main:

lui  s0, 0x10010

    addi s3, x0, 0  # k = 0
    addi s4, x0, 0  # sum = 0
    addi s5, s0, 0  # pointer to A[0][0]
    addi s6, s0, 0x40 # pointer to B[0][0]
    addi s7, x0, 4 # bound

k_loop:
    beq  s3, s7, k_done
    
    lw a0, 0(s5) #A[0][k]
    lw a1, 0(s6) #B[k][0]
    jal ra, mult #returns a0 with the product
    add s4, s4, a0 #accumulate
    
    addi s5, s5, 4 #moves A across the row
    addi s6, s6, 16 #B setsp down the column
    addi s3, s3, 1 # k++
    jal x0, k_loop
    

k_done:
    sw   s4, 128(s0)
    
done:
addi a0, x0, 0
addi a7, x0, 93
ecall


# mult: product = multiplicand * multiplier


# a0: arrives with the multiplicand leaves with the Final Product
# a1:genuine multiplier
# t0:working copy of multiplicand
# t1:working copy of multiplier
# t2:used for low bit testing

#Labels
#mult: setting up the multiplication loop, copying "a" and "b" to temp ergisters to work on, initializes product at 0
#mult_loop: top of the loop, it exits when the multiplier is 0
#mult_skip: Merge point after the conditional add, shifts multiplicand up and multiplier downf or the next bit position.
#mult_done: returns product to called
mult:
    addi t0, a0, 0        # working copy of multiplicand
    addi t1, a1, 0        # working copy of multiplier
    addi a0, x0, 0         # Product = 0

mult_loop:
    beq  t1, x0, mult_done    # early exit: multiplier copy empty
    andi t2, t1, 1           # test low bit
    beq  t2, x0, mult_skip
    add  a0, a0, t0           # accumulate

mult_skip:
    slli t0, t0, 1           # multiplicand <<= 1
    srli t1, t1, 1           # multiplier >>= 1
    jal  x0, mult_loop

mult_done:
    jalr x0, ra, 0
