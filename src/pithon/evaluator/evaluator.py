from typing import Any, Type, TypeVar
from pithon.evaluator.envframe import EnvFrame
from pithon.syntax import (
    PiAssignment, PiBinaryOperation, PiNumber, PiBool, PiStatement, PiProgram, PiVariable,
    PiIfThenElse, PiNot, PiAnd, PiOr, PiWhile, PiNone, PiList, PiTuple, PiString,
    PiFunctionDef, PiFunctionCall, PiFor, PiBreak, PiContinue, PiIn, PiReturn, PiSubscript
)
from pithon.evaluator.envvalue import EnvValue, FunctionClosure

# Définit un type générique "T" qui représente n'importe quel sous-type de EnvValue.
# Utilisé pour des fonctions génériques de vérification/conversion de types.
T = TypeVar('T', bound=EnvValue)


# =============================================================================
# EXCEPTIONS PERSONNALISÉES
# =============================================================================

class BreakException(Exception):
    """Exception levée pour implémenter break"""
    pass


class ContinueException(Exception):
    """Exception levée pour implémenter continue"""
    pass


class ReturnException(Exception):
    """Exception levée pour implémenter return"""
    def __init__(self, value: EnvValue):
        self.value = value


# =============================================================================
# FONCTIONS BUILT-IN (PRIMITIVES)
# =============================================================================

def builtin_print(*args) -> PiNone:
    """Implémentation de `print` pour Pithon.
    1. Convertit les args Pithon en valeurs Python, puis en chaînes
    2. Joint les chaînes avec des espaces
    3. Affiche le résultat
    4. Retourne PiNone (équivalent de None en Python)
    """
    output = ' '.join(str(pi_value_to_python(arg)) for arg in args)
    print(output)
    return PiNone(value=None)


def builtin_len(obj) -> PiNumber:
    """Implémentation de `len` pour Pithon.
    Calcule la longueur des listes, tuples et chaînes.
    Lève TypeError si l'objet n'est pas compatible.
    """
    if isinstance(obj, list):
        return PiNumber(value=len(obj))
    elif isinstance(obj, tuple):
        return PiNumber(value=len(obj))
    elif isinstance(obj, PiString):
        return PiNumber(value=len(obj.value))
    else:
        raise TypeError(f"object du type '{type(obj).__name__}' a pas de len()")


def builtin_range(*args) -> list:
    """Implémentation de `range` pour Pithon.
    Convertit les arguments en entiers Python, génère une plage,
    et retourne une liste de PiNumber.
    Lève TypeError si plus de 3 arguments sont passés.
    """
    if len(args) == 1:
        start, stop, step = 0, int(pi_value_to_python(args[0])), 1
    elif len(args) == 2:
        start, stop, step = int(pi_value_to_python(args[0])), int(pi_value_to_python(args[1])), 1
    elif len(args) == 3:
        start, stop, step = int(pi_value_to_python(args[0])), int(pi_value_to_python(args[1])), int(pi_value_to_python(args[2]))
    else:
        raise TypeError(f"range attend au maximum 3 arguments, mais a reçu {len(args)}")

    return [PiNumber(value=i) for i in range(start, stop, step)]


# =============================================================================
# ENVIRONNEMENT INITIAL
# =============================================================================

def initial_env() -> EnvFrame:
    """Crée l'environnement initial avec les fonctions built-in.
    Grâce à cette fonction, dès qu'un programme Pithon démarre,
    il peut utiliser print(), len(), et range().
    """
    env = EnvFrame()
    env.insert('print', builtin_print)
    env.insert('len', builtin_len)
    env.insert('range', builtin_range)
    return env


# =============================================================================
# FONCTIONS PRINCIPALES D'ÉVALUATION
# =============================================================================

def evaluate(program: PiProgram, env: EnvFrame) -> EnvValue:
    """Évalue un programme complet (liste de statements).
    Point d'entrée principal de l'évaluateur.
    Exécute chaque instruction séquentiellement.
    """
    result = PiNone(value=None)
    for stmt in program:
        result = evaluate_statement(stmt, env)
    return result


def evaluate_statement(stmt: PiStatement, env: EnvFrame) -> EnvValue:
    """Évalue une instruction Pithon et retourne la valeur.
    Fonction de dispatch qui traite tous les types d'instructions.
    """
    if isinstance(stmt, PiAssignment):
        return evaluate_assignment(stmt, env)
    elif isinstance(stmt, PiIfThenElse):
        return evaluate_if_then_else(stmt, env)
    elif isinstance(stmt, PiWhile):
        return evaluate_while(stmt, env)
    elif isinstance(stmt, PiFor):
        return evaluate_for(stmt, env)
    elif isinstance(stmt, PiBreak):
        raise BreakException()
    elif isinstance(stmt, PiContinue):
        raise ContinueException()
    elif isinstance(stmt, PiFunctionDef):
        return evaluate_function_def(stmt, env)
    elif isinstance(stmt, PiReturn):
        return evaluate_return(stmt, env)
    else:
        return evaluate_expression(stmt, env)


def evaluate_expression(expr, env: EnvFrame) -> EnvValue:
    """Évalue une expression Pithon en une valeur concrète.
    Fonction de dispatch pour tous les types d'expressions.
    """
    if isinstance(expr, PiNumber):
        return expr
    elif isinstance(expr, PiBool):
        return expr
    elif isinstance(expr, PiNone):
        return expr
    elif isinstance(expr, PiString):
        return expr
    elif isinstance(expr, PiList):
        return [evaluate_expression(elem, env) for elem in expr.elements]
    elif isinstance(expr, PiTuple):
        return tuple(evaluate_expression(elem, env) for elem in expr.elements)
    elif isinstance(expr, PiVariable):
        return lookup(env, expr.name)
    elif isinstance(expr, PiBinaryOperation):
        return evaluate_binary_operation(expr, env)
    elif isinstance(expr, PiNot):
        operand = evaluate_expression(expr.operand, env)
        return PiBool(value=not is_truthy(operand))
    elif isinstance(expr, PiAnd):
        left = evaluate_expression(expr.left, env)
        if not is_truthy(left):
            return left
        return evaluate_expression(expr.right, env)
    elif isinstance(expr, PiOr):
        left = evaluate_expression(expr.left, env)
        if is_truthy(left):
            return left
        return evaluate_expression(expr.right, env)
    elif isinstance(expr, PiFunctionCall):
        return evaluate_function_call(expr, env)
    elif isinstance(expr, PiIn):
        element = evaluate_expression(expr.element, env)
        container = evaluate_expression(expr.container, env)
        return PiBool(value=element_in_container(element, container))
    elif isinstance(expr, PiSubscript):
        collection = evaluate_expression(expr.collection, env)
        index = evaluate_expression(expr.index, env)
        return evaluate_subscript(collection, index)
    else:
        raise ValueError(f"Expression non supportée: {type(expr).__name__}")


# =============================================================================
# ÉVALUATEURS SPÉCIALISÉS POUR CHAQUE TYPE D'INSTRUCTION
# =============================================================================

def evaluate_assignment(stmt: PiAssignment, env: EnvFrame) -> EnvValue:
    """Évalue une affectation (x = valeur)."""
    value = evaluate_expression(stmt.value, env)
    insert(env, stmt.name, value)
    return value


def evaluate_if_then_else(stmt: PiIfThenElse, env: EnvFrame) -> EnvValue:
    """Évalue une instruction if/then/else."""
    condition = evaluate_expression(stmt.condition, env)
    if is_truthy(condition):
        return evaluate(stmt.then_branch, env)
    else:
        return evaluate(stmt.else_branch, env)


def evaluate_while(stmt: PiWhile, env: EnvFrame) -> EnvValue:
    """Évalue une boucle while."""
    result = PiNone(value=None)
    while True:
        condition = evaluate_expression(stmt.condition, env)
        if not is_truthy(condition):
            break
        try:
            result = evaluate(stmt.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return result


def evaluate_for(stmt: PiFor, env: EnvFrame) -> EnvValue:
    """Évalue une boucle for."""
    result = PiNone(value=None)
    iterable = evaluate_expression(stmt.iterable, env)

    if isinstance(iterable, list):
        items = iterable
    elif isinstance(iterable, tuple):
        items = list(iterable)
    elif isinstance(iterable, PiString):
        items = [PiString(value=char) for char in iterable.value]
    else:
        raise TypeError(f"L'objet'{type(iterable).__name__}' n'est pas itérable")

    for item in items:
        insert(env, stmt.var, item)
        try:
            result = evaluate(stmt.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return result


def evaluate_function_def(stmt: PiFunctionDef, env: EnvFrame) -> EnvValue:
    """Évalue une définition de fonction."""
    closure = FunctionClosure(funcdef=stmt, closure_env=env)
    insert(env, stmt.name, closure)
    return closure


def evaluate_return(stmt: PiReturn, env: EnvFrame) -> EnvValue:
    """Évalue une instruction return."""
    value = evaluate_expression(stmt.value, env)
    raise ReturnException(value)


# =============================================================================
# ÉVALUATEURS SPÉCIALISÉS POUR LES OPÉRATIONS
# =============================================================================

def evaluate_binary_operation(expr: PiBinaryOperation, env: EnvFrame) -> EnvValue:
    """Évalue une opération binaire entre deux expressions Pithon et retourne le résultat."""
    left = evaluate_expression(expr.left, env)
    right = evaluate_expression(expr.right, env)

    if expr.operator == '+':
        if isinstance(left, PiNumber) and isinstance(right, PiNumber):
            return PiNumber(value=left.value + right.value)
        elif isinstance(left, PiString) and isinstance(right, PiString):
            return PiString(value=left.value + right.value)
        elif isinstance(left, list) and isinstance(right, list):
            return left + right
    elif expr.operator == '-':
        if isinstance(left, PiNumber) and isinstance(right, PiNumber):
            return PiNumber(value=left.value - right.value)
    elif expr.operator == '*':
        if isinstance(left, PiNumber) and isinstance(right, PiNumber):
            return PiNumber(value=left.value * right.value)
        elif isinstance(left, PiString) and isinstance(right, PiNumber):
            return PiString(value=left.value * int(right.value))
        elif isinstance(left, PiNumber) and isinstance(right, PiString):
            return PiString(value=right.value * int(left.value))
        elif isinstance(left, list) and isinstance(right, PiNumber):
            return left * int(right.value)
        elif isinstance(left, PiNumber) and isinstance(right, list):
            return right * int(left.value)
    elif expr.operator == '/':
        if isinstance(left, PiNumber) and isinstance(right, PiNumber):
            if right.value == 0:
                raise ZeroDivisionError("division par zero")
            return PiNumber(value=left.value / right.value)
    elif expr.operator == '%':
        if isinstance(left, PiNumber) and isinstance(right, PiNumber):
            return PiNumber(value=left.value % right.value)
    elif expr.operator == '==':
        return PiBool(value=values_equal(left, right))
    elif expr.operator == '!=':
        return PiBool(value=not values_equal(left, right))
    elif expr.operator == '<':
        return PiBool(value=compare_values(left, right) < 0)
    elif expr.operator == '<=':
        return PiBool(value=compare_values(left, right) <= 0)
    elif expr.operator == '>':
        return PiBool(value=compare_values(left, right) > 0)
    elif expr.operator == '>=':
        return PiBool(value=compare_values(left, right) >= 0)

    raise TypeError(f"Opérateur {expr.operator} non supporté pour les types {type(left).__name__} et {type(right).__name__}")


def evaluate_function_call(expr: PiFunctionCall, env: EnvFrame) -> EnvValue:
    """Évalue un appel de fonction."""
    func = evaluate_expression(expr.function, env)
    args = [evaluate_expression(arg, env) for arg in expr.args]

    # Vérifier si c'est une fonction primitive (built-in)
    if callable(func) and not isinstance(func, FunctionClosure):
        return func(*args)
    elif isinstance(func, FunctionClosure):
        return call_user_function(func, args)
    else:
        raise TypeError(f"'{type(func).__name__}' L'objet n'est pas appelable ")


def evaluate_subscript(collection: EnvValue, index: EnvValue) -> EnvValue:
    """Évalue un accès par index."""
    if not isinstance(index, PiNumber):
        raise TypeError("Les indices doivent être des entiers")

    idx = int(index.value)

    if isinstance(collection, list):
        try:
            return collection[idx]
        except IndexError:
            raise IndexError("Index de liste hors limites")
    elif isinstance(collection, tuple):
        try:
            return collection[idx]
        except IndexError:
            raise IndexError("Index de tuple hors limites")
    elif isinstance(collection, PiString):
        try:
            return PiString(value=collection.value[idx])
        except IndexError:
            raise IndexError("Index de chaîne hors limites")
    else:
        raise TypeError(f"'{type(collection).__name__}' L'objet de type '...' ne supporte pas l'indexation")


# =============================================================================
# FONCTIONS D'APPEL DE FONCTIONS UTILISATEUR
# =============================================================================

def call_user_function(closure: FunctionClosure, args: list[EnvValue]) -> EnvValue:
    """Appelle une fonction définie par l'utilisateur."""
    funcdef = closure.funcdef

    # Créer un nouvel environnement pour la fonction
    func_env = EnvFrame(parent=closure.closure_env)

    # Lier les arguments
    if funcdef.vararg:
        # Fonction avec *args
        regular_args = len(funcdef.arg_names)
        for i, arg_name in enumerate(funcdef.arg_names):
            if i < len(args):
                func_env.insert(arg_name, args[i])
            else:
                raise TypeError(f"Argument requis manquant: {arg_name}")

        # Reste des arguments dans vararg
        varargs = args[regular_args:] if len(args) > regular_args else []
        func_env.insert(funcdef.vararg, varargs)
    else:
        # Fonction normale
        if len(args) != len(funcdef.arg_names):
            raise TypeError(f"La fonction attend {len(funcdef.arg_names)} arguments, {len(args)} fournis")

        for arg_name, arg_value in zip(funcdef.arg_names, args):
            func_env.insert(arg_name, arg_value)

    # Exécuter le corps de la fonction
    try:
        result = evaluate(funcdef.body, func_env)
        return result if result is not None else PiNone(value=None)
    except ReturnException as ret:
        return ret.value


# =============================================================================
# FONCTIONS UTILITAIRES DE MANIPULATION D'ENVIRONNEMENT
# =============================================================================

def lookup(env: EnvFrame, name: str) -> EnvValue:
    """Recherche une variable dans l'environnement."""
    return env.lookup(name)


def insert(env: EnvFrame, name: str, value: EnvValue) -> None:
    """Insère une variable dans l'environnement."""
    env.insert(name, value)


# =============================================================================
# FONCTIONS UTILITAIRES DE CONVERSION ET COMPARAISON
# =============================================================================

def pi_value_to_python(value: EnvValue) -> Any:
    """Convertit une valeur Pithon (PiNumber, PiString...) en valeur Python native."""
    if isinstance(value, PiNumber):
        return value.value
    elif isinstance(value, PiBool):
        return value.value
    elif isinstance(value, PiNone):
        return None
    elif isinstance(value, PiString):
        return value.value
    elif isinstance(value, list):
        return [pi_value_to_python(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(pi_value_to_python(item) for item in value)
    else:
        return value


def is_truthy(value: EnvValue) -> bool:
    """Détermine si une valeur est vraie en contexte booléen."""
    if isinstance(value, PiBool):
        return value.value
    elif isinstance(value, PiNumber):
        return value.value != 0
    elif isinstance(value, PiNone):
        return False
    elif isinstance(value, PiString):
        return len(value.value) > 0
    elif isinstance(value, list):
        return len(value) > 0
    elif isinstance(value, tuple):
        return len(value) > 0
    else:
        return True


def values_equal(left: EnvValue, right: EnvValue) -> bool:
    """Compare deux valeurs pour l'égalité (==).
    Retourne True seulement si :
    - Même type ET même valeur (pour nombres, booléens, chaînes).
    - Les deux sont PiNone.
    - Listes/tuples de mêmes longueurs avec éléments égaux.
    Retourne False pour des types différents ou valeurs inégales.
    """
    if isinstance(left, PiNumber) and isinstance(right, PiNumber):
        return left.value == right.value
    elif isinstance(left, PiBool) and isinstance(right, PiBool):
        return left.value == right.value
    elif isinstance(left, PiNone) and isinstance(right, PiNone):
        return True
    elif isinstance(left, PiString) and isinstance(right, PiString):
        return left.value == right.value
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(values_equal(a, b) for a, b in zip(left, right))
    elif isinstance(left, tuple) and isinstance(right, tuple):
        if len(left) != len(right):
            return False
        return all(values_equal(a, b) for a, b in zip(left, right))
    else:
        return False


def compare_values(left: EnvValue, right: EnvValue) -> int:
    """Compare deux valeurs Pithon et retourne :
        -1 si left < right,
        0 si left == right,
        1 si left > right.
    Supporte seulement les nombres et chaînes.
    Lève TypeError pour des types incomparables.
    """
    if isinstance(left, PiNumber) and isinstance(right, PiNumber):
        if left.value < right.value:
            return -1
        elif left.value > right.value:
            return 1
        else:
            return 0
    elif isinstance(left, PiString) and isinstance(right, PiString):
        if left.value < right.value:
            return -1
        elif left.value > right.value:
            return 1
        else:
            return 0
    else:
        raise TypeError(f"Comparaison non supportée entre {type(left).__name__} et {type(right).__name__}")


def element_in_container(element: EnvValue, container: EnvValue) -> bool:
    """Vérifie si un élément Pithon est présent dans un conteneur (liste/tuple/chaîne).
    Pour les listes/tuples : utilise une comparaison récursive via values_equal.
    Pour les chaînes : vérifie si la sous-chaîne est incluse (uniquement entre PiString).
    Retourne False pour des types incompatibles ou si l'élément est absent.
    """
    if isinstance(container, list):
        return any(values_equal(element, item) for item in container)
    elif isinstance(container, tuple):
        return any(values_equal(element, item) for item in container)
    elif isinstance(container, PiString):
        if isinstance(element, PiString):
            return element.value in container.value
    return False


# =============================================================================
# FONCTIONS UTILITAIRES DE VÉRIFICATION DE TYPES
# =============================================================================

def check_type(value: EnvValue, expected_type: Type[T]) -> bool:
    """Vérifie si `value` est du type `expected_type` (un sous-type de EnvValue)."""
    return isinstance(value, expected_type)


def cast_to_type(value: EnvValue, target_type: Type[T]) -> T:
    """Convertit `value` vers `target_type` (un sous-type de EnvValue).
    Lève TypeError si la conversion est impossible.
    """
    if isinstance(value, target_type):
        return value
    else:
        raise TypeError(f"Conversion impossible de {type(value).__name__} vers {target_type.__name__}")


def is_instance(value: EnvValue, type_name: str) -> bool:
    """Vérifie si `value` est une instance du type spécifié par `type_name`.
    Supporte les types prédéfinis de Pithon (PiNumber, PiBool, etc.).
    Retourne True si c'est le cas, False sinon.
    """
    type_map = {
        'number': PiNumber,
        'bool': PiBool,
        'none': PiNone,
        'string': PiString,
        'list': list,
        'tuple': tuple,
        'function': FunctionClosure
    }
    return isinstance(value, type_map.get(type_name, EnvValue))