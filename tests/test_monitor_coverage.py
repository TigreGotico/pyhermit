"""Comprehensive tests for hermit.monitor to reach 95%+ coverage."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

from hermit.monitor import (
    CountingMonitor,
    MemoryConsumptionMonitor,
    TableauMonitorAdapter,
    TableauMonitorFork,
    TableauMonitorForwarder,
    TestRecord,
    Timer,
    TimerWithPause,
)

# Sentinel values for callback arguments
_SENTINEL = object()
_TUPLE = ("a", "b")
_TUPLES = (("a",), ("b",))
_NODE_A = MagicMock(name="nodeA")
_NODE_B = MagicMock(name="nodeB")


# ---- TableauMonitorAdapter ---------------------------------------------------

class TestTableauMonitorAdapter:
    def test_set_tableau(self):
        m = TableauMonitorAdapter()
        assert m._tableau is None
        m.set_tableau("tab")
        assert m._tableau == "tab"

    def test_all_callbacks_are_noop(self):
        m = TableauMonitorAdapter()
        # Just call every method; they should not raise
        m.is_satisfiable_started("desc")
        m.is_satisfiable_finished("desc", True)
        m.tableau_cleared()
        m.saturate_started()
        m.saturate_finished(True)
        m.iteration_started()
        m.iteration_finished()
        m.dl_clause_matched_started("ev", 0)
        m.dl_clause_matched_finished("ev", 0)
        m.add_fact_started(_TUPLE, True)
        m.add_fact_finished(_TUPLE, True, False)
        m.merge_started(_NODE_A, _NODE_B)
        m.node_pruned(_NODE_A)
        m.merge_fact_started(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
        m.merge_fact_finished(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
        m.merge_finished(_NODE_A, _NODE_B)
        m.clash_detection_started(_TUPLES)
        m.clash_detection_finished(_TUPLES)
        m.clash_detected()
        m.backtrack_to_started("bp")
        m.tuple_removed(_TUPLE)
        m.backtrack_to_finished("bp")
        m.ground_disjunction_derived("gd")
        m.process_ground_disjunction_started("gd")
        m.ground_disjunction_satisfied("gd")
        m.process_ground_disjunction_finished("gd")
        m.disjunct_processing_started("gd", 0)
        m.disjunct_processing_finished("gd", 0)
        m.push_branching_point_started("bp")
        m.push_branching_point_finished("bp")
        m.start_next_branching_point_started("bp")
        m.start_next_branching_point_finished("bp")
        m.existential_expansion_started("ec", _NODE_A)
        m.existential_expansion_finished("ec", _NODE_A)
        m.existential_satisfied("ec", _NODE_A)
        m.nominal_introduction_started(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
        m.nominal_introduction_finished(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
        m.description_graph_checking_started(1, 2, 3, 4, 5, 6)
        m.description_graph_checking_finished(1, 2, 3, 4, 5, 6)
        m.node_created(_NODE_A)
        m.node_destroyed(_NODE_A)
        m.unknown_datatype_restriction_detection_started("dr1", _NODE_A, "dr2", _NODE_B)
        m.unknown_datatype_restriction_detection_finished("dr1", _NODE_A, "dr2", _NODE_B)
        m.datatype_checking_started()
        m.datatype_checking_finished(True)
        m.datatype_conjunction_checking_started("conj")
        m.datatype_conjunction_checking_finished("conj", True)
        m.blocking_validation_started()
        m.blocking_validation_finished(5)
        m.possible_instance_is_instance()
        m.possible_instance_is_not_instance()


# ---- TableauMonitorFork ------------------------------------------------------

def _call_all_fork_methods(fork):
    """Call every method on a fork to exercise delegation."""
    fork.set_tableau("tab")
    fork.is_satisfiable_started("desc")
    fork.is_satisfiable_finished("desc", True)
    fork.tableau_cleared()
    fork.saturate_started()
    fork.saturate_finished(True)
    fork.iteration_started()
    fork.iteration_finished()
    fork.dl_clause_matched_started("ev", 0)
    fork.dl_clause_matched_finished("ev", 0)
    fork.add_fact_started(_TUPLE, True)
    fork.add_fact_finished(_TUPLE, True, False)
    fork.merge_started(_NODE_A, _NODE_B)
    fork.node_pruned(_NODE_A)
    fork.merge_fact_started(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
    fork.merge_fact_finished(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
    fork.merge_finished(_NODE_A, _NODE_B)
    fork.clash_detection_started(_TUPLES)
    fork.clash_detection_finished(_TUPLES)
    fork.clash_detected()
    fork.backtrack_to_started("bp")
    fork.tuple_removed(_TUPLE)
    fork.backtrack_to_finished("bp")
    fork.ground_disjunction_derived("gd")
    fork.process_ground_disjunction_started("gd")
    fork.ground_disjunction_satisfied("gd")
    fork.process_ground_disjunction_finished("gd")
    fork.disjunct_processing_started("gd", 0)
    fork.disjunct_processing_finished("gd", 0)
    fork.push_branching_point_started("bp")
    fork.push_branching_point_finished("bp")
    fork.start_next_branching_point_started("bp")
    fork.start_next_branching_point_finished("bp")
    fork.existential_expansion_started("ec", _NODE_A)
    fork.existential_expansion_finished("ec", _NODE_A)
    fork.existential_satisfied("ec", _NODE_A)
    fork.nominal_introduction_started(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
    fork.nominal_introduction_finished(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
    fork.description_graph_checking_started(1, 2, 3, 4, 5, 6)
    fork.description_graph_checking_finished(1, 2, 3, 4, 5, 6)
    fork.node_created(_NODE_A)
    fork.node_destroyed(_NODE_A)
    fork.unknown_datatype_restriction_detection_started("dr1", _NODE_A, "dr2", _NODE_B)
    fork.unknown_datatype_restriction_detection_finished("dr1", _NODE_A, "dr2", _NODE_B)
    fork.datatype_checking_started()
    fork.datatype_checking_finished(True)
    fork.datatype_conjunction_checking_started("conj")
    fork.datatype_conjunction_checking_finished("conj", True)
    fork.blocking_validation_started()
    fork.blocking_validation_finished(5)
    fork.possible_instance_is_instance()
    fork.possible_instance_is_not_instance()


class TestTableauMonitorFork:
    def test_delegates_to_both(self):
        a = TableauMonitorAdapter()
        b = TableauMonitorAdapter()
        fork = TableauMonitorFork(a, b)
        _call_all_fork_methods(fork)
        assert a._tableau == "tab"
        assert b._tableau == "tab"


# ---- TableauMonitorForwarder -------------------------------------------------

class TestTableauMonitorForwarder:
    def test_forwarding_off_by_default(self):
        target = TableauMonitorAdapter()
        fwd = TableauMonitorForwarder(target)
        assert not fwd.forwarding_on
        assert not fwd.is_forwarding_on()

    def test_set_tableau_always_forwarded(self):
        target = TableauMonitorAdapter()
        fwd = TableauMonitorForwarder(target)
        fwd.set_tableau("tab")
        assert target._tableau == "tab"

    def test_callbacks_blocked_when_off(self):
        target = MagicMock()
        fwd = TableauMonitorForwarder(target)
        # With forwarding off, only set_tableau should forward
        fwd.is_satisfiable_started("desc")
        target.is_satisfiable_started.assert_not_called()

    def test_callbacks_forwarded_when_on(self):
        target = TableauMonitorAdapter()
        fwd = TableauMonitorForwarder(target)
        fwd.forwarding_on = True
        assert fwd.is_forwarding_on()
        # Call all methods
        _call_all_forwarder_methods(fwd)

    def test_set_forwarding_on_legacy(self):
        target = TableauMonitorAdapter()
        fwd = TableauMonitorForwarder(target)
        fwd.set_forwarding_on(True)
        assert fwd.forwarding_on is True
        fwd.set_forwarding_on(False)
        assert fwd.forwarding_on is False


def _call_all_forwarder_methods(fwd):
    """Call every forwarded method."""
    fwd.set_tableau("tab")
    fwd.is_satisfiable_started("desc")
    fwd.is_satisfiable_finished("desc", True)
    fwd.tableau_cleared()
    fwd.saturate_started()
    fwd.saturate_finished(True)
    fwd.iteration_started()
    fwd.iteration_finished()
    fwd.dl_clause_matched_started("ev", 0)
    fwd.dl_clause_matched_finished("ev", 0)
    fwd.add_fact_started(_TUPLE, True)
    fwd.add_fact_finished(_TUPLE, True, False)
    fwd.merge_started(_NODE_A, _NODE_B)
    fwd.node_pruned(_NODE_A)
    fwd.merge_fact_started(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
    fwd.merge_fact_finished(_NODE_A, _NODE_B, _TUPLE, _TUPLE)
    fwd.merge_finished(_NODE_A, _NODE_B)
    fwd.clash_detection_started(_TUPLES)
    fwd.clash_detection_finished(_TUPLES)
    fwd.clash_detected()
    fwd.backtrack_to_started("bp")
    fwd.tuple_removed(_TUPLE)
    fwd.backtrack_to_finished("bp")
    fwd.ground_disjunction_derived("gd")
    fwd.process_ground_disjunction_started("gd")
    fwd.ground_disjunction_satisfied("gd")
    fwd.process_ground_disjunction_finished("gd")
    fwd.disjunct_processing_started("gd", 0)
    fwd.disjunct_processing_finished("gd", 0)
    fwd.push_branching_point_started("bp")
    fwd.push_branching_point_finished("bp")
    fwd.start_next_branching_point_started("bp")
    fwd.start_next_branching_point_finished("bp")
    fwd.existential_expansion_started("ec", _NODE_A)
    fwd.existential_expansion_finished("ec", _NODE_A)
    fwd.existential_satisfied("ec", _NODE_A)
    fwd.nominal_introduction_started(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
    fwd.nominal_introduction_finished(_NODE_A, _NODE_B, "eq", _NODE_A, _NODE_B)
    fwd.description_graph_checking_started(1, 2, 3, 4, 5, 6)
    fwd.description_graph_checking_finished(1, 2, 3, 4, 5, 6)
    fwd.node_created(_NODE_A)
    fwd.node_destroyed(_NODE_A)
    fwd.unknown_datatype_restriction_detection_started("dr1", _NODE_A, "dr2", _NODE_B)
    fwd.unknown_datatype_restriction_detection_finished("dr1", _NODE_A, "dr2", _NODE_B)
    fwd.datatype_checking_started()
    fwd.datatype_checking_finished(True)
    fwd.datatype_conjunction_checking_started("conj")
    fwd.datatype_conjunction_checking_finished("conj", True)
    fwd.blocking_validation_started()
    fwd.blocking_validation_finished(5)
    fwd.possible_instance_is_instance()
    fwd.possible_instance_is_not_instance()


# ---- TestRecord --------------------------------------------------------------

class TestTestRecord:
    def test_properties(self):
        r = TestRecord(100, "test A", True)
        assert r.test_time == 100
        assert r.test_description == "test A"
        assert r.test_result is True

    def test_lt_by_time_descending(self):
        a = TestRecord(200, "a", True)
        b = TestRecord(100, "b", True)
        assert a < b  # 200 > 100 => a < b in sort order

    def test_lt_by_name_when_time_equal(self):
        a = TestRecord(100, "alpha", True)
        b = TestRecord(100, "beta", True)
        assert a < b  # alpha < beta

    def test_le_eq_gt_ge(self):
        a = TestRecord(100, "a", True)
        b = TestRecord(100, "a", True)
        assert a == b
        assert a <= b
        assert a >= b
        assert not (a < b)
        assert not (a > b)
        assert not (a != b)

    def test_ne(self):
        a = TestRecord(100, "a", True)
        b = TestRecord(200, "b", False)
        assert a != b

    def test_eq_not_implemented(self):
        r = TestRecord(100, "a", True)
        assert r.__eq__("not a record") is NotImplemented

    def test_lt_not_implemented(self):
        r = TestRecord(100, "a", True)
        assert r.__lt__("not a record") is NotImplemented

    def test_repr_short(self):
        r = TestRecord(500, "desc", True)
        s = repr(r)
        assert "500 ms" in s
        assert "desc" in s

    def test_repr_long(self):
        r = TestRecord(5000, "desc", False)
        s = repr(r)
        assert "5000 ms" in s
        assert "desc" in s
        # Should have the parenthesized time string
        assert "(" in s


# ---- CountingMonitor ---------------------------------------------------------

class TestCountingMonitor:
    def test_initial_state(self):
        m = CountingMonitor()
        assert m.time == 0
        assert m.get_time() == 0
        assert m.number_of_backtrackings == 0
        assert m.get_number_of_backtrackings() == 0
        assert m.number_of_nodes == 0
        assert m.get_number_of_nodes() == 0
        assert m.number_of_blocked_nodes == 0
        assert m.get_number_of_blocked_nodes() == 0
        assert m.get_test_description() == ""
        assert m.get_test_result() is False

    def test_satisfiable_lifecycle(self):
        m = CountingMonitor()
        m.is_satisfiable_started("task1")
        m.backtrack_to_finished("bp")
        m.backtrack_to_finished("bp")
        m.clash_detected()
        m.clash_detected()
        m.possible_instance_is_instance()
        m.possible_instance_is_not_instance()
        m.is_satisfiable_finished("task1", True)

        assert m.get_overall_number_of_tests() == 1
        assert m.get_overall_number_of_backtrackings() == 2
        assert m.get_overall_number_of_clashes() == 2
        assert m.get_number_of_possible_instances_tested() == 2
        assert m.get_number_of_possible_instances_instances() == 1
        assert m.get_test_result() is True
        assert m.time >= 0
        assert m.get_overall_time() >= 0

    def test_reset(self):
        m = CountingMonitor()
        m.is_satisfiable_started("t")
        m.clash_detected()
        m.is_satisfiable_finished("t", True)
        m.reset()
        assert m.get_overall_number_of_tests() == 0
        assert m.get_overall_number_of_clashes() == 0
        assert m.get_overall_time() == 0

    def test_averages_zero_tests(self):
        m = CountingMonitor()
        assert m.get_average_time() == 0
        assert m.get_average_number_of_backtrackings() == 0
        assert m.get_average_number_of_nodes() == 0
        assert m.get_average_number_of_blocked_nodes() == 0
        assert m.get_average_number_of_clashes() == 0
        assert m.get_possibles_to_instances() == 0.0
        assert m.get_average_initial_model_size() == 0
        assert m.get_average_initially_blocked() == 0
        assert m.get_average_initially_invalid() == 0
        assert m.get_average_no_validations() == 0
        assert m.get_average_validation_time() == 0

    def test_averages_with_tests(self):
        m = CountingMonitor()
        m.is_satisfiable_started("t1")
        m.backtrack_to_finished("bp")
        m.clash_detected()
        m.is_satisfiable_finished("t1", True)
        m.is_satisfiable_started("t2")
        m.is_satisfiable_finished("t2", False)
        # Now we have 2 tests
        assert m.get_average_time() >= 0
        assert isinstance(m.get_average_number_of_backtrackings(), float)
        assert isinstance(m.get_average_number_of_nodes(), float)
        assert isinstance(m.get_average_number_of_blocked_nodes(), float)
        assert isinstance(m.get_average_number_of_clashes(), float)

    def test_blocking_validation(self):
        m = CountingMonitor()
        m.is_satisfiable_started("t")
        m.blocking_validation_started()
        m.blocking_validation_finished(3)
        m.blocking_validation_started()
        m.blocking_validation_finished(1)
        m.is_satisfiable_finished("t", True)
        assert m.get_no_validations() == 2
        assert m.get_initially_invalid() == 3
        assert m.get_validation_time() >= 0
        assert m.get_overall_no_validations() == 2
        assert m.get_overall_initially_invalid() == 3

    def test_blocking_validation_with_tableau(self):
        """Test blocking_validation_started with a mock tableau."""
        m = CountingMonitor()
        node1 = MagicMock()
        node1.is_active.return_value = True
        node1.is_blocked.return_value = True
        node1.has_unprocessed_existentials.return_value = True
        node1.get_next_tableau_node.return_value = None

        tableau = MagicMock()
        tableau.get_first_tableau_node.return_value = node1
        m.set_tableau(tableau)
        m.is_satisfiable_started("t")
        m.blocking_validation_started()
        assert m.get_initial_model_size() == 1
        assert m.get_initially_blocked() == 1

    def test_test_records(self):
        m = CountingMonitor()
        m.is_satisfiable_started("t1")
        m.is_satisfiable_finished("t1", True)
        m.is_satisfiable_started("t2")
        m.is_satisfiable_finished("t2", False)
        patterns = m.get_used_message_patterns()
        assert len(patterns) >= 1
        records = m.get_time_sorted_test_records(10)
        assert len(records) == 2
        # With specific pattern
        for p in patterns:
            recs = m.get_time_sorted_test_records(10, p)
            assert len(recs) >= 1

    def test_test_records_limit(self):
        m = CountingMonitor()
        for i in range(5):
            m.is_satisfiable_started(f"t{i}")
            m.is_satisfiable_finished(f"t{i}", True)
        records = m.get_time_sorted_test_records(2)
        assert len(records) == 2

    def test_millis_to_hours_minutes_seconds(self):
        assert "ms" in CountingMonitor.millis_to_hours_minutes_seconds_string(500)
        s = CountingMonitor.millis_to_hours_minutes_seconds_string(65000)
        assert "m" in s
        s = CountingMonitor.millis_to_hours_minutes_seconds_string(3661000)
        assert "h" in s

    def test_maybe_flip_result(self):
        # No flip attr
        assert CountingMonitor._maybe_flip_result("desc", True) is True
        # With flip returning True
        desc = MagicMock()
        desc.flip_satisfiability_result.return_value = True
        assert CountingMonitor._maybe_flip_result(desc, True) is False
        # With flip returning False
        desc.flip_satisfiability_result.return_value = False
        assert CountingMonitor._maybe_flip_result(desc, True) is True
        # With flip raising
        desc.flip_satisfiability_result.side_effect = RuntimeError
        assert CountingMonitor._maybe_flip_result(desc, True) is True

    def test_get_message_pattern(self):
        desc = MagicMock()
        desc.message_pattern = "pattern1"
        assert CountingMonitor._get_message_pattern(desc) == "pattern1"
        # Without attribute
        assert CountingMonitor._get_message_pattern("fallback") == "fallback"

    def test_get_task_description_fallback(self):
        assert CountingMonitor._get_task_description("desc") == "desc"

    def test_get_rounded(self):
        assert CountingMonitor._get_rounded(1, 3) == 0.33
        assert CountingMonitor._get_rounded(2, 3) == 0.66

    def test_number_of_nodes_no_tableau(self):
        m = CountingMonitor()
        assert m._get_number_of_nodes_in_tableau() == 0

    def test_number_of_nodes_with_tableau(self):
        m = CountingMonitor()
        tab = MagicMock()
        tab.get_number_of_nodes_in_tableau.return_value = 10
        tab.get_number_of_merged_or_pruned_nodes.return_value = 3
        m.set_tableau(tab)
        assert m._get_number_of_nodes_in_tableau() == 7

    def test_count_blocked_nodes_no_tableau(self):
        m = CountingMonitor()
        assert m._count_blocked_nodes() == 0

    def test_count_blocked_nodes_with_tableau(self):
        m = CountingMonitor()
        node = MagicMock()
        node.is_active.return_value = True
        node.is_blocked.return_value = True
        node.has_unprocessed_existentials.return_value = True
        node.get_next_tableau_node.return_value = None
        tab = MagicMock()
        tab.get_first_tableau_node.return_value = node
        m.set_tableau(tab)
        assert m._count_blocked_nodes() == 1

    def test_overall_blocking_getters(self):
        m = CountingMonitor()
        assert m.get_overall_initial_model_size() == 0
        assert m.get_overall_initially_blocked() == 0
        assert m.get_overall_initially_invalid() == 0
        assert m.get_overall_validation_time() == 0

    def test_average_blocking_with_tests(self):
        m = CountingMonitor()
        m.is_satisfiable_started("t")
        m.blocking_validation_started()
        m.blocking_validation_finished(2)
        m.is_satisfiable_finished("t", True)
        assert isinstance(m.get_average_initial_model_size(), float)
        assert isinstance(m.get_average_initially_blocked(), float)
        assert isinstance(m.get_average_initially_invalid(), float)
        assert isinstance(m.get_average_no_validations(), float)
        assert m.get_average_validation_time() >= 0

    def test_possibles_to_instances(self):
        m = CountingMonitor()
        m.possible_instance_is_instance()
        m.possible_instance_is_instance()
        m.possible_instance_is_not_instance()
        assert m.get_possibles_to_instances() == 0.66


# ---- Timer -------------------------------------------------------------------

class TestTimer:
    def test_basic_lifecycle(self):
        buf = io.StringIO()
        t = Timer(buf)
        t.is_satisfiable_started("test task")
        t.saturate_started()
        t.backtrack_to_finished("bp")
        t.is_satisfiable_finished("test task", True)
        output = buf.getvalue()
        assert "test task" in output
        assert "YES" in output

    def test_result_no(self):
        buf = io.StringIO()
        t = Timer(buf)
        t.is_satisfiable_started("task")
        t.is_satisfiable_finished("task", False)
        assert "NO" in buf.getvalue()

    def test_iteration_started_no_status(self):
        """iteration_started should not print if < 30s elapsed."""
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        t.iteration_started()
        # Should not have printed stats (< 30s)

    def test_iteration_started_with_status(self):
        """Force status print by faking old last_status_time."""
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        t._last_status_time = t._problem_start_time - 31000
        t.iteration_started()
        assert "Test:" in buf.getvalue()

    def test_iteration_started_first_status(self):
        """First status should print newline."""
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        # Make last_status_time == problem_start_time (default) and old enough
        t._problem_start_time -= 31000
        t._last_status_time = t._problem_start_time
        t.iteration_started()
        output = buf.getvalue()
        assert output.startswith("\n")

    def test_do_statistics_no_tableau(self):
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        t._number_of_backtrackings = 5
        t._do_statistics()
        output = buf.getvalue()
        assert "Test:" in output
        assert "Duration:" in output
        assert "Backtrackings: 5" in output
        assert "allocated:" in output

    def test_do_statistics_with_tableau(self):
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        tab = MagicMock()
        tab.get_current_branching_point_level.return_value = 42
        tab.get_number_of_allocated_nodes.return_value = 100
        tab.get_number_of_node_creations.return_value = 80
        tab.get_number_of_nodes_in_tableau.return_value = 60
        tab.get_number_of_merged_or_pruned_nodes.return_value = 5
        ext_mgr = MagicMock()
        ext_mgr.get_binary_extension_table.return_value.size_in_memory.return_value = 5000
        ext_mgr.get_ternary_extension_table.return_value.size_in_memory.return_value = 3000
        tab.get_extension_manager.return_value = ext_mgr
        dsf = MagicMock()
        dsf.size_in_memory.return_value = 2000
        tab.get_dependency_set_factory.return_value = dsf
        t.set_tableau(tab)
        t._do_statistics()
        output = buf.getvalue()
        assert "merged/pruned: 5" in output

    def test_do_statistics_tableau_attribute_errors(self):
        """Tableau with missing attributes should fall back gracefully."""
        buf = io.StringIO()
        t = Timer(buf)
        t._start()
        tab = MagicMock()
        tab.get_current_branching_point_level.side_effect = AttributeError
        tab.get_number_of_allocated_nodes.side_effect = AttributeError
        tab.get_number_of_node_creations.side_effect = AttributeError
        tab.get_number_of_nodes_in_tableau.side_effect = AttributeError
        tab.get_number_of_merged_or_pruned_nodes.side_effect = AttributeError
        tab.get_extension_manager.side_effect = AttributeError
        tab.get_dependency_set_factory.side_effect = AttributeError
        t.set_tableau(tab)
        t._do_statistics()
        # Should not raise

    def test_default_output_is_stdout(self):
        t = Timer()
        import sys
        assert t._output is sys.stdout

    def test_print_padded_methods(self):
        buf = io.StringIO()
        t = Timer(buf)
        t._print_padded_int(42, 10)
        t._print_padded_ms(100, 15)
        t._print_padded_kb(50, 10)
        output = buf.getvalue()
        assert "42" in output
        assert "100 ms" in output
        assert "50 kb" in output

    def test_get_task_description_fallback(self):
        assert Timer._get_task_description("hello") == "hello"


# ---- TimerWithPause ----------------------------------------------------------

class TestTimerWithPause:
    def test_do_statistics_pauses(self, monkeypatch):
        buf = io.StringIO()
        t = TimerWithPause(buf)
        t._start()
        monkeypatch.setattr("builtins.print", lambda *a, **kw: None)
        monkeypatch.setattr("sys.stdin", io.StringIO("x\n"))
        t._do_statistics()


# ---- MemoryConsumptionMonitor ------------------------------------------------

class TestMemoryConsumptionMonitor:
    def test_initial_state(self):
        m = MemoryConsumptionMonitor()
        assert m.get_current_tableau_expansion_memory_use() == 0
        assert m.get_current_tableau_expansion_binary_table_size() == 0
        assert m.get_current_tableau_expansion_ternary_table_size() == 0
        assert m.get_current_tableau_expansion_dependency_sets_size() == 0
        assert m.get_average_tableau_expansion_memory_use() == 0
        assert m.get_average_tableau_expansion_binary_table_size() == 0
        assert m.get_average_tableau_expansion_ternary_table_size() == 0
        assert m.get_average_tableau_expansion_dependency_sets_size() == 0
        assert m.get_max_tableau_expansion_memory_use() == 0

    def test_lifecycle_no_tableau(self):
        m = MemoryConsumptionMonitor()
        m.is_satisfiable_started("t")
        m.is_satisfiable_finished("t", True)
        assert m.get_current_tableau_expansion_memory_use() == 0

    def test_lifecycle_with_tableau(self):
        m = MemoryConsumptionMonitor()
        ext_mgr = MagicMock()
        ext_mgr.get_binary_extension_table.return_value.size_in_memory.return_value = 2048
        ext_mgr.get_ternary_extension_table.return_value.size_in_memory.return_value = 1024
        dsf = MagicMock()
        dsf.size_in_memory.return_value = 4096
        tab = MagicMock()
        tab.get_extension_manager.return_value = ext_mgr
        tab.get_dependency_set_factory.return_value = dsf
        tab.get_number_of_nodes_in_tableau.return_value = 10
        tab.get_number_of_merged_or_pruned_nodes.return_value = 0
        tab.get_first_tableau_node.return_value = None
        m.set_tableau(tab)
        m.is_satisfiable_started("t")
        m.is_satisfiable_finished("t", True)
        assert m.get_current_tableau_expansion_binary_table_size() == 2
        assert m.get_current_tableau_expansion_ternary_table_size() == 1
        assert m.get_current_tableau_expansion_dependency_sets_size() == 4
        assert m.get_current_tableau_expansion_memory_use() == 7
        assert m.get_max_tableau_expansion_memory_use() == 7

    def test_lifecycle_tableau_attribute_errors(self):
        m = MemoryConsumptionMonitor()
        tab = MagicMock()
        tab.get_extension_manager.side_effect = AttributeError
        tab.get_dependency_set_factory.side_effect = AttributeError
        tab.get_number_of_nodes_in_tableau.side_effect = AttributeError
        tab.get_first_tableau_node.return_value = None
        m.set_tableau(tab)
        m.is_satisfiable_started("t")
        m.is_satisfiable_finished("t", True)
        assert m.get_current_tableau_expansion_memory_use() == 0

    def test_averages_with_tests(self):
        m = MemoryConsumptionMonitor()
        m.is_satisfiable_started("t1")
        m.is_satisfiable_finished("t1", True)
        m.is_satisfiable_started("t2")
        m.is_satisfiable_finished("t2", True)
        assert m.get_average_tableau_expansion_memory_use() == 0
        assert m.get_average_tableau_expansion_binary_table_size() == 0
        assert m.get_average_tableau_expansion_ternary_table_size() == 0
        assert m.get_average_tableau_expansion_dependency_sets_size() == 0

    def test_reset(self):
        m = MemoryConsumptionMonitor()
        m.is_satisfiable_started("t")
        m.is_satisfiable_finished("t", True)
        m.reset()
        assert m.get_max_tableau_expansion_memory_use() == 0
        assert m._test_number == 0

    def test_max_mem_updated(self):
        m = MemoryConsumptionMonitor()
        ext_mgr = MagicMock()
        ext_mgr.get_binary_extension_table.return_value.size_in_memory.return_value = 10240
        ext_mgr.get_ternary_extension_table.return_value.size_in_memory.return_value = 5120
        dsf = MagicMock()
        dsf.size_in_memory.return_value = 2048
        tab = MagicMock()
        tab.get_extension_manager.return_value = ext_mgr
        tab.get_dependency_set_factory.return_value = dsf
        tab.get_number_of_nodes_in_tableau.return_value = 5
        tab.get_number_of_merged_or_pruned_nodes.return_value = 0
        tab.get_first_tableau_node.return_value = None
        m.set_tableau(tab)
        m.is_satisfiable_started("t1")
        m.is_satisfiable_finished("t1", True)
        first_max = m.get_max_tableau_expansion_memory_use()
        # Second run with smaller values
        ext_mgr.get_binary_extension_table.return_value.size_in_memory.return_value = 1024
        ext_mgr.get_ternary_extension_table.return_value.size_in_memory.return_value = 1024
        dsf.size_in_memory.return_value = 1024
        m.is_satisfiable_started("t2")
        m.is_satisfiable_finished("t2", True)
        # Max should not decrease
        assert m.get_max_tableau_expansion_memory_use() == first_max
