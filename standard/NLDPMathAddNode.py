from core import constants, NLDPNode

class NLDPMathAddNode(NLDPNode):
    """
    A basic addition node.
    """
    def __init__(self, x=0, y=0):
        layout = [
            {'field_type': constants.FIELD_TYPE_DYNAMIC, 'label': 'Value A', 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'field_type': constants.FIELD_TYPE_DYNAMIC, 'label': 'Value B', 'data_type': constants.DTYPE_INT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'field_type': constants.FIELD_TYPE_OUTPUT, 'label': 'Output'}
        ]
        super().__init__(title="Value", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the static field value to the output.
        """
        a = float(inputs[0])
        b = float(inputs[1])
        sum = a + b
        return {2: sum}
