"""Unit tests for roadmap prioritization service"""
import pytest
from datetime import datetime
from app.api.schemas.roadmap import (
    ScoringWeights, InitiativeScoring, CompositeScore,
    PrioritizationRequest, PrioritizationResponse
)
from app.services.roadmap_prioritization import RoadmapPrioritizationService


class TestScoringWeights:
    """Test scoring weights validation and configuration"""
    
    def test_default_weights_sum_to_one(self):
        """Test that default weights sum to 1.0"""
        weights = ScoringWeights()
        total = weights.impact + weights.risk + weights.effort + weights.compliance + weights.dependency_penalty
        assert abs(total - 1.0) < 0.01
    
    def test_valid_custom_weights(self):
        """Test creating valid custom weights"""
        weights = ScoringWeights(
            impact=0.4,
            risk=0.3,
            effort=0.15,
            compliance=0.1,
            dependency_penalty=0.05
        )
        assert weights.impact == 0.4
        assert weights.risk == 0.3
    
    def test_invalid_weights_sum(self):
        """Test that invalid weight sums are rejected"""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ScoringWeights(
                impact=0.5,
                risk=0.3,
                effort=0.3,
                compliance=0.1,
                dependency_penalty=0.1
            )
    
    def test_weights_bounds(self):
        """Test that weights are bounded between 0 and 1"""
        with pytest.raises(ValueError):
            ScoringWeights(impact=-0.1, risk=0.3, effort=0.3, compliance=0.3, dependency_penalty=0.2)
        
        with pytest.raises(ValueError):
            ScoringWeights(impact=1.1, risk=0.0, effort=0.0, compliance=0.0, dependency_penalty=-0.1)


class TestInitiativeScoring:
    """Test initiative scoring components"""
    
    def test_valid_scoring_components(self):
        """Test creating valid scoring components"""
        scoring = InitiativeScoring(
            impact_score=8.5,
            risk_score=7.0,
            effort_score=4.0,
            compliance_score=9.0,
            dependency_count=2
        )
        assert scoring.impact_score == 8.5
        assert scoring.dependency_count == 2
    
    def test_scoring_bounds(self):
        """Test that scoring components are properly bounded"""
        with pytest.raises(ValueError):
            InitiativeScoring(
                impact_score=11.0,  # > 10
                risk_score=7.0,
                effort_score=4.0,
                compliance_score=9.0,
                dependency_count=2
            )
        
        with pytest.raises(ValueError):
            InitiativeScoring(
                impact_score=8.0,
                risk_score=7.0,
                effort_score=0.5,  # < 1
                compliance_score=9.0,
                dependency_count=2
            )


class TestRoadmapPrioritizationService:
    """Test roadmap prioritization service functionality"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapPrioritizationService()
    
    def test_calculate_composite_score_default_weights(self):
        """Test composite score calculation with default weights"""
        scoring = InitiativeScoring(
            impact_score=8.0,
            risk_score=6.0,
            effort_score=4.0,  # Inverted to 6.0 in calculation
            compliance_score=7.0,
            dependency_count=1
        )
        
        result = self.service.calculate_composite_score(scoring)
        
        # Verify calculation
        expected = (8.0 * 0.3) + (6.0 * 0.25) + (6.0 * 0.2) + (7.0 * 0.15) - (1 * 0.1)
        assert abs(result.total_score - expected) < 0.01
        assert result.weighted_impact == 8.0 * 0.3
        assert result.weighted_effort == 6.0 * 0.2  # 10 - 4 = 6
        assert result.dependency_penalty == 1 * 0.1
    
    def test_calculate_composite_score_custom_weights(self):
        """Test composite score calculation with custom weights"""
        scoring = InitiativeScoring(
            impact_score=9.0,
            risk_score=5.0,
            effort_score=3.0,
            compliance_score=8.0,
            dependency_count=0
        )
        
        custom_weights = ScoringWeights(
            impact=0.5,
            risk=0.2,
            effort=0.15,
            compliance=0.1,
            dependency_penalty=0.05
        )
        
        result = self.service.calculate_composite_score(scoring, custom_weights)
        
        expected = (9.0 * 0.5) + (5.0 * 0.2) + (7.0 * 0.15) + (8.0 * 0.1) - (0 * 0.05)
        assert abs(result.total_score - expected) < 0.01
        assert result.weights_used == custom_weights
    
    def test_score_bounds_enforcement(self):
        """Test that composite scores are bounded between 0 and 10"""
        # Test upper bound
        high_scoring = InitiativeScoring(
            impact_score=10.0,
            risk_score=10.0,
            effort_score=1.0,  # Minimum effort
            compliance_score=10.0,
            dependency_count=0
        )
        
        result = self.service.calculate_composite_score(high_scoring)
        assert result.total_score <= 10.0
        
        # Test lower bound with high effort and dependencies
        low_scoring = InitiativeScoring(
            impact_score=0.0,
            risk_score=0.0,
            effort_score=10.0,  # Maximum effort
            compliance_score=0.0,
            dependency_count=50  # Many dependencies
        )
        
        result = self.service.calculate_composite_score(low_scoring)
        assert result.total_score >= 0.0
    
    def test_prioritize_initiatives(self):
        """Test prioritizing multiple initiatives"""
        initiatives = [
            InitiativeScoring(
                impact_score=8.0, risk_score=6.0, effort_score=4.0,
                compliance_score=7.0, dependency_count=1
            ),
            InitiativeScoring(
                impact_score=9.0, risk_score=8.0, effort_score=3.0,
                compliance_score=8.0, dependency_count=0
            ),
            InitiativeScoring(
                impact_score=5.0, risk_score=4.0, effort_score=8.0,
                compliance_score=6.0, dependency_count=3
            )
        ]
        
        request = PrioritizationRequest(
            initiatives=initiatives,
            initiative_ids=["init-1", "init-2", "init-3"]
        )
        
        response = self.service.prioritize_initiatives(request)
        
        assert len(response.prioritized_initiatives) == 3
        
        # Verify sorting (highest score first)
        scores = [init.composite_score.total_score for init in response.prioritized_initiatives]
        assert scores == sorted(scores, reverse=True)
        
        # Verify priority ranks
        for i, initiative in enumerate(response.prioritized_initiatives):
            assert initiative.priority_rank == i + 1
    
    def test_update_weights(self):
        """Test updating weights configuration"""
        new_weights = ScoringWeights(
            impact=0.4,
            risk=0.3,
            effort=0.15,
            compliance=0.1,
            dependency_penalty=0.05
        )
        
        self.service.update_weights(new_weights, "Test weights", "test-user")
        
        current_weights, description, updated_at, updated_by = self.service.get_current_weights()
        
        assert current_weights == new_weights
        assert description == "Test weights"
        assert updated_by == "test-user"
        assert isinstance(updated_at, datetime)
    
    def test_reset_weights_to_default(self):
        """Test resetting weights to default configuration"""
        # First update to custom weights
        custom_weights = ScoringWeights(
            impact=0.4,
            risk=0.3,
            effort=0.15,
            compliance=0.1,
            dependency_penalty=0.05
        )
        self.service.update_weights(custom_weights)
        
        # Reset to defaults
        self.service.reset_weights_to_default("test-user")
        
        current_weights, description, updated_at, updated_by = self.service.get_current_weights()
        default_weights = self.service.get_default_weights()
        
        assert current_weights == default_weights
        assert "default" in description.lower()
        assert updated_by == "test-user"
    
    def test_get_algorithm_schema(self):
        """Test retrieving algorithm schema"""
        schema = self.service.get_algorithm_schema()
        
        assert "algorithm" in schema
        assert "components" in schema
        assert "weights" in schema
        assert "constraints" in schema
        
        assert schema["algorithm"]["version"] == "v2.0"
        assert schema["constraints"]["weights_sum"] == 1.0
        assert schema["constraints"]["score_range"] == [0.0, 10.0]


class TestPrioritizationRequest:
    """Test prioritization request validation"""
    
    def test_valid_request(self):
        """Test creating a valid prioritization request"""
        initiatives = [
            InitiativeScoring(
                impact_score=8.0, risk_score=6.0, effort_score=4.0,
                compliance_score=7.0, dependency_count=1
            )
        ]
        
        request = PrioritizationRequest(
            initiatives=initiatives,
            initiative_ids=["init-1"]
        )
        
        assert len(request.initiatives) == 1
        assert request.initiative_ids == ["init-1"]
    
    def test_mismatched_lengths(self):
        """Test that service validates matching lengths"""
        service = RoadmapPrioritizationService()
        
        initiatives = [
            InitiativeScoring(
                impact_score=8.0, risk_score=6.0, effort_score=4.0,
                compliance_score=7.0, dependency_count=1
            )
        ]
        
        request = PrioritizationRequest(
            initiatives=initiatives,
            initiative_ids=["init-1", "init-2"]  # Mismatched length
        )
        
        with pytest.raises(ValueError, match="Number of initiatives must match"):
            service.prioritize_initiatives(request)


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapPrioritizationService()
    
    def test_cybersecurity_initiatives_prioritization(self):
        """Test prioritizing cybersecurity initiatives"""
        initiatives = [
            # High impact, low effort security initiative
            InitiativeScoring(
                impact_score=9.0,  # High security impact
                risk_score=8.0,    # High risk mitigation
                effort_score=3.0,  # Low effort
                compliance_score=9.0,  # High compliance
                dependency_count=1
            ),
            # Medium impact, high effort infrastructure upgrade
            InitiativeScoring(
                impact_score=6.0,
                risk_score=7.0,
                effort_score=8.0,  # High effort
                compliance_score=5.0,
                dependency_count=4
            ),
            # Low impact, quick win
            InitiativeScoring(
                impact_score=4.0,
                risk_score=3.0,
                effort_score=2.0,  # Very low effort
                compliance_score=6.0,
                dependency_count=0
            )
        ]
        
        request = PrioritizationRequest(
            initiatives=initiatives,
            initiative_ids=["sec-001", "infra-002", "quick-003"]
        )
        
        response = self.service.prioritize_initiatives(request)
        
        # High impact/low effort security should be first
        assert response.prioritized_initiatives[0].initiative_id == "sec-001"
        assert response.prioritized_initiatives[0].priority_rank == 1
        
        # Verify all initiatives have valid scores
        for initiative in response.prioritized_initiatives:
            assert 0.0 <= initiative.composite_score.total_score <= 10.0
            assert initiative.priority_rank is not None