; Calibration cell H: is ptest (SSE4.1) supported on the server?   Written with AI help.
; Executes exactly: ptest xmm0, xmm1 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	ptest xmm0, xmm1
	mov	al, ACT_REST
	ret
