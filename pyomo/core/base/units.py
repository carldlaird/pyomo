#  _________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright (c) 2014 Sandia Corporation.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  This software is distributed under the BSD License.
#  _________________________________________________________________________

"""Pyomo Units Module ** WORK IN PROGRESS **

This module provides support for including units within Pyomo expressions, and provides
methods for checking the consistency of units within those expresions.

To use this package within your Pyomo model, you first need an instance of a PyomoUnitsContainer.
You can use the module level instance called units_container or you can create your own instance.
With this object you can then use the pre-defined units or even create new units.

Examples:
    To use a unit within an expression, simply reference the unit
    as a field on the units manager.

        >>> from pyomo.environ import *
        >>> from pyomo.units import units_container as uc
        >>> model = ConcreteModel()
        >>> model.acc = Var()
        >>> model.obj = Objective(expr=(model.acc*uc.m/uc.s**2 - 9.81*uc.m/uc.s**2)**2)
        >>>

Notes:
    * The implementation is currently based on `pint <http://pint.readthedocs.io>`_
        Python package and supports all the units that are supported by pint.
    * Currently, we do NOT test units of unary functions that include native types since
        these are removed by the expression system before getting to the units checking code
Todo:
    * fix documentation to include proper docstring references to classes/methods, etc.
    * create a new pint unit definition file (and load from that file)
        since the precision in pint is insufficient for 1e-8 constraint tolerances
    * implement and test pickling and un-pickling
    * implement convert functionality
    * implement remove_unit(x, expected_unit) that returns a dimensionless version of the expression
    * Add units capabilities to Var and Param
    * Investigate issues surrounding absolute and relative temperatures (delta units)
    * Implement external function interface that specifies units for the arguments and the function itself
    * Implement LinearExpression and NPV_LinearExpression


"""
# Note: This documentation is not yet correct - this is how the units will eventually work when complete
# Examples:
#     To use a unit within an expression, simply reference the unit
#     as a field on the units manager.
#
#         >>> from pyomo.environ import *
#         >>> from pyomo.units import units_manager as um
#         >>> model = ConcreteModel()
#         >>> model.x = Var(units=um.kg)
#         >>> model.obj = Objective(expr=(model.x - 97.2*um.kg)**2)
#
# """

from pyomo.core.expr.numvalue import NumericValue, nonpyomo_leaf_types, value
from pyomo.core.base.template_expr import IndexTemplate
from pyomo.core.expr import current as expr
import pint


class UnitsError(Exception):
    """
    An exception class for all general errors/warnings associated with units
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Units Error: ' + str(self.msg)


class InconsistentUnitsError(UnitsError):
    """
    An exception indicating that inconsistent units are present on an expression.

    E.g., x == y, where x is in units of um.kg and y is in units of um.meter
    """
    def __init__(self, exp1, exp2, msg):
        msg = '{} not compatible with {}. {}'.format(str(exp1), str(exp2), str(msg))
        super(InconsistentUnitsError, self).__init__(msg)


class _PyomoUnit(NumericValue):
    """An object that represents a single unit in Pyomo (e.g., kg, meter)

    Users should not create instances of _PyomoUnit directly, but rather access
    units as attributes on an instance of a PyomoUnitsContainer. See module documentation
    for more information.
    """
    def __init__(self, pint_unit, pint_registry):
        self._pint_unit = pint_unit
        self._pint_registry = pint_registry

    def _get_pint_unit(self):
        return self._pint_unit

    def _get_pint_registry(self):
        return self._pint_registry

    # Todo: test pickle and implement __getstate__/__setstate__ to do the right thing

    def getname(self, fully_qualified=False, name_buffer=None):
        return str(self)

    # methods/properties that use the NumericValue base class implementation
    # name property
    # local_name
    # cname

    def is_constant(self):
        """
        Indicates if the NumericValue is constant and can be replaced with a plain old number
        Overloaded from: NumericValue

        This method indicates if the NumericValue is a constant and can be replaced with a plain
        old number. Although units are, in fact, constant, we do NOT want this replaced - therefore
        we return False here to prevent replacement.

        Returns
        =======
            bool : False (This method always returns False)
        """
        return False

    def is_fixed(self):
        """
        Indicates if the NumericValue is fixed with respect to a "solver".
        Overloaded from: NumericValue

        Indicates if the Unit should be treated as fixed. Since the Unit is always treated as
        a constant value of 1.0, it is fixed.

        Returns
        =======
            bool : True (This method always returns True)

        """
        return True

    def is_parameter_type(self):
        """ This is not a parameter type (overloaded from NumericValue) """
        return False

    def is_variable_type(self):
        """ This is not a variable type (overloaded from NumericValue) """
        return False

    def is_potentially_variable(self):
        """
        This is not potentially variable (does not and cannot contain a variable).
        Overloaded from NumericValue
        """
        return False

    def is_named_expression_type(self):
        """ This is not a named expression (overloaded from NumericValue) """
        return False

    def is_expression_type(self):
        """ This is a leaf, not an expression (overloaded from NumericValue) """
        return False

    def is_component_type(self):
        """ This is not a component type (overloaded from NumericValue) """
        return False

    def is_relational(self):
        """ This is not relational (overloaded from NumericValue) """
        return False

    def is_indexed(self):
        """ This is not indexed (overloaded from NumericValue) """
        return False

    # polynomial_degree using implementation in NumericValue
    def _compute_polynomial_degree(self, result):
        # ToDo: check why NumericalValue returns None instead of 0
        return 0

    def __float__(self):
        """
        Coerce the value to a floating point

        Raises:
            TypeError
        """
        raise TypeError(
            "Implicit conversion of Pyomo Unit `%s' to a float is "
            "disabled. This error is often the result of treating a unit "
            "as though it were a number (e.g., passing a unit to a built-in "
            "math function). Avoid this error by using Pyomo-provided math "
            "functions."
            % self.name)

    def __int__(self):
        """
        Coerce the value to an integer

        Raises:
            TypeError
        """
        raise TypeError(
            "Implicit conversion of Pyomo Unit `%s' to an int is "
            "disabled. This error is often the result of treating a unit "
            "as though it were a number (e.g., passing a unit to a built-in "
            "math function). Avoid this error by using Pyomo-provided math "
            "math function). Avoid this error by using Pyomo-provided math "
            "functions."
            % self.name)

    # __lt__ uses NumericValue base class implementation
    # __gt__ uses NumericValue base class implementation
    # __le__ uses NumericValue base class implementation
    # __ge__ uses NumericValue base class implementation
    # __eq__ uses NumericValue base class implementation
    # __add__ uses NumericValue base class implementation
    # __sub__ uses NumericValue base class implementation
    # __mul__ uses NumericValue base class implementation
    # __div__ uses NumericValue base class implementation
    # __truediv__ uses NumericValue base class implementation
    # __pow__ uses NumericValue vase class implementation
    # __radd__ uses NumericValue base class implementation
    # __rsub__ uses NumericValue base class implementation
    # __rmul__ uses NumericValue base class implementation
    # __rdiv__ uses NumericValue base class implementation
    # __rtruediv__ uses NumericValue base class implementation
    # __rpow__ uses NumericValue base class implementation

    # def __iadd__(self, other):
    #     """
    #     Incremental addition
    #
    #     This method is called when Python processes the statement::
    #
    #         self += other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place addition (+=)."
    #         % self.name)
    #
    # def __isub__(self, other):
    #     """
    #     Incremental subtraction
    #
    #     This method is called when Python processes the statement::
    #
    #         self -= other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place subtraction (-=)."
    #         % self.name)
    #
    # def __imul__(self, other):
    #     """
    #     Incremental multiplication
    #
    #     This method is called when Python processes the statement::
    #
    #         self *= other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place multiplication (*=)."
    #         % self.name)
    #
    # def __idiv__(self, other):
    #     """
    #     Incremental division
    #
    #     This method is called when Python processes the statement::
    #
    #         self /= other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place division (/=)."
    #         % self.name)
    #
    # def __itruediv__(self, other):
    #     """
    #     Incremental division (when __future__.division is in effect)
    #
    #     This method is called when Python processes the statement::
    #
    #         self /= other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place division (/=)."
    #         % self.name)
    #
    # def __ipow__(self, other):
    #     """
    #     Incremental power
    #
    #     This method is called when Python processes the statement::
    #
    #         self **= other
    #     Raises:
    #         TypeError
    #     """
    #     raise TypeError(
    #         "The Pyomo Unit `%s' is read-only and cannot be the target of an in-place exponentiation (**=)."
    #         % self.name)

    # __neg__ uses NumericValue base class implementation
    # __pos__ uses NumericValue base class implementation
    # __add__ uses NumericValue base class implementation

    def __str__(self):
        """ Returns a string representing the unit """

        # The ~ returns the short form of the pint unit
        return '{:!~s}'.format(self._pint_unit)

    def to_string(self, verbose=None, labeler=None, smap=None,
                  compute_values=False):
        """
        Return a string representation of the expression tree.

        See documentation on NumericValue

        Returns:
            A string representation for the expression tree.
        """
        return str(self)

    def __nonzero__(self):
        """Unit is treated as a constant value of 1.0. Therefore, it is always nonzero
        Returns: (bool)
        """
        return self.__bool__()

    def __bool__(self):
        """Unit is treated as a constant value of 1.0. Therefore, it is always "True"
        Returns: (bool)"""
        return True

    def __call__(self, exception=True):
        """Unit is treated as a constant value, and this method always returns 1.0"""
        return 1.0

    def pprint(self, ostream=None, verbose=False):
        """Display a user readable string description of this object.
        """
        if ostream is None:         #pragma:nocover
            ostream = sys.stdout
        ostream.write(str(self))
        # There is also a long form, but the verbose flag is not really the correct indicator
        # if verbose:
        #     ostream.write('{:!s}'.format(self._pint_unit))
        # else:
        #     ostream.write('{:!~s}'.format(self._pint_unit))

def is_leaf(expr):
    """
    Returns True if the object in expr is a leaf node (i.e. it has
    no args method with children)

    Parameters
    ----------
    expr : Pyomo expression
        The expression to test

    Returns
    -------
        bool : Returns True if the expr is a leaf node, False otherwise
    """
    if type(expr) in nonpyomo_leaf_types \
        or not expr.is_expression_type():
        return True
    return False


class _UnitExtractionVisitor(expr.StreamBasedExpressionVisitor):
    def __init__(self, pyomo_units_container, units_equivalence_tolerance=1e-12):
        """
        Visitor class used to determine units of an expression. Do not use
        this class directly, but rather use :func:`get_units` or
        :func:`check_units_consistency`.

        Parameters
        ----------
        pyomo_units_container : PyomoUnitsContainer
           Instance of the PyomoUnitsContainer that was used for the units
           in the expressions. Pyomo does not support "mixing" units from
           different containers

        units_equivalence_tolerance : float (default 1e-12)
            Floating point tolerance used when deciding if units are equivalent
            or not. (It can happen that units

        Notes
        -----

        This class inherits from the :class:`StreamBasedExpressionVisitor` to implement
        a walker that returns the pyomo units and pint units corresponding to an
        expression.

        There are class attributes (dicts) that map the expression node type to the
        particular method that should be called to return the units of the node based
        on the units of its child arguments. This map is used in exitNode.
        """
        super(_UnitExtractionVisitor, self).__init__()
        self._pyomo_units_container = pyomo_units_container
        self._pint_ureg = self._pyomo_units_container._pint_registry()
        self._units_equivalence_tolerance = units_equivalence_tolerance

    def _pint_units_equivalent(self, lhs, rhs):
        """
        Check if two pint units are equivalent

        Parameters
        ----------
        lhs : pint unit
            first pint unit to compare
        rhs : pint unit
            second pint unit to compare

        Returns
        -------
            bool : True if they are equivalent, and False otherwise
        """
        if lhs == rhs:
            return True

        # Units are not the same actual objects.
        # Use pint mechanisms to compare
        # First, convert to quantities
        lhsq = 1.0 * lhs
        rhsq = 1.0 * rhs
        if lhsq.dimensionality == rhsq.dimensionality and \
            abs(lhsq-rhsq).magnitude < self._units_equivalence_tolerance:
            return True

        return False

    def _get_unit_for_equivalent_children(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to a operation where all
        children should have the same units (e.g., equality, sum). This method
        also checks to make sure the units are valid.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        # ToDo: This may be expensive for long summations and, in the case of reporting only, we may want to skip the checks
        assert len(list_of_unit_tuples) > 0

        # verify that the pint units are equivalent from each
        # of the child nodes - assume that PyomoUnits are equivalent
        pint_unit_0 = list_of_unit_tuples[0][1]
        for i in range(1, len(list_of_unit_tuples)):
            pint_unit_i = list_of_unit_tuples[i][1]
            if not self._pint_units_equivalent(pint_unit_0, pint_unit_i):
                raise InconsistentUnitsError(pint_unit_0, pint_unit_i,
                        'Error in units found in expression: {}'.format(str(node)))

        # checks were OK, return the first one in the list
        return (list_of_unit_tuples[0][0], list_of_unit_tuples[0][1])

    def _get_unit_for_linear_expression(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to a node of LinearExpression
        type. This is a special node since it does not use "args" the way
        other expression types do. Because of this, the StreamBasedExpressionVisitor
        does not pick up on the "children", and list_of_unit_tuples is empty.
        Therefore, we implement the recursion into coeffs and vars ourselves.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair (Note: this is different for LinearExpression,
           - see method documentation above).

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        # StreamBasedExpressionVisitor does not handle the children of this node
        assert len(list_of_unit_tuples) == 0

        # ToDo: This may be expensive for long summations and, in the case of reporting only, we may want to skip the checks
        term_unit_list = []
        if node.constant:
            const_units = _get_units_tuple(node.constant, self._pyomo_units_container)
            term_unit_list.append(const_units)
        assert len(node.linear_coefs) == len(node.linear_vars)
        for k,v in enumerate(node.linear_vars):
            c = node.linear_coefs[k]
            v_units = _get_units_tuple(v, self._pyomo_units_container)
            c_units = _get_units_tuple(c, self._pyomo_units_container)
            if self._pint_units_equivalent(c_units[1], self._pint_ureg.dimensionless):
                term_unit_list.append((v_units[0], v_units[1]))
            elif self._pint_units_equivalent(v_units[1], self._pint_ureg.dimensionless):
                term_unit_list.append((c_units[0], c_units[1]))
            else:
                term_unit_list.append((c_units[0]*v_units[0], c_units[1]*v_units[1]))

        # collected the units for all the terms, so now
        # verify that the pint units are equivalent from each
        # of the child nodes - assume that PyomoUnits are equivalent
        pint_unit_0 = term_unit_list[0][1]
        for i in range(1, len(term_unit_list)):
            pint_unit_i = term_unit_list[i][1]
            if not self._pint_units_equivalent(pint_unit_0, pint_unit_i):
                raise InconsistentUnitsError(pint_unit_0, pint_unit_i,
                        'Error in units found in expression: {}'.format(str(node)))

        # checks were OK, return the first one in the list
        return (term_unit_list[0][0], term_unit_list[0][1])

    def _get_unit_for_product(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresonding to a product
        of the child data in list_of_unit_tuples

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) > 1

        dless = self._pyomo_units_container.dimensionless
        pyomo_unit = None
        pint_unit = None
        for i in range(len(list_of_unit_tuples)):
            pyomo_unit_i = list_of_unit_tuples[i][0]
            pint_unit_i = list_of_unit_tuples[i][1]
            if self._pint_units_equivalent(pint_unit_i, self._pint_ureg.dimensionless):
                continue

            # we have units
            if pyomo_unit is None:
                assert pint_unit is None
                pyomo_unit = pyomo_unit_i
                pint_unit = pint_unit_i
            else:
                pyomo_unit = pyomo_unit * pyomo_unit_i
                pint_unit = pint_unit * pint_unit_i

        if pyomo_unit is None:
            assert pint_unit is None
            return (self._pyomo_units_container.dimensionless, self._pint_ureg.dimensionless)

        return (pyomo_unit, pint_unit)

    def _get_unit_for_reciprocal(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to a reciprocal
        of the child data in list_of_unit_tuples

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) == 1

        pyomo_unit = list_of_unit_tuples[0][0]
        pint_unit = list_of_unit_tuples[0][1]
        if self._pint_units_equivalent(pint_unit, self._pint_ureg.dimensionless):
            return (pyomo_unit, pint_unit) # these are dimensionless
        return (1.0/pyomo_unit, 1.0/pint_unit)

    def _get_unit_for_pow(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to a pow expression
        with the base and exponent in list_of_unit_tuples

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) == 2

        # this operation is x^y
        # x should be in list_of_unit_tuples[0] and
        # y should be in list_of_unit_tuples[1]
        pyomo_unit_base = list_of_unit_tuples[0][0]
        pint_unit_base = list_of_unit_tuples[0][1]
        pyomo_unit_exponent = list_of_unit_tuples[1][0]
        pint_unit_exponent = list_of_unit_tuples[1][1]

        # check to make sure that the exponent is dimensionless
        if not self._pint_units_equivalent(pint_unit_exponent, self._pint_ureg.dimensionless):
            raise UnitsError("Error in sub-expression: {}. "
                             "Exponents in a pow expression must be dimensionless."
                             "".format(node))

        # if the base is dimensionless, return Dimensionless
        if self._pint_units_equivalent(pint_unit_base, self._pint_ureg.dimensionless):
            # base is dimensionless - does not matter if the exponent is fixed
            return (pyomo_unit_base, pyomo_unit_exponent)

        # Since the base is not dimensionless, make sure that the exponent
        # is a fixed number
        exponent = node.args[1]
        if type(exponent) not in nonpyomo_leaf_types \
            and not (exponent.is_fixed() or exponent.is_constant()):
            raise UnitsError("The base of an exponent has units {}, but "
                             "the exponent is not a fixed numerical value."
                             "".format(str(list_of_unit_tuples[0][0])))
        exponent_value = value(exponent)
        pyomo_unit = pyomo_unit_base**exponent_value
        pint_unit = pint_unit_base**exponent_value

        return (pyomo_unit, pint_unit)

    def _get_unit_for_single_child(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to the (single)
        child in the list_of_unit_tuples. This is intended for unary nodes
        in the expression tree.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) == 1

        pyomo_unit = list_of_unit_tuples[0][0]
        pint_unit = list_of_unit_tuples[0][1]
        return (pyomo_unit, pint_unit)

    def _get_dimensionless_with_dimensionless_children(self, node, list_of_unit_tuples):
        """
        Check to make sure that any child arguments are dimensionless (for functions like exp())
        and return dimensionless if successful. Although odd that this does not just return
        a boolean, it is done this way to match the signature of the other methods used to get
        units for expressions.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (dimensionless (PyomoUnit), dimensionless (pint unit))
                if successful, returns dimensionless for both pyomo_unit
                and pint_unit, otherwise raises UnitError
        """
        for (pyomo_unit, pint_unit) in list_of_unit_tuples:
            if not self._pint_units_equivalent(pint_unit, self._pint_ureg.dimensionless):
                raise UnitsError('Expected dimensionless units in {}, but found {}.'.format(str(node), str(pyomo_unit)))

        # if we make it here, then all are equal to None
        return (pyomo_unit, pint_unit)

    def _get_dimensionless_no_children(self, node, list_of_unit_tuples):
        """
        Check to make sure the length of list_of_unit_tuples is zero, and returns
        dimensionless units of PyomoUnit and pint unit types.
        Used for leaf nodes that should not have any units.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (dimensionless (PyomoUnit), dimensionless (pint unit))
                if successful, returns dimensionless for both pyomo_unit
                and pint_unit, otherwise raises UnitError
        """
        assert len(list_of_unit_tuples) == 0
        assert is_leaf(node)

        # # check that the leaf does not have any units
        # # ToDo: Leave this commented code here since this "might" be similar to the planned mechanism for getting units from Pyomo component leaves
        # if hasattr(node, 'get_units') and node.get_units() is not None:
        #     raise UnitsError('Expected dimensionless units in {}, but found {}.'.format(str(node),
        #                         str(node.get_units())))

        return (self._pyomo_units_container.dimensionless, self._pint_ureg.dimensionless)

    def _get_unit_for_unary_function(self, node, list_of_unit_tuples):
        """
        Get the units for a unary function. Checks that the list_of_unit_tuples is of length 1
        and calls the appropriate method from the unary function method map.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) == 1
        func_name = node.getname()
        if func_name in self.unary_function_method_map:
            node_func = self.unary_function_method_map[func_name]
            if node_func is not None:
                return node_func(self, node, list_of_unit_tuples)
        raise TypeError('An unhandled unary function: {} was encountered while retrieving the'
                        ' units of expression {}'.format(func_name, str(node)))

    def _get_unit_for_expr_if(self, node, list_of_unit_tuples):
        """
        Return the unit expression corresponding to an Expr_if expression. The
        _if relational expression should be consistent, and _then/_else should be
        the same units. Also checks to make sure length of list_of_unit_tuples is 3

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)
        """
        assert len(list_of_unit_tuples) == 3

        # the _if should already be consistent (since the children were
        # already checked)

        # verify that they _then and _else are equivalent
        then_pyomo_unit, then_pint_unit = list_of_unit_tuples[1]
        else_pyomo_unit, else_pint_unit = list_of_unit_tuples[2]

        if not self._pint_units_equivalent(then_pint_unit, else_pint_unit):
            raise InconsistentUnitsError(then_pyomo_unit, else_pyomo_unit,
                    'Error in units found in expression: {}'.format(str(node)))

        # then and else are the same
        return (then_pyomo_unit, then_pint_unit)

    def _get_dimensionless_with_radians_child(self, node, list_of_unit_tuples):
        """
        Get the units for trig functions. Checks that the length of list_of_unit_tuples is 1
        and that the units of that child expression are radians, and returns dimensionless
        for the Pyomo unit and the pint unit

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (dimensionless (PyomoUnit), dimensionless (pint unit))
                if successful, returns dimensionless for both pyomo_unit
                and pint_unit, otherwise raises UnitError

        """
        assert len(list_of_unit_tuples) == 1

        pyomo_unit = list_of_unit_tuples[0][0]
        pint_unit = list_of_unit_tuples[0][1]
        ureg = self._pyomo_units_container._pint_registry()
        if not self._pint_units_equivalent(pint_unit, ureg.radians):
            raise UnitsError('Expected radians in argument to function in expression {}, but found {}'.format(
                str(node), str(pyomo_unit)))

        return (self._pyomo_units_container.dimensionless, self._pint_ureg.dimensionless)

    def _get_radians_with_dimensionless_child(self, node, list_of_unit_tuples):
        """
        Get the units for inverse trig functions. Checks that the length of list_of_unit_tuples is 1
        and that the child argument is dimensionless, and returns radians

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit for radians, pint_unit for radians)

        """
        assert len(list_of_unit_tuples) == 1

        pyomo_unit = list_of_unit_tuples[0][0]
        pint_unit = list_of_unit_tuples[0][1]
        if not self._pint_units_equivalent(pint_unit, self._pint_ureg.dimensionless):
            raise UnitsError('Expected dimensionless argument to function in expression {},'
                             ' but found {}'.format(
                             str(node), str(pyomo_unit)))

        uc = self._pyomo_units_container
        return (uc.radians, self._pint_ureg.radians)

    def _get_unit_sqrt(self, node, list_of_unit_tuples):
        """
        Return the units for sqrt. Checks that the length of list_of_unit_tuples is one.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        list_of_unit_tuples : list
           This is a list of tuples (one for each of the children) where each tuple
           is a PyomoUnit, pint unit pair

        Returns
        -------
            tuple : (PyomoUnit, pint unit)

        """
        assert len(list_of_unit_tuples) == 1
        if self._pint_units_equivalent(list_of_unit_tuples[0][1], self._pint_ureg.dimensionless):
            return (self._pyomo_units_container.dimensionless, self._pint_ureg.dimensionless)
        return (list_of_unit_tuples[0][0]**0.5, list_of_unit_tuples[0][1]**0.5)

    node_type_method_map = {
        expr.EqualityExpression: _get_unit_for_equivalent_children,
        expr.InequalityExpression: _get_unit_for_equivalent_children,
        expr.RangedExpression: _get_unit_for_equivalent_children,
        expr.SumExpression: _get_unit_for_equivalent_children,
        expr.NPV_SumExpression: _get_unit_for_equivalent_children,
        expr.ProductExpression: _get_unit_for_product,
        expr.MonomialTermExpression: _get_unit_for_product,
        expr.NPV_ProductExpression: _get_unit_for_product,
        expr.ReciprocalExpression: _get_unit_for_reciprocal,
        expr.NPV_ReciprocalExpression: _get_unit_for_reciprocal,
        expr.PowExpression: _get_unit_for_pow,
        expr.NPV_PowExpression: _get_unit_for_pow,
        expr.NegationExpression: _get_unit_for_single_child,
        expr.NPV_NegationExpression: _get_unit_for_single_child,
        expr.AbsExpression: _get_unit_for_single_child,
        expr.NPV_AbsExpression: _get_unit_for_single_child,
        expr.UnaryFunctionExpression: _get_unit_for_unary_function,
        expr.NPV_UnaryFunctionExpression: _get_unit_for_unary_function,
        expr.Expr_ifExpression: _get_unit_for_expr_if,
        IndexTemplate: _get_dimensionless_no_children,
        expr.GetItemExpression: _get_dimensionless_with_dimensionless_children,
        expr.ExternalFunctionExpression: _get_dimensionless_with_dimensionless_children,
        expr.NPV_ExternalFunctionExpression: _get_dimensionless_with_dimensionless_children,
        expr.LinearExpression: _get_unit_for_linear_expression
    }

    unary_function_method_map = {
        'log': _get_dimensionless_with_dimensionless_children,
        'log10':_get_dimensionless_with_dimensionless_children,
        'sin': _get_dimensionless_with_radians_child,
        'cos': _get_dimensionless_with_radians_child,
        'tan': _get_dimensionless_with_radians_child,
        'sinh': _get_dimensionless_with_radians_child,
        'cosh': _get_dimensionless_with_radians_child,
        'tanh': _get_dimensionless_with_radians_child,
        'asin': _get_radians_with_dimensionless_child,
        'acos': _get_radians_with_dimensionless_child,
        'atan': _get_radians_with_dimensionless_child,
        'exp': _get_dimensionless_with_dimensionless_children,
        'sqrt': _get_unit_sqrt,
        'asinh': _get_radians_with_dimensionless_child,
        'acosh': _get_radians_with_dimensionless_child,
        'atanh': _get_radians_with_dimensionless_child,
        'ceil': _get_unit_for_single_child,
        'floor': _get_unit_for_single_child
    }

    def exitNode(self, node, data):
        if is_leaf(node):
            if isinstance(node, _PyomoUnit):
                return (node, node._get_pint_unit())

            # ToDo: Check for Var or Param and return their units...

            # I have a leaf, but this is not a PyomoUnit - (treat as dimensionless)
            dless = self._pyomo_units_container.dimensionless
            return (dless, dless._pint_unit)

        # not a leaf - get the appropriate function for type of the node
        node_type = type(node)
        if node_type in self.node_type_method_map:
            node_func = self.node_type_method_map[node_type]
            if node_func is not None:
                pyomo_unit, pint_unit = node_func(self, node, data)
                return (pyomo_unit, pint_unit)

        raise TypeError('An unhandled expression node type: {} was encountered while retrieving the'
                        ' units of expression'.format(str(node_type), str(node)))


def _get_units_tuple(expr, pyomo_units_container):
    pyomo_unit, pint_unit = _UnitExtractionVisitor(pyomo_units_container).walk_expression(expr=expr)
    return (pyomo_unit, pint_unit)


def get_units(expr, pyomo_units_container):
    """
    Return the Pyomo units corresponding to this expression (also performs validation
    and will raise an exception if units are not consistent).

    Parameters
    ----------
    expr : Pyomo expression
        The expression containing the desired units

    Returns
    -------
        Pyomo expression containing only units.
    """
    pyomo_unit, pint_unit = _get_units_tuple(expr=expr, pyomo_units_container=pyomo_units_container)
    # ToDo: If we get dimensionless, should we return None?
    return pyomo_unit


def check_units_consistency(expr, pyomo_units_container, allow_exceptions=True):
    """
    Check the consistency of the units within an expression. IF allow_exceptions is False,
    then this function swallows the exception and returns only True or False. Otherwise,
    it will throw an exception if the units are inconsistent.

    Parameters
    ----------
    expr : Pyomo expression
        The source expression to check.

    allow_exceptions: bool
        True if you want any exceptions to be thrown, False if you only want a boolean
        (and the exception is ignored).

    Returns
    -------
        bool : True if units are consistent, and False if not
    """
    if allow_exceptions is True:
        pyomo_unit, pint_unit = _get_units_tuple(expr=expr, pyomo_units_container=pyomo_units_container)
        # if we make it here, then no exceptions were thrown
        return True

    # allow_exceptions is not True, therefore swallow any exceptions in a try-except
    try:
        pyomo_unit, pint_unit = _get_units_tuple(expr=expr, pyomo_units_container=pyomo_units_container)
    except:
        return False

    return True

# def convert_value(src_value, from_units=None, to_units=None):
#     """
#     This method performs explicit conversion of a numerical value in
#     one unit to a numerical value in another unit.
#     This method returns a new expression object that has the conversion for expr in its units to
#     the units specified by to_units.
#
#     Parameters
#     ----------
#     src_value : float
#        The numeric value that will be converted
#     from_units : Pyomo expression with units
#        The source units for value
#     to_units : Pyomo expression with units
#        The desired target units for the new value
#
#     Returns
#     -------
#        float : The new value (src_value converted from from_units to to_units)
#     """
#     pint_src_unit = self._get_units_from_expression(from_units, pint_version=True)
#     pint_dest_unit = self._get_units_from_expression(to_units, pint_version=True)
#
#     src_quantity = src_value*pint_src_unit
#     dest_quantity = src_quantity.to(pint_dest_unit)
#     return dest_quantity.magnitude


class PyomoUnitsContainer(object):
    """Class that is used to create and contain units in Pyomo.

    This is the class that is used to create, contain, and interact with units in Pyomo.
    The module (:mod:`units`) also contains a module attribute called units_container that is
    a singleton instance of a PyomoUnitsContainer. Once a unit is created in the container,
    the unit can be used in expressions.
    For an overview of the usage of this class, see the module documentation (:mod:`.units`)

    This class is based on the "pint" module. Documentation for available units can be found
    at the following url: https://github.com/hgrecco/pint/blob/master/pint/default_en.txt

    Note: Pre-defined units can be accessed through attributes on the PyomoUnitsContainer
    class; however, these attributes are created dynamically through the __getattr__ method,
    and are not present on the class until they are requested.

    This class also supports creation of new units and even new dimensions. These are advanced
    features that should not be needed often. Check to see if the unit already exists before
    trying to create new units.
    """
    def __init__(self):
        """Create a PyomoUnitsContainer instance. """
        self._pint_ureg = pint.UnitRegistry()

    def _pint_registry(self):
        return self._pint_ureg

    def __getattr__(self, item):
        """
        Here, __getattr__ is implemented to automatically create the necessary unit if
        the attribute does not already exist.

        Parameters
        ----------
        item : str
            the name of the new field requested

        Returns
        -------
            PyomoUnit : returns a PyomoUnit corresponding to the requested attribute,
               or None if it cannot be created.

        """
        # since __getattr__ was called, we must not have this field yet
        # try to build a unit from the requested item
        pint_unit = None
        try:
            pint_unit = getattr(self._pint_ureg, item)
            if pint_unit is not None:
                unit = _PyomoUnit(pint_unit, self._pint_ureg)
                setattr(self, item, unit)
                return unit
        except pint.errors.UndefinedUnitError as exc:
            pint_unit = None

        if pint_unit is None:
            raise AttributeError('Attribute {0} not found.'.format(str(item)))

    def create_new_base_dimension(self, dimension_name, base_unit_name):
        """
        Use this method to create a new base dimension (e.g. a new dimension other than Length, Mass) for the unit manager.

        Parameters
        ----------
        dimension_name : str
           name of the new dimension (needs to be unique from other dimension names)

        base_unit_name : str
           base_unit_name: name of the base unit for this dimension

        """
        # ToDo: Error checking - if dimension already exists then we should return a useful error message.
        defn_str = str(base_unit_name) + ' = [' + str(dimension_name) + ']'
        self._pint_ureg.define(defn_str)

    def create_new_unit(self, unit_name, base_unit_name, conv_factor, conv_offset=None):
        """
        Create a new unit that is not already included in the units manager.

        Examples:
            # create a new unit of length called football field that is 1000 yards
            # defines: x (in yards) = y (in football fields) X 100.0
            >>> um.create_new_unit('football_field', 'yards', 100.0)

            # create a new unit of temperature that is half the size of a degree F
            # defines x (in K) = y (in half degF) X 10/9 + 255.3722222 K
            >>> um.create_new_unit('half_degF', 'kelvin', 10.0/9.0, 255.3722222)

        Parameters
        ----------
        unit_name : str
           name of the new unit to create
        base_unit_name : str
           name of the base unit from the same "dimension" as the new unit
        conv_factor : float
           value of the multiplicative factor needed to convert the new unit
           to the base unit
        conv_offset : float
           value of any offset between the new unit and the base unit
           Note that the units of this offset are the same as the base unit,
           and it is applied after the factor conversion
           (e.g., base_value = new_value*conv_factor + conv_offset)

        """
        if conv_offset is None:
            defn_str = '{0!s} = {1:g} * {2!s}'.format(unit_name, float(conv_factor), base_unit_name)
        else:
            defn_str = '{0!s} = {1:17.16g} * {2!s}; offset: {3:17.16g}'.format(unit_name, float(conv_factor), base_unit_name,
                                                                     float(conv_offset))
        self._pint_ureg.define(defn_str)


units_container = PyomoUnitsContainer()

