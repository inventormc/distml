import logging

import ray
import ray.util.collective as col

logger = logging.getLogger(__name__)

class BaseTrainer:
    def __init__(self, 
                 *,
                 training_operator_cls, 
                 operator_config=None,
                 initialization_hook=None,
                 world_size=2,
                 num_cpus_per_worker=1,
                 num_gpus_per_worker=1,
                 use_tqdm=True,
                 **kwargs):
        self.training_operator_cls = training_operator_cls
        self.initialization_hook = initialization_hook
        if world_size < 2:
            raise RuntimeError("ray.util.distml does not support single-process training "
                               "at this moment.")
        self.world_size = world_size
        self.num_cpus_per_worker = num_cpus_per_worker
        self.num_gpus_per_worker = num_gpus_per_worker

        self._use_tqdm = use_tqdm
        self._operator_config = operator_config

        if not ray.is_initialized() and self.max_replicas > 1:
            logger.info("Automatically initializing single-node Ray. To use "
                        "multi-node training, be sure to run `ray.init("
                        "address='auto')` before instantiating the Trainer.")
            ray.init()
        self._start_workers()

    def train(self):
        """Call operator train_one_epoch. Or run all epochs."""
        raise NotImplementedError()

    def validate(self):
        """Call operator validate to evaluate val_dataloader.
        """
        raise NotImplementedError()

    def step(self):
        """Call step in self.train(). different strategy calling here?
        """
        pass

    def get_parameters(self, state_dict, blocking=False):
        """load model parameter.
        """
        raise NotImplementedError()

    def save_parameters(self, checkpoint):
        """Saves the Trainer state to the provided checkpoint path.

        Args:
            checkpoint (str): Path to target checkpoint file.
        """
        raise NotImplementedError()

    def load_parameters(self, checkpoint):
        raise NotImplementedError()

    def _start_workers(self):
        """Start all the workers to be used for training."""
        raise NotImplementedError()

    def shutdown(self, force=False):
        """Kill all workers.
        """
        raise NotImplementedError()