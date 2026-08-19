# =============================================================================
#  pineapple_calculator — lógica pura da calculadora do Pineapple OS (sem dependência GTK)
# =============================================================================
import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Pow: operator.pow,
}


def evaluate(expr: str) -> str:
    """Avalia uma expressão aritmética com segurança (sem eval()).

    Retorna o resultado formatado, ou "Erro" em expressões inválidas.
    """
    if not expr:
        return "0"

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](eval_node(node.operand))
        raise ValueError("expressão inválida")

    try:
        result = eval_node(ast.parse(expr, mode="eval"))
        return f"{result:g}"
    except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
        return "Erro"
