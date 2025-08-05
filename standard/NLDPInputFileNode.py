from core import constants, NLDPNode

class NLDPInputFileNode(NLDPNode):
    """
    A node for specifying a file path, with a browse button.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'field_type': constants.FIELD_TYPE_STATIC, 'label': 'File Path', 'data_type': constants.DTYPE_FILEPATH, 'widget_type': constants.WIDGET_FILE_BROWSER, 'default_value': ''},
            {'field_type': constants.FIELD_TYPE_OUTPUT, 'label': 'Data', 'data_type': constants.DTYPE_STRING}
        ]
        super().__init__(**kwargs, title="File", layout=layout, x=x, y=y)

    def evaluate(self, inputs):
        """
        Reads the contents of the specified .txt file and passes them to the output.
        """
        file_path = inputs.get(0)
        file_contents = None

        if file_path and isinstance(file_path, str):
            if file_path.lower().endswith('.txt'):
                try:
                    with open(file_path, 'r') as f:
                        file_contents = f.read()
                except FileNotFoundError:
                    print(f"Error: File not found at '{file_path}'")
                except Exception as e:
                    print(f"An error occurred while reading the file: {e}")
            else:
                raise Exception("Error: File type not supported")
        
        return {1: file_contents}
