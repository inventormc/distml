"""Test the send/recv API."""
import pytest
import numpy as np
import os

import ray
from ray.util.collective.types import Backend
from ray.util.collective.tests.conftest import clean_up

from tests.jax_util import make_jax_ar_strategy, ToyOperator

import jax
import jax.numpy as jnp

from ray.util.sgd.utils import AverageMeterCollection


class Test_allreduce_strategy_single_node_2workers:
    world_size = 2

    def setup_class(self):
        world_size = self.world_size
        ray.init(num_gpus=world_size,
                 num_cpus=world_size * 2)
        self.strategy = make_jax_ar_strategy(world_size)

    def teardown_class(self):
        del self.strategy
        ray.shutdown()
        # os.system("ray stop")

    def test_init_strategy(self):
        self._check_sync_params()

    def _check_sync_params(self):
        strategy = self.strategy

        rets = [replica.get_named_parameters.remote(cpu=True)
                for replica in strategy.data_parallel_group.replicas]

        params = ray.get(rets)

        keys = params[0].keys()
        num_replica = len(params)
        for key in keys:
            for i in range(num_replica - 1):
                self._assert_allclose(params[i][key],
                                      params[i+1][key])

    def _assert_allclose(self, p, q):
        assert np.allclose(p, q, atol=0.01, rtol=0.1)

    @pytest.mark.parametrize("num_steps", [None, 2, 10])
    def test_train(self, num_steps):
        self.strategy.train(num_steps) # train a full epoch
        self._check_sync_params()

    def test_validate(self):
        metrics = self.strategy.validate()

    def test_validate_result(self):
        """Make sure all replicas validate results are the same.

        But it cant be test after using distributed sampler.
        """
        strategy = self.strategy

        steps = strategy.data_parallel_group.get_data_loader_len(training=False)
        metrics = [AverageMeterCollection()
                   for _ in range(len(strategy.data_parallel_group.replicas))]

        strategy.data_parallel_group.make_iterator(training=False)
        for idx in range(steps):
            batch_metrics = strategy.data_parallel_group.validate_batch()
            for metric_idx, metric in enumerate(batch_metrics):
                samples_num = metric.pop("samples_num")
                metrics[metric_idx].update(metric, n=samples_num)

        keys = ["num_samples", "val_loss", "val_accuracy"]
        num_replica = len(metrics)
        for key in keys:
            for i in range(num_replica - 1):
                assert metrics[i]._meters[key].avg - \
                       metrics[i+1]._meters[key].avg < 1e-4


class Test_allreduce_strategy_single_node_multi_task:
    def setup_class(self):
        ray.init(num_gpus=8,
                 num_cpus=16)

    def teardown_class(self):
        ray.shutdown()

    # @pytest.mark.parametrize("num_task", [2,3,4])
    # def test_multi_task(self, num_task):
    #     """Just try to create multi-task.
    #     Can not run multi-task asynchronous."""
    #     strategy_list = []
    #     for i in range(num_task):
    #         strategy = make_jax_ar_strategy(group_name=f"task{i}")
    #         strategy_list.append(strategy)
    #
    #     for i in range(num_task):
    #         strategy_list[i].train()

if __name__ == "__main__":
    import pytest
    import sys

    sys.exit(pytest.main(["-v", "-x", __file__])) #  ,"-s" # for debug