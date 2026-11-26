import hashlib
import secrets
from typing import Tuple
from app.config import settings

class ProofOfWork:
    """
    Mecanismo soberano de Prueba de Trabajo (Proof of Work - PoW):
    Impone un costo computacional mínimo a los clientes para mitigar ataques DDoS y fuerza bruta.
    Cálculo: SHA-256(nonce + solution) debe comenzar con 'difficulty' ceros (en hex).
    """

    @staticmethod
    def generate_challenge(difficulty: int = settings.POW_DIFFICULTY) -> Tuple[str, int]:
        """Genera un nonce criptográfico y el nivel de dificultad."""
        nonce = secrets.token_hex(16)
        return nonce, difficulty

    @staticmethod
    def verify_solution(nonce: str, solution: str, difficulty: int = settings.POW_DIFFICULTY) -> bool:
        """Valida que SHA-256(nonce + solution) empiece con 'difficulty' ceros hexadecimales."""
        if not nonce or not solution:
            return False
        
        target_prefix = "0" * difficulty
        data = f"{nonce}{solution}".encode("utf-8")
        computed_hash = hashlib.sha256(data).hexdigest()
        return computed_hash.startswith(target_prefix)

    @staticmethod
    def solve_for_test(nonce: str, difficulty: int = settings.POW_DIFFICULTY, max_iterations: int = 1000000) -> str:
        """Función utilitaria de resolución rápida para pruebas unitarias e integración interna."""
        target_prefix = "0" * difficulty
        for i in range(max_iterations):
            sol = hex(i)[2:]
            data = f"{nonce}{sol}".encode("utf-8")
            if hashlib.sha256(data).hexdigest().startswith(target_prefix):
                return sol
        raise RuntimeError("No se encontró solución en el rango de iteraciones")

pow_service = ProofOfWork()
