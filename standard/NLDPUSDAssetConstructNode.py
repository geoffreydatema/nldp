from core import constants, NLDPNode

class NLDPUSDAssetConstructNode(NLDPNode):
    """
    A basic addition node.
    """
    def __init__(self, x=0, y=0, **kwargs):
        layout = [
            {'label': 'Asset Definition', 'field_type': constants.FIELD_TYPE_INPUT, 'data_type': constants.DTYPE_FILE},
            {'label': 'Highres Geometry A', 'field_type': constants.FIELD_TYPE_INPUT, 'data_type': constants.DTYPE_FILE},
            {'label': 'Output', 'field_type': constants.FIELD_TYPE_OUTPUT, 'data_type': constants.DTYPE_FILE}
        ]
        super().__init__(**kwargs, title="USD Asset Construct", layout=layout, x=x, y=y, color=(50, 70, 70), width=10)

    def evaluate(self, inputs):
        """
        Constructs a USD asset from an asset definition (locators) and geometry.
        """
        stage = inputs[0]
        high_res = inputs[1].GetRootLayer().realPath
        locator = stage.GetPrimAtPath("/root/Empty")
        locator.GetReferences().ClearReferences()
        locator.GetReferences().AddReference(high_res)
        
        return {2: stage}
