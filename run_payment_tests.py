#!/usr/bin/env python
"""
Script pour exécuter les tests de paiement
Usage: python run_payment_tests.py
"""

import subprocess
import sys
import os

def run_tests():
    """Exécute les tests de paiement"""
    print("=" * 60)
    print("Exécution des tests de paiement CinetPay")
    print("=" * 60)
    print()
    
    # Changer vers le répertoire du backend
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Commande pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "src/test/test_payments.py",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    print(f"Commande: {' '.join(cmd)}")
    print()
    
    # Exécuter les tests
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    print()
    print("=" * 60)
    if result.returncode == 0:
        print("✅ Tous les tests sont passés avec succès!")
    else:
        print("❌ Certains tests ont échoué")
    print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

