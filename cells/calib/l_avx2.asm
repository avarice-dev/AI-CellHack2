; Calibration cell L: is vpcmpeqb_ymm (AVX2) supported on the server?   Written with AI help.
; Executes exactly: vpcmpeqb ymm0, ymm1, ymm2 / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	vpcmpeqb ymm0, ymm1, ymm2
	mov	al, ACT_REST
	ret
