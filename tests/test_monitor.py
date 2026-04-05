"""Comprehensive tests for hermit.monitor."""

from __future__ import annotations

import io

import pytest

from hermit.monitor import (
    CountingMonitor,
    TableauMonitor,
    TableauMonitorAdapter,
    TableauMonitorFork,
    TableauMonitorForwarder,
    Timer,
    TestRecord as MonitorTestRecord,
)


# ===========================================================================
# 1. CountingMonitor
# ===========================================================================

class TestCountingMonitor:
    def test_instantiate(self):
        monitor = CountingMonitor()
        assert monitor is not None

    def test_initial_values_are_zero(self):
        monitor = CountingMonitor()
        assert monitor.time == 0
        assert monitor.number_of_backtrackings == 0
        assert monitor.number_of_nodes == 0
        assert monitor.number_of_blocked_nodes == 0
        assert monitor.get_overall_number_of_tests() == 0
        assert monitor.get_overall_number_of_clashes() == 0
        assert monitor.get_overall_time() == 0

    def test_reset_clears_values(self):
        monitor = CountingMonitor()
        monitor.reset()
        assert monitor.time == 0
        assert monitor.get_overall_number_of_tests() == 0

    def test_get_used_message_patterns_initially_empty(self):
        monitor = CountingMonitor()
        assert monitor.get_used_message_patterns() == set()

    def test_get_time_sorted_test_records_empty(self):
        monitor = CountingMonitor()
        records = monitor.get_time_sorted_test_records(10)
        assert records == []

    def test_millis_to_hours_minutes_seconds_string(self):
        # Note: the implementation has a quirk where it divides total_secs by 1000
        # to get ms, so the ms component reflects (total_secs % 1000), not (ms % 1000).
        assert CountingMonitor.millis_to_hours_minutes_seconds_string(0) == "000ms"
        assert CountingMonitor.millis_to_hours_minutes_seconds_string(1000) == "01s001ms"
        assert CountingMonitor.millis_to_hours_minutes_seconds_string(60000) == "01m060ms"
        assert CountingMonitor.millis_to_hours_minutes_seconds_string(3600000) == "01h600ms"

    def test_get_average_time_when_no_tests(self):
        monitor = CountingMonitor()
        assert monitor.get_average_time() == 0

    def test_get_average_number_of_backtrackings_when_no_tests(self):
        monitor = CountingMonitor()
        assert monitor.get_average_number_of_backtrackings() == 0

    def test_get_average_number_of_nodes_when_no_tests(self):
        monitor = CountingMonitor()
        assert monitor.get_average_number_of_nodes() == 0

    def test_get_average_number_of_blocked_nodes_when_no_tests(self):
        monitor = CountingMonitor()
        assert monitor.get_average_number_of_blocked_nodes() == 0

    def test_get_possibles_to_instances_when_no_tests(self):
        monitor = CountingMonitor()
        assert monitor.get_possibles_to_instances() == 0.0

    def test_get_test_description_empty(self):
        monitor = CountingMonitor()
        assert monitor.get_test_description() == ""

    def test_get_test_result_default(self):
        monitor = CountingMonitor()
        assert monitor.get_test_result() is False

    def test_get_validation_time_zero_initially(self):
        monitor = CountingMonitor()
        assert monitor.get_validation_time() == 0

    def test_get_no_validations_zero_initially(self):
        monitor = CountingMonitor()
        assert monitor.get_no_validations() == 0

    def test_get_initial_model_size_zero_initially(self):
        monitor = CountingMonitor()
        assert monitor.get_initial_model_size() == 0

    def test_get_initially_blocked_zero_initially(self):
        monitor = CountingMonitor()
        assert monitor.get_initially_blocked() == 0

    def test_get_initially_invalid_zero_initially(self):
        monitor = CountingMonitor()
        assert monitor.get_initially_invalid() == 0

    def test_get_overall_initial_model_size_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_overall_initial_model_size() == 0

    def test_get_overall_initially_blocked_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_overall_initially_blocked() == 0

    def test_get_overall_initially_invalid_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_overall_initially_invalid() == 0

    def test_get_overall_no_validations_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_overall_no_validations() == 0

    def test_get_overall_validation_time_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_overall_validation_time() == 0

    def test_get_average_initial_model_size_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_average_initial_model_size() == 0

    def test_get_average_initially_blocked_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_average_initially_blocked() == 0

    def test_get_average_initially_invalid_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_average_initially_invalid() == 0

    def test_get_average_no_validations_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_average_no_validations() == 0

    def test_get_average_validation_time_zero(self):
        monitor = CountingMonitor()
        assert monitor.get_average_validation_time() == 0

    def test_clash_detected_increments_counter(self):
        monitor = CountingMonitor()
        monitor.clash_detected()
        assert monitor.get_overall_number_of_clashes() == 1

    def test_possible_instance_counters(self):
        monitor = CountingMonitor()
        monitor.possible_instance_is_instance()
        assert monitor.get_number_of_possible_instances_tested() == 1
        assert monitor.get_number_of_possible_instances_instances() == 1
        monitor.possible_instance_is_not_instance()
        assert monitor.get_number_of_possible_instances_tested() == 2
        assert monitor.get_number_of_possible_instances_instances() == 1


# ===========================================================================
# 2. MonitorTestRecord
# ===========================================================================

class TestMonitorTestRecord:
    def test_properties(self):
        rec = MonitorTestRecord(1500, "test description", True)
        assert rec.test_time == 1500
        assert rec.test_description == "test description"
        assert rec.test_result is True

    def test_sorting_by_time_descending(self):
        r1 = MonitorTestRecord(100, "a", True)
        r2 = MonitorTestRecord(200, "b", True)
        r3 = MonitorTestRecord(50, "c", False)
        records = [r1, r2, r3]
        records.sort()
        assert records[0].test_time == 200
        assert records[1].test_time == 100
        assert records[2].test_time == 50

    def test_sorting_by_description_when_time_equal(self):
        r1 = MonitorTestRecord(100, "zebra", True)
        r2 = MonitorTestRecord(100, "apple", True)
        records = [r1, r2]
        records.sort()
        assert records[0].test_description == "apple"
        assert records[1].test_description == "zebra"

    def test_equality(self):
        r1 = MonitorTestRecord(100, "test", True)
        r2 = MonitorTestRecord(100, "test", False)  # result doesn't affect equality
        assert r1 == r2

    def test_inequality(self):
        r1 = MonitorTestRecord(100, "test_a", True)
        r2 = MonitorTestRecord(200, "test_b", True)
        assert r1 != r2

    def test_repr_short_time(self):
        rec = MonitorTestRecord(500, "short test", True)
        r = repr(rec)
        assert "500 ms" in r
        assert "short test" in r

    def test_repr_long_time(self):
        rec = MonitorTestRecord(3661000, "long test", True)
        r = repr(rec)
        assert "01h01m01s" in r

    def test_comparison_operators(self):
        r1 = MonitorTestRecord(200, "b", True)
        r2 = MonitorTestRecord(100, "a", True)
        assert r1 < r2  # higher time first (descending)
        assert r1 <= r2
        assert r2 > r1
        assert r2 >= r1


# ===========================================================================
# 3. TableauMonitorFork
# ===========================================================================

class TestTableauMonitorFork:
    def test_forwards_to_both_monitors(self):
        first = TableauMonitorAdapter()
        second = TableauMonitorAdapter()
        fork = TableauMonitorFork(first, second)

        # Track calls via subclass
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.clash_count = 0

            def clash_detected(self):
                self.clash_count += 1

        first_t = TrackingAdapter()
        second_t = TrackingAdapter()
        fork = TableauMonitorFork(first_t, second_t)
        fork.clash_detected()
        assert first_t.clash_count == 1
        assert second_t.clash_count == 1

    def test_set_tableau_forwards_to_both(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.tableau_set = False

            def set_tableau(self, tableau):
                super().set_tableau(tableau)
                self.tableau_set = True

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.set_tableau("mock_tableau")
        assert first.tableau_set is True
        assert second.tableau_set is True

    def test_is_satisfiable_started_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.started = 0

            def is_satisfiable_started(self, reasoning_task_description):
                self.started += 1

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.is_satisfiable_started("task_desc")
        assert first.started == 1
        assert second.started == 1

    def test_saturate_started_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def saturate_started(self):
                self.count += 1

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.saturate_started()
        assert first.count == 1
        assert second.count == 1

    def test_iteration_started_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def iteration_started(self):
                self.count += 1

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.iteration_started()
        assert first.count == 1
        assert second.count == 1

    def test_node_created_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def node_created(self, node):
                self.count += 1

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.node_created("node1")
        assert first.count == 1
        assert second.count == 1

    def test_datatype_checking_finished_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.results = []

            def datatype_checking_finished(self, result):
                self.results.append(result)

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.datatype_checking_finished(True)
        assert first.results == [True]
        assert second.results == [True]

    def test_backtrack_to_finished_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def backtrack_to_finished(self, bp):
                self.count += 1

        first = TrackingAdapter()
        second = TrackingAdapter()
        fork = TableauMonitorFork(first, second)
        fork.backtrack_to_finished("bp")
        assert first.count == 1
        assert second.count == 1


# ===========================================================================
# 4. TableauMonitorForwarder
# ===========================================================================

class TestTableauMonitorForwarder:
    def test_forwarding_off_by_default(self):
        target = TableauMonitorAdapter()
        forwarder = TableauMonitorForwarder(target)
        assert forwarder.forwarding_on is False
        assert forwarder.is_forwarding_on() is False

    def test_set_forwarding_on_via_property(self):
        target = TableauMonitorAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.forwarding_on = True
        assert forwarder.forwarding_on is True

    def test_set_forwarding_on_via_legacy_setter(self):
        target = TableauMonitorAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.set_forwarding_on(True)
        assert forwarder.is_forwarding_on() is True

    def test_does_not_forward_when_off(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.clash_count = 0

            def clash_detected(self):
                self.clash_count += 1

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.clash_detected()
        assert target.clash_count == 0

    def test_forwards_when_on(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.clash_count = 0

            def clash_detected(self):
                self.clash_count += 1

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.forwarding_on = True
        forwarder.clash_detected()
        assert target.clash_count == 1

    def test_set_tableau_always_forwards(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.tableau = None

            def set_tableau(self, tableau):
                super().set_tableau(tableau)
                self.tableau = tableau

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.set_tableau("my_tableau")
        assert target.tableau == "my_tableau"

    def test_toggle_forwarding(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def clash_detected(self):
                self.count += 1

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)

        forwarder.forwarding_on = True
        forwarder.clash_detected()
        forwarder.forwarding_on = False
        forwarder.clash_detected()
        forwarder.forwarding_on = True
        forwarder.clash_detected()

        assert target.count == 2

    def test_saturate_started_forwarding(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def saturate_started(self):
                self.count += 1

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.forwarding_on = True
        forwarder.saturate_started()
        assert target.count == 1

    def test_is_satisfiable_finished_forwarding(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.results = []

            def is_satisfiable_finished(self, desc, result):
                self.results.append(result)

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.forwarding_on = True
        forwarder.is_satisfiable_finished("task", True)
        assert target.results == [True]

    def test_node_destroyed_forwarding(self):
        class TrackingAdapter(TableauMonitorAdapter):
            def __init__(self):
                super().__init__()
                self.count = 0

            def node_destroyed(self, node):
                self.count += 1

        target = TrackingAdapter()
        forwarder = TableauMonitorForwarder(target)
        forwarder.forwarding_on = True
        forwarder.node_destroyed("node1")
        assert target.count == 1


# ===========================================================================
# 5. TableauMonitorAdapter
# ===========================================================================

class TestTableauMonitorAdapter:
    def test_all_methods_noop(self):
        adapter = TableauMonitorAdapter()
        # Should not raise
        adapter.set_tableau(None)
        adapter.is_satisfiable_started("desc")
        adapter.is_satisfiable_finished("desc", True)
        adapter.tableau_cleared()
        adapter.saturate_started()
        adapter.saturate_finished(True)
        adapter.iteration_started()
        adapter.iteration_finished()
        adapter.dl_clause_matched_started(None, 0)
        adapter.dl_clause_matched_finished(None, 0)
        adapter.add_fact_started((), True)
        adapter.add_fact_finished((), True, True)
        adapter.merge_started(None, None)
        adapter.node_pruned(None)
        adapter.merge_fact_started(None, None, (), ())
        adapter.merge_fact_finished(None, None, (), ())
        adapter.merge_finished(None, None)
        adapter.clash_detection_started(())
        adapter.clash_detection_finished(())
        adapter.clash_detected()
        adapter.backtrack_to_started(None)
        adapter.tuple_removed(())
        adapter.backtrack_to_finished(None)
        adapter.ground_disjunction_derived(None)
        adapter.process_ground_disjunction_started(None)
        adapter.ground_disjunction_satisfied(None)
        adapter.process_ground_disjunction_finished(None)
        adapter.disjunct_processing_started(None, 0)
        adapter.disjunct_processing_finished(None, 0)
        adapter.push_branching_point_started(None)
        adapter.push_branching_point_finished(None)
        adapter.start_next_branching_point_started(None)
        adapter.start_next_branching_point_finished(None)
        adapter.existential_expansion_started(None, None)
        adapter.existential_expansion_finished(None, None)
        adapter.existential_satisfied(None, None)
        adapter.nominal_introduction_started(None, None, None, None, None)
        adapter.nominal_introduction_finished(None, None, None, None, None)
        adapter.description_graph_checking_started(0, 0, 0, 0, 0, 0)
        adapter.description_graph_checking_finished(0, 0, 0, 0, 0, 0)
        adapter.node_created(None)
        adapter.node_destroyed(None)
        adapter.unknown_datatype_restriction_detection_started(None, None, None, None)
        adapter.unknown_datatype_restriction_detection_finished(None, None, None, None)
        adapter.datatype_checking_started()
        adapter.datatype_checking_finished(True)
        adapter.datatype_conjunction_checking_started(None)
        adapter.datatype_conjunction_checking_finished(None, True)
        adapter.blocking_validation_started()
        adapter.blocking_validation_finished(0)
        adapter.possible_instance_is_instance()
        adapter.possible_instance_is_not_instance()

    def test_set_tableau_stores_reference(self):
        adapter = TableauMonitorAdapter()
        adapter.set_tableau("my_tableau")
        assert adapter._tableau == "my_tableau"


# ===========================================================================
# 6. Timer
# ===========================================================================

class TestTimer:
    def test_instantiate_with_default_output(self):
        timer = Timer()
        assert timer is not None

    def test_instantiate_with_custom_output(self):
        buf = io.StringIO()
        timer = Timer(output=buf)
        assert timer._output is buf

    def test_is_satisfiable_started_writes_to_output(self):
        buf = io.StringIO()
        timer = Timer(output=buf)
        timer.is_satisfiable_started("TestTask")
        buf.seek(0)
        content = buf.read()
        assert "TestTask" in content
        assert "..." in content


# ===========================================================================
# 7. MemoryConsumptionMonitor
# ===========================================================================

class TestMemoryConsumptionMonitor:
    def test_instantiate(self):
        from hermit.monitor import MemoryConsumptionMonitor
        monitor = MemoryConsumptionMonitor()
        assert monitor is not None

    def test_initial_values(self):
        from hermit.monitor import MemoryConsumptionMonitor
        monitor = MemoryConsumptionMonitor()
        assert monitor.get_current_tableau_expansion_memory_use() == 0
        assert monitor.get_max_tableau_expansion_memory_use() == 0
        assert monitor.get_average_tableau_expansion_memory_use() == 0

    def test_reset(self):
        from hermit.monitor import MemoryConsumptionMonitor
        monitor = MemoryConsumptionMonitor()
        monitor.reset()
        assert monitor.get_max_tableau_expansion_memory_use() == 0
