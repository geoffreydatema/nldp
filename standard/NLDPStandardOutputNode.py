from core import constants, NLDPNode

class NLDPStandardOutputNode(NLDPNode):
    """
    An endpoint node that receives a value for display or final output.
    """
    def __init__(self, x=0, y=0):
        layout = [
            {'type': constants.ROW_TYPE_INPUT, 'label': 'Input'}
        ]
        super().__init__(title="Output", layout=layout, x=x, y=y, color=(50, 50, 70))
        
        # This is the internal, "hidden" member for the final result.
        self.dead_end_values = []

    def evaluate(self, inputs):
        """
        Fetches the input value and stores it as the final result.
        """
        self.dead_end_values.append(inputs.get(0))
        return {}
