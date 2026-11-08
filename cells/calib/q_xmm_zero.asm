; Calibration cell Q: are xmm0..xmm15 all zero at entry?  (also: is VEX vpmovmskb accepted?)   Written with AI help.
; ORs all 16 xmm registers into xmm0, compares with zero, and returns an invalid action (0xFF) if any bit was set.
; Match page: 22 insns/call, no faults -> all xmm zero at entry on every call.
;   bad_action faults (path is 23) -> some xmm register is NOT zero at entry (or keeps state between calls).
;   invalid_insn fault -> vpmovmskb (VEX) is not accepted; result about zeroing unknown.

	por	xmm0, xmm1
	por	xmm0, xmm2
	por	xmm0, xmm3
	por	xmm0, xmm4
	por	xmm0, xmm5
	por	xmm0, xmm6
	por	xmm0, xmm7
	por	xmm0, xmm8
	por	xmm0, xmm9
	por	xmm0, xmm10
	por	xmm0, xmm11
	por	xmm0, xmm12
	por	xmm0, xmm13
	por	xmm0, xmm14
	por	xmm0, xmm15
	vpxor	xmm1, xmm1, xmm1
	vpcmpeqb xmm0, xmm0, xmm1		; 0xFF in every byte that was zero
	vpmovmskb eax, xmm0
	cmp	eax, 0xFFFF
	jne	bad
	mov	al, ACT_REST
	ret
bad:
	mov	al, 0xFF
	ret
