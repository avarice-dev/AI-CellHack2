; Calibration cell E: may a call end with a jump to EXIT_ADDR instead of `ret`?   Written with AI help.
; Run in the Sandbox (paste this whole file; no org/bits/section/%include needed).
; Covetous (cells/covetous.asm) leaves its bite path with `jnz EXIT_ADDR`; this checks that on the site.
;
; Executes exactly: mov al,ACT_REST / jmp EXIT_ADDR
; Match page:
;   2 instructions per call, no faults, colony rests and grows energy -> the jump ends the call like ret.
;   any fault (e.g. bad rsp, fetch at EXIT_ADDR) or no action -> do NOT ladder Covetous.
; Result (Sandbox match 99887, vs Idle, 500 ticks): 2 insns/call, 0 faults, energy 50 -> works like ret.

	mov	al, ACT_REST
	jmp	EXIT_ADDR
