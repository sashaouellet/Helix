import nuke

def read(file=None):
	"""Convenience for setting the Read node's file path in a way
	that properly updates the other knobs based on the input.

	Args:
	    file (None, optional): The file path to set the read to

	Returns:
	    nuke.nodes.Read: The Read node, with the file path set if it
	    	was specified
	"""
	read = nuke.nodes.Read()

	if file is not None:
		read['file'].fromUserText(file)

	return read

def write(file=None):
    """Similar to the read function above, this conveniently sets the file path in
    a way that updates the other knobs on the node.
    """
    write = nuke.nodes.Write()

    if file is not None:
    	write['file'].fromUserText(file)

    return write

def wireConsecutively(chain):
	"""Connects the given list of nodes consecutively, returning the last node
	in the chain.

	E.g. if given a Read, Reformat, and Write node:
	The Read will be connected to the Reformat, which will then be connected to
	Write node. The Write node is returned.

	Args:
	    chain (list): A list of nuke.Node, the order of which determines
	    	the connection order.

	Returns:
	    nuke.Node: The last node in the chain (the last in the given list)
	"""
	if chain is None or len(chain) == 0:
		raise ValueError('Must specify a list of at least 1 node')

	if len(chain) > 1:
		for i in range(1, len(chain)):
			connect(chain[i - 1], chain[i])

	return chain[-1]

def connect(nodeFrom, nodeTo, inputNum=0):
    """Sets the input of "nodeTo" to the output of "nodeFrom",
    at the connection point "inputNum"

    Args:
        nodeFrom (nuke.Node): The node whose output will be connected to "nodeTo"
        nodeTo (nuke.Node): The node that will be connected next in the node chain (connected to "nodeFrom")
        inputNum (int, optional): The input number on "nodeTo" to connect "nodeFrom" to. Defaults to 0 (the standard 1:1 connection for nodes)

    Returns:
        nuke.Node: The last node in the chain, after the connection has been performed
    """

    nodeTo.setInput(inputNum, nodeFrom)
    return nodeTo

def setRootKnobValue(name, val):
	nuke.knobDefault('Root.' + name, str(val))
	nuke.Root().knob(name).setValue(val)
