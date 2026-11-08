; Calibration cell I: is andn (BMI1) supported on the server?   Written with AI help.
; Executes exactly: andn eax, ecx, edx / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	andn eax, ecx, edx
	mov	al, ACT_REST
	ret
