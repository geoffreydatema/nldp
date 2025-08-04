from core import constants, NLDPNode

class NLDPStandardValueNode(NLDPNode):
    """
    A simple node that provides a user-defined static value.
    """
    def __init__(self, x=0, y=0):
        layout = [
            {'field_type': constants.FIELD_TYPE_STATIC, 'label': 'Value', 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'field_type': constants.FIELD_TYPE_OUTPUT, 'label': 'Output'}
        ]
        super().__init__(title="Value", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the static field value to the output.
        """
        value = inputs.get(0)
        return {1: value} # Output is at row 1
