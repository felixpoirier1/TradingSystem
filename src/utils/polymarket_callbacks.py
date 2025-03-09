from inspect import Parameter, Signature
from typing import Dict, Callable


callback_sig_table = {
}
callback_sig_table["market_ws_msg"] = Signature(
        parameters=[
            Parameter("msg", Parameter.POSITIONAL_ONLY, annotation=Dict)
        ],
        return_annotation = None
    )

