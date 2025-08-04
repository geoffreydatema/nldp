from core import constants, NLDPNode

class NLDPMathAddNode(NLDPNode):
    """
    A basic addition node.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Value A', 'field_type': constants.FIELD_TYPE_DYNAMIC, 'data_type': constants.DTYPE_FLOAT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'label': 'Value B', 'field_type': constants.FIELD_TYPE_DYNAMIC, 'data_type': constants.DTYPE_INT, 'widget_type': constants.WIDGET_LINEEDIT, 'default_value': 0.0},
            {'label': 'Output', 'field_type': constants.FIELD_TYPE_OUTPUT, 'data_type': constants.DTYPE_FLOAT}
        ]
        super().__init__(**kwargs, title="Add", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the static field value to the output.
        """
        return {2: inputs[0] + inputs[1]}
