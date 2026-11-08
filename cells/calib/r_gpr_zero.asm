; Calibration cell R: are rbx, rcx, rbp, r8..r15 zero at entry?   Written with AI help.
; (rdi, rsi, rdx are the arguments, rsp is the stack; rax = 0 was shown by cell C.)
; Match page: 15 insns/call, no faults -> all zero.  bad_action faults (path 16) -> at least one is not.

	mov	rax, rbx
	or	rax, rcx
	or	rax, rbp
	or	rax, r8
	or	rax, r9
	or	rax, r10
	or	rax, r11
	or	rax, r12
	or	rax, r13
	or	rax, r14
	or	rax, r15
	test	rax, rax
	jnz	bad
	mov	al, ACT_REST
	ret
bad:
	mov	al, 0xFF
	ret
