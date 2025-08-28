from core import constants, NLDPNode

class NLDPMathSumNode(NLDPNode):
    """
    A basic addition node.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Value A', 'field_type': constants.FIELD_TYPE_DYNAMIC, 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'label': 'Output', 'field_type': constants.FIELD_TYPE_OUTPUT, 'data_type': constants.DTYPE_FLOAT}
        ]
        super().__init__(**kwargs, title="Sum", layout=layout, x=x, y=y, extra_height=10)

    def evaluate(self, inputs):
        """
        Sums all input values.
        """
        return {2: inputs[0]}
