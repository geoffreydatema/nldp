from core import constants, NLDPNode

class NLDPStandardValueNode(NLDPNode):
    """
    A simple node that provides a user-defined static value.
    """
    def __init__(self, x=0, y=0):
        layout = [
            {'type': constants.ROW_TYPE_STATIC, 'label': 'Value', 'default_value': 0.0},
            {'type': constants.ROW_TYPE_OUTPUT, 'label': 'Output'}
        ]
        super().__init__(title="Value", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the static field value to the output.
        """
        value = inputs[0]
        return {1: value}
