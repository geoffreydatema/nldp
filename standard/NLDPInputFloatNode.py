from core import constants, NLDPNode

class NLDPInputFloatNode(NLDPNode):
    """
    A simple node that provides a user-defined static value.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Value', 'field_type': constants.FIELD_TYPE_STATIC, 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'label': 'Output', 'field_type': constants.FIELD_TYPE_OUTPUT, 'data_type': constants.DTYPE_FLOAT}
        ]
        super().__init__(**kwargs, title="Float", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the static field value to the output.
        """
        value = inputs.get(0)
        return {1: value}