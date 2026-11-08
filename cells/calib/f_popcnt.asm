; Calibration cell F: is popcnt (POPCNT) supported on the server?   Written with AI help.
; Executes exactly: popcnt eax, ecx / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	popcnt eax, ecx
	mov	al, ACT_REST
	ret
