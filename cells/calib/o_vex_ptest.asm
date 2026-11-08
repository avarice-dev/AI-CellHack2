; Calibration cell O: VEX-encoded SSE4.1 (vptest xmm)   Written with AI help.
; Executes exactly: vptest xmm0, xmm1 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported; an invalid_insn (or other) fault every call -> not.

	vptest xmm0, xmm1
	mov	al, ACT_REST
	ret
