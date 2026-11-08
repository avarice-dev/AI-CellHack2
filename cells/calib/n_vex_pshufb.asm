; Calibration cell N: VEX-encoded SSSE3 (vpshufb xmm)   Written with AI help.
; Executes exactly: vpshufb xmm0, xmm1, xmm2 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported; an invalid_insn (or other) fault every call -> not.

	vpshufb xmm0, xmm1, xmm2
	mov	al, ACT_REST
	ret
