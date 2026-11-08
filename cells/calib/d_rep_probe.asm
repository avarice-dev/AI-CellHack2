; Calibration cell D: does `rep stosb` count once or once per iteration?   Written with AI help.
; Run in the Sandbox (paste this whole file; no org/bits/section/%include needed).
;
; Writes 100 bytes to the scratch part of the cell page ([rdx+64 .. rdx+163]); the 64 persistent
; bytes are not touched, and the scratch is zeroed before every call anyway.
; Executes: lea / mov ecx,100 / rep stosb / mov al,ACT_REST / ret
; Match page "average instructions per call":
;   5    -> rep stosb counts as ONE instruction (a cheap way to do bulk work)
;   104  -> each of the 100 iterations counts (4 other instructions + 100)
;   other (e.g. 103, 105) -> per-iteration counting with an off-by-one (QEMU counts the final
;           check or not); send the exact number.
; Expected fault log: empty.  A memory fault would mean the scratch area is not writable as documented.

	lea	rdi, [rdx + 64]
	mov	ecx, 100
	rep	stosb
	mov	al, ACT_REST
	ret
