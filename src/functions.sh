__array_shift_ret=()

__array_shift() {
	array=($@)
	__array_shift_ret=( ${array[@]:1:$#})
}

__exec() {

  if [ $DEBUG = 1 ]
  then
    echo "Debugging: $@"
  else
    echo "Executing this: " $@
  fi

}
