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

#REGISTERS USED
#s0: data base, 0x10010000
#s1: m counter
#s2: n counter
#s3: k counter
#s4: running sum for C[m][n]
#s5: A pointer, &A[m][k]
#s6: B pointer, &B[k][n]
#s7: loop trip count (4)
#t0: C address at k_done
#t1: m*16 term at k_done
#a0: mult argument, returns the product
#a1: mult argument
#ra: return address for mult
#a7: syscall number at exit

#LABELS
#m_loop/m_done: iterates m over rows of A
#n_done/n_loop: iterates over n columns of B
#k_loop/k_done: dot product for C[m][n]
#mult/mult_loop/mult_skip/mult_done: bit-serial multiply subroutine
main:

lui  s0, 0x10010
addi s1, x0, 0 #m = 0
addi s3, x0, 0 #k = 0
addi s4, x0, 0 #sum = 0
addi s5, s0, 0 #pointer to A[0][0]
addi s6, s0, 0x40# pointer to B[0][0]
addi s7, x0, 4 #k/n bound

	m_loop:
	beq  s1, s7, m_done
	addi s2, x0, 0 # n = 0
    
		n_loop:    
		beq s2, s7, n_done #exit when n==N
		addi s4, x0, 0 #resets sum
		slli s5, s1, 4 #s5 = m*16
		add s5, s5, s0 #base + m*16
		addi s3, x0, 0 #resets k
		
		#computes B[0][n] = base + 0x40 + n*4
		slli s6, s2, 2  #s6 = n * 4
		add  s6, s6, s0 #s6 += base
		addi s6, s6, 0x40 #s6 += B's offset

			k_loop:
			beq  s3, s7, k_done #exit when k==K
			
			lw a0, 0(s5) #A[m][k]
			lw a1, 0(s6) #B[k][n]
			jal ra, mult #returns a0 with the product
			add s4, s4, a0 #accumulate
			
			addi s5, s5, 4 #moves A across the row
			addi s6, s6, 16 #steps down the column
			addi s3, s3, 1 #k++
			jal x0, k_loop
			
			k_done:
			slli t0, s2, 2 #t0 = n * 4
			add  t0, t0, s0 #t0 = base + n*4
			slli t1, s1, 4 #m*16
			add t0, t0, t1 # + m*16
			sw  s4, 128(t0) #stores to C[m][n]

			addi s2, s2, 1 #n++
			jal  x0, n_loop

		n_done:
		addi s1, s1, 1
		jal  x0, m_loop

	m_done:

done:
addi a0, x0, 0
addi a7, x0, 93
ecall


#a0: arrives with the multiplicand leaves with the Final Product
#a1:genuine multiplier
#t0:working copy of multiplicand
#t1:working copy of multiplier
#t2:used for low bit testing

#Labels
#mult: multiplies a0 by a1 using bit-serial shift-and-add the product is returned in a0
#mult_loop: top of the loop, it exits when the multiplier is 0
#mult_skip: Merge point after the conditional add, shifts multiplicand up and multiplier downf or the next bit position.
#mult_done: returns product to caller
mult:
addi t0, a0, 0 #working copy of multiplicand
addi t1, a1, 0 #working copy of multiplier
addi a0, x0, 0 #Product = 0

mult_loop:
beq  t1, x0, mult_done #early exit: multiplier copy empty
andi t2, t1, 1 #test low bit
beq  t2, x0, mult_skip
add  a0, a0, t0 # accumulate

mult_skip:
slli t0, t0, 1 #multiplicand <<= 1
srli t1, t1, 1 #multiplier >>= 1
jal  x0, mult_loop

mult_done:
jalr x0, ra, 0
