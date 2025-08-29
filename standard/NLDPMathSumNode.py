from core import constants, NLDPNode

class NLDPMathSumNode(NLDPNode):
    """
    A basic addition node.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Values', 'field_type': constants.FIELD_TYPE_MULTI_INPUT, 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'label': 'Output', 'field_type': constants.FIELD_TYPE_OUTPUT, 'data_type': constants.DTYPE_FLOAT}
        ]
        super().__init__(**kwargs, title="Sum", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Sums all input values.
        """
        sum = 0
        for number in inputs[0]:
            sum += number
        return {1: sum}
