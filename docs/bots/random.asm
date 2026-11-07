;
; random
;
; rests until it has 6 energy, then does something random: a move, split, eat or feed in random direction.
;

	; do we have enough energy to do something? otherwise rest.

	cmp		rsi, 6
	jb		rest

	; get two random nibbles
	mov		bl, byte [rdi + VIEW_RAND]
	and		bl, 0xf0
	shr		bl, 4
	mov		cl, byte [rdi + VIEW_RAND]
	and		cl, 0x0f

	; pick a random action
	and 	bl, 0x3				; last two bits gives b00 (0) -> b11 (3)
	add		bl, 1				; 0->3 becomes 1->4
	shl		bl, 4				; move to high nibble

	; pick a random direction
	and		cl, ACT_DIR_MASK

	; do a random thing in a random direction
	; al = rand act + rand dir
	mov		al, bl
	add		al, cl
	ret

rest:
	mov		al, ACT_REST
	ret