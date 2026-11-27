from app.core.pow import pow_service

def test_pow_generation_and_verification():
    nonce, difficulty = pow_service.generate_challenge(difficulty=2)
    assert nonce is not None
    assert len(nonce) == 32
    assert difficulty == 2

    # Resolver reto
    solution = pow_service.solve_for_test(nonce, difficulty=difficulty)
    assert solution is not None

    # Validar solución correcta
    assert pow_service.verify_solution(nonce, solution, difficulty=difficulty) is True

    # Validar solución falsa
    fake_solution = "solucion_invalida_12345"
    assert pow_service.verify_solution(nonce, fake_solution, difficulty=difficulty) is False
