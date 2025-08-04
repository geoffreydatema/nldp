from core import constants, NLDPNode

class NLDPInputFileNode(NLDPNode):
    """
    A node for specifying a file path, with a browse button.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'field_type': constants.FIELD_TYPE_STATIC, 'label': 'File Path', 'data_type': constants.DTYPE_FILEPATH, 'widget_type': constants.WIDGET_FILE_BROWSER, 'default_value': ''},
            {'field_type': constants.FIELD_TYPE_OUTPUT, 'label': 'Path', 'data_type': constants.DTYPE_FILEPATH}
        ]
        super().__init__(**kwargs, title="File", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Passes the file path to the output.
        """
        value = inputs.get(0)
        return {1: value}
