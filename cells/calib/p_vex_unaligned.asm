; Calibration cell P: VEX op with an UNALIGNED memory operand (view at +7; legacy SSE would fault)   Written with AI help.
; Executes exactly: vpcmpeqb xmm0, xmm0, [rdi + VIEW_CELLS + 7] / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported; an invalid_insn (or other) fault every call -> not.

	vpcmpeqb xmm0, xmm0, [rdi + VIEW_CELLS + 7]
	mov	al, ACT_REST
	ret
