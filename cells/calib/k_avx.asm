; Calibration cell K: is vpcmpeqb (AVX) supported on the server?   Written with AI help.
; Executes exactly: vpcmpeqb xmm0, xmm1, xmm2 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	vpcmpeqb xmm0, xmm1, xmm2
	mov	al, ACT_REST
	ret
