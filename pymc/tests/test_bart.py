import numpy as np
import pytest

from numpy.random import RandomState

import pymc as pm

from pymc.tests.test_distributions_moments import assert_moment_is_expected


def test_split_node():
    split_node = pm.bart.tree.SplitNode(index=5, idx_split_variable=2, split_value=3.0)
    assert split_node.index == 5
    assert split_node.idx_split_variable == 2
    assert split_node.split_value == 3.0
    assert split_node.depth == 2
    assert split_node.get_idx_parent_node() == 2
    assert split_node.get_idx_left_child() == 11
    assert split_node.get_idx_right_child() == 12


def test_leaf_node():
    leaf_node = pm.bart.tree.LeafNode(index=5, value=3.14, idx_data_points=[1, 2, 3])
    assert leaf_node.index == 5
    assert np.array_equal(leaf_node.idx_data_points, [1, 2, 3])
    assert leaf_node.value == 3.14
    assert leaf_node.get_idx_parent_node() == 2
    assert leaf_node.get_idx_left_child() == 11
    assert leaf_node.get_idx_right_child() == 12


def test_bart_vi():
    X = np.random.normal(0, 1, size=(3, 250)).T
    Y = np.random.normal(0, 1, size=250)
    X[:, 0] = np.random.normal(Y, 0.1)

    with pm.Model() as model:
        mu = pm.BART("mu", X, Y, m=10)
        sigma = pm.HalfNormal("sigma", 1)
        y = pm.Normal("y", mu, sigma, observed=Y)
        idata = pm.sample(random_seed=3415)
        var_imp = (
            idata.sample_stats["variable_inclusion"]
            .stack(samples=("chain", "draw"))
            .mean("samples")
        )
        var_imp /= var_imp.sum()
        assert var_imp[0] > var_imp[1:].sum()
        np.testing.assert_almost_equal(var_imp.sum(), 1)


def test_missing_data():
    X = np.random.normal(0, 1, size=(2, 50)).T
    Y = np.random.normal(0, 1, size=50)
    X[10:20, 0] = np.nan

    with pm.Model() as model:
        mu = pm.BART("mu", X, Y, m=10)
        sigma = pm.HalfNormal("sigma", 1)
        y = pm.Normal("y", mu, sigma, observed=Y)
        idata = pm.sample(random_seed=3415, chains=1)


@pytest.mark.xfail(reason="random fn is not yet implemented")
def test_random_fn():
    X = np.random.normal(0, 1, size=(2, 50)).T
    Y = np.random.normal(0, 1, size=50)

    with pm.Model() as model:
        mu = pm.BART("mu", X, Y, m=10)
    rng = RandomState(12345)
    pred_all = mu.owner.op.rng_fn(rng, size=2)
    rng = RandomState(12345)
    pred_first = mu.owner.op.rng_fn(rng, X_new=X[:10])

    assert pred_all.shape == (2, 50)
    assert pred_first.shape == (10,)
    np.testing.assert_almost_equal(pred_first, pred_all[0, :10], decimal=4)


class TestUtils:
    X = np.random.normal(0, 1, size=(2, 50)).T
    Y = np.random.normal(0, 1, size=50)

    with pm.Model() as model:
        mu = pm.BART("mu", X, Y, m=10, response="mix")
        sigma = pm.HalfNormal("sigma", 1)
        y = pm.Normal("y", mu, sigma, observed=Y)
        idata = pm.sample(random_seed=3415)

    def test_predict(self):
        rng = RandomState(12345)
        pred_all = pm.bart.utils.predict(self.idata, rng, size=2)
        rng = RandomState(12345)
        pred_first = pm.bart.utils.predict(self.idata, rng, X_new=self.X[:10])

        np.testing.assert_almost_equal(pred_first, pred_all[0, :10], decimal=4)
        assert pred_all.shape == (2, 50)
        assert pred_first.shape == (10,)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {},
            {
                "kind": "pdp",
                "samples": 2,
                "xs_interval": "quantiles",
                "xs_values": [0.25, 0.5, 0.75],
            },
            {"kind": "ice", "instances": 2},
            {"var_idx": [0], "rug": False, "smooth": False, "color": "k"},
            {"grid": (1, 2), "sharey": "none", "alpha": 1},
        ],
    )
    def test_pdp(self, kwargs):
        pm.bart.utils.plot_dependence(self.idata, X=self.X, Y=self.Y, **kwargs)


@pytest.mark.parametrize(
    "size, expected",
    [
        (None, np.zeros(50)),
    ],
)
def test_bart_moment(size, expected):
    X = np.zeros((50, 2))
    Y = np.zeros(50)
    with pm.Model() as model:
        pm.BART("x", X=X, Y=Y, size=size)
    assert_moment_is_expected(model, expected)
