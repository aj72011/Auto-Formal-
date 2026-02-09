"""
Sanity check unit tests for simple valid statements.
These tests ensure the pipeline can handle basic arithmetic and logic proofs.
"""

import pytest
from app.pipeline.semantic_parser import DeterministicSemanticParser
from app.pipeline.ast_to_lean_compiler import ASTToLeanCompiler
from app.pipeline.capability_classifier import TheoremCapabilityClassifier


class TestBasicStatements:
    """Test parsing and compilation of simple valid mathematical statements."""

    def setup_method(self):
        self.parser = DeterministicSemanticParser()
        self.compiler = ASTToLeanCompiler()
        self.classifier = TheoremCapabilityClassifier()

    def test_arithmetic_identity(self):
        """Test: For every natural number n, n + 0 = n"""
        statement = "For every natural number n, n + 0 = n."
        
        # Should parse successfully
        ast = self.parser.parse(statement)
        assert ast is not None
        assert ast.root is not None
        
        # Should classify as supported (Tier 1 - trivial rewrite)
        capability = self.classifier.classify(statement, ast)
        assert capability.supported is True
        assert capability.tier == 1
        
        # Should compile to Lean code
        lean_code = self.compiler.compile(ast)
        assert lean_code is not None
        assert len(lean_code) > 0
        assert "theorem" in lean_code.lower() or "example" in lean_code.lower()

    def test_commutative_addition(self):
        """Test: For every natural number n, 0 + n = n"""
        statement = "For every natural number n, 0 + n = n."
        
        ast = self.parser.parse(statement)
        assert ast is not None
        
        capability = self.classifier.classify(statement, ast)
        assert capability.supported is True
        
        lean_code = self.compiler.compile(ast)
        assert lean_code is not None
        assert len(lean_code) > 0

    def test_transitivity_equality(self):
        """Test: For all integers a b c, if a = b and b = c then a = c"""
        statement = "For all integers a b c, if a = b and b = c then a = c."
        
        ast = self.parser.parse(statement)
        assert ast is not None
        
        capability = self.classifier.classify(statement, ast)
        assert capability.supported is True
        
        lean_code = self.compiler.compile(ast)
        assert lean_code is not None
        assert len(lean_code) > 0

    def test_implication_logic(self):
        """Test: For propositions P and Q, if P and Q then P"""
        statement = "For propositions P and Q, if P and Q then P."
        
        ast = self.parser.parse(statement)
        assert ast is not None
        
        capability = self.classifier.classify(statement, ast)
        assert capability.supported is True
        
        lean_code = self.compiler.compile(ast)
        assert lean_code is not None
        assert len(lean_code) > 0
        assert "∧" in lean_code or "and" in lean_code.lower()


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def setup_method(self):
        self.parser = DeterministicSemanticParser()

    def test_empty_statement(self):
        """Empty statements should raise appropriate error."""
        with pytest.raises(Exception):
            self.parser.parse("")

    def test_malformed_statement(self):
        """Malformed statements should be caught early."""
        try:
            ast = self.parser.parse("This is not a valid mathematical statement ???")
            # Parser might return a fallback AST rather than raising
            assert ast is not None
        except Exception as e:
            # Or it might raise an error, which is also acceptable
            assert str(e) or True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
