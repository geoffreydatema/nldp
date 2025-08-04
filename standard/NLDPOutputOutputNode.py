from core import constants, NLDPNode

class NLDPOutputOutputNode(NLDPNode):
    """
    An endpoint node that receives a value for display or final output.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Input', 'field_type': constants.FIELD_TYPE_INPUT}
        ]
        super().__init__(**kwargs, title="Output", layout=layout, x=x, y=y, color=(50, 50, 70))
        
        self.dead_end_values = []

    def evaluate(self, inputs):
        """
        Fetches the input value and stores it as the final result.
        """
        self.dead_end_values = [inputs.get(0)]
        return {}
