"""Base validator assembled from focused lifecycle mixins.

`BaseValidator` is the minimal, runnable-agnostic validator: it wires together
configuration, chain/metagraph state and tabular reporting, then initialises the
instance attributes that the rest of the system mutates. The concrete proxy
validator (`HashLayerProxyValidator`) layers evaluation/weights/state mixins on
top of this class.
"""

from hashlayer.validator.chain import ChainStateMixin
from hashlayer.validator.config import ValidatorConfigMixin
from hashlayer.validator.reporting import ValidatorReportingMixin
from hashlayer.validator.storage import get_validator_storage


class BaseValidator(ValidatorConfigMixin, ChainStateMixin, ValidatorReportingMixin):
    """Core validator: config + chain lifecycle + reporting.

    Composed from:
    - ``ValidatorConfigMixin``    — argument parsing and logging setup
    - ``ChainStateMixin``         — wallet/subtensor/metagraph lifecycle
    - ``ValidatorReportingMixin`` — score/weight table rendering
    """

    def __init__(self):
        # Resolve configuration and bring logging online first so every
        # subsequent step is captured.
        self.config = self.get_config()
        self.setup_logging_path()
        self.setup_logging()

        self.storage = get_validator_storage(
            storage_type=self.config.storage, config=self.config
        )

        # Chain handles, populated by setup_bittensor_objects().
        self.subtensor = None
        self.wallet = None
        self.metagraph = None
        self.tempo = None
        self.uid = None
        self.weights_interval = None

        # Scheduling / scoring state.
        self.eval_interval = self.config.eval_interval
        self.last_update = 0
        self.current_block = 0
        self.scores = []
        self.hotkeys = []
        self.block_at_registration = []
