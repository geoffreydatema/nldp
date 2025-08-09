from core import constants, NLDPNode

class NLDPInputUSDFileNode(NLDPNode):
    """
    A node for opening a USD file.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'field_type': constants.FIELD_TYPE_STATIC, 'label': 'File Path', 'data_type': constants.DTYPE_FILE, 'widget_type': constants.WIDGET_FILE_BROWSER, 'default_value': ''},
            {'field_type': constants.FIELD_TYPE_OUTPUT, 'label': 'Data', 'data_type': constants.DTYPE_FILE}
        ]
        super().__init__(**kwargs, title="USD File", layout=layout, x=x, y=y, color=(50, 50, 70), width=12)

    def evaluate(self, inputs):
        file_path = inputs.get(0)

        if file_path and isinstance(file_path, str):
            if file_path.lower().endswith('.usda'):
                return {1: file_path}
        
        return {1: None}
