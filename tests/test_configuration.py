"""Comprehensive tests for hermit.configuration."""

from __future__ import annotations

import pytest

from hermit.configuration import (
    Configuration,
    TableauMonitorType,
    DirectBlockingType,
    BlockingStrategyType,
    BlockingSignatureCacheType,
    ExistentialStrategyType,
    PrepareReasonerInferences,
)


# ===========================================================================
# 1. Configuration defaults match Java defaults
# ===========================================================================

class TestConfigurationDefaults:
    @pytest.fixture
    def config(self):
        return Configuration()

    def test_warning_monitor_default(self, config):
        assert config.warning_monitor is None

    def test_reasoner_progress_monitor_default(self, config):
        assert config.reasoner_progress_monitor is None

    def test_tableau_monitor_type_default(self, config):
        assert config.tableau_monitor_type == TableauMonitorType.NONE

    def test_direct_blocking_type_default(self, config):
        assert config.direct_blocking_type == DirectBlockingType.OPTIMAL

    def test_blocking_strategy_type_default(self, config):
        assert config.blocking_strategy_type == BlockingStrategyType.OPTIMAL

    def test_blocking_signature_cache_type_default(self, config):
        assert config.blocking_signature_cache_type == BlockingSignatureCacheType.CACHED

    def test_existential_strategy_type_default(self, config):
        assert config.existential_strategy_type == ExistentialStrategyType.CREATION_ORDER

    def test_ignore_unsupported_datatypes_default(self, config):
        assert config.ignore_unsupported_datatypes is False

    def test_monitor_default(self, config):
        assert config.monitor is None

    def test_parameters_default(self, config):
        assert config.parameters == {}

    def test_individual_task_timeout_default(self, config):
        assert config.individual_task_timeout == -1

    def test_fresh_entity_policy_default(self, config):
        assert config.fresh_entity_policy.value == "ALLOW"

    def test_individual_node_set_policy_default(self, config):
        assert config.individual_node_set_policy.value == "BY_NAME"

    def test_use_disjunction_learning_default(self, config):
        assert config.use_disjunction_learning is True

    def test_buffer_changes_default(self, config):
        assert config.buffer_changes is True

    def test_throw_inconsistent_ontology_exception_default(self, config):
        assert config.throw_inconsistent_ontology_exception is True

    def test_prepare_reasoner_inferences_default(self, config):
        assert config.prepare_reasoner_inferences is None

    def test_force_quasi_order_classification_default(self, config):
        assert config.force_quasi_order_classification is False


# ===========================================================================
# 2. clone() produces independent copy
# ===========================================================================

class TestConfigurationClone:
    def test_clone_is_independent(self):
        config = Configuration()
        clone = config.clone()
        assert clone is not config

    def test_clone_copies_values(self):
        config = Configuration()
        config.individual_task_timeout = 5000
        config.ignore_unsupported_datatypes = True
        clone = config.clone()
        assert clone.individual_task_timeout == 5000
        assert clone.ignore_unsupported_datatypes is True

    def test_clone_has_fresh_parameters_dict(self):
        config = Configuration()
        config.parameters["key"] = "value"
        clone = config.clone()
        assert clone.parameters == {"key": "value"}
        assert clone.parameters is not config.parameters

    def test_clone_parameters_independent(self):
        config = Configuration()
        config.parameters["key"] = "value"
        clone = config.clone()
        clone.parameters["key"] = "changed"
        assert config.parameters["key"] == "value"

    def test_clone_copies_all_enum_fields(self):
        config = Configuration()
        config.tableau_monitor_type = TableauMonitorType.TIMING
        config.direct_blocking_type = DirectBlockingType.SINGLE
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        config.blocking_signature_cache_type = BlockingSignatureCacheType.NOT_CACHED
        config.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        clone = config.clone()
        assert clone.tableau_monitor_type == TableauMonitorType.TIMING
        assert clone.direct_blocking_type == DirectBlockingType.SINGLE
        assert clone.blocking_strategy_type == BlockingStrategyType.ANYWHERE
        assert clone.blocking_signature_cache_type == BlockingSignatureCacheType.NOT_CACHED
        assert clone.existential_strategy_type == ExistentialStrategyType.INDIVIDUAL_REUSE


# ===========================================================================
# 3. Enum values
# ===========================================================================

class TestEnumValues:
    def test_tableau_monitor_type_values(self):
        assert TableauMonitorType.NONE.value == "NONE"
        assert TableauMonitorType.TIMING.value == "TIMING"
        assert TableauMonitorType.TIMING_WITH_PAUSE.value == "TIMING_WITH_PAUSE"
        assert TableauMonitorType.DEBUGGER_NO_HISTORY.value == "DEBUGGER_NO_HISTORY"
        assert TableauMonitorType.DEBUGGER_HISTORY_ON.value == "DEBUGGER_HISTORY_ON"

    def test_direct_blocking_type_values(self):
        assert DirectBlockingType.SINGLE.value == "SINGLE"
        assert DirectBlockingType.PAIR_WISE.value == "PAIR_WISE"
        assert DirectBlockingType.OPTIMAL.value == "OPTIMAL"

    def test_blocking_strategy_type_values(self):
        assert BlockingStrategyType.ANYWHERE.value == "ANYWHERE"
        assert BlockingStrategyType.ANCESTOR.value == "ANCESTOR"
        assert BlockingStrategyType.COMPLEX_CORE.value == "COMPLEX_CORE"
        assert BlockingStrategyType.SIMPLE_CORE.value == "SIMPLE_CORE"
        assert BlockingStrategyType.OPTIMAL.value == "OPTIMAL"

    def test_blocking_signature_cache_type_values(self):
        assert BlockingSignatureCacheType.CACHED.value == "CACHED"
        assert BlockingSignatureCacheType.NOT_CACHED.value == "NOT_CACHED"

    def test_existential_strategy_type_values(self):
        assert ExistentialStrategyType.CREATION_ORDER.value == "CREATION_ORDER"
        assert ExistentialStrategyType.INDIVIDUAL_REUSE.value == "INDIVIDUAL_REUSE"
        assert ExistentialStrategyType.EL.value == "EL"


# ===========================================================================
# 4. PrepareReasonerInferences defaults
# ===========================================================================

class TestPrepareReasonerInferences:
    @pytest.fixture
    def pri(self):
        return PrepareReasonerInferences()

    def test_class_classification_required(self, pri):
        assert pri.class_classification_required is True

    def test_object_property_classification_required(self, pri):
        assert pri.object_property_classification_required is True

    def test_data_property_classification_required(self, pri):
        assert pri.data_property_classification_required is True

    def test_object_property_domains_required(self, pri):
        assert pri.object_property_domains_required is True

    def test_object_property_ranges_required(self, pri):
        assert pri.object_property_ranges_required is True

    def test_realisation_required(self, pri):
        assert pri.realisation_required is True

    def test_object_property_realisation_required(self, pri):
        assert pri.object_property_realisation_required is True

    def test_data_property_realisation_required(self, pri):
        assert pri.data_property_realisation_required is True

    def test_same_as(self, pri):
        assert pri.same_as is True

    def test_can_set_fields_to_false(self, pri):
        pri.class_classification_required = False
        pri.realisation_required = False
        assert pri.class_classification_required is False
        assert pri.realisation_required is False


# ===========================================================================
# 5. Compatibility methods
# ===========================================================================

class TestConfigurationCompatibility:
    def test_get_time_out(self):
        config = Configuration()
        config.individual_task_timeout = 30000
        assert config.getTimeOut() == 30000

    def test_get_fresh_entity_policy(self):
        config = Configuration()
        assert config.getFreshEntityPolicy().value == "ALLOW"

    def test_get_progress_monitor(self):
        config = Configuration()
        assert config.getProgressMonitor() is None

    def test_get_individual_node_set_policy(self):
        config = Configuration()
        assert config.getIndividualNodeSetPolicy().value == "BY_NAME"
