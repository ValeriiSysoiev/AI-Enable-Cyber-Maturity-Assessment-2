"""Unit tests for roadmap resource profile service"""
import pytest
from datetime import datetime, date, timedelta
from app.api.schemas.resource_profile import (
    SkillLevel, RoleType, WavePhase, SkillRequirement, RoleProfile,
    WaveResourceAllocation, ResourcePlanningRequest, CSVExportRequest,
    GanttChartRequest, WaveOverlayRequest
)
from app.services.roadmap_resource_profile import RoadmapResourceProfileService


class TestSkillRequirement:
    """Test skill requirement validation"""
    
    def test_valid_skill_requirement(self):
        """Test creating valid skill requirement"""
        skill = SkillRequirement(
            skill_name="Cloud Security Architecture",
            skill_category="technical",
            required_level=SkillLevel.ADVANCED,
            critical=True,
            description="Advanced cloud security design skills"
        )
        assert skill.skill_name == "Cloud Security Architecture"
        assert skill.required_level == SkillLevel.ADVANCED
        assert skill.critical is True
    
    def test_skill_levels(self):
        """Test all skill levels are valid"""
        for level in [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT]:
            skill = SkillRequirement(
                skill_name="Test Skill",
                skill_category="technical",
                required_level=level
            )
            assert skill.required_level == level


class TestRoleProfile:
    """Test role profile validation"""
    
    def test_valid_role_profile(self):
        """Test creating valid role profile"""
        skills = [
            SkillRequirement(
                skill_name="Azure Security",
                skill_category="technical", 
                required_level=SkillLevel.ADVANCED
            )
        ]
        
        role = RoleProfile(
            role_type=RoleType.SECURITY_ARCHITECT,
            role_title="Senior Security Architect",
            fte_required=1.0,
            duration_weeks=12,
            skill_requirements=skills,
            seniority_level="senior",
            remote_eligible=True
        )
        
        assert role.role_type == RoleType.SECURITY_ARCHITECT
        assert role.fte_required == 1.0
        assert len(role.skill_requirements) == 1
    
    def test_fte_bounds(self):
        """Test FTE bounds validation"""
        with pytest.raises(ValueError):
            RoleProfile(
                role_type=RoleType.SECURITY_ENGINEER,
                role_title="Test Role",
                fte_required=2.5,  # > 2.0 limit
                duration_weeks=8,
                skill_requirements=[],
                seniority_level="mid"
            )
        
        with pytest.raises(ValueError):
            RoleProfile(
                role_type=RoleType.SECURITY_ENGINEER,
                role_title="Test Role",
                fte_required=-0.5,  # < 0 limit
                duration_weeks=8,
                skill_requirements=[],
                seniority_level="mid"
            )


class TestWaveResourceAllocation:
    """Test wave resource allocation validation"""
    
    def test_valid_wave_allocation(self):
        """Test creating valid wave allocation"""
        start_date = date.today()
        end_date = start_date + timedelta(weeks=12)
        
        role = RoleProfile(
            role_type=RoleType.SECURITY_ENGINEER,
            role_title="Security Engineer",
            fte_required=1.0,
            duration_weeks=12,
            skill_requirements=[],
            seniority_level="mid"
        )
        
        wave = WaveResourceAllocation(
            wave=WavePhase.WAVE_1,
            wave_name="Wave 1: Planning",
            start_date=start_date,
            end_date=end_date,
            role_allocations=[role],
            critical_path=True
        )
        
        assert wave.wave == WavePhase.WAVE_1
        assert wave.end_date > wave.start_date
        assert len(wave.role_allocations) == 1
    
    def test_date_validation(self):
        """Test that end_date must be after start_date"""
        start_date = date.today()
        end_date = start_date - timedelta(days=1)  # Invalid: before start
        
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            WaveResourceAllocation(
                wave=WavePhase.WAVE_1,
                wave_name="Invalid Wave",
                start_date=start_date,
                end_date=end_date,
                role_allocations=[]
            )


class TestRoadmapResourceProfileService:
    """Test roadmap resource profile service functionality"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapResourceProfileService()
    
    def test_initialization(self):
        """Test service initialization"""
        assert len(self.service._skill_catalog) > 0
        assert len(self.service._role_templates) > 0
        assert "technical_skills" in self.service._skill_catalog
        assert RoleType.SECURITY_ARCHITECT in self.service._role_templates
    
    def test_generate_wave_allocations_basic(self):
        """Test basic wave allocation generation"""
        initiative_data = {
            'initiative_id': 'test-001',
            'name': 'Test Security Initiative',
            'duration_weeks': 24,
            't_shirt_size': 'M',
            'type': 'security_implementation'
        }
        
        waves = self.service.generate_wave_allocations(initiative_data, wave_duration_weeks=12)
        
        # Should generate 2 waves for 24-week initiative
        assert len(waves) == 2
        assert waves[0].wave == WavePhase.WAVE_1
        assert waves[1].wave == WavePhase.WAVE_2
        
        # Each wave should have role allocations
        for wave in waves:
            assert len(wave.role_allocations) > 0
            assert wave.total_fte is not None
            assert wave.estimated_cost is not None
    
    def test_generate_wave_allocations_different_sizes(self):
        """Test wave generation for different T-shirt sizes"""
        base_initiative = {
            'initiative_id': 'size-test',
            'name': 'Size Test',
            'duration_weeks': 12,
            'type': 'security_implementation'
        }
        
        # Test different sizes
        sizes = ['S', 'M', 'L', 'XL']
        size_results = {}
        
        for size in sizes:
            initiative = {**base_initiative, 't_shirt_size': size}
            waves = self.service.generate_wave_allocations(initiative)
            
            total_fte = sum(wave.total_fte or 0 for wave in waves)
            size_results[size] = total_fte
        
        # Larger sizes should require more FTE
        assert size_results['S'] < size_results['M']
        assert size_results['M'] < size_results['L']
        assert size_results['L'] < size_results['XL']
    
    def test_calculate_resource_profile(self):
        """Test complete resource profile calculation"""
        initiatives = [
            {
                'initiative_id': 'sec-001',
                'name': 'Security Infrastructure Upgrade',
                'duration_weeks': 24,
                't_shirt_size': 'L',
                'type': 'infrastructure'
            },
            {
                'initiative_id': 'comp-001',
                'name': 'SOC 2 Compliance',
                'duration_weeks': 16,
                't_shirt_size': 'M',
                'type': 'compliance'
            }
        ]
        
        request = ResourcePlanningRequest(
            initiatives=initiatives,
            planning_horizon_weeks=52,
            target_start_date=date.today(),
            wave_duration_weeks=12
        )
        
        response = self.service.calculate_resource_profile(request)
        
        # Verify response structure
        assert len(response.initiative_profiles) == 2
        assert "total_initiatives" in response.planning_summary
        assert response.planning_summary["total_initiatives"] == 2
        
        # Verify each initiative profile
        for profile in response.initiative_profiles:
            assert profile.initiative_id in ['sec-001', 'comp-001']
            assert len(profile.wave_allocations) > 0
            assert profile.total_fte_demand > 0
            assert profile.total_estimated_cost > 0
            assert isinstance(profile.skill_summary, dict)
        
        # Verify skill demand forecast
        assert len(response.skill_demand_forecast) > 0
        
        # Verify wave overlay data
        assert len(response.wave_overlay) > 0
    
    def test_skill_summary_calculation(self):
        """Test skill summary calculation"""
        # Create test wave with specific roles
        role1 = RoleProfile(
            role_type=RoleType.SECURITY_ARCHITECT,
            role_title="Security Architect",
            fte_required=1.0,
            duration_weeks=12,
            skill_requirements=[
                SkillRequirement(skill_name="Cloud Security", skill_category="technical", required_level=SkillLevel.EXPERT),
                SkillRequirement(skill_name="Risk Assessment", skill_category="compliance", required_level=SkillLevel.ADVANCED)
            ],
            seniority_level="senior"
        )
        
        role2 = RoleProfile(
            role_type=RoleType.COMPLIANCE_ANALYST,
            role_title="Compliance Analyst",
            fte_required=0.5,
            duration_weeks=16,
            skill_requirements=[
                SkillRequirement(skill_name="SOC 2", skill_category="compliance", required_level=SkillLevel.EXPERT),
                SkillRequirement(skill_name="Audit Skills", skill_category="compliance", required_level=SkillLevel.ADVANCED)
            ],
            seniority_level="mid"
        )
        
        wave = WaveResourceAllocation(
            wave=WavePhase.WAVE_1,
            wave_name="Test Wave",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=12),
            role_allocations=[role1, role2]
        )
        
        skill_summary = self.service._calculate_skill_summary([wave])
        
        # Should have technical and compliance skills
        assert "technical" in skill_summary
        assert "compliance" in skill_summary
        assert skill_summary["technical"] == 1  # One technical skill from role1
        assert skill_summary["compliance"] == 3  # Three compliance skills total
    
    def test_resource_conflict_identification(self):
        """Test resource conflict identification"""
        # Create profiles with overlapping high-demand periods
        profile1_waves = [
            WaveResourceAllocation(
                wave=WavePhase.WAVE_1,
                wave_name="Initiative 1 - Wave 1",
                start_date=date.today(),
                end_date=date.today() + timedelta(weeks=12),
                role_allocations=[],
                total_fte=3.0
            )
        ]
        
        profile2_waves = [
            WaveResourceAllocation(
                wave=WavePhase.WAVE_1,
                wave_name="Initiative 2 - Wave 1", 
                start_date=date.today(),
                end_date=date.today() + timedelta(weeks=12),
                role_allocations=[],
                total_fte=4.0
            )
        ]
        
        from app.api.schemas.resource_profile import InitiativeResourceProfile
        
        profiles = [
            InitiativeResourceProfile(
                initiative_id="init-1",
                initiative_name="Initiative 1",
                total_duration_weeks=12,
                wave_allocations=profile1_waves,
                skill_summary={},
                total_fte_demand=3.0,
                total_estimated_cost=100000
            ),
            InitiativeResourceProfile(
                initiative_id="init-2", 
                initiative_name="Initiative 2",
                total_duration_weeks=12,
                wave_allocations=profile2_waves,
                skill_summary={},
                total_fte_demand=4.0,
                total_estimated_cost=150000
            )
        ]
        
        conflicts = self.service._identify_resource_conflicts(profiles)
        
        # Should identify high resource demand conflict
        assert len(conflicts) > 0
        conflict = conflicts[0]
        assert conflict["conflict_type"] == "high_resource_demand"
        assert conflict["total_fte_demand"] == 7.0
        assert len(conflict["affected_initiatives"]) == 2
    
    def test_export_to_csv_summary(self):
        """Test CSV export in summary format"""
        # Create test profile
        from app.api.schemas.resource_profile import InitiativeResourceProfile
        
        profile = InitiativeResourceProfile(
            initiative_id="csv-test-001",
            initiative_name="CSV Test Initiative",
            total_duration_weeks=24,
            wave_allocations=[],
            skill_summary={"technical": 3, "compliance": 2},
            total_fte_demand=5.5,
            total_estimated_cost=275000,
            resource_constraints=["High demand for security architects"]
        )
        
        request = CSVExportRequest(
            export_format="summary",
            include_skills=True,
            include_costs=True
        )
        
        response = self.service.export_to_csv([profile], request)
        
        # Verify CSV response
        assert response.export_format == "summary"
        assert response.record_count > 0
        assert "csv-test-001" in response.csv_content
        assert "CSV Test Initiative" in response.csv_content
        assert "275000" in response.csv_content
    
    def test_export_to_csv_detailed(self):
        """Test CSV export in detailed format"""
        # Create test profile with wave data
        role = RoleProfile(
            role_type=RoleType.SECURITY_ENGINEER,
            role_title="Security Engineer",
            fte_required=1.0,
            duration_weeks=12,
            skill_requirements=[
                SkillRequirement(skill_name="Network Security", skill_category="technical", required_level=SkillLevel.ADVANCED)
            ],
            seniority_level="mid"
        )
        
        wave = WaveResourceAllocation(
            wave=WavePhase.WAVE_1,
            wave_name="Wave 1: Implementation",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=12),
            role_allocations=[role],
            estimated_cost=120000
        )
        
        from app.api.schemas.resource_profile import InitiativeResourceProfile
        
        profile = InitiativeResourceProfile(
            initiative_id="detailed-test-001",
            initiative_name="Detailed Test",
            total_duration_weeks=12,
            wave_allocations=[wave],
            skill_summary={"technical": 1},
            total_fte_demand=1.0,
            total_estimated_cost=120000
        )
        
        request = CSVExportRequest(
            export_format="detailed",
            include_skills=True,
            include_costs=True
        )
        
        response = self.service.export_to_csv([profile], request)
        
        # Verify detailed CSV content
        assert "security_engineer" in response.csv_content
        assert "Network Security" in response.csv_content
        assert "120000" in response.csv_content
        assert "wave_1" in response.csv_content
    
    def test_generate_gantt_chart_data(self):
        """Test Gantt chart data generation"""
        # Create test profile
        role = RoleProfile(
            role_type=RoleType.PROJECT_MANAGER,
            role_title="Project Manager",
            fte_required=0.5,
            duration_weeks=12,
            skill_requirements=[],
            seniority_level="senior"
        )
        
        wave = WaveResourceAllocation(
            wave=WavePhase.WAVE_1,
            wave_name="Wave 1: Planning",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=12),
            role_allocations=[role],
            critical_path=True
        )
        
        from app.api.schemas.resource_profile import InitiativeResourceProfile
        
        profile = InitiativeResourceProfile(
            initiative_id="gantt-test-001",
            initiative_name="Gantt Test Initiative",
            total_duration_weeks=12,
            wave_allocations=[wave],
            skill_summary={},
            total_fte_demand=0.5,
            total_estimated_cost=60000
        )
        
        request = GanttChartRequest(
            include_resource_overlay=True,
            include_skill_heatmap=False,
            timeline_granularity="weekly"
        )
        
        response = self.service.generate_gantt_chart_data([profile], request)
        
        # Verify Gantt response
        assert len(response.tasks) >= 2  # Initiative + wave tasks
        assert response.timeline_start <= response.timeline_end
        assert len(response.milestone_dates) > 0
        assert len(response.critical_path) > 0
        
        # Verify task structure
        initiative_task = next(task for task in response.tasks if task.task_id.startswith("init_"))
        assert initiative_task.task_name == "Gantt Test Initiative"
        assert initiative_task.critical_path is True
        
        wave_task = next(task for task in response.tasks if task.task_id.startswith("wave_"))
        assert wave_task.wave == WavePhase.WAVE_1
        assert len(wave_task.resource_allocation) > 0
    
    def test_generate_wave_overlay(self):
        """Test wave overlay generation"""
        request = WaveOverlayRequest(
            planning_horizon_weeks=60,
            include_resource_utilization=True,
            aggregate_by="role"
        )
        
        response = self.service.generate_wave_overlay(request)
        
        # Verify overlay response
        assert len(response.wave_periods) == 5  # 5 standard waves
        assert "resource_utilization" in response.resource_utilization
        assert "skill_demand_trends" in response.skill_demand_trends
        assert "cost_distribution" in response.cost_distribution
        assert len(response.recommendations) > 0
        
        # Verify wave period structure
        for wave_period in response.wave_periods:
            assert "wave" in wave_period
            assert "start_date" in wave_period
            assert "end_date" in wave_period
            assert "duration_weeks" in wave_period
    
    def test_get_configuration_info(self):
        """Test configuration information retrieval"""
        config = self.service.get_configuration_info()
        
        # Verify configuration structure
        assert len(config.available_roles) > 0
        assert len(config.skill_mapping.available_skills) > 0
        assert len(config.skill_mapping.skill_categories) > 0
        assert config.default_wave_duration == 12
        assert config.max_planning_horizon == 156  # 3 years
        
        # Verify role templates
        assert any(role["role_type"] == "security_architect" for role in config.available_roles)
        assert any(role["role_type"] == "security_engineer" for role in config.available_roles)
        
        # Verify skill mapping
        assert "technical" in config.skill_mapping.skill_categories
        assert "compliance" in config.skill_mapping.skill_categories
        assert RoleType.SECURITY_ARCHITECT in config.skill_mapping.role_skill_matrix
        
        # Verify proficiency definitions
        assert SkillLevel.BEGINNER in config.skill_mapping.proficiency_definitions
        assert SkillLevel.EXPERT in config.skill_mapping.proficiency_definitions


class TestResourcePlanningRequest:
    """Test resource planning request validation"""
    
    def test_valid_request(self):
        """Test creating valid resource planning request"""
        initiatives = [
            {
                'initiative_id': 'test-001',
                'name': 'Test Initiative',
                'duration_weeks': 24
            }
        ]
        
        request = ResourcePlanningRequest(
            initiatives=initiatives,
            planning_horizon_weeks=52,
            target_start_date=date.today(),
            wave_duration_weeks=12
        )
        
        assert len(request.initiatives) == 1
        assert request.planning_horizon_weeks == 52
        assert request.wave_duration_weeks == 12
    
    def test_planning_horizon_bounds(self):
        """Test planning horizon bounds validation"""
        with pytest.raises(ValueError):
            ResourcePlanningRequest(
                initiatives=[],
                planning_horizon_weeks=2,  # < 4 minimum
                target_start_date=date.today(),
                wave_duration_weeks=12
            )
        
        with pytest.raises(ValueError):
            ResourcePlanningRequest(
                initiatives=[],
                planning_horizon_weeks=200,  # > 156 maximum
                target_start_date=date.today(),
                wave_duration_weeks=12
            )
    
    def test_wave_duration_bounds(self):
        """Test wave duration bounds validation"""
        with pytest.raises(ValueError):
            ResourcePlanningRequest(
                initiatives=[],
                planning_horizon_weeks=52,
                target_start_date=date.today(),
                wave_duration_weeks=2  # < 4 minimum
            )
        
        with pytest.raises(ValueError):
            ResourcePlanningRequest(
                initiatives=[],
                planning_horizon_weeks=52,
                target_start_date=date.today(),
                wave_duration_weeks=30  # > 26 maximum
            )


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapResourceProfileService()
    
    def test_cybersecurity_transformation_resource_planning(self):
        """Test resource planning for cybersecurity transformation"""
        initiatives = [
            # Large infrastructure security initiative
            {
                'initiative_id': 'infra-001',
                'name': 'Cloud Security Infrastructure',
                'duration_weeks': 36,
                't_shirt_size': 'L',
                'type': 'infrastructure',
                'priority': 'high'
            },
            # Medium compliance initiative
            {
                'initiative_id': 'comp-001',
                'name': 'SOC 2 Type II Certification',
                'duration_weeks': 24,
                't_shirt_size': 'M',
                'type': 'compliance',
                'priority': 'high'
            },
            # Small security training initiative
            {
                'initiative_id': 'train-001',
                'name': 'Security Awareness Training',
                'duration_weeks': 12,
                't_shirt_size': 'S',
                'type': 'training',
                'priority': 'medium'
            }
        ]
        
        request = ResourcePlanningRequest(
            initiatives=initiatives,
            planning_horizon_weeks=52,
            target_start_date=date.today(),
            wave_duration_weeks=12,
            skill_constraints={
                "security_architect": 2,
                "security_engineer": 4,
                "compliance_analyst": 2
            }
        )
        
        response = self.service.calculate_resource_profile(request)
        
        # Verify comprehensive planning
        assert len(response.initiative_profiles) == 3
        
        # Large initiative should have highest resource demand
        infra_profile = next(p for p in response.initiative_profiles if p.initiative_id == 'infra-001')
        train_profile = next(p for p in response.initiative_profiles if p.initiative_id == 'train-001')
        
        assert infra_profile.total_fte_demand > train_profile.total_fte_demand
        assert infra_profile.total_estimated_cost > train_profile.total_estimated_cost
        
        # Should identify resource constraints if any
        if response.resource_conflicts:
            assert any("capacity" in conflict["recommendation"].lower() for conflict in response.resource_conflicts)
        
        # Skill demand should include technical and compliance skills
        skill_categories = set()
        for period_skills in response.skill_demand_forecast.values():
            for skill_data in period_skills:
                skill_categories.add(skill_data["skill_category"])
        
        assert "technical" in skill_categories
        assert "compliance" in skill_categories
    
    def test_multi_wave_resource_coordination(self):
        """Test resource coordination across multiple waves"""
        # Create initiative that spans multiple waves
        initiative = {
            'initiative_id': 'multi-wave-001',
            'name': 'Enterprise Security Transformation',
            'duration_weeks': 48,  # 4 waves at 12 weeks each
            't_shirt_size': 'XL',
            'type': 'transformation'
        }
        
        request = ResourcePlanningRequest(
            initiatives=[initiative],
            planning_horizon_weeks=52,
            target_start_date=date.today(),
            wave_duration_weeks=12
        )
        
        response = self.service.calculate_resource_profile(request)
        
        profile = response.initiative_profiles[0]
        
        # Should have 4 waves
        assert len(profile.wave_allocations) == 4
        
        # Verify wave progression
        wave_names = [wave.wave.value for wave in profile.wave_allocations]
        assert "wave_1" in wave_names
        assert "wave_4" in wave_names
        
        # Early waves should be marked as critical path
        early_waves = [wave for wave in profile.wave_allocations if wave.wave in [WavePhase.WAVE_1, WavePhase.WAVE_2]]
        assert any(wave.critical_path for wave in early_waves)
        
        # Verify role allocation changes across waves
        wave_1_roles = {role.role_type for role in profile.wave_allocations[0].role_allocations}
        wave_4_roles = {role.role_type for role in profile.wave_allocations[-1].role_allocations}
        
        # First wave should emphasize architecture/planning
        assert RoleType.SECURITY_ARCHITECT in wave_1_roles or RoleType.PROJECT_MANAGER in wave_1_roles
        
        # Final wave should emphasize implementation/testing
        assert RoleType.SECURITY_ENGINEER in wave_4_roles or RoleType.COMPLIANCE_ANALYST in wave_4_roles
    
    def test_csv_export_content_validation(self):
        """Test CSV export content validation for UI integration"""
        # Create comprehensive test data
        skill = SkillRequirement(
            skill_name="Azure Security Center",
            skill_category="technical",
            required_level=SkillLevel.ADVANCED,
            critical=True
        )
        
        role = RoleProfile(
            role_type=RoleType.SECURITY_ARCHITECT,
            role_title="Senior Security Architect",
            fte_required=1.0,
            duration_weeks=12,
            skill_requirements=[skill],
            seniority_level="senior",
            hourly_rate_range={"min": 180, "max": 220}
        )
        
        wave = WaveResourceAllocation(
            wave=WavePhase.WAVE_1,
            wave_name="Wave 1: Architecture Design",
            start_date=date.today(),
            end_date=date.today() + timedelta(weeks=12),
            role_allocations=[role],
            estimated_cost=150000,
            critical_path=True
        )
        
        from app.api.schemas.resource_profile import InitiativeResourceProfile
        
        profile = InitiativeResourceProfile(
            initiative_id="csv-validation-001",
            initiative_name="CSV Validation Test",
            total_duration_weeks=12,
            wave_allocations=[wave],
            skill_summary={"technical": 1},
            total_fte_demand=1.0,
            total_estimated_cost=150000,
            resource_constraints=["Need senior security architect availability"]
        )
        
        # Test detailed export with all options
        request = CSVExportRequest(
            export_format="detailed",
            include_skills=True,
            include_costs=True
        )
        
        response = self.service.export_to_csv([profile], request)
        
        # Validate CSV structure and content
        lines = response.csv_content.strip().split('\n')
        headers = lines[0].split(',')
        data_row = lines[1].split(',')
        
        # Verify required headers are present
        required_headers = [
            "Initiative ID", "Initiative Name", "Wave", "Role Type", 
            "FTE Required", "Skills Required", "Wave Cost"
        ]
        for header in required_headers:
            assert any(header in h for h in headers), f"Missing header: {header}"
        
        # Verify data content
        assert "csv-validation-001" in response.csv_content
        assert "security_architect" in response.csv_content
        assert "Azure Security Center" in response.csv_content
        assert "150000" in response.csv_content
        assert "senior" in response.csv_content
    
    def test_gantt_chart_ui_totals_calculation(self):
        """Test Gantt chart data for UI totals calculation"""
        # Create multiple overlapping initiatives
        initiatives = []
        for i in range(3):
            role = RoleProfile(
                role_type=RoleType.SECURITY_ENGINEER,
                role_title="Security Engineer",
                fte_required=1.0,
                duration_weeks=8,
                skill_requirements=[],
                seniority_level="mid"
            )
            
            wave = WaveResourceAllocation(
                wave=WavePhase.WAVE_1,
                wave_name=f"Initiative {i+1} - Wave 1",
                start_date=date.today() + timedelta(weeks=i*4),  # Staggered starts
                end_date=date.today() + timedelta(weeks=i*4 + 8),
                role_allocations=[role],
                estimated_cost=80000
            )
            
            from app.api.schemas.resource_profile import InitiativeResourceProfile
            
            profile = InitiativeResourceProfile(
                initiative_id=f"gantt-ui-{i+1:03d}",
                initiative_name=f"UI Test Initiative {i+1}",
                total_duration_weeks=8,
                wave_allocations=[wave],
                skill_summary={"technical": 1},
                total_fte_demand=1.0,
                total_estimated_cost=80000
            )
            
            initiatives.append(profile)
        
        request = GanttChartRequest(
            include_resource_overlay=True,
            timeline_granularity="weekly"
        )
        
        response = self.service.generate_gantt_chart_data(initiatives, request)
        
        # Verify UI-relevant calculations
        assert len(response.tasks) == 6  # 3 initiatives + 3 waves
        assert "total_tasks" in response.resource_summary
        assert "role_utilization" in response.resource_summary
        assert "peak_fte_demand" in response.resource_summary
        
        # Verify overlapping period calculations
        security_engineer_demand = response.resource_summary["role_utilization"].get("security_engineer", 0)
        assert security_engineer_demand == 3.0  # 3 x 1.0 FTE
        
        # Verify timeline spans all initiatives
        timeline_days = (response.timeline_end - response.timeline_start).days
        assert timeline_days >= 56  # At least 8 weeks for longest spanning initiatives