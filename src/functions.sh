__array_shift_ret=()

__array_shift() {
	array=($@)
	__array_shift_ret=( ${array[@]:1:$#})
}