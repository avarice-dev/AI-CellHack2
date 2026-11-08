; Calibration cell G: is pshufb (SSSE3) supported on the server?   Written with AI help.
; Executes exactly: pshufb xmm0, xmm1 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	pshufb xmm0, xmm1
	mov	al, ACT_REST
	ret
