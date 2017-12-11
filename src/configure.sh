source vars

__configure() {
	echo "CONFIGURE FUNCTION"
	echo "args:" $@

	# i3
	__exec ln -s "${FILES}/i3"  "${CONFIG_DIR}/i3"

	# polybar
	__exec ln -s "${FILES}/polybar"  "${CONFIG_DIR}/polybar"
}
