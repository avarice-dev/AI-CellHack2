; Calibration cell M: is crc32 (SSE4.2) supported on the server?   Written with AI help.
; Executes exactly: crc32 eax, ecx / mov al,ACT_REST / ret  (3 instructions).
; Match page: 3 insns/call and no faults -> supported.  An invalid-opcode fault every call -> not supported.

	crc32 eax, ecx
	mov	al, ACT_REST
	ret
