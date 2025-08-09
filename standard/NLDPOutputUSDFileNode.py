from core import constants, widgets, NLDPNode

class NLDPOutputUSDFileNode(NLDPNode):
    """
    An endpoint node that writes incoming string data to a specified .usda file.
    The write operation is triggered manually by an 'Execute' button.
    """
    def __init__(self, x=0, y=0, **kwargs):
        # Create the button instance first, so we can reference it in the layout
        self.execute_button = widgets.NLDPExecuteButtonWidget()
        
        layout = [
            {'field_type': constants.FIELD_TYPE_INPUT, 'label': 'Data', 'data_type': constants.DTYPE_FILE},
            {'field_type': constants.FIELD_TYPE_STATIC, 'label': 'File Path', 'data_type': constants.DTYPE_FILE, 'widget_type': constants.WIDGET_FILE_BROWSER, 'default_value': ''},
            {'field_type': 'custom_widget', 'widget': self.execute_button}
        ]
        super().__init__(**kwargs, title="Write USD File", layout=layout, x=x, y=y, color=(50, 70, 50), width=12)
        
        # This is the internal, "hidden" member for the final result.
        self.dead_end_values = []

        # Connect the button's signal
        self.execute_button.clicked.connect(self.execute_write)

    def execute_write(self):
        """
        Writes a USD file to disk.
        """
        print("--- Execute Write Triggered ---")
        content = self.dead_end_values[0] if self.dead_end_values else ""
        file_path = self.static_fields[1]['value']

        if not file_path or not isinstance(file_path, str) or not file_path.lower().endswith('.usda'):
            print(f"Error: Invalid or non-.usda file path: '{file_path}'")
            return
            
        if content is None:
            print("Error: No content to write.")
            return

        print("writing will happen here")
        # try:
        #     with open(file_path, 'w') as f:
        #         f.write(str(content))
        #     print(f"Successfully wrote to '{file_path}'")
        # except Exception as e:
        #     print(f"Failed to write to file: {e}")

    def evaluate(self, inputs):
        """
        Fetches the input value and stores it as a dead-end value.
        Does NOT write to the file.
        """
        # The input socket is at row 1
        self.dead_end_values = [inputs.get(0)]
        return {}