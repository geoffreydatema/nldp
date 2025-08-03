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
        self.final_result = None

    def evaluate(self, inputs):
        """
        Fetches the input value and stores it as the final result.
        """
        # The input is at row 0
        self.final_result = inputs.get(0)
        
        # This node has no outputs, so it returns an empty dictionary.
        return {}
