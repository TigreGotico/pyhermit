"""Datatype manager.

Handles datatype reasoning, including D-conjunction management,
value-space subset enumeration, and datatype clash detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermit.tableau.union_dependency_set import UnionDependencySet

if TYPE_CHECKING:
    from hermit.model import (
        ConstantEnumeration,
        DataRange,
        DatatypeRestriction,
        DLOntology,
    )
    from hermit.model import Prefixes
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.extension_manager import Retrieval
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau
    from hermit.tableau.union_dependency_set import UnionDependencySet


class DatatypeManager:
    """Manages datatype constraint checking during tableau expansion."""

    @staticmethod
    def _get_index_for(hash_code: int, table_length: int) -> int:
        return hash_code % table_length if table_length > 0 else 0

    def __init__(self, tableau: Tableau) -> None:
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_tableau_monitor = tableau.m_tableau_monitor
        self.m_extension_manager = tableau.m_extension_manager
        self.m_assertions_delta_old_retrieval: Retrieval = (
            self.m_extension_manager.get_binary_extension_table().create_retrieval(
                [False, False], "DELTA_OLD"
            )
        )
        # Note: inequality retrieval iterates through entire extension for efficiency
        # and filters out inequalities manually (see Java source comment).
        self.m_inequality_delta_old_retrieval: Retrieval = (
            self.m_extension_manager.get_ternary_extension_table().create_retrieval(
                [False, False, False], "DELTA_OLD"
            )
        )
        self.m_inequality01_retrieval: Retrieval = (
            self.m_extension_manager.get_ternary_extension_table().create_retrieval(
                [True, True, False], "EXTENSION_THIS"
            )
        )
        self.m_inequality02_retrieval: Retrieval = (
            self.m_extension_manager.get_ternary_extension_table().create_retrieval(
                [True, False, True], "EXTENSION_THIS"
            )
        )
        self.m_assertions0_retrieval: Retrieval = (
            self.m_extension_manager.get_binary_extension_table().create_retrieval(
                [True, False], "EXTENSION_THIS"
            )
        )
        self.m_assertions1_retrieval: Retrieval = (
            self.m_extension_manager.get_binary_extension_table().create_retrieval(
                [False, True], "EXTENSION_THIS"
            )
        )
        self.m_conjunction = DConjunction()
        self.m_auxiliary_variable_list: list[DVariable] = []
        self.m_union_dependency_set = UnionDependencySet(16)
        self.m_new_variable_added: list[bool] = [False]
        self.m_unknown_datatype_restrictions_permanent: set[DatatypeRestriction] = (
            tableau.m_permanent_dl_ontology.get_all_unknown_datatype_restrictions()
        )
        self.m_unknown_datatype_restrictions_additional: set[DatatypeRestriction] | None = (
            tableau.m_additional_dl_ontology.get_all_unknown_datatype_restrictions()
            if tableau.m_additional_dl_ontology is not None
            else None
        )

    def additional_dl_ontology_set(self, additional_dl_ontology: DLOntology) -> None:
        self.m_unknown_datatype_restrictions_additional = (
            additional_dl_ontology.get_all_unknown_datatype_restrictions()
        )

    def additional_dl_ontology_cleared(self) -> None:
        self.m_unknown_datatype_restrictions_additional = None

    def clear(self) -> None:
        self.m_assertions_delta_old_retrieval.clear()
        self.m_inequality_delta_old_retrieval.clear()
        self.m_inequality01_retrieval.clear()
        self.m_inequality02_retrieval.clear()
        self.m_assertions0_retrieval.clear()
        self.m_assertions1_retrieval.clear()
        self.m_conjunction.clear()
        self.m_auxiliary_variable_list.clear()
        self.m_union_dependency_set.clear_constituents()

    def apply_unknown_datatype_restriction_semantics(self) -> None:
        """Generate inequalities for unknown datatype restrictions."""
        from hermit.model import AtomicNegationDataRange, DatatypeRestriction

        tuple_buffer = self.m_assertions_delta_old_retrieval.get_tuple_buffer()
        self.m_assertions_delta_old_retrieval.open()
        while not self.m_extension_manager.contains_clash() and not self.m_assertions_delta_old_retrieval.after_last():
            data_range_object = tuple_buffer[0]
            if isinstance(data_range_object, DatatypeRestriction):
                datatype_restriction: DatatypeRestriction = data_range_object
                if (
                    datatype_restriction in self.m_unknown_datatype_restrictions_permanent
                    or (
                        self.m_unknown_datatype_restrictions_additional is not None
                        and datatype_restriction in self.m_unknown_datatype_restrictions_additional
                    )
                ):
                    self._generate_inequalities_for(
                        datatype_restriction,
                        tuple_buffer[1],  # type: ignore[arg-type]
                        self.m_assertions_delta_old_retrieval.get_dependency_set(),
                        AtomicNegationDataRange.create(datatype_restriction),
                    )
            elif isinstance(data_range_object, AtomicNegationDataRange):
                negation_data_range: AtomicNegationDataRange = data_range_object
                negated_data_range = negation_data_range.negated
                if isinstance(negated_data_range, DatatypeRestriction):
                    datatype_restriction = negated_data_range
                    if (
                        datatype_restriction in self.m_unknown_datatype_restrictions_permanent
                        or (
                            self.m_unknown_datatype_restrictions_additional is not None
                            and datatype_restriction in self.m_unknown_datatype_restrictions_additional
                        )
                    ):
                        self._generate_inequalities_for(
                            negation_data_range,
                            tuple_buffer[1],  # type: ignore[arg-type]
                            self.m_assertions_delta_old_retrieval.get_dependency_set(),
                            datatype_restriction,
                        )
            self.m_assertions_delta_old_retrieval.next()

    def _generate_inequalities_for(
        self,
        data_range1: DataRange,
        node1: Node,
        dependency_set1: DependencySet,
        data_range2: DataRange,
    ) -> None:
        """Generate inequality assertions between nodes with conflicting data ranges."""
        from hermit.model import Inequality

        self.m_union_dependency_set.clear_constituents()
        self.m_union_dependency_set.add_constituent(dependency_set1)
        self.m_union_dependency_set.add_constituent(None)
        self.m_assertions0_retrieval.get_bindings_buffer()[0] = data_range2
        tuple_buffer = self.m_assertions0_retrieval.get_tuple_buffer()
        self.m_assertions0_retrieval.open()
        while not self.m_assertions0_retrieval.after_last():
            node2: Node = tuple_buffer[1]  # type: ignore[assignment]
            self.m_union_dependency_set.m_dependency_sets[1] = (
                self.m_assertions0_retrieval.get_dependency_set()
            )
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.unknown_datatype_restriction_detection_started(
                    data_range1, node1, data_range2, node2
                )
            self.m_extension_manager.add_assertion(
                Inequality.INSTANCE, node1, node2, self.m_union_dependency_set, False
            )
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.unknown_datatype_restriction_detection_finished(
                    data_range1, node1, data_range2, node2
                )
            self.m_assertions0_retrieval.next()

    def check_datatype_constraints(self) -> None:
        """Check all datatype constraints for consistency."""
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.datatype_checking_started()
        self.m_conjunction.clear()
        tuple_buffer = self.m_assertions_delta_old_retrieval.get_tuple_buffer()
        self.m_assertions_delta_old_retrieval.open()
        while not self.m_extension_manager.contains_clash() and not self.m_assertions_delta_old_retrieval.after_last():
            from hermit.model import DataRange

            if isinstance(tuple_buffer[0], DataRange):
                node: Node = tuple_buffer[1]  # type: ignore[assignment]
                variable = self._get_and_initialize_variable_for(node, self.m_new_variable_added)
                if self.m_new_variable_added[0]:
                    self.m_conjunction.clear_active_variables()
                    self._load_conjunction_from(variable)
                    self._check_conjunction_satisfiability()
            self.m_assertions_delta_old_retrieval.next()
        tuple_buffer = self.m_inequality_delta_old_retrieval.get_tuple_buffer()
        self.m_inequality_delta_old_retrieval.open()
        while not self.m_extension_manager.contains_clash() and not self.m_inequality_delta_old_retrieval.after_last():
            from hermit.model import Inequality

            if tuple_buffer[0] is Inequality.INSTANCE:
                node1: Node = tuple_buffer[1]  # type: ignore[assignment]
                node2: Node = tuple_buffer[2]  # type: ignore[assignment]
                if not node1.node_type.is_abstract and not node2.node_type.is_abstract:  # type: ignore[union-attr]
                    self.m_conjunction.clear_active_variables()
                    variable1 = self._get_and_initialize_variable_for(
                        node1, self.m_new_variable_added
                    )
                    if self.m_new_variable_added[0]:
                        self._load_conjunction_from(variable1)
                    variable2 = self._get_and_initialize_variable_for(
                        node2, self.m_new_variable_added
                    )
                    if self.m_new_variable_added[0]:
                        self._load_conjunction_from(variable2)
                    self.m_conjunction.add_inequality(variable1, variable2)
                    self._check_conjunction_satisfiability()
            self.m_inequality_delta_old_retrieval.next()
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.datatype_checking_finished(
                not self.m_extension_manager.contains_clash()
            )
        self.m_union_dependency_set.clear_constituents()
        self.m_conjunction.clear()
        self.m_auxiliary_variable_list.clear()

    def _load_conjunction_from(self, start_variable: DVariable) -> None:
        """Load the D-conjunction reachable from *start_variable*."""
        from hermit.model import Inequality

        self.m_auxiliary_variable_list.clear()
        self.m_auxiliary_variable_list.append(start_variable)
        while not self.m_extension_manager.contains_clash() and self.m_auxiliary_variable_list:
            reached_variable = self.m_auxiliary_variable_list.pop()
            if reached_variable not in self.m_conjunction.m_active_variables:
                self.m_conjunction.m_active_variables.add(reached_variable)
                # Concrete root nodes act as "breakers" in the conjunction.
                if reached_variable.m_node is not None and reached_variable.m_node.node_type != "ROOT_CONSTANT_NODE":  # type: ignore[union-attr]
                    # Look for inequalities where reached_node occurs in first position.
                    self.m_inequality01_retrieval.get_bindings_buffer()[0] = Inequality.INSTANCE
                    self.m_inequality01_retrieval.get_bindings_buffer()[1] = reached_variable.m_node
                    self.m_inequality01_retrieval.open()
                    tuple_buffer = self.m_inequality01_retrieval.get_tuple_buffer()
                    while (
                        not self.m_extension_manager.contains_clash()
                        and not self.m_inequality01_retrieval.after_last()
                    ):
                        new_node: Node = tuple_buffer[2]  # type: ignore[assignment]
                        new_variable = self._get_and_initialize_variable_for(
                            new_node, self.m_new_variable_added
                        )
                        self.m_auxiliary_variable_list.append(new_variable)
                        self.m_conjunction.add_inequality(reached_variable, new_variable)
                        self.m_inequality01_retrieval.next()
                        self.m_interrupt_flag.check_interrupt()
                    # Look for inequalities where reached_node occurs in second position.
                    self.m_inequality02_retrieval.get_bindings_buffer()[0] = Inequality.INSTANCE
                    self.m_inequality02_retrieval.get_bindings_buffer()[2] = reached_variable.m_node
                    self.m_inequality02_retrieval.open()
                    tuple_buffer = self.m_inequality02_retrieval.get_tuple_buffer()
                    while (
                        not self.m_extension_manager.contains_clash()
                        and not self.m_inequality02_retrieval.after_last()
                    ):
                        new_node = tuple_buffer[1]  # type: ignore[assignment]
                        new_variable = self._get_and_initialize_variable_for(
                            new_node, self.m_new_variable_added
                        )
                        self.m_auxiliary_variable_list.append(new_variable)
                        self.m_conjunction.add_inequality(new_variable, reached_variable)
                        self.m_inequality02_retrieval.next()
                        self.m_interrupt_flag.check_interrupt()

    def _get_and_initialize_variable_for(
        self, node: Node, new_variable_added: list[bool]
    ) -> DVariable:
        """Get or create a DVariable for the given node and initialize it."""
        variable = self.m_conjunction.get_variable_for_ex(node, new_variable_added)
        if new_variable_added[0]:
            self.m_assertions1_retrieval.get_bindings_buffer()[1] = variable.m_node
            self.m_assertions1_retrieval.open()
            tuple_buffer = self.m_assertions1_retrieval.get_tuple_buffer()
            while (
                not self.m_extension_manager.contains_clash()
                and not self.m_assertions1_retrieval.after_last()
            ):
                potential_data_range = tuple_buffer[0]
                from hermit.model import DataRange

                if isinstance(potential_data_range, DataRange):
                    self._add_data_range(variable, potential_data_range)
                self.m_assertions1_retrieval.next()
                self.m_interrupt_flag.check_interrupt()
            if not self.m_extension_manager.contains_clash():
                self._normalize(variable)
        return variable

    def _add_data_range(self, variable: DVariable, data_range: DataRange) -> None:
        """Add a data range assertion to a variable."""
        from hermit.datatypes.registry import DatatypeRegistry
        from hermit.model import (
            AtomicNegationDataRange,
            ConstantEnumeration,
            DatatypeRestriction,
            InternalDatatype,
        )

        if isinstance(data_range, InternalDatatype):
            # Internal datatypes are skipped (used for rdfs:Literal etc.).
            pass
        elif isinstance(data_range, DatatypeRestriction):
            if (
                data_range not in self.m_unknown_datatype_restrictions_permanent
                and (
                    self.m_unknown_datatype_restrictions_additional is None
                    or data_range not in self.m_unknown_datatype_restrictions_additional
                )
            ):
                variable.m_positive_datatype_restrictions.append(data_range)
                if variable.m_most_specific_restriction is None:
                    variable.m_most_specific_restriction = data_range
                elif DatatypeRegistry.is_disjoint_with(
                    variable.m_most_specific_restriction.datatype_iri,
                    data_range.datatype_iri,
                ):
                    self.m_union_dependency_set.clear_constituents()
                    self.m_union_dependency_set.add_constituent(
                        self.m_extension_manager.get_assertion_dependency_set_unary(
                            variable.m_most_specific_restriction, variable.m_node
                        )
                    )
                    self.m_union_dependency_set.add_constituent(
                        self.m_extension_manager.get_assertion_dependency_set_unary(
                            data_range, variable.m_node
                        )
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_started(
                            [variable.m_most_specific_restriction, variable.m_node],
                            [data_range, variable.m_node],
                        )
                    self.m_extension_manager.set_clash(self.m_union_dependency_set)
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_finished(
                            [variable.m_most_specific_restriction, variable.m_node],
                            [data_range, variable.m_node],
                        )
                elif DatatypeRegistry.is_subset_of(
                    data_range.datatype_iri,
                    variable.m_most_specific_restriction.datatype_iri,
                ):
                    variable.m_most_specific_restriction = data_range
        elif isinstance(data_range, ConstantEnumeration):
            variable.m_positive_constant_enumerations.append(data_range)
        elif isinstance(data_range, AtomicNegationDataRange):
            negated_data_range = data_range.negated
            if isinstance(negated_data_range, InternalDatatype):
                pass  # Skip for same reasons as above.
            elif isinstance(negated_data_range, DatatypeRestriction):
                if (
                    negated_data_range not in self.m_unknown_datatype_restrictions_permanent
                    and (
                        self.m_unknown_datatype_restrictions_additional is None
                        or negated_data_range not in self.m_unknown_datatype_restrictions_additional
                    )
                ):
                    variable.m_negative_datatype_restrictions.append(negated_data_range)
            elif isinstance(negated_data_range, ConstantEnumeration):
                variable.m_negative_constant_enumerations.append(negated_data_range)
                for i in range(negated_data_range.get_number_of_constants() - 1, -1, -1):
                    variable.add_forbidden_data_value(
                        negated_data_range.get_constant(i).data_value
                    )
            else:
                raise RuntimeError("Internal error: invalid data range.")
        else:
            raise RuntimeError("Internal error: invalid data range.")

    def _normalize(self, variable: DVariable) -> None:
        """Normalize a variable's datatype information."""
        if variable.m_positive_constant_enumerations:
            self._normalize_as_enumeration(variable)
        elif variable.m_positive_datatype_restrictions:
            self._normalize_as_value_space_subset(variable)

    def _normalize_as_enumeration(self, variable: DVariable) -> None:
        """Normalize when positive constant enumerations are present."""
        from hermit.datatypes.registry import DatatypeRegistry

        variable.m_has_explicit_data_values = True
        explicit_data_values = variable.m_explicit_data_values
        positive_constant_enumerations = variable.m_positive_constant_enumerations
        first_data_value_enumeration = positive_constant_enumerations[0]
        for index in range(first_data_value_enumeration.get_number_of_constants() - 1, -1, -1):
            data_value = first_data_value_enumeration.get_constant(index).data_value
            if (
                data_value not in explicit_data_values
                and data_value not in variable.m_forbidden_data_values
            ):
                found = True
                for enum_index in range(len(positive_constant_enumerations) - 1, 0, -1):
                    if not self._contains_data_value(
                        positive_constant_enumerations[enum_index], data_value
                    ):
                        found = False
                        break
                if found:
                    explicit_data_values.append(data_value)
        variable.m_forbidden_data_values.clear()
        for restriction in reversed(variable.m_positive_datatype_restrictions):
            if explicit_data_values:
                value_space_subset = DatatypeRegistry.create_value_space_subset(restriction)
                self._eliminate_data_values_using_value_space_subset(
                    value_space_subset, explicit_data_values, False
                )
        for restriction in reversed(variable.m_negative_datatype_restrictions):
            if explicit_data_values:
                value_space_subset = DatatypeRegistry.create_value_space_subset(restriction)
                self._eliminate_data_values_using_value_space_subset(
                    value_space_subset, explicit_data_values, True
                )
        if not explicit_data_values:
            self._set_clash_for(variable)

    @staticmethod
    def _contains_data_value(
        constant_enumeration: ConstantEnumeration, data_value: object
    ) -> bool:
        """Check if a constant enumeration contains a specific data value."""
        for i in range(constant_enumeration.get_number_of_constants() - 1, -1, -1):
            if constant_enumeration.get_constant(i).data_value == data_value:
                return True
        return False

    @staticmethod
    def _eliminate_data_values_using_value_space_subset(
        value_space_subset: Any,
        explicit_data_values: list[object],
        eliminate_when_value: bool,
    ) -> None:
        """Remove data values based on value space subset containment."""
        for value_index in range(len(explicit_data_values) - 1, -1, -1):
            data_value = explicit_data_values[value_index]
            if value_space_subset.contains_data_value(data_value) == eliminate_when_value:
                explicit_data_values.pop(value_index)

    def _normalize_as_value_space_subset(self, variable: DVariable) -> None:
        """Normalize when positive datatype restrictions are present."""
        from hermit.datatypes.registry import DatatypeRegistry

        restriction = variable.m_most_specific_restriction
        most_specific_datatype_uri = restriction.datatype_iri
        variable.m_value_space_subset = DatatypeRegistry.create_value_space_subset(
            most_specific_datatype_uri,
            restriction._facet_uris,
            restriction._facet_values
        )
        for restriction in reversed(variable.m_positive_datatype_restrictions):
            if restriction != variable.m_most_specific_restriction:
                variable.m_value_space_subset = DatatypeRegistry.conjoin_with_dr(
                    variable.m_value_space_subset, restriction
                )
        for restriction in reversed(variable.m_negative_datatype_restrictions):
            if not DatatypeRegistry.is_disjoint_with(
                most_specific_datatype_uri, restriction.datatype_iri
            ):
                variable.m_value_space_subset = DatatypeRegistry.conjoin_with_dr_negation(
                    variable.m_value_space_subset, restriction
                )
        if not variable.m_value_space_subset.has_cardinality_at_least(1):
            variable.m_forbidden_data_values.clear()
            self._set_clash_for(variable)
        else:
            for value_index in range(len(variable.m_forbidden_data_values) - 1, -1, -1):
                forbidden_value = variable.m_forbidden_data_values[value_index]
                if not variable.m_value_space_subset.contains_data_value(forbidden_value):
                    variable.m_forbidden_data_values.pop(value_index)

    def _eliminate_trivial_inequalities(self) -> None:
        """Remove inequalities between variables with disjoint datatypes."""
        from hermit.datatypes.registry import DatatypeRegistry

        for variable1 in list(self.m_conjunction.m_active_variables):
            if variable1.m_most_specific_restriction is not None:
                datatype_uri1 = variable1.m_most_specific_restriction.datatype_iri
                for variable2 in list(variable1.m_unequal_to_direct):
                    if variable2.m_most_specific_restriction is not None and DatatypeRegistry.is_disjoint_with(
                        datatype_uri1,
                        variable2.m_most_specific_restriction.datatype_iri,
                    ):
                        variable1.m_unequal_to.discard(variable2)
                        variable1.m_unequal_to_direct.discard(variable2)
                        variable2.m_unequal_to.discard(variable1)
                        variable2.m_unequal_to_direct.discard(variable1)

    def _eliminate_trivially_satisfiable_nodes(self) -> None:
        """Remove variables whose inequalities are trivially satisfiable."""
        self.m_auxiliary_variable_list.clear()
        self.m_auxiliary_variable_list.extend(self.m_conjunction.m_active_variables)
        while self.m_auxiliary_variable_list:
            variable = self.m_auxiliary_variable_list.pop()
            if variable.has_cardinality_at_least(len(variable.m_unequal_to) + 1):
                for neighbor_variable in list(variable.m_unequal_to):
                    neighbor_variable.m_unequal_to.discard(variable)
                    neighbor_variable.m_unequal_to_direct.discard(variable)
                    if neighbor_variable not in self.m_auxiliary_variable_list:
                        self.m_auxiliary_variable_list.append(neighbor_variable)
                variable.clear_inequalities()
                self.m_conjunction.m_active_variables.discard(variable)

    def _enumerate_value_space_subsets(self) -> None:
        """Enumerate explicit data values from value space subsets."""
        for variable in list(self.m_conjunction.m_active_variables):
            if self.m_extension_manager.contains_clash():
                return
            if variable.m_value_space_subset is not None:
                variable.m_has_explicit_data_values = True
                variable.m_value_space_subset.enumerate_data_values(
                    variable.m_explicit_data_values
                )
                if variable.m_forbidden_data_values:
                    for value_index in range(
                        len(variable.m_explicit_data_values) - 1, -1, -1
                    ):
                        data_value = variable.m_explicit_data_values[value_index]
                        if data_value in variable.m_forbidden_data_values:
                            variable.m_explicit_data_values.pop(value_index)
                variable.m_value_space_subset = None
                variable.m_forbidden_data_values.clear()
                if not variable.m_explicit_data_values:
                    self._set_clash_for(variable)

    def _check_conjunction_satisfiability(self) -> None:
        """Check if the current conjunction is satisfiable."""
        if (
            not self.m_extension_manager.contains_clash()
            and self.m_conjunction.m_active_variables
        ):
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.datatype_conjunction_checking_started(
                    self.m_conjunction
                )
            if self.m_conjunction.is_symmetric_clique():
                representative = next(iter(self.m_conjunction.m_active_variables))
                if (
                    not self.m_extension_manager.contains_clash()
                    and not representative.has_cardinality_at_least(
                        len(self.m_conjunction.m_active_variables)
                    )
                ):
                    self._set_clash_for_list(list(self.m_conjunction.m_active_variables))
            elif not self.m_extension_manager.contains_clash():
                self._eliminate_trivial_inequalities()
                self._eliminate_trivially_satisfiable_nodes()
                self._enumerate_value_space_subsets()
                if not self.m_extension_manager.contains_clash():
                    self._eliminate_trivially_satisfiable_nodes()
                    self._check_assignments()
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.datatype_conjunction_checking_finished(
                    self.m_conjunction, not self.m_extension_manager.contains_clash()
                )

    def _check_assignments(self) -> None:
        """Try to find a satisfying assignment for the conjunction."""
        # Variables are sorted so that we get a kind of "join order" optimization.
        sorted_vars = sorted(
            self.m_conjunction.m_active_variables,
            key=lambda v: len(v.m_explicit_data_values),
        )
        if not self._find_assignment(sorted_vars, 0):
            self._set_clash_for_list(sorted_vars)

    def _find_assignment(self, variables: list[DVariable], node_index: int) -> bool:
        """Recursively search for a valid data value assignment."""
        if node_index == len(variables):
            return True
        variable = variables[node_index]
        for value_index in range(len(variable.m_explicit_data_values) - 1, -1, -1):
            data_value = variable.m_explicit_data_values[value_index]
            if self._satisfies_neighbors(variable, data_value):
                variable.m_data_value = data_value
                if self._find_assignment(variables, node_index + 1):
                    return True
            self.m_interrupt_flag.check_interrupt()
        variable.m_data_value = None
        return False

    @staticmethod
    def _satisfies_neighbors(variable: DVariable, data_value: object) -> bool:
        """Check if *data_value* differs from all already-assigned neighbors."""
        for neighbor_variable in variable.m_unequal_to:
            neighbor_data_value = neighbor_variable.m_data_value
            if neighbor_data_value is not None and neighbor_data_value == data_value:
                return False
        return True

    def _set_clash_for(self, variable: DVariable) -> None:
        """Set a clash caused by a single variable."""
        self.m_union_dependency_set.clear_constituents()
        self._load_assertion_dependency_sets(variable)
        self.m_extension_manager.set_clash(self.m_union_dependency_set)

    def _set_clash_for_list(self, variables: list[DVariable]) -> None:
        """Set a clash caused by a set of variables."""
        from hermit.model import Inequality

        self.m_union_dependency_set.clear_constituents()
        for variable in reversed(variables):
            self._load_assertion_dependency_sets(variable)
            for neighbor_variable in variable.m_unequal_to_direct:
                dependency_set = self.m_extension_manager.get_assertion_dependency_set_binary(
                    Inequality.INSTANCE, variable.m_node, neighbor_variable.m_node
                )
                self.m_union_dependency_set.add_constituent(dependency_set)
        self.m_extension_manager.set_clash(self.m_union_dependency_set)

    def _load_assertion_dependency_sets(self, variable: DVariable) -> None:
        """Load dependency sets for all assertions on a variable."""
        node = variable.m_node
        for data_range in reversed(variable.m_positive_datatype_restrictions):
            dependency_set = self.m_extension_manager.get_assertion_dependency_set_unary(
                data_range, node
            )
            self.m_union_dependency_set.add_constituent(dependency_set)
        for data_range in reversed(variable.m_negative_datatype_restrictions):
            literal_data_range = data_range.get_negation()
            dependency_set = self.m_extension_manager.get_assertion_dependency_set_unary(
                literal_data_range, node
            )
            self.m_union_dependency_set.add_constituent(dependency_set)
        for data_range in reversed(variable.m_positive_constant_enumerations):
            dependency_set = self.m_extension_manager.get_assertion_dependency_set_unary(
                data_range, node
            )
            self.m_union_dependency_set.add_constituent(dependency_set)
        for data_range in reversed(variable.m_negative_constant_enumerations):
            literal_data_range = data_range.get_negation()
            dependency_set = self.m_extension_manager.get_assertion_dependency_set_unary(
                literal_data_range, node
            )
            self.m_union_dependency_set.add_constituent(dependency_set)


class DConjunction:
    """A conjunction of datatype variables with inequalities."""

    def __init__(self) -> None:
        self.m_unused_variables: list[DVariable] = []
        self.m_used_variables: list[DVariable] = []
        self.m_active_variables: set[DVariable] = set()
        self.m_buckets: list[DVariable | None] = [None] * 16
        self.m_number_of_entries = 0
        self.m_resize_threshold = int(len(self.m_buckets) * 0.75)

    def clear(self) -> None:
        """Clear all variables and reset."""
        for variable in reversed(self.m_used_variables):
            variable.dispose()
            self.m_unused_variables.append(variable)
        self.m_used_variables.clear()
        self.m_active_variables.clear()
        for i in range(len(self.m_buckets)):
            self.m_buckets[i] = None
        self.m_number_of_entries = 0

    def clear_active_variables(self) -> None:
        """Clear the active variable set and their inequalities."""
        for variable in list(self.m_active_variables):
            variable.clear_inequalities()
        self.m_active_variables.clear()

    def get_active_variables(self) -> list[DVariable]:
        """Return an unmodifiable view of active variables."""
        return list(self.m_active_variables)

    def get_variable_for(self, node: Node) -> DVariable | None:
        """Look up a variable by node."""
        index = DatatypeManager._get_index_for(hash(node), len(self.m_buckets))
        entry = self.m_buckets[index]
        while entry is not None:
            if entry.m_node is node:
                return entry
            entry = entry.m_next_entry
        return None

    def get_variable_for_ex(
        self, node: Node, new_variable_added: list[bool]
    ) -> DVariable:
        """Get or create a variable for the given node."""
        index = DatatypeManager._get_index_for(hash(node), len(self.m_buckets))
        entry = self.m_buckets[index]
        while entry is not None:
            if entry.m_node is node:
                new_variable_added[0] = False
                return entry
            entry = entry.m_next_entry
        if self.m_unused_variables:
            new_variable = self.m_unused_variables.pop()
        else:
            new_variable = DVariable()
        new_variable.m_node = node
        new_variable.m_next_entry = self.m_buckets[index]
        self.m_buckets[index] = new_variable
        self.m_number_of_entries += 1
        if self.m_number_of_entries >= self.m_resize_threshold:
            self._resize(len(self.m_buckets) * 2)
        new_variable_added[0] = True
        self.m_used_variables.append(new_variable)
        return new_variable

    def _resize(self, new_capacity: int) -> None:
        """Resize the hash table."""
        new_buckets: list[DVariable | None] = [None] * new_capacity
        for entry in self.m_buckets:
            current = entry
            while current is not None:
                next_entry = current.m_next_entry
                new_index = DatatypeManager._get_index_for(
                    hash(current.m_node), new_capacity
                )
                current.m_next_entry = new_buckets[new_index]
                new_buckets[new_index] = current
                current = next_entry
        self.m_buckets = new_buckets
        self.m_resize_threshold = int(new_capacity * 0.75)

    def add_inequality(self, variable1: DVariable, variable2: DVariable) -> None:
        """Add an inequality between two variables."""
        assert variable1 != variable2
        if variable2 not in variable1.m_unequal_to:
            variable1.m_unequal_to.add(variable2)
            variable2.m_unequal_to.add(variable1)
            variable1.m_unequal_to_direct.add(variable2)

    def is_symmetric_clique(self) -> bool:
        """Check if all active variables form a symmetric clique of inequalities."""
        number_of_variables = len(self.m_active_variables)
        if number_of_variables > 0:
            first = next(iter(self.m_active_variables))
            for variable in self.m_active_variables:
                if len(variable.m_unequal_to) + 1 != number_of_variables or not first.has_same_restrictions(variable):
                    return False
        return True

    def __str__(self, prefixes: Prefixes | None = None) -> str:
        from hermit.model import Prefixes as Pfx

        if prefixes is None:
            prefixes = Pfx.SEMANTIC_WEB_PREFIXES
        parts = []
        first = True
        active_list = list(self.m_active_variables)
        for variable_index in range(len(active_list)):
            if first:
                first = False
            else:
                parts.append(" & ")
            variable = active_list[variable_index]
            parts.append(str(variable))
            parts.append("(")
            parts.append(str(variable_index))
            parts.append(")")
            for neighbor_variable in variable.m_unequal_to_direct:
                neighbor_index = active_list.index(neighbor_variable)
                parts.append(" & ")
                parts.append(str(variable_index))
                parts.append(" != ")
                parts.append(str(neighbor_index))
        return "".join(parts)

    def __repr__(self) -> str:
        return self.__str__()


class DVariable:
    """A variable in a datatype conjunction, tracking datatype restrictions and inequalities."""

    def __init__(self) -> None:
        self.m_positive_constant_enumerations: list[ConstantEnumeration] = []
        self.m_negative_constant_enumerations: list[ConstantEnumeration] = []
        self.m_positive_datatype_restrictions: list[DatatypeRestriction] = []
        self.m_negative_datatype_restrictions: list[DatatypeRestriction] = []
        self.m_unequal_to: set[DVariable] = set()
        self.m_unequal_to_direct: set[DVariable] = set()
        self.m_forbidden_data_values: list[object] = []
        self.m_explicit_data_values: list[object] = []
        self.m_has_explicit_data_values = False
        self.m_most_specific_restriction: DatatypeRestriction | None = None
        self.m_node: Node | None = None
        self.m_next_entry: DVariable | None = None
        self.m_value_space_subset: Any = None
        self.m_data_value: object | None = None

    def dispose(self) -> None:
        """Clear all data for reuse."""
        self.m_positive_constant_enumerations.clear()
        self.m_negative_constant_enumerations.clear()
        self.m_positive_datatype_restrictions.clear()
        self.m_negative_datatype_restrictions.clear()
        self.m_unequal_to.clear()
        self.m_unequal_to_direct.clear()
        self.m_forbidden_data_values.clear()
        self.m_explicit_data_values.clear()
        self.m_has_explicit_data_values = False
        self.m_most_specific_restriction = None
        self.m_node = None
        self.m_next_entry = None
        self.m_value_space_subset = None
        self.m_data_value = None

    def clear_inequalities(self) -> None:
        """Clear all inequalities."""
        self.m_unequal_to.clear()
        self.m_unequal_to_direct.clear()

    def add_forbidden_data_value(self, forbidden_data_value: object) -> None:
        """Add a forbidden data value."""
        if forbidden_data_value not in self.m_forbidden_data_values:
            self.m_forbidden_data_values.append(forbidden_data_value)

    def has_cardinality_at_least(self, number: int) -> bool:
        """Check if the variable has at least *number* possible values."""
        if self.m_has_explicit_data_values:
            return len(self.m_explicit_data_values) >= number
        if self.m_value_space_subset is not None:
            return self.m_value_space_subset.has_cardinality_at_least(
                number + len(self.m_forbidden_data_values)
            )
        return True

    @property
    def node(self) -> Node | None:
        """Return the tableau node this variable represents."""
        return self.m_node

    @property
    def positive_data_value_enumerations(self) -> list[ConstantEnumeration]:
        return list(self.m_positive_constant_enumerations)

    @property
    def negative_data_value_enumerations(self) -> list[ConstantEnumeration]:
        return list(self.m_negative_constant_enumerations)

    @property
    def positive_datatype_restrictions(self) -> list[DatatypeRestriction]:
        return list(self.m_positive_datatype_restrictions)

    @property
    def negative_datatype_restrictions(self) -> list[DatatypeRestriction]:
        return list(self.m_negative_datatype_restrictions)

    @property
    def unequal_to_direct(self) -> list[DVariable]:
        return list(self.m_unequal_to_direct)

    def has_same_restrictions(self, that: DVariable) -> bool:
        """Check if this variable has the same datatype restrictions as *that*."""
        if self is that:
            return True
        return (
            self._lists_equal(
                self.m_positive_constant_enumerations,
                that.m_positive_constant_enumerations,
            )
            and self._lists_equal(
                self.m_negative_constant_enumerations,
                that.m_negative_constant_enumerations,
            )
            and self._lists_equal(
                self.m_positive_datatype_restrictions,
                that.m_positive_datatype_restrictions,
            )
            and self._lists_equal(
                self.m_negative_datatype_restrictions,
                that.m_negative_datatype_restrictions,
            )
        )

    @staticmethod
    def _lists_equal(first: list[object], second: list[object]) -> bool:
        if len(first) != len(second):
            return False
        for item in first:
            if item not in second:
                return False
        return True

    def __str__(self) -> str:
        parts = ["["]
        first = True
        for item in self.m_positive_constant_enumerations:
            if first:
                first = False
            else:
                parts.append(", ")
            parts.append(str(item))
        for item in self.m_negative_constant_enumerations:
            if first:
                first = False
            else:
                parts.append(", ")
            parts.append(str(item.get_negation()))
        for item in self.m_positive_datatype_restrictions:
            if first:
                first = False
            else:
                parts.append(", ")
            parts.append(str(item))
        for item in self.m_negative_datatype_restrictions:
            if first:
                first = False
            else:
                parts.append(", ")
            parts.append(str(item.get_negation()))
        parts.append("]")
        return "".join(parts)

    def __repr__(self) -> str:
        return self.__str__()
