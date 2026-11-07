;
; hunter
;
; eats any enemy next to it, otherwise splits when fat, otherwise rests.
;

	; is there an enemy above, right, below or left of me?

	lea		r8, [rdi + VIEW_CELLS]
	mov		al, BYTE [r8 + VIEW_UP]
	cmp		al, CELL_ENEMY
	je		eat_up
	mov		al, BYTE [r8 + VIEW_RIGHT]
	cmp		al, CELL_ENEMY
	je		eat_right
	mov		al, BYTE [r8 + VIEW_DOWN]
	cmp		al, CELL_ENEMY
	je		eat_down
	mov		al, BYTE [r8 + VIEW_LEFT]
	cmp		al, CELL_ENEMY
	je		eat_left

	; nobody to eat, how much energy do we have? rest or grow?

	cmp		rsi, 6
	jb		rest

	; grow in a random direction

	; choose random direction
	mov		cl, BYTE [rdi + VIEW_RAND]
	and		cl, ACT_DIR_MASK
	; al = ACT_SPLIT + dir
	mov		al, ACT_SPLIT
	add		al, cl
	ret

rest:
	mov		al, ACT_REST
	ret

eat_up:
	mov		al, ACT_EAT
	add		al, DIR_UP
	ret
eat_right:
	mov		al, ACT_EAT
	add		al, DIR_RIGHT
	ret
eat_down:
	mov		al, ACT_EAT
	add		al, DIR_DOWN
	ret
eat_left:
	mov		al, ACT_EAT
	add		al, DIR_LEFT
	ret